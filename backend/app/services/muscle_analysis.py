"""肌群覆盖统计与薄弱部位建议；核心函数不依赖数据库，便于独立验证。"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

MUSCLE_GROUPS = ("胸", "背", "腿", "肩", "臂", "核心")
GOAL_FOCUS = {"whole_body": [], "glutes_legs": ["腿"], "shoulders_back": ["肩", "背"]}


def calculate_muscle_stats(entries: list[dict[str, Any]], period_start: date, period_end: date) -> list[dict[str, Any]]:
    sets_by_group = defaultdict(int)
    dates_by_group: dict[str, set[date]] = defaultdict(set)
    for entry in entries:
        group = entry.get("muscle_group")
        if group not in MUSCLE_GROUPS or entry.get("completion") == "skipped":
            continue
        sets_by_group[group] += max(0, int(entry.get("sets") or 0))
        if isinstance(entry.get("training_date"), date):
            dates_by_group[group].add(entry["training_date"])
    total_sets = sum(sets_by_group.values())
    return [{
        "muscle_group": group,
        "frequency": len(dates_by_group[group]),
        "total_sets": sets_by_group[group],
        "coverage_percent": round(sets_by_group[group] / total_sets * 100, 1) if total_sets else 0.0,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
    } for group in MUSCLE_GROUPS]


def identify_weak_parts(stats: list[dict[str, Any]], observed_days: int, focus_groups: list[str],
                        excluded_groups: list[str]) -> dict[str, Any]:
    if observed_days < 14:
        return {"status": "insufficient_data", "message": "训练记录不足 2 周，暂不判定薄弱部位。", "weak_groups": []}
    eligible = [row for row in stats if row["muscle_group"] not in set(focus_groups + excluded_groups)]
    total_sets = sum(row["total_sets"] for row in eligible)
    if total_sets == 0:
        return {"status": "insufficient_data", "message": "近 4 周缺少可统计的动作组数，暂不判定薄弱部位。", "weak_groups": []}
    mean_coverage = sum(row["coverage_percent"] for row in eligible) / max(1, len(eligible))
    observed_weeks = max(2.0, observed_days / 7)
    weak = []
    for row in eligible:
        weekly_sets = row["total_sets"] / observed_weeks
        low_share = row["coverage_percent"] < mean_coverage * 0.5
        below_floor = weekly_sets < 2 and row["frequency"] < max(2, int(observed_weeks))
        if low_share or below_floor:
            weak.append({**row, "weekly_sets": round(weekly_sets, 1),
                         "reason": f"近 {observed_days} 天共 {row['total_sets']} 组、{row['frequency']} 次，覆盖 {row['coverage_percent']}%；可比较部位均值为 {mean_coverage:.1f}%。"})
    return {"status": "ready", "message": "已按近 4 周动作记录统计；侧重和禁忌部位不参与薄弱判定。",
            "mean_coverage_percent": round(mean_coverage, 1), "weak_groups": weak}


def build_addition(group: str, stat: dict[str, Any], exercises: list[Any], plan_data: dict | None) -> dict[str, Any]:
    choices = [item for item in exercises if item.category == group][:2]
    sessions = list((plan_data or {}).get("sessions") or [])
    strength_sessions = [item for item in sessions if isinstance(item, dict) and item.get("focus") == "力量练习"] or sessions
    training_days = {item.get("weekday"): item for item in strength_sessions if isinstance(item.get("weekday"), int)}
    def conflict_score(item: dict) -> int:
        weekday = item.get("weekday")
        own = sum(1 for ex in item.get("exercises", []) if ex.get("category") == group)
        adjacent = sum(any(ex.get("category") == group for ex in training_days[day].get("exercises", []))
                       for day in (weekday - 1, weekday + 1) if isinstance(weekday, int) and day in training_days)
        return own + adjacent * 3
    target = min(strength_sessions, key=conflict_score, default=None)
    weekday = target.get("weekday") if target else None
    day_label = target.get("day") if target else "下次力量训练日"
    reps = "10–15 次" if group == "核心" else "8–12 次"
    return {
        "muscle_group": group,
        "evidence": stat["reason"],
        "exercises": [{"id": item.id, "name": item.name, "category": item.category,
                       "target_muscles": item.target_muscles} for item in choices],
        "prescription": f"选择其中 1–2 个动作，各 2 组 × {reps}，先保持中等用力程度。",
        "target_weekday": weekday,
        "target_day_label": day_label,
        "integration": f"建议加到{day_label}末尾；一次只增加这一处训练量，并与相邻训练日至少间隔一天观察恢复。",
    }
