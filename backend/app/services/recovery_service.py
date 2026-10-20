"""恢复状态与减载触发规则。"""


def assess_recovery(checkin: dict, performance_declined: bool) -> dict:
    symptom = checkin.get("warning_symptom", "none")
    if symptom != "none":
        return {"status": "stop", "message": "已记录关节疼痛、锐痛或肿胀。请停止引发不适的动作并休息；若症状明显、持续或加重，请及时寻求专业医疗帮助。", "allow_progression": False}
    if checkin.get("is_sick"):
        return {"status": "rest", "message": "今天记录了生病状态，建议暂停训练并优先休息，恢复后再评估。", "allow_progression": False}
    poor_sleep = checkin["sleep_hours"] < 6 or checkin["sleep_quality"] <= 2
    if checkin["soreness"] >= 4 and poor_sleep and performance_declined:
        return {"status": "insufficient", "message": "酸痛、睡眠和近期表现同时提示恢复不足。建议降低本周训练量或安排休息日。", "allow_progression": False}
    if checkin["soreness"] >= 4 or poor_sleep or checkin["energy"] <= 2:
        return {"status": "attention", "message": "有一项恢复指标偏低。下次训练先保持原计划，并根据热身感受决定是否减量。", "allow_progression": True}
    return {"status": "good", "message": "本次恢复指标整体平稳，可保持计划并继续观察。", "allow_progression": True}


def needs_deload(consecutive_training_weeks: int) -> bool:
    return consecutive_training_weeks >= 4

