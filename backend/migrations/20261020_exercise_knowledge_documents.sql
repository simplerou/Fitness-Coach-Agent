CREATE TABLE IF NOT EXISTS exercise_knowledge_documents (
  id SERIAL PRIMARY KEY,
  document_key VARCHAR(120) NOT NULL UNIQUE,
  source_type VARCHAR(20) NOT NULL,
  exercise_id INTEGER NULL REFERENCES exercise_library(id) ON DELETE SET NULL,
  title VARCHAR(240) NOT NULL,
  body TEXT NOT NULL,
  source_name VARCHAR(180) NOT NULL,
  source_url TEXT NULL,
  source_published_at VARCHAR(32) NULL,
  source_retrieved_at DATE NOT NULL,
  content_rights VARCHAR(80) NOT NULL DEFAULT 'paraphrased_summary',
  target_muscles JSON NOT NULL DEFAULT '[]',
  equipment JSON NOT NULL DEFAULT '[]',
  tags JSON NOT NULL DEFAULT '[]',
  review_status VARCHAR(20) NOT NULL DEFAULT 'approved',
  content_hash VARCHAR(64) NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- Remove prototype vectors previously stored in PostgreSQL JSON columns; Chroma owns embeddings now.
ALTER TABLE exercise_knowledge_documents DROP COLUMN IF EXISTS embedding;
ALTER TABLE exercise_knowledge_documents DROP COLUMN IF EXISTS embedding_model;
CREATE INDEX IF NOT EXISTS ix_exercise_knowledge_documents_document_key ON exercise_knowledge_documents(document_key);
CREATE INDEX IF NOT EXISTS ix_exercise_knowledge_documents_source_type ON exercise_knowledge_documents(source_type);
CREATE INDEX IF NOT EXISTS ix_exercise_knowledge_documents_exercise_id ON exercise_knowledge_documents(exercise_id);
CREATE INDEX IF NOT EXISTS ix_exercise_knowledge_documents_review_status ON exercise_knowledge_documents(review_status);
