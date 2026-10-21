CREATE TABLE IF NOT EXISTS shaping_intelligence_preferences (
  user_id INTEGER PRIMARY KEY REFERENCES account_users(id) ON DELETE CASCADE,
  goal VARCHAR(24) NOT NULL DEFAULT 'whole_body', focus_groups JSON NOT NULL DEFAULT '[]',
  excluded_groups JSON NOT NULL DEFAULT '[]', updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS muscle_group_stats (
  id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES account_users(id) ON DELETE CASCADE,
  period_start DATE NOT NULL, period_end DATE NOT NULL, muscle_group VARCHAR(16) NOT NULL,
  frequency INTEGER NOT NULL, total_sets INTEGER NOT NULL, coverage_percent FLOAT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_muscle_stat_period UNIQUE(user_id, period_start, period_end, muscle_group)
);
CREATE TABLE IF NOT EXISTS weak_part_advice (
  id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES account_users(id) ON DELETE CASCADE,
  period_start DATE NOT NULL, period_end DATE NOT NULL, muscle_group VARCHAR(16) NOT NULL,
  advice_data JSON NOT NULL, status VARCHAR(16) NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), resolved_at TIMESTAMPTZ,
  CONSTRAINT uq_weak_part_period UNIQUE(user_id, period_end, muscle_group)
);
CREATE TABLE IF NOT EXISTS qa_log (
  id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES account_users(id) ON DELETE CASCADE,
  question TEXT NOT NULL, answer TEXT NOT NULL, intent VARCHAR(24) NOT NULL,
  exercise_ids JSON NOT NULL DEFAULT '[]', used_llm BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS diet_day_adjustment (
  user_id INTEGER NOT NULL REFERENCES account_users(id) ON DELETE CASCADE, adjustment_date DATE NOT NULL,
  day_type VARCHAR(20) NOT NULL, intensity VARCHAR(20) NOT NULL, suggestion JSON NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'proposed', updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY(user_id, adjustment_date)
);
CREATE TABLE IF NOT EXISTS report_snapshot (
  id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES account_users(id) ON DELETE CASCADE,
  period_type VARCHAR(12) NOT NULL, period_start DATE NOT NULL, period_end DATE NOT NULL,
  report_data JSON NOT NULL, generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_shape_report_period UNIQUE(user_id, period_type, period_start)
);
CREATE INDEX IF NOT EXISTS ix_muscle_group_stats_user ON muscle_group_stats(user_id);
CREATE INDEX IF NOT EXISTS ix_weak_part_advice_user ON weak_part_advice(user_id);
CREATE INDEX IF NOT EXISTS ix_qa_log_user ON qa_log(user_id);
CREATE INDEX IF NOT EXISTS ix_report_snapshot_user ON report_snapshot(user_id);
