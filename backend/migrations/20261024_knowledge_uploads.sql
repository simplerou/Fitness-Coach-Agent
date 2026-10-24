CREATE TABLE IF NOT EXISTS knowledge_uploads (
    id SERIAL PRIMARY KEY,
    title VARCHAR(240) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(12) NOT NULL,
    file_size INTEGER NOT NULL,
    file_hash VARCHAR(64) NOT NULL UNIQUE,
    original_file BYTEA NOT NULL,
    extracted_text TEXT NOT NULL,
    source_name VARCHAR(180) NOT NULL,
    source_url TEXT,
    uploaded_by INTEGER REFERENCES account_users(id) ON DELETE SET NULL,
    index_status VARCHAR(24) NOT NULL DEFAULT 'not_indexed',
    index_model VARCHAR(120),
    index_error TEXT,
    index_started_at TIMESTAMPTZ,
    indexed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE exercise_knowledge_documents ADD COLUMN IF NOT EXISTS upload_id INTEGER REFERENCES knowledge_uploads(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS ix_exercise_knowledge_documents_upload_id ON exercise_knowledge_documents(upload_id);
