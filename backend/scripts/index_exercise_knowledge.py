"""Index reviewed exercise knowledge documents into the local Chroma collection."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
from sqlalchemy import select

load_dotenv(PROJECT_ROOT / ".env")

from app.database import SessionLocal, initialize_database
from app.models.training_intelligence import ExerciseKnowledgeDocumentRecord
from app.services.exercise_knowledge import EMBEDDING_MODEL, get_vector_collection


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="re-embed and replace every approved document")
    parser.add_argument("--batch-size", type=int, default=10)
    args = parser.parse_args()
    if args.batch_size < 1 or args.batch_size > 32:
        parser.error("--batch-size must be between 1 and 32")
    if not os.getenv("DASHSCOPE_API_KEY", "").strip():
        parser.error("DASHSCOPE_API_KEY is missing from the project .env")

    initialize_database()
    from langchain_openai import OpenAIEmbeddings

    embedder = OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=os.environ["DASHSCOPE_API_KEY"],
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", check_embedding_ctx_length=False)
    collection = get_vector_collection()
    with SessionLocal() as db:
        rows = db.scalars(select(ExerciseKnowledgeDocumentRecord).where(
            ExerciseKnowledgeDocumentRecord.review_status == "approved").order_by(
                ExerciseKnowledgeDocumentRecord.id)).all()
        current_by_key = {row.document_key: row for row in rows}
        stored = collection.get(include=["metadatas"])
        stored_ids = stored.get("ids", [])
        stored_metadata = stored.get("metadatas", [])
        indexed_metadata = {key: metadata or {}
                            for key, metadata in zip(stored_ids, stored_metadata)}
        stale_ids = [key for key in stored_ids if key not in current_by_key]
        if stale_ids:
            collection.delete(ids=stale_ids)
        if args.force:
            rows_to_index = rows
        else:
            rows_to_index = [row for row in rows if
                indexed_metadata.get(row.document_key, {}).get("content_hash") != row.content_hash
                or indexed_metadata.get(row.document_key, {}).get("embedding_model") != EMBEDDING_MODEL]
        for start in range(0, len(rows_to_index), args.batch_size):
            batch = rows_to_index[start:start + args.batch_size]
            if not batch:
                break
            vectors = embedder.embed_documents([f"{row.title}\n{row.body}" for row in batch])
            collection.upsert(ids=[row.document_key for row in batch],
                documents=[f"{row.title}\n{row.body}" for row in batch], embeddings=vectors,
                metadatas=[{"source_type": row.source_type, "content_hash": row.content_hash,
                            "embedding_model": EMBEDDING_MODEL} for row in batch])
            print(f"Indexed {min(start + len(batch), len(rows_to_index))}/{len(rows_to_index)} documents")
        print(f"Done. {len(rows_to_index)} document(s) stored in Chroma using {EMBEDDING_MODEL}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
