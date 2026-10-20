-- 训练智能闭环迁移。应用启动时 SQLAlchemy create_all 也会创建这些表；本文件用于正式迁移审阅。
ALTER TABLE training_preferences ADD COLUMN IF NOT EXISTS preferred_exercise_ids JSON NOT NULL DEFAULT '[]';
CREATE TABLE IF NOT EXISTS exercise_library (
  id SERIAL PRIMARY KEY, slug VARCHAR(64) NOT NULL UNIQUE, name VARCHAR(80) NOT NULL,
  category VARCHAR(24) NOT NULL, target_muscles JSON NOT NULL, equipment JSON NOT NULL,
  cues JSON NOT NULL, common_errors JSON NOT NULL, regressions JSON NOT NULL,
  progressions JSON NOT NULL, alternatives JSON NOT NULL,
  demo_images JSON NOT NULL DEFAULT '[]', demo_video_url TEXT,
  media_credit VARCHAR(160), media_license VARCHAR(80), media_source_url TEXT,
  is_seed BOOLEAN NOT NULL DEFAULT TRUE
);
ALTER TABLE exercise_library ADD COLUMN IF NOT EXISTS demo_images JSON NOT NULL DEFAULT '[]';
ALTER TABLE exercise_library ADD COLUMN IF NOT EXISTS demo_video_url TEXT;
ALTER TABLE exercise_library ADD COLUMN IF NOT EXISTS media_credit VARCHAR(160);
ALTER TABLE exercise_library ADD COLUMN IF NOT EXISTS media_license VARCHAR(80);
ALTER TABLE exercise_library ADD COLUMN IF NOT EXISTS media_source_url TEXT;
CREATE INDEX IF NOT EXISTS ix_exercise_library_name ON exercise_library(name);
CREATE INDEX IF NOT EXISTS ix_exercise_library_category ON exercise_library(category);

CREATE TABLE IF NOT EXISTS training_exercise_entries (
  id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES account_users(id) ON DELETE CASCADE,
  log_id INTEGER NOT NULL REFERENCES training_logs(id) ON DELETE CASCADE,
  exercise_id INTEGER NOT NULL REFERENCES exercise_library(id), sets INTEGER NOT NULL, reps INTEGER NOT NULL,
  target_reps_min INTEGER NOT NULL, target_reps_max INTEGER NOT NULL, weight_kg FLOAT NOT NULL DEFAULT 0,
  rpe INTEGER NOT NULL, completion VARCHAR(16) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_training_exercise_user ON training_exercise_entries(user_id);
CREATE INDEX IF NOT EXISTS ix_training_exercise_log ON training_exercise_entries(log_id);

CREATE TABLE IF NOT EXISTS recovery_checkins (
  id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES account_users(id) ON DELETE CASCADE,
  log_id INTEGER NOT NULL UNIQUE REFERENCES training_logs(id) ON DELETE CASCADE, checkin_date DATE NOT NULL,
  soreness INTEGER NOT NULL, sleep_hours FLOAT NOT NULL, sleep_quality INTEGER NOT NULL, energy INTEGER NOT NULL,
  is_sick BOOLEAN NOT NULL DEFAULT FALSE, warning_symptom VARCHAR(20) NOT NULL DEFAULT 'none',
  note TEXT, status VARCHAR(20) NOT NULL, message TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_recovery_user_date ON recovery_checkins(user_id, checkin_date);

CREATE TABLE IF NOT EXISTS exercise_advice (
  id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES account_users(id) ON DELETE CASCADE,
  log_id INTEGER NOT NULL REFERENCES training_logs(id) ON DELETE CASCADE,
  exercise_id INTEGER NOT NULL REFERENCES exercise_library(id), advice_type VARCHAR(16) NOT NULL,
  prescription JSON NOT NULL, evidence JSON NOT NULL, reason TEXT NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'pending', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), resolved_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_exercise_advice_user ON exercise_advice(user_id);

CREATE TABLE IF NOT EXISTS plan_adjustments (
  id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES account_users(id) ON DELETE CASCADE,
  source_week_start DATE NOT NULL, target_week_start DATE NOT NULL, status VARCHAR(16) NOT NULL DEFAULT 'pending',
  recommendation JSON NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), resolved_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_plan_adjustments_user ON plan_adjustments(user_id);
