"""训练日与休息日营养目标联动；只生成候选值，不修改饮食档案。"""
from typing import Any


def calculate_day_nutrition(base: dict[str, Any], day_type: str, intensity: str) -> dict[str, Any]:
    calories = int(base["calories_kcal"])
    protein = int(base["protein_g"])
    fat = int(base["fat_g"])
    if day_type == "training":
        increment = 200 if intensity == "high" else 100 if intensity == "regular" else 0
        calories += increment
        if intensity == "high":
            protein += 5
        reason = (f"今天是{'高强度' if intensity == 'high' else '常规'}训练日，在基础目标上增加约 {increment} kcal，"
                  "主要留给训练相关碳水；蛋白质保持稳定或小幅增加。")
    elif day_type == "recovery":
        reason = "今天的恢复记录提示需要放慢节奏，因此维持基础能量与蛋白质目标，不额外增加训练日能量。"
    else:
        reason = "今天是计划休息日，能量回到基础目标，蛋白质维持，碳水随总能量回落。"
    carbs = max(0, round((calories - protein * 4 - fat * 9) / 4))
    return {"calories_kcal": calories, "protein_g": protein, "carbs_g": carbs, "fat_g": fat,
            "basis_calories_kcal": int(base["calories_kcal"]), "reason": reason,
            "calculation": "训练日按强度增加 0/100/200 kcal；蛋白质沿用基础目标，高强度日增加 5g；脂肪保持，剩余能量分配给碳水。"}
