"""Administrator-only document catalogue, file import and explicit cloud indexing."""
from datetime import datetime, timedelta, timezone
import logging
import os
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import ValidationError
from sqlalchemy import case, func, literal, select, union_all
from sqlalchemy.exc import IntegrityError

from .admin import create_admin_dependency
from ..models.knowledge import KnowledgeUploadRecord as Upload
from ..models.training_intelligence import ExerciseKnowledgeDocumentRecord as Document
from ..schemas.knowledge import KnowledgeIndexRequest, KnowledgeMetadata
from ..services.exercise_knowledge import EMBEDDING_MODEL
from ..services.knowledge_import import MAX_FILE_BYTES, KnowledgeImportError, index_document_rows, store_document

logger = logging.getLogger(__name__)


def upload_info(db, row, include_body=False):
    count = db.scalar(select(func.count(Document.id)).where(Document.upload_id == row.id)) or 0
    status = row.index_status
    if status == "indexed" and row.index_model != EMBEDDING_MODEL:
        status = "outdated"
    result = {"id": row.id, "kind": "uploaded", "title": row.title, "filename": row.filename,
              "file_type": row.file_type, "file_size": row.file_size, "source_name": row.source_name,
              "source_url": row.source_url, "review_status": "approved", "chunk_count": count,
              "characters": len(row.extracted_text), "created_at": row.created_at,
              "index_status": status, "index_error": row.index_error,
              "indexed_at": row.indexed_at, "index_model": row.index_model}
    if include_body:
        result["body"] = row.extracted_text
    return result


