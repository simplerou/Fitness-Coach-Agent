# 数据库模块：管理 PostgreSQL 连接、ORM 表结构、租户迁移和用户初始化。
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("未设置 DATABASE_URL。请复制 .env.example 为 .env，并填写本机 PostgreSQL 连接信息。")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

from .models.base import Base
from .models.user_profile import AccountUserRecord, LocalProfileRecord, BodyProfileRecord, BodyWeightHistoryRecord
from .models.daily_signal import DailySignalRecord
from .models.training_log import TrainingLogRecord
from .models.training_plan import WeeklyPlanRecord, TrainingPreferencesRecord, TrainingSchedulePreferencesRecord
from .models.safety_hold import LocalSafetyStateRecord
from .models.diet import DietMealRecord, DietProfileRecord, DietDayReviewRecord, DietPlanSnapshotRecord, DailyWaterRecord

DEFAULT_TRAINING_WEEKDAYS_BY_COUNT = {
    1: [1], 2: [1, 4], 3: [1, 3, 5], 4: [1, 2, 4, 6],
    5: [1, 2, 3, 5, 6], 6: [1, 2, 3, 4, 5, 6],
}

TENANT_TABLES = (
    "daily_signals", "training_logs", "local_profiles", "body_profiles",
    "body_weight_history", "weekly_plans", "training_preferences",
    "training_schedule_preferences", "local_safety_state", "diet_meals", "daily_water_intakes",
    "diet_profiles", "diet_day_reviews", "diet_plan_snapshots",
    "training_exercise_entries", "recovery_checkins", "exercise_advice", "plan_adjustments",
    "shaping_intelligence_preferences", "muscle_group_stats", "weak_part_advice", "qa_log",
    "diet_day_adjustment", "report_snapshot",
)

def initialize_database() -> None:
    """建表并为旧版单用户表预留账号归属列；实际归属在首个注册时迁移。"""
    from .models import coach as _coach_models  # noqa: F401
    # 显式导入扩展模型，确保直接调用初始化函数时也注册全部表。
    from .models import shaping as _shaping_models  # noqa: F401
    from .models import shaping_intelligence as _shaping_intelligence_models  # noqa: F401
    from .models import training_intelligence as _training_models  # noqa: F401
    from .services.exercise_library import ensure_exercise_seed
    from .services.exercise_knowledge import ensure_knowledge_seed

    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        for table_name in TENANT_TABLES:
            connection.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS user_id INTEGER'))
        connection.execute(text('ALTER TABLE local_safety_state ADD COLUMN IF NOT EXISTS hold_date DATE'))
        connection.execute(text('ALTER TABLE body_profiles ADD COLUMN IF NOT EXISTS target_weight_kg FLOAT'))
        connection.execute(text('ALTER TABLE body_profiles ADD COLUMN IF NOT EXISTS age_years INTEGER'))
        connection.execute(text('ALTER TABLE body_profiles ADD COLUMN IF NOT EXISTS biological_sex VARCHAR(16)'))
        # Move demographic values users already entered in the diet form into their body profile.
        connection.execute(text(
            'UPDATE body_profiles AS body SET '
            'age_years = COALESCE(body.age_years, diet.age_years), '
            'biological_sex = COALESCE(body.biological_sex, diet.biological_sex) '
            'FROM diet_profiles AS diet WHERE body.user_id = diet.user_id'
        ))
        connection.execute(text(
            "UPDATE body_profiles SET age_band = CASE "
            "WHEN age_years < 18 THEN 'under_18' WHEN age_years < 30 THEN '18_29' "
            "WHEN age_years < 45 THEN '30_44' WHEN age_years < 60 THEN '45_59' "
            "ELSE '60_plus' END WHERE age_years IS NOT NULL"
        ))
        connection.execute(text('ALTER TABLE training_logs ADD COLUMN IF NOT EXISTS planned_session_title VARCHAR(120)'))
        connection.execute(text("ALTER TABLE training_preferences ADD COLUMN IF NOT EXISTS preferred_exercise_ids JSON NOT NULL DEFAULT '[]'"))
        connection.execute(text("ALTER TABLE exercise_library ADD COLUMN IF NOT EXISTS demo_images JSON NOT NULL DEFAULT '[]'"))
        connection.execute(text('ALTER TABLE exercise_library ADD COLUMN IF NOT EXISTS demo_video_url TEXT'))
        connection.execute(text('ALTER TABLE exercise_library ADD COLUMN IF NOT EXISTS media_credit VARCHAR(160)'))
        connection.execute(text('ALTER TABLE exercise_library ADD COLUMN IF NOT EXISTS media_license VARCHAR(80)'))
        connection.execute(text('ALTER TABLE exercise_library ADD COLUMN IF NOT EXISTS media_source_url TEXT'))
        connection.execute(text('ALTER TABLE diet_profiles ADD COLUMN IF NOT EXISTS injuries TEXT'))
        connection.execute(text('ALTER TABLE diet_profiles ADD COLUMN IF NOT EXISTS allergies_reviewed BOOLEAN NOT NULL DEFAULT FALSE'))
        connection.execute(text('ALTER TABLE diet_profiles ADD COLUMN IF NOT EXISTS training_end_time VARCHAR(5)'))
        connection.execute(text('ALTER TABLE diet_profiles ADD COLUMN IF NOT EXISTS water_target_ml INTEGER'))
        for column, sql_type in (
            ("portion", "VARCHAR(120)"), ("eaten_at", "VARCHAR(5)"),
            ("calories_kcal", "FLOAT"), ("protein_g", "FLOAT"),
            ("carbs_g", "FLOAT"), ("fat_g", "FLOAT"),
            ("nutrition_source", "VARCHAR(16)"),
        ):
            connection.execute(text(f'ALTER TABLE diet_meals ADD COLUMN IF NOT EXISTS "{column}" {sql_type}'))
        connection.execute(text(
            'UPDATE local_safety_state SET hold_date = CURRENT_DATE '
            'WHERE hold_active = TRUE AND hold_date IS NULL'
        ))
    with SessionLocal() as db:
        ensure_exercise_seed(db)
        ensure_knowledge_seed(db)
        db.commit()

