"""Aggregate recorded meals, hydration and training into a diet planning review."""
from __future__ import annotations


def build_record_analysis(meals, reviews, water_records, training_logs, profile, bmr, calorie_target, macro_targets, protein_was_capped):
    complete_dates = {row.log_date for row in reviews}
    by_day = {}
    discrepancies = []
    for meal in meals:
        day = by_day.setdefault(meal.log_date, {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0,
                                                "kcal_complete": True, "protein_complete": True,
                                                "carbs_complete": True, "fat_complete": True, "count": 0})
        day["count"] += 1
        macros_complete = all(value is not None for value in (meal.protein_g, meal.carbs_g, meal.fat_g))
        derived_kcal = (meal.protein_g * 4 + meal.carbs_g * 4 + meal.fat_g * 9) if macros_complete else None
        kcal = meal.calories_kcal if meal.calories_kcal is not None else derived_kcal
        if kcal is None: day["kcal_complete"] = False
        else: day["calories"] += kcal
        for key, value in (("protein", meal.protein_g), ("carbs", meal.carbs_g), ("fat", meal.fat_g)):
            if value is None: day[key + "_complete"] = False
            else: day[key] += value
        if meal.calories_kcal is not None and derived_kcal is not None and max(meal.calories_kcal, derived_kcal) > 0:
            if abs(meal.calories_kcal - derived_kcal) / max(meal.calories_kcal, derived_kcal) > 0.25:
                discrepancies.append(meal.log_date.isoformat())
    tracked_days = [by_day[d] for d in complete_dates if d in by_day]
    averages = {}
    metric_day_counts = {}
    for key, complete_key in (
        ("calories", "kcal_complete"), ("protein", "protein_complete"),
        ("carbs", "carbs_complete"), ("fat", "fat_complete"),
    ):
        values = [day[key] for day in tracked_days if day[complete_key]]
        metric_day_counts[key] = len(values)
        averages[key] = round(sum(values) / len(values)) if len(values) >= 3 else None
    actual_training_dates = {record.training_date for record in training_logs}
    training_values = [by_day[d]["carbs"] for d in complete_dates
                       if d in by_day and d in actual_training_dates and by_day[d]["carbs_complete"]]
    rest_values = [by_day[d]["carbs"] for d in complete_dates
                   if d in by_day and d not in actual_training_dates and by_day[d]["carbs_complete"]]
    training_day_comparison = {
        "training_days_with_data": len(training_values),
        "rest_days_with_data": len(rest_values),
        "training_day_carbs_g": round(sum(training_values) / len(training_values)) if training_values else None,
        "rest_day_carbs_g": round(sum(rest_values) / len(rest_values)) if rest_values else None,
    }
    meal_counts = {label: sum(1 for meal in meals if meal.meal_type == key)
                   for key, label in (("breakfast", "早餐"), ("lunch", "午餐"), ("dinner", "晚餐"), ("snack", "加餐"))}
    meal_description_counts = {}
    for meal in meals:
        normalized = " ".join(meal.description.split())
        if normalized:
            meal_description_counts[normalized] = meal_description_counts.get(normalized, 0) + 1
    common_meals = [
        {"description": label, "count": count}
        for label, count in sorted(meal_description_counts.items(), key=lambda item: (-item[1], item[0]))
        if count >= 2
    ][:3]
    meal_distribution = {
        "counts": meal_counts,
        "timed_meals": sum(1 for meal in meals if meal.eaten_at),
        "meals_with_portion": sum(1 for meal in meals if meal.portion),
        "repeated_meals": common_meals,
    }
    training_timing_review = {"training_days_with_complete_logs": 0, "days_with_meal_time_data": 0,
                              "days_last_meal_over_4h_before_training": 0}
    if profile.training_time:
        training_minute = int(profile.training_time[:2]) * 60 + int(profile.training_time[3:])
        for day_date in complete_dates.intersection(actual_training_dates):
            day_meals = [meal for meal in meals if meal.log_date == day_date and meal.eaten_at]
            if not day_meals:
                continue
            training_timing_review["training_days_with_complete_logs"] += 1
            training_timing_review["days_with_meal_time_data"] += 1
            meal_minutes = [int(meal.eaten_at[:2]) * 60 + int(meal.eaten_at[3:]) for meal in day_meals]
            earlier_meals = [minute for minute in meal_minutes if minute <= training_minute]
            if earlier_meals and training_minute - max(earlier_meals) > 240:
                training_timing_review["days_last_meal_over_4h_before_training"] += 1

    water_by_day = {record.log_date: record.amount_ml for record in water_records}
    hydration_summary = {
        "days_logged": len(water_by_day),
        "total_ml": sum(water_by_day.values()) if water_by_day else None,
        "average_on_logged_days_ml": round(sum(water_by_day.values()) / len(water_by_day)) if water_by_day else None,
    }
    coverage = {
        "window_days": 7,
        "days_marked_complete": len(complete_dates),
        "days_with_meals": len(by_day),
        "water_days_logged": hydration_summary["days_logged"],
        "days_with_complete_nutrition": sum(1 for day in tracked_days if day["kcal_complete"] and day["protein_complete"] and day["carbs_complete"] and day["fat_complete"]),
        "days_with_each_metric": metric_day_counts,
        "nutrition_source": "用户录入的包装标签或估算值；未补营养数据的餐次不会按零计算",
    }
    diagnosis = []
    warnings = []
    if hydration_summary["days_logged"]:
        diagnosis.append(
            f"近 7 天记录饮水 {hydration_summary['days_logged']} 天，累计 {hydration_summary['total_ml']} 毫升；有记录日均约 "
            f"{hydration_summary['average_on_logged_days_ml']} 毫升。未记录日期不按 0 计算。"
        )
    else:
        diagnosis.append("近 7 天没有饮水量记录，暂时无法回顾饮水情况；可按需记录实际饮水量。")
    if profile.water_target_ml is not None:
        diagnosis.append(f"你设置的日常饮水参考值为 {profile.water_target_ml} 毫升；饮水记录仅用于个人回顾，记录不足时不据此判断是否缺水。")
    else:
        diagnosis.append("尚未设置个人饮水参考值；饮水数据只作记录回顾，不推断是否达标或缺水。")
    if len(complete_dates) < 3:
        diagnosis.append("最近 7 天标记为完整的饮食记录少于 3 天，暂不根据记录计算日均差距；继续记录后再看趋势。")
    else:
        if averages["calories"] is None:
            diagnosis.append("完整日的能量信息仍不齐，暂时不能比较实际能量与目标。")
        elif averages["calories"] < bmr:
            warnings.append(f"最近完整记录日的平均摄入约 {averages['calories']} 千卡，低于估算 BMR {round(bmr)} 千卡。记录可能有漏项；若持续如此或正在刻意限制饮食，请优先保证健康并咨询专业人士。")
        else:
            diagnosis.append(f"完整记录日的平均能量约 {averages['calories']} 千卡，与目标 {calorie_target} 千卡相差约 {round(averages['calories']-calorie_target):+} 千卡。")
        if averages["protein"] is not None:
            diagnosis.append(f"完整记录日蛋白质日均约 {averages['protein']} 克，目标约 {macro_targets['protein_g']} 克，差约 {round(averages['protein']-macro_targets['protein_g']):+} 克。")
        else:
            diagnosis.append("蛋白质数据不完整，暂不判断是否达到目标。")
    if discrepancies:
        warnings.append("部分餐次的标注热量与按蛋白质/碳水/脂肪（4/4/9 千卡/克）推算值相差超过 25%；请核对份量或标签。")
    if protein_was_capped:
        warnings.append("按体重计算的蛋白质目标会超过目标能量的 35%，为避免宏量比例失衡已限制显示值；请让注册营养师结合体成分个别化评估。")
    if training_values and rest_values:
        training_day_comparison["carb_difference_g"] = round(training_day_comparison["training_day_carbs_g"] - training_day_comparison["rest_day_carbs_g"])
        diagnosis.append(f"已记录训练日碳水日均约 {training_day_comparison['training_day_carbs_g']} 克、休息日约 {training_day_comparison['rest_day_carbs_g']} 克（分别 {len(training_values)} 天与 {len(rest_values)} 天完整数据）；此差异仅描述记录，不代表优劣。")
    elif actual_training_dates:
        diagnosis.append("最近 7 天有训练记录，但训练日与休息日的完整碳水数据不足，暂不比较两类日期。")
    if profile.allergies or profile.avoid_foods:
        warnings.append("食物示例需由你逐项核对过敏原和忌口；文字匹配不能替代标签检查。")

    return (averages, coverage, meal_distribution, hydration_summary,
            training_day_comparison, training_timing_review, diagnosis, warnings)