def create_admin_knowledge_router(authenticate, session_factory):
    router = APIRouter(prefix="/api/admin/knowledge", tags=["管理员知识库"])
    require_admin = create_admin_dependency(authenticate, session_factory)

    def find_upload(db, upload_id):
        row = db.get(Upload, upload_id)
        if row is None:
            raise HTTPException(404, "未找到上传文档。")
        return row

    @router.get("/documents")
    def documents(q: str = "", kind: Literal["all", "exercise", "external", "uploaded"] = "all",
                  page: int = 1, page_size: int = 20, admin_id: int = Depends(require_admin)):
        if page < 1 or page_size < 1 or page_size > 100 or len(q) > 200:
            raise HTTPException(422, "查询页码、每页数量或关键词长度不正确。")
        chunks = select(func.count(Document.id)).where(Document.upload_id == Upload.id).correlate(Upload).scalar_subquery()
        seed = select(Document.id.label("id"),
            case((Document.source_type == "exercise", "exercise"), else_="external").label("kind"),
            Document.title.label("title"), Document.source_name.label("source_name"),
            Document.source_url.label("source_url"), Document.review_status.label("review_status"),
            Document.updated_at.label("created_at"), func.length(Document.body).label("characters"),
            literal(1).label("chunk_count"), literal(None).label("filename"),
            literal(None).label("file_type"), literal(None).label("file_size"),
            literal("managed").label("index_status"), literal(None).label("index_model")
        ).where(Document.upload_id.is_(None))
        uploaded = select(Upload.id, literal("uploaded"), Upload.title, Upload.source_name,
            Upload.source_url, literal("approved"), Upload.created_at, func.length(Upload.extracted_text),
            chunks, Upload.filename, Upload.file_type, Upload.file_size, Upload.index_status, Upload.index_model)
        catalogue = union_all(seed, uploaded).subquery()
        query = select(catalogue)
        if kind != "all":
            query = query.where(catalogue.c.kind == kind)
        keyword = q.strip()
        if keyword:
            pattern = "%" + keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            query = query.where(catalogue.c.title.ilike(pattern, escape="\\") |
                                catalogue.c.source_name.ilike(pattern, escape="\\") |
                                catalogue.c.filename.ilike(pattern, escape="\\"))
        with session_factory() as db:
            total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
            rows = db.execute(query.order_by(catalogue.c.created_at.desc(), catalogue.c.kind, catalogue.c.id.desc())
                              .offset((page - 1) * page_size).limit(page_size)).mappings().all()
            items = [dict(row) for row in rows]
            for row in items:
                if row["index_status"] == "indexed" and row["index_model"] != EMBEDDING_MODEL:
                    row["index_status"] = "outdated"
            summary = {
                "documents": (db.scalar(select(func.count(Document.id)).where(Document.upload_id.is_(None))) or 0)
                             + (db.scalar(select(func.count(Upload.id))) or 0),
                "uploads": db.scalar(select(func.count(Upload.id))) or 0,
                "segments": db.scalar(select(func.count(Document.id))) or 0,
                "active_segments": db.scalar(select(func.count(Document.id)).where(Document.review_status == "approved")) or 0,
            }
            return {"items": items, "total": total, "page": page, "page_size": page_size, "summary": summary}

    @router.get("/documents/{document_id}")
    def document(document_id: int, admin_id: int = Depends(require_admin)):
        with session_factory() as db:
            row = db.get(Document, document_id)
            if row is None or row.upload_id is not None:
                raise HTTPException(404, "未找到此知识文档。")
            return {"id": row.id, "kind": "exercise" if row.source_type == "exercise" else "external",
                    "title": row.title, "body": row.body, "source_name": row.source_name,
                    "source_url": row.source_url, "review_status": row.review_status,
                    "source_published_at": row.source_published_at, "created_at": row.updated_at,
                    "characters": len(row.body), "chunk_count": 1, "index_status": "managed",
                    "tags": row.tags, "target_muscles": row.target_muscles, "equipment": row.equipment}

    @router.post("/uploads", status_code=201)
    def upload(file: UploadFile = File(...), title: str | None = Form(default=None),
               source_name: str | None = Form(default=None), source_url: str | None = Form(default=None),
               admin_id: int = Depends(require_admin)):
        try:
            metadata = KnowledgeMetadata(title=title, source_name=source_name, source_url=source_url)
        except ValidationError:
            raise HTTPException(422, "标题最多200字，来源最多180字；来源链接请填写有效的 http 或 https 地址。") from None
        data = file.file.read(MAX_FILE_BYTES + 1)
        try:
            with session_factory() as db:
                row, count = store_document(db, admin_id, file.filename, data, metadata)
                db.commit()
                db.refresh(row)
                return {"document": upload_info(db, row, include_body=True),
                        "message": f"文档已上传并分成{count}段，可用于 AI 教练的本地检索。"}
        except KnowledgeImportError as error:
            raise HTTPException(error.status, str(error)) from None
        except IntegrityError:
            raise HTTPException(409, "这份文档已存在，请在列表中查看。") from None

    @router.get("/uploads/{upload_id}")
    def uploaded_document(upload_id: int, admin_id: int = Depends(require_admin)):
        with session_factory() as db:
            return upload_info(db, find_upload(db, upload_id), include_body=True)

    @router.get("/uploads/{upload_id}/file")
    def original(upload_id: int, admin_id: int = Depends(require_admin)):
        with session_factory() as db:
            row = find_upload(db, upload_id)
            return Response(row.original_file, media_type="application/octet-stream",
                headers={"Content-Disposition": "attachment; filename*=UTF-8''" + quote(row.filename, safe=""),
                         "Cache-Control": "private, no-store", "Vary": "Cookie",
                         "X-Content-Type-Options": "nosniff"})

    @router.post("/uploads/{upload_id}/index")
    def index_upload(upload_id: int, payload: KnowledgeIndexRequest, admin_id: int = Depends(require_admin)):
        if not os.getenv("DASHSCOPE_API_KEY", "").strip():
            raise HTTPException(503, "请先在后端配置云端模型密钥，再生成语义索引。文档已可用于本地检索。")
        now = datetime.now(timezone.utc)
        with session_factory() as db:
            row = db.scalar(select(Upload).where(Upload.id == upload_id).with_for_update())
            if row is None:
                raise HTTPException(404, "未找到上传文档。")
            started = row.index_started_at
            if started and started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            if row.index_status == "indexing" and started and now - started < timedelta(minutes=30):
                raise HTTPException(409, "此文档正在生成语义索引，请稍后刷新查看。")
            docs = db.scalars(select(Document).where(Document.upload_id == upload_id,
                Document.review_status == "approved").order_by(Document.id)).all()
            if not docs:
                raise HTTPException(409, "文档没有可建立索引的有效分段。")
            rows = [{key: getattr(doc, key) for key in ("document_key", "title", "body", "source_type", "content_hash")}
                    for doc in docs]
            row.index_status = "indexing"; row.index_started_at = now; row.index_error = None
            db.commit()
        try:
            index_document_rows(rows)
        except Exception as error:
            logger.warning("Knowledge indexing failed for upload %s (%s)", upload_id, type(error).__name__)
            with session_factory() as db:
                row = find_upload(db, upload_id)
                row.index_status = "failed"; row.index_started_at = None
                row.index_error = "语义索引未全部完成，可以重试；本地检索仍可用。"
                db.commit()
            raise HTTPException(502, "语义索引未全部完成，可以重试；文档仍可用于本地检索。") from None
        with session_factory() as db:
            row = find_upload(db, upload_id)
            row.index_status = "indexed"; row.index_model = EMBEDDING_MODEL
            row.indexed_at = datetime.now(timezone.utc); row.index_started_at = None; row.index_error = None
            db.commit(); db.refresh(row)
            return {"document": upload_info(db, row, include_body=True),
                    "message": f"已为{len(rows)}个分段生成语义索引，教练可使用混合检索。"}
    return router