def claim_legacy_data_for_first_user(db, user_id: int) -> None:
    """首个注册账号继承旧版单用户数据，并将日期键改为账号复合键。"""
    for table_name in TENANT_TABLES:
        db.execute(text(f'UPDATE "{table_name}" SET user_id = :user_id WHERE user_id IS NULL'), {"user_id": user_id})

    date_key_tables = {
        "daily_signals": "signal_date",
        "body_weight_history": "recorded_on",
        "weekly_plans": "week_start",
    }
    for table_name, date_column in date_key_tables.items():
        db.execute(text(f'ALTER TABLE "{table_name}" DROP CONSTRAINT IF EXISTS "{table_name}_pkey"'))
        db.execute(text(
            f'ALTER TABLE "{table_name}" ADD CONSTRAINT "{table_name}_pkey" PRIMARY KEY (user_id, "{date_column}")'
        ))

    for table_name in TENANT_TABLES:
        db.execute(text(f'ALTER TABLE "{table_name}" ALTER COLUMN user_id SET NOT NULL'))
        constraint_name = f'{table_name}_user_id_fkey'
        exists = db.scalar(text('SELECT 1 FROM pg_constraint WHERE conname = :name'), {"name": constraint_name})
        if not exists:
            db.execute(text(
                f'ALTER TABLE "{table_name}" ADD CONSTRAINT "{constraint_name}" '
                'FOREIGN KEY (user_id) REFERENCES account_users(id) ON DELETE CASCADE'
            ))

    for table_name in (
        "local_profiles", "body_profiles", "training_preferences",
        "training_schedule_preferences", "local_safety_state",
    ):
        db.execute(text(f'CREATE UNIQUE INDEX IF NOT EXISTS "uq_{table_name}_user_id" ON "{table_name}" (user_id)'))
    db.execute(text('CREATE INDEX IF NOT EXISTS "ix_training_logs_user_date" ON training_logs (user_id, training_date)'))
    # 老版单例曾显式写入 id=1，推进自增序列，避免第二个账号的默认行撞主键。
    for table_name in ("local_profiles", "body_profiles", "training_preferences", "training_schedule_preferences", "local_safety_state"):
        db.execute(text(
            f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), "
            f"GREATEST(COALESCE((SELECT MAX(id) FROM {table_name}), 1), 1), "
            f"EXISTS(SELECT 1 FROM {table_name}))"
        ))

def initialize_user_defaults(db, user_id: int, registered_on: date) -> None:
    """为新账号创建独立起始日期、安全状态和训练偏好。"""
    local_profile = db.scalar(select(LocalProfileRecord).where(LocalProfileRecord.user_id == user_id))
    if local_profile is None:
        db.add(LocalProfileRecord(user_id=user_id, registered_on=registered_on))

    safety_state = db.scalar(select(LocalSafetyStateRecord).where(LocalSafetyStateRecord.user_id == user_id))
    if safety_state is None:
        db.add(LocalSafetyStateRecord(user_id=user_id, hold_active=False, hold_requires_professional_confirmation=False, hold_date=None))

    preferences = db.scalar(select(TrainingPreferencesRecord).where(TrainingPreferencesRecord.user_id == user_id))
    if preferences is None:
        preferences = TrainingPreferencesRecord(
            user_id=user_id, goal="fitness", days_per_week=3,
            experience_level="beginner", equipment=["bodyweight_only"], session_minutes=30,
            preferred_exercise_ids=[],
        )
        db.add(preferences)
        db.flush()

    schedule = db.scalar(select(TrainingSchedulePreferencesRecord).where(TrainingSchedulePreferencesRecord.user_id == user_id))
    if schedule is None:
        days = preferences.days_per_week
        db.add(TrainingSchedulePreferencesRecord(
            user_id=user_id, weekdays=DEFAULT_TRAINING_WEEKDAYS_BY_COUNT.get(days, [1, 3, 5]),
        ))
