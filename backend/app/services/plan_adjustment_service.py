"""周计划自适应规则；只生成预览，不直接写入计划。"""
from copy import deepcopy


def build_adjustment(plan: dict, stats: dict) -> dict:
    proposed = deepcopy(plan)
    completion_rate = stats.get("completion_rate", 0)
    avg_rpe = stats.get("average_rpe")
    recovery = stats.get("recovery_status", "unknown")
    injured = stats.get("has_warning_symptom", False)
    stalled = stats.get("progressed_exercises", 0) == 0 and stats.get("tracked_exercises", 0) > 0
    changed: list[str] = []
    reasons: list[str] = []
    kind = "maintain"
    if injured:
        kind = "hold"
        reasons.append("本周记录了关节疼痛、锐痛或肿胀，因此不生成加量建议。")
    elif stats.get("consecutive_training_weeks", 0) >= 4 and (recovery in {"insufficient", "attention"} or (avg_rpe or 0) >= 8):
        kind = "deload"
        for session in proposed.get("sessions", []):
            session["deload"] = True
            session["volume_multiplier"] = 0.5
            session["description"] = "减载周：动作保持不变，组数或训练强度降低约一半。" + session.get("description", "")
        changed.append("下周设为减载周：动作不变，组数或强度降低约一半")
        reasons.append("已连续训练至少 4 周，且恢复或用力指标提示需要降低累积疲劳。")
    elif completion_rate < 0.6 or recovery == "insufficient":
        kind = "reduce"
        old = int(proposed.get("session_minutes", 30))
        new = {60: 45, 45: 30, 30: 20}.get(old, old)
        proposed["session_minutes"] = new
        for session in proposed.get("sessions", []):
            session["duration_minutes"] = new
        changed.append(f"单次训练时长由约 {old} 分钟调整为约 {new} 分钟" if new != old else "保持当前最低时长，不再减量")
        reasons.append("本周完成率偏低或恢复不足，先降低执行负担并继续观察原因。")
    elif completion_rate >= 0.8 and recovery == "good" and (avg_rpe is None or avg_rpe <= 8):
        kind = "slight_increase"
        changed.append("保持训练日与动作，每个动作可按已采纳的进阶建议小幅调整一个变量")
        reasons.append("本周完成率较高且恢复良好，适合小幅、单变量进阶。")
    elif stalled:
        kind = "variation"
        replacement = stats.get("replacement")
        if replacement:
            for session in proposed.get("sessions", []):
                session["exercises"] = [replacement["to"] if item.get("id") == replacement["from"]["id"] else item
                                        for item in session.get("exercises", [])]
            changed.append(f"将 {replacement['from']['name']} 替换为同部位的 {replacement['to']['name']}")
            reasons.append("目标动作本周未见进阶，替换为相同目标部位且符合器械或动作偏好的变式。")
        else:
            changed.append("暂不替换动作，保留当前组次安排")
            reasons.append("目标动作本周未见进阶，但动作偏好和器械范围内没有合适的同部位替代项。")
    else:
        reasons.append("现有完成率、RPE 与恢复数据暂不支持明显调整。")
    return {"kind": kind, "changed": changed or ["下周沿用当前计划"], "reasons": reasons,
            "unchanged": ["训练目标不变", "用户选择的训练星期不变", "目标肌群与可用器械不变"], "proposed_plan": proposed, "stats": stats}

