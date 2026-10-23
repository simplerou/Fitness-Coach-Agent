"规则生成可确认草案；确认时校验归属、时效、源数据及目标计划是否变化。"
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy import select
from ..models.coach import CoachActionDraftRecord
from ..models.shaping_intelligence import DietDayAdjustmentRecord
from ..models.training_intelligence import PlanAdjustmentRecord
from ..models.training_plan import WeeklyPlanRecord
from .coach_data import CoachData
from .coach_plan import compute_plan_adjustment
from .nutrition_link import calculate_day_nutrition
from .plan_service import week_start_for

def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()

def prepare_diet(data: CoachData):
    if data.day != date.today():
        raise HTTPException(409, "教练只能生成今天的饮食目标草案，请切换到今天后重试。")
    if data.latest_stop():
        raise HTTPException(409, "最近恢复记录存在疼痛风险，请先咨询专业人士，暂不生成联动调整。")
    nutrition = data.diet()
    if nutrition["target_status"] != "ready":
        raise HTTPException(409, nutrition["target_message"] or "请先补全饮食规划档案。")
    plan = data.plan()
    schedule = plan["today_schedule"]
    if schedule["status"] not in {"training", "rest"}:
        raise HTTPException(409, "今日训练安排未明确，不能推断为休息日；请先完善周计划。")
    recovery = data.recovery(1)["records"]
    training = data.training(1)["logs"]
    kind = "recovery" if recovery and recovery[0]["status"] in {"insufficient", "stop"} else (
        "training" if schedule["status"] == "training" else "rest")
    intensity = ("high" if training and (training[-1]["rpe"] or 0) >= 8 else "regular") if kind == "training" else kind
    suggestion = calculate_day_nutrition(nutrition["target"], kind, intensity)
    current = data.db.get(DietDayAdjustmentRecord, (data.user_id, data.day))
    stored = {"status": current.status, "suggestion": current.suggestion} if current else None
    payload = {"date": data.day.isoformat(), "day_type": kind, "intensity": intensity, "suggestion": suggestion}
    return {"kind": "diet_target", "title": "采纳今日饮食参考目标", "summary": suggestion["reason"],
            "impact": "只设置今天的参考目标，基础饮食档案不变。",
            "details": [f"热量 {suggestion['calories_kcal']} kcal", f"蛋白质 {suggestion['protein_g']} g",
                        f"碳水 {suggestion['carbs_g']} g；脂肪 {suggestion['fat_g']} g", suggestion["calculation"]],
            "payload": payload, "fingerprint": fingerprint({"payload": payload, "plan": plan, "current": stored})}

def prepare_plan(data: CoachData):
    if data.day != date.today():
        raise HTTPException(409, "请切换到今天后生成下周调整草案；历史记录仅用于查看和复盘。")
    if data.latest_stop():
        raise HTTPException(409, "最近恢复记录存在疼痛风险，暂不生成训练调整建议，请先咨询专业人士。")
    source = week_start_for(data.day)
    target = source + timedelta(days=7)
    recommendation = compute_plan_adjustment(data.db, data.user_id, source, as_of=data.day)
    stats = recommendation["stats"]
    if stats["recovery_status"] == "unknown" or not data.training(7)["record_count"]:
        raise HTTPException(409, "训练或恢复样本不足，请补充记录后再生成调整草案。")
    if recommendation["kind"] == "hold":
        raise HTTPException(409, "本周存在疼痛或伤病记录，暂不输出训练调整方案。")
    existing = data.db.get(WeeklyPlanRecord, (data.user_id, target))
    original = data.db.get(WeeklyPlanRecord, (data.user_id, source))
    payload = {"source_week_start": source.isoformat(), "target_week_start": target.isoformat(),
               "recommendation": recommendation}
    return {"kind": "plan_adjustment", "title": "确认下周训练调整",
            "summary": "；".join(recommendation["reasons"]),
            "impact": f"将保存 {target.isoformat()} 起的整周计划。" + ("会覆盖已保存的下周计划。" if existing else "当前周和历史计划不变。"),
            "details": recommendation["changed"] + recommendation["unchanged"],
            "payload": payload, "fingerprint": fingerprint({"payload": payload,
                "source": original.plan_data if original else None, "target": existing.plan_data if existing else None})}

