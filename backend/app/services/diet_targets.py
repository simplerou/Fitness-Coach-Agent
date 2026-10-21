"""????????????"""
from __future__ import annotations


DIET_ACTIVITY_FACTORS = {
    "sedentary": 1.2, "light": 1.375, "moderate": 1.55,
    "active": 1.725, "very_active": 1.9,
}


DIET_ACTIVITY_LABELS = {
    "sedentary": "久坐为主", "light": "轻度活动", "moderate": "中等活动",
    "active": "活动较多", "very_active": "高活动量",
}


DIET_GOAL_LABELS = {
    "fat_loss": "减脂", "muscle_gain": "增肌", "maintain": "维持",
    "body_shape": "塑形", "performance": "提升运动表现",
}


def calculate_diet_targets(body, profile) -> dict:
    """按身体档案与饮食档案计算每日营养目标起点；不读取或写入历史计划。"""
    if body is None:
        return {"status": "needs_data", "missing": ["个人身体档案：身高和当前体重"], "message": "先填写身体档案，才能估算个性化营养目标。"}
    if body.age_band == "under_18" or (body.age_years is not None and body.age_years < 18):
        return {"status": "professional_support", "message": "青少年仍处于生长发育阶段，本工具不生成成人热量或宏量营养素目标；建议和监护人一起咨询医生或注册营养师。"}
    if profile is None:
        return {"status": "needs_data", "missing": ["饮食规划档案"], "message": "请补充饮食规划档案后生成个性化目标。"}

    missing = []
    if body.age_years is None: missing.append("身体档案中的准确年龄")
    if body.biological_sex not in ("female", "male"): missing.append("身体档案中的代谢估算性别")
    if not profile.goal: missing.append("健身目标")
    if not profile.activity_level: missing.append("日常活动水平")
    if not profile.health_reviewed: missing.append("健康约束确认")
    if not profile.allergies_reviewed: missing.append("过敏源与忌口确认")
    if missing:
        return {"status": "needs_data", "missing": missing, "message": "补充这些信息后，系统才能计算参考目标。"}
    if (profile.medical_conditions or "").strip() or (profile.injuries or "").strip():
        return {"status": "professional_support", "message": "档案中记录了疾病、孕期、进食障碍、伤病或其他健康情况。请咨询医生或注册营养师后再设定营养目标。"}

    height_m = body.height_cm / 100
    bmi = body.weight_kg / (height_m * height_m)
    sex_adjustment = 5 if body.biological_sex == "male" else -161
    bmr = 10 * body.weight_kg + 6.25 * body.height_cm - 5 * body.age_years + sex_adjustment
    bmr_source = "Mifflin–St Jeor 公式估算"
    factor = DIET_ACTIVITY_FACTORS[profile.activity_level]
    tdee = bmr * factor
    tdee_source = f"估算 BMR × 活动系数 {factor}（{DIET_ACTIVITY_LABELS[profile.activity_level]}）"
    if tdee < bmr:
        return {"status": "data_conflict", "message": "TDEE 低于 BMR，请核对测量值与活动水平。"}
    if profile.goal == "fat_loss" and bmi < 18.5:
        return {"status": "professional_support", "message": "成人 BMI 参考值低于 18.5，系统不会生成减脂目标。建议咨询医生或注册营养师。"}

    if profile.goal == "fat_loss":
        calorie_target = max(bmr, tdee * 0.9)
        target_note = "温和约 10% 能量缺口，并确保估算目标不低于 BMR"
    elif profile.goal == "muscle_gain":
        calorie_target = tdee * 1.05
        target_note = "以 TDEE 为基准增加约 5%，属于保守起点"
    else:
        calorie_target = tdee
        target_note = "以估算 TDEE 作为维持基线；塑形不自动等同于减脂"
    protein_raw = 1.6 * body.weight_kg
    protein = min(protein_raw, calorie_target * 0.35 / 4)
    fat = calorie_target * 0.25 / 9
    carbs = max(0, (calorie_target - protein * 4 - fat * 9) / 4)
    calorie_target = round(calorie_target)
    macro_targets = {"protein_g": round(protein), "carbs_g": round(carbs), "fat_g": round(fat)}
    basis = f"{target_note}；蛋白质按约 1.6 克/公斤体重估算（若超过目标能量的 35% 则限制显示）；脂肪约占能量 25%，剩余能量分配给碳水。"
    return {
        "status": "ready",
        "summary": {
            "height_cm": body.height_cm, "weight_kg": body.weight_kg,
            "bmi": round(bmi, 1), "bmr_kcal": round(bmr), "bmr_source": bmr_source,
            "tdee_kcal": round(tdee), "tdee_source": tdee_source,
            "goal": DIET_GOAL_LABELS[profile.goal], "activity_level": DIET_ACTIVITY_LABELS[profile.activity_level],
        },
        "target": {
            "calories_kcal": calorie_target, **macro_targets,
            "protein_percent": round(macro_targets["protein_g"] * 4 / calorie_target * 100),
            "carbs_percent": round(macro_targets["carbs_g"] * 4 / calorie_target * 100),
            "fat_percent": round(macro_targets["fat_g"] * 9 / calorie_target * 100),
            "basis": basis,
        },
        "warnings": (["按体重计算的蛋白质目标超过目标能量的 35%，已限制显示；可咨询注册营养师评估。"] if protein < protein_raw else []),
        "calculation": {"target_note": target_note, "protein_was_capped": protein < protein_raw},
    }
