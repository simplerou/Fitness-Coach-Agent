-- 教练草案独立保存；pending 不会修改饮食或训练计划。
CREATE TABLE IF NOT EXISTS coach_action_drafts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES account_users(id) ON DELETE CASCADE,
    kind VARCHAR(24) NOT NULL,
    draft_data JSON NOT NULL,
    source_fingerprint VARCHAR(64) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_coach_action_drafts_user_id ON coach_action_drafts(user_id);