def public_action(row):
    data = row.draft_data
    return {"id": row.id, "kind": row.kind, "title": data["title"], "summary": data["summary"],
            "impact": data["impact"], "details": data["details"], "status": row.status,
            "target_date": data["payload"].get("date") or data["payload"].get("target_week_start")}

def save_drafts(db, user_id, proposals):
    result = []
    for proposal in proposals[:2]:
        row = CoachActionDraftRecord(user_id=user_id, kind=proposal["kind"], draft_data=proposal,
                                     source_fingerprint=proposal["fingerprint"], status="pending")
        db.add(row)
        db.flush()
        result.append(public_action(row))
    return result

def decide_action(db, user_id, action_id, decision):
    row = db.scalar(select(CoachActionDraftRecord).where(
        CoachActionDraftRecord.id == action_id, CoachActionDraftRecord.user_id == user_id).with_for_update())
    if row is None:
        raise HTTPException(404, "未找到这条教练调整草案。")
    if row.status == decision:
        return {"ok": True, "action": public_action(row), "message": "这条草案已经处理，无需重复提交。"}
    if row.status != "pending":
        raise HTTPException(409, "这条草案已经处理，请重新生成。")
    if decision == "ignored":
        row.status = "ignored"
        db.commit()
        return {"ok": True, "action": public_action(row), "message": "已取消草案，原有计划和目标未改变。"}
    created = row.created_at.replace(tzinfo=timezone.utc) if row.created_at.tzinfo is None else row.created_at
    if datetime.now(timezone.utc) - created > timedelta(minutes=15):
        raise HTTPException(409, "草案已超过15分钟，请根据最新数据重新生成。")
    payload = row.draft_data["payload"]
    day = date.fromisoformat(payload["date"]) if row.kind == "diet_target" else date.today()
    data = CoachData(db, user_id, day)
    # 串行化同账号草案确认，避免并发写入覆盖彼此。
    from ..models.user_profile import AccountUserRecord
    db.scalar(select(AccountUserRecord).where(AccountUserRecord.id == user_id).with_for_update())
    fresh = prepare_diet(data) if row.kind == "diet_target" else prepare_plan(data)
    if fresh["fingerprint"] != row.source_fingerprint:
        raise HTTPException(409, "计划、目标或相关记录已经变化，请重新生成草案后确认。")
    if row.kind == "diet_target":
        item = db.get(DietDayAdjustmentRecord, (user_id, day))
        if item is None:
            item = DietDayAdjustmentRecord(user_id=user_id, adjustment_date=day)
            db.add(item)
        item.day_type, item.intensity = payload["day_type"], payload["intensity"]
        item.suggestion, item.status = payload["suggestion"], "adopted"
        message = "已采纳为今天的参考目标，基础饮食设置没有改变。"
    elif row.kind == "plan_adjustment":
        target = date.fromisoformat(payload["target_week_start"])
        item = db.get(WeeklyPlanRecord, (user_id, target))
        if item is None:
            item = WeeklyPlanRecord(user_id=user_id, week_start=target)
            db.add(item)
        item.plan_data = payload["recommendation"]["proposed_plan"]
        db.add(PlanAdjustmentRecord(user_id=user_id, source_week_start=date.fromisoformat(payload["source_week_start"]),
            target_week_start=target, recommendation=payload["recommendation"], status="adopted", resolved_at=datetime.now(timezone.utc)))
        message = "下周计划已按确认的草案保存。"
    else:
        raise HTTPException(422, "不支持的教练草案类型。")
    db.flush()
    db.refresh(item)
    expected = payload["suggestion"] if row.kind == "diet_target" else payload["recommendation"]["proposed_plan"]
    actual = item.suggestion if row.kind == "diet_target" else item.plan_data
    if actual != expected:
        raise HTTPException(409, "保存结果与草案不一致，请重试。")
    row.status = "adopted"
    db.commit()
    return {"ok": True, "action": public_action(row), "message": message}
