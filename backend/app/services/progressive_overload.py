"""渐进超负荷规则。纯函数部分可脱离数据库单测。"""
from datetime import date, timedelta


def progression_recommendation(records: list[dict], experience: str, last_advice_date: date | None = None,
                               warning_symptom: str = "none") -> dict | None:
    if warning_symptom != "none":
        return None
    required = 2 if experience == "beginner" else 3
    cooldown = {"beginner": 7, "some_experience": 14, "experienced": 21}.get(experience, 14)
    if last_advice_date and date.today() - last_advice_date < timedelta(days=cooldown):
        return None
    recent = sorted(records, key=lambda row: row["training_date"], reverse=True)[:required]
    if len(recent) < required:
        return None
    weights = [round(float(row["weight_kg"]), 2) for row in recent]
    if max(weights) - min(weights) > 0.01:
        return None
    if not all(row["completion"] == "completed" and row["reps"] >= row["target_reps_min"] and row["rpe"] <= 8 for row in recent):
        return None
    latest = recent[0]
    evidence = []
    for row in recent:
        item = {key: row[key] for key in ("training_date", "sets", "reps", "weight_kg", "rpe")}
        if isinstance(item["training_date"], date):
            item["training_date"] = item["training_date"].isoformat()
        evidence.append(item)
    if latest["reps"] < latest["target_reps_max"]:
        next_reps = min(latest["target_reps_max"], latest["reps"] + 2)
        return {"advice_type": "reps", "prescription": {"sets": latest["sets"], "reps": next_reps, "weight_kg": latest["weight_kg"]},
                "evidence": evidence, "reason": "最近训练在相同重量下均达到目标且 RPE 不高于 8。按双进阶先提高次数，本次只调整次数。"}
    if latest["weight_kg"] > 0:
        rate = 0.05 if experience == "beginner" else 0.025
        next_weight = round(latest["weight_kg"] * (1 + rate) * 2) / 2
        if next_weight <= latest["weight_kg"]:
            next_weight = latest["weight_kg"] + 0.5
        return {"advice_type": "weight", "prescription": {"sets": latest["sets"], "reps": latest["target_reps_min"], "weight_kg": next_weight},
                "evidence": evidence, "reason": f"最近训练已在当前重量达到次数区间上限且 RPE 不高于 8。建议加重约 {int(rate * 100)}%，并回到较低次数，本次只调整重量。"}
    return {"advice_type": "sets", "prescription": {"sets": latest["sets"] + 1, "reps": latest["reps"], "weight_kg": 0},
            "evidence": evidence, "reason": "自重动作已连续达到次数区间上限。无法小幅加重时增加 1 组，本次只调整组数。"}

