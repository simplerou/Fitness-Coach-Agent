"""中文动作与外部训练资料混合检索：jieba BM25 + 可选 DashScope embedding + RRF。"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select

from ..models.training_intelligence import ExerciseKnowledgeDocumentRecord, ExerciseLibraryRecord

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SEED_PATH = PROJECT_ROOT / "backend" / "data" / "exercise_knowledge_seed.json"
EMBEDDING_MODEL = os.getenv("EXERCISE_RAG_EMBEDDING_MODEL", "qwen3.7-text-embedding").strip() or "qwen3.7-text-embedding"
CHROMA_COLLECTION = os.getenv("EXERCISE_RAG_CHROMA_COLLECTION", "fitness_exercise_knowledge").strip() or "fitness_exercise_knowledge"
_CHROMA_PATH_VALUE = Path(os.getenv("EXERCISE_RAG_CHROMA_PATH", "backend/.chroma"))
CHROMA_PATH = _CHROMA_PATH_VALUE if _CHROMA_PATH_VALUE.is_absolute() else PROJECT_ROOT / _CHROMA_PATH_VALUE
_TOKENIZER = None
_VECTOR_COLLECTION = None
ALIASES = {
    "屁股": "臀 臀大肌 臀桥 髋",
    "臀部": "臀 臀大肌 臀桥 髋",
    "背阔": "背 背阔肌 高位下拉 划船",
    "肩膀": "肩 三角肌 推举 侧平举",
    "胳膊": "手臂 肱二头肌 肱三头肌 弯举 臂屈伸",
    "肚子": "核心 腹肌 腹直肌 腹横肌",
    "练大": "增肌 肌肉增长 肌肥大 训练量",
    "没器械": "自重 居家 无器械 替代",
    "器械被占": "器械占用 替代动作 弹力带 自重",
    "动作标准": "动作要领 姿势 技术 常见错误",
    "怎么呼吸": "呼吸 吸气 呼气 发力",
}


def tokenize(text: str) -> list[str]:
    global _TOKENIZER
    text = re.sub(r"[\W_]+", " ", (text or "").casefold(), flags=re.UNICODE).strip()
    if not text:
        return []
    try:
        if _TOKENIZER is None:
            import jieba
            _TOKENIZER = jieba
        tokens = [token.strip() for token in _TOKENIZER.cut(text) if token.strip()]
        # Add character bigrams so rare compound words still match Chinese queries.
        for run in re.findall(r"[\u4e00-\u9fff]{2,}", text):
            tokens.extend(run[index:index + 2] for index in range(len(run) - 1))
        return tokens
    except ImportError:
        tokens = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", text)
        compact = re.sub(r"\s+", "", text)
        tokens.extend(compact[index:index + 2] for index in range(max(0, len(compact) - 1)))
        return tokens


def expand_query(question: str) -> str:
    expanded = question
    for phrase, aliases in ALIASES.items():
        if phrase in question:
            expanded += " " + aliases
    return expanded


def action_document_text(exercise: ExerciseLibraryRecord) -> str:
    errors = "；".join(f"{row.get('error', '')}：{row.get('correction', '')}" for row in exercise.common_errors or [])
    alternatives = "；".join(f"{row.get('name', '')}（{row.get('scene', '')}）" for row in exercise.alternatives or [])
    return "\n".join([
        f"动作：{exercise.name}；别名：{exercise.slug}",
        f"目标肌群：{'、'.join(exercise.target_muscles or [])}；部位：{exercise.category}",
        f"器械：{'、'.join(exercise.equipment or [])}",
        f"动作要领：{'；'.join(exercise.cues or [])}",
        f"常见错误与修正：{errors}",
        f"退阶：{'、'.join(exercise.regressions or [])}；进阶：{'、'.join(exercise.progressions or [])}",
        f"替代动作：{alternatives}",
    ])


def _document_hash(body: str, metadata: dict[str, Any]) -> str:
    packed = json.dumps({"body": body, **metadata}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(packed.encode("utf-8")).hexdigest()


def ensure_knowledge_seed(db) -> int:
    """幂等地同步动作库文档与经筛选的外部资料摘要，不在启动时调用外部 embedding API。"""
    existing = {row.document_key: row for row in db.scalars(select(ExerciseKnowledgeDocumentRecord)).all()}
    payloads: list[dict[str, Any]] = []
    with SEED_PATH.open("r", encoding="utf-8") as source_file:
        payloads.extend(json.load(source_file))
    exercises = db.scalars(select(ExerciseLibraryRecord).order_by(ExerciseLibraryRecord.id)).all()
    for exercise in exercises:
        payloads.append({
            "document_key": f"exercise:{exercise.slug}", "source_type": "exercise", "exercise_id": exercise.id,
            "title": exercise.name, "body": action_document_text(exercise), "source_name": "项目动作库",
            "source_url": None, "source_published_at": None, "content_rights": "project_seed",
            "target_muscles": exercise.target_muscles or [], "equipment": exercise.equipment or [],
            "tags": [exercise.category, "动作要领", "替代动作"],
        })
    today = date.today()
    changed = 0
    for payload in payloads:
        source_type = payload.get("source_type", "external")
        metadata = {key: payload.get(key) for key in ("document_key", "title", "source_name", "source_url",
            "source_published_at", "content_rights", "target_muscles", "equipment", "tags", "exercise_id")}
        metadata["source_type"] = source_type
        digest = _document_hash(payload["body"], metadata)
        row = existing.get(payload["document_key"])
        if row is None:
            row = ExerciseKnowledgeDocumentRecord(
                **metadata, body=payload["body"], source_retrieved_at=today,
                review_status="approved", content_hash=digest,
            )
            db.add(row); existing[payload["document_key"]] = row; changed += 1
        elif row.content_hash != digest:
            for key, value in metadata.items():
                setattr(row, key, value)
            row.body = payload["body"]; row.content_hash = digest
            row.source_retrieved_at = today
            row.review_status = "approved"; changed += 1
    return changed


def get_vector_collection():
    """Return the persistent local Chroma collection without configuring remote telemetry or embeddings."""
    global _VECTOR_COLLECTION
    if _VECTOR_COLLECTION is None:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _VECTOR_COLLECTION = client.get_or_create_collection(
            name=CHROMA_COLLECTION, metadata={"hnsw:space": "cosine"})
    return _VECTOR_COLLECTION


def create_query_embedding(question: str) -> list[float]:
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("未配置 DASHSCOPE_API_KEY")
    from langchain_openai import OpenAIEmbeddings
    embeddings = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        check_embedding_ctx_length=False,
    )
    return embeddings.embed_query(question)


def _bm25_scores(query_tokens: list[str], documents: list[list[str]]) -> list[float]:
    if not query_tokens or not documents:
        return [0.0] * len(documents)
    count = len(documents)
    lengths = [len(document) for document in documents]
    average_length = sum(lengths) / count if count else 0.0
    frequencies = [Counter(document) for document in documents]
    document_frequency = Counter(token for tokens in documents for token in set(tokens))
    scores = []
    for tf_by_term, length in zip(frequencies, lengths):
        score = 0.0
        for token in set(query_tokens):
            tf = tf_by_term.get(token, 0)
            if not tf:
                continue
            df = document_frequency[token]
            idf = math.log(1 + (count - df + 0.5) / (df + 0.5))
            denominator = tf + 1.5 * (1 - 0.75 + 0.75 * length / max(average_length, 1))
            score += idf * tf * 2.5 / denominator
        scores.append(score)
    return scores


def retrieve_documents(question: str, rows: list[ExerciseKnowledgeDocumentRecord],
                        allow_semantic: bool = False, top_k: int = 8) -> tuple[list[dict[str, Any]], str | None]:
    active = [row for row in rows if row.review_status == "approved" and row.body]
    if not active:
        return [], "知识文档库暂时为空，请运行动作知识库导入脚本。"
    expanded = expand_query(question)
    query_tokens = tokenize(expanded)
    doc_tokens = [tokenize(f"{row.title} {' '.join(row.target_muscles or [])} {' '.join(row.equipment or [])} {' '.join(row.tags or [])} {row.body}") for row in active]
    sparse_scores = _bm25_scores(query_tokens, doc_tokens)
    sparse_order = sorted(range(len(active)), key=lambda index: sparse_scores[index], reverse=True)
    sparse_order = [index for index in sparse_order if sparse_scores[index] > 0][:max(top_k * 3, top_k)]
    dense_scores: dict[int, float] = {}
    note = None
    if allow_semantic:
        try:
            collection = get_vector_collection()
            if collection.count() == 0:
                note = "Chroma 向量索引尚未生成；当前仍使用中文 BM25。运行 backend/scripts/index_exercise_knowledge.py 建立索引。"
                raise LookupError("empty_chroma_collection")
            query_embedding = create_query_embedding(question)
            result = collection.query(query_embeddings=[query_embedding], n_results=min(max(top_k * 3, top_k), collection.count()),
                                      include=["distances", "metadatas"])
            rows_by_key = {row.document_key: index for index, row in enumerate(active)}
            ids = (result.get("ids") or [[]])[0]
            distances = (result.get("distances") or [[]])[0]
            metadatas = (result.get("metadatas") or [[]])[0]
            stale_vector_found = False
            for document_key, distance, metadata in zip(ids, distances, metadatas):
                index = rows_by_key.get(document_key)
                if index is None:
                    continue
                if ((metadata or {}).get("content_hash") != active[index].content_hash
                        or (metadata or {}).get("embedding_model") != EMBEDDING_MODEL):
                    stale_vector_found = True
                    continue
                dense_scores[index] = max(0.0, 1.0 - float(distance))
            if stale_vector_found:
                note = "部分 Chroma 向量与资料版本不一致；请重新运行 backend/scripts/index_exercise_knowledge.py 更新索引。"
        except LookupError:
            pass
        except Exception as exc:
            note = f"向量检索暂不可用（{type(exc).__name__}），已使用中文 BM25 检索。"
    dense_order = sorted(dense_scores, key=dense_scores.get, reverse=True)[:max(top_k * 3, top_k)]
    if not dense_order:
        combined_order = sparse_order[:top_k]
    else:
        fused: dict[int, float] = {}
        for order in (sparse_order, dense_order):
            for rank, index in enumerate(order, start=1):
                fused[index] = fused.get(index, 0.0) + 1 / (60 + rank)
        combined_order = sorted(fused, key=fused.get, reverse=True)[:top_k]
    results = []
    for index in combined_order:
        row = active[index]
        results.append({
            "document_key": row.document_key, "source_type": row.source_type, "exercise_id": row.exercise_id,
            "title": row.title, "body": row.body, "source_name": row.source_name, "source_url": row.source_url,
            "source_published_at": row.source_published_at, "source_retrieved_at": row.source_retrieved_at.isoformat(),
            "target_muscles": row.target_muscles or [], "equipment": row.equipment or [], "tags": row.tags or [],
            "bm25_score": round(sparse_scores[index], 4),
            "vector_score": round(dense_scores.get(index, 0.0), 4) if dense_scores else None,
            "retrieval_channels": (["bm25"] if sparse_scores[index] > 0 else []) + (["vector"] if index in dense_scores else []),
        })
    return results, note
