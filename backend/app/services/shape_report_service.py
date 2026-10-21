"""周/月塑型报告聚合；所有结论都保留数据来源与样本数量。"""
from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select

from ..database import BodyWeightHistoryRecord, TrainingLogRecord
from ..models.shaping import ShapeMeasurementRecord, ShapeTargetRecord
from ..models.shaping_intelligence import WeakPartAdviceRecord
from ..models.training_intelligence import ExerciseAdviceRecord, ExerciseLibraryRecord, RecoveryCheckinRecord, TrainingExerciseEntryRecord
from .shaping_service import LABELS, METRICS


def completed_period(period_type: str, anchor: date) -> tuple[date, date]:
    if period_type == "week":
        this_monday = anchor - timedelta(days=anchor.weekday())
        return this_monday - timedelta(days=7), this_monday - timedelta(days=1)
    first = anchor.replace(day=1)
    previous_end = first - timedelta(days=1)
    return previous_end.replace(day=1), previous_end


def previous_period(period_type: str, start: date, end: date) -> tuple[date, date]:
    if period_type == "week": return start - timedelta(days=7), end - timedelta(days=7)
    previous_end = start - timedelta(days=1)
    return previous_end.replace(day=1), previous_end


def _round(value: float | None, digits: int = 1) -> float | None:
    return round(value, digits) if value is not None else None


def build_shape_report(db, user_id: int, period_type: str, start: date, end: date) -> dict[str, Any]:
    previous_start, previous_end = previous_period(period_type, start, end)
    measurements = db.scalars(select(ShapeMeasurementRecord).where(
        ShapeMeasurementRecord.user_id == user_id,
        ShapeMeasurementRecord.recorded_on >= previous_start,
        ShapeMeasurementRecord.recorded_on <= end,
    ).order_by(ShapeMeasurementRecord.recorded_on)).all()
    current_measurements = [row for row in measurements if start <= row.recorded_on <= end]
    previous_measurements = [row for row in measurements if previous_start <= row.recorded_on <= previous_end]

    changes = []
    for metric in METRICS:
        current = next((row for row in reversed(current_measurements) if getattr(row, metric) is not None), None)
        previous = next((row for row in reversed(previous_measurements) if getattr(row, metric) is not None), None)
        current_value = getattr(current, metric) if current else None
        previous_value = getattr(previous, metric) if previous else None
        changes.append({"metric": metric, "label": LABELS[metric], "current": current_value,
                        "previous": previous_value,
                        "change": _round(current_value - previous_value) if current_value is not None and previous_value is not None else None,
                        "measurement_count": sum(getattr(row, metric) is not None for row in current_measurements),
                        "current_date": current.recorded_on.isoformat() if current else None,
                        "previous_date": previous.recorded_on.isoformat() if previous else None})

    logs = db.scalars(select(TrainingLogRecord).where(TrainingLogRecord.user_id == user_id,
        TrainingLogRecord.training_date >= start, TrainingLogRecord.training_date <= end)).all()
    log_ids = [row.id for row in logs]
    entries = db.scalars(select(TrainingExerciseEntryRecord).where(
        TrainingExerciseEntryRecord.user_id == user_id,
        TrainingExerciseEntryRecord.log_id.in_(log_ids))).all() if log_ids else []
    active_logs = [row for row in logs if row.completion in ("completed", "partial")]
    completion_rate = round(sum(row.completion == "completed" for row in logs) / len(logs) * 100, 1) if logs else None

    recoveries = db.scalars(select(RecoveryCheckinRecord).where(RecoveryCheckinRecord.user_id == user_id,
        RecoveryCheckinRecord.checkin_date >= start, RecoveryCheckinRecord.checkin_date <= end)).all()
    average = lambda values: _round(sum(values) / len(values)) if values else None

    advice_rows = db.execute(select(ExerciseAdviceRecord, ExerciseLibraryRecord.name).join(
        ExerciseLibraryRecord, ExerciseLibraryRecord.id == ExerciseAdviceRecord.exercise_id).join(
        TrainingLogRecord, TrainingLogRecord.id == ExerciseAdviceRecord.log_id).where(
        ExerciseAdviceRecord.user_id == user_id, TrainingLogRecord.training_date >= start,
        TrainingLogRecord.training_date <= end)).all()
    highlights = [{"exercise": exercise_name, "type": advice.advice_type,
                   "status": advice.status, "reason": advice.reason} for advice, exercise_name in advice_rows[:6]]

    targets = db.scalars(select(ShapeTargetRecord).where(ShapeTargetRecord.user_id == user_id)).all()
    milestones = [{"metric": row.metric, "label": LABELS.get(row.metric, row.metric), "milestones": row.milestones}
                  for row in targets if row.milestones]
    weak_rows = db.scalars(select(WeakPartAdviceRecord).where(WeakPartAdviceRecord.user_id == user_id,
        WeakPartAdviceRecord.period_end <= end).order_by(WeakPartAdviceRecord.period_end.desc()).limit(6)).all()
    weak_progress = [{"muscle_group": row.muscle_group, "status": row.status,
                      "evidence": row.advice_data.get("evidence"), "integration": row.advice_data.get("integration")}
                     for row in weak_rows]

    weights = db.scalars(select(BodyWeightHistoryRecord).where(BodyWeightHistoryRecord.user_id == user_id,
        BodyWeightHistoryRecord.recorded_on >= previous_start, BodyWeightHistoryRecord.recorded_on <= end)
        .order_by(BodyWeightHistoryRecord.recorded_on)).all()
    current_weights = [row for row in weights if start <= row.recorded_on <= end]
    previous_weights = [row for row in weights if previous_start <= row.recorded_on <= previous_end]
    weight_change = None
    if current_weights and previous_weights:
        weight_change = _round(current_weights[-1].weight_kg - previous_weights[-1].weight_kg)

    enough_shape_data = len(current_measurements) >= 1 and len(previous_measurements) >= 1
    enough_training_data = len(logs) >= (2 if period_type == "week" else 4)
    notes = []
    if not enough_shape_data: notes.append("围度或体成分数据样本不足，暂不判断变化趋势。")
    if not enough_training_data: notes.append("训练记录样本不足，训练量仅作记录汇总。")
    if not recoveries: notes.append("本周期没有恢复打卡，无法汇总酸痛和睡眠情况。")
    return {
        "period_type": period_type, "period_start": start.isoformat(), "period_end": end.isoformat(),
        "sample_status": "sufficient" if enough_shape_data and enough_training_data else "insufficient",
        "data_notes": notes,
        "measurements": {"changes": changes, "record_count": len(current_measurements),
            "trend": [{"date": row.recorded_on.isoformat(), **{key: getattr(row, key) for key in METRICS}} for row in current_measurements],
            "source": "用户手动记录的围度与体成分；环比取本周期和上一周期各自最后一次有效读数。"},
        "weight": {"change_kg": weight_change, "record_count": len(current_weights),
                   "source": "用户身体档案中的体重历史；缺少相邻周期记录时不计算变化。"},
        "training": {"training_days": len({row.training_date for row in active_logs}),
            "log_count": len(logs), "total_sets": sum(row.sets for row in entries),
            "total_reps": sum(row.sets * row.reps for row in entries), "completion_rate": completion_rate,
            "source": "训练记录与动作级组次；完成率为已完整完成记录数 ÷ 本周期全部训练记录数。"},
        "performance": {"highlights": highlights, "milestones": milestones,
                        "source": "渐进超负荷建议与已保存的塑型目标里程碑。"},
        "recovery": {"checkin_count": len(recoveries), "average_soreness": average([row.soreness for row in recoveries]),
            "average_sleep_hours": average([row.sleep_hours for row in recoveries]),
            "insufficient_days": sum(row.status in ("insufficient", "stop") for row in recoveries),
            "source": "训练后恢复打卡；未打卡日期不推断为恢复正常。"},
        "weak_part_progress": weak_progress,
        "next_actions": (["继续按相同测量条件记录，积累至少两个周期后再比较。"] if not enough_shape_data else []) +
                        (["继续记录动作组次和恢复状态，让下周期建议有足够依据。"] if not enough_training_data else
                         ["结合薄弱部位卡与恢复状态，只选择一项调整用于下一周期。"]),
    }
