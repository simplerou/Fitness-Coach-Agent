"""Bounded document extraction, chunking and opt-in semantic indexing."""
from datetime import date
import hashlib
from io import BytesIO
import os
from pathlib import PurePosixPath
import re
from zipfile import BadZipFile, ZipFile

from sqlalchemy import select
from ..models.knowledge import KnowledgeUploadRecord
from ..models.training_intelligence import ExerciseKnowledgeDocumentRecord
from .exercise_knowledge import EMBEDDING_MODEL, _document_hash, get_vector_collection

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TEXT_CHARS = 200_000
MAX_DOCX_XML_BYTES = 8 * 1024 * 1024
MAX_PDF_PAGES = 200
FORMATS = {".txt": "TXT", ".md": "Markdown", ".pdf": "PDF", ".docx": "Word"}


class KnowledgeImportError(ValueError):
    def __init__(self, message, status=422):
        super().__init__(message)
        self.status = status


def _bounded_text(text):
    if len(text) > MAX_TEXT_CHARS:
        raise KnowledgeImportError("文档文字过多，请拆成不超过20万字的多个文件后上传。")
    return text


def extract_document(filename, data):
    name = PurePosixPath((filename or "").replace("\\", "/")).name
    suffix = PurePosixPath(name).suffix.lower()
    if suffix not in FORMATS:
        raise KnowledgeImportError("仅支持 TXT、Markdown、PDF 和 Word（DOCX）文档。")
    if len(name) > 255:
        raise KnowledgeImportError("文件名过长，请缩短后再上传。")
    if not data:
        raise KnowledgeImportError("文件为空，请选择包含文字的文档。")
    if len(data) > MAX_FILE_BYTES:
        raise KnowledgeImportError("单个文件不能超过10 MB。", 413)
    try:
        if suffix in {".txt", ".md"}:
            if data.startswith((b"%PDF-", b"PK\x03\x04")):
                raise KnowledgeImportError("文件内容与扩展名不一致，请保留原始文件格式。")
            if data.startswith((b"\xff\xfe", b"\xfe\xff")):
                text = data.decode("utf-16")
            else:
                try:
                    text = data.decode("utf-8-sig")
                except UnicodeDecodeError:
                    text = data.decode("gb18030")
            if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", text):
                raise KnowledgeImportError("文件不是有效的文字文档，请重新选择。")
        elif suffix == ".pdf":
            if not data.startswith(b"%PDF-"):
                raise KnowledgeImportError("PDF 文件内容无效。")
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(data))
            if reader.is_encrypted:
                raise KnowledgeImportError("暂不支持加密 PDF，请先解除文件密码。")
            if len(reader.pages) > MAX_PDF_PAGES:
                raise KnowledgeImportError("PDF 不能超过200页，请拆分后上传。")
            parts, length = [], 0
            for page in reader.pages:
                part = page.extract_text() or ""
                length += len(part) + 2
                if length > MAX_TEXT_CHARS:
                    raise KnowledgeImportError("文档文字过多，请拆成不超过20万字的多个文件。")
                parts.append(part)
            text = "\n\n".join(parts)
        else:
            from defusedxml.ElementTree import fromstring
            with ZipFile(BytesIO(data)) as archive:
                info = archive.getinfo("word/document.xml")
                if info.file_size > MAX_DOCX_XML_BYTES or info.flag_bits & 1:
                    raise KnowledgeImportError("Word 文档过大或已加密，请拆分或解除密码后上传。")
                xml = archive.read(info)
                root = fromstring(xml)
                ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
                paragraphs = []
                length = 0
                for paragraph in root.iter(ns + "p"):
                    line = "".join((element.text or "") if element.tag == ns + "t" else
                                   "\t" if element.tag == ns + "tab" else
                                   "\n" if element.tag in {ns + "br", ns + "cr"} else ""
                                   for element in paragraph.iter())
                    length += len(line) + 2
                    if length > MAX_TEXT_CHARS:
                        raise KnowledgeImportError("文档文字过多，请拆分后上传。")
                    paragraphs.append(line)
                text = "\n\n".join(paragraphs)
    except KnowledgeImportError:
        raise
    except Exception:
        raise KnowledgeImportError("无法读取文档，请确认文件未损坏且格式正确。") from None
    text = _bounded_text(text.replace("\r\n", "\n").replace("\r", "\n").strip())
    if not text:
        message = "PDF 没有可提取的文字，扫描件请先识别文字或转换为 TXT/Markdown。" if suffix == ".pdf" else "文档未包含可提取的文字。"
        raise KnowledgeImportError(message)
    return name, suffix, text


def split_document(text, size=1600, overlap=200):
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = max(text.rfind("\n", start + size // 2, end),
                           text.rfind("。", start + size // 2, end),
                           text.rfind("；", start + size // 2, end))
            if boundary > start:
                end = boundary + 1
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end == len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks


def store_document(db, admin_id, filename, data, metadata):
    digest = hashlib.sha256(data).hexdigest()
    if db.scalar(select(KnowledgeUploadRecord.id).where(KnowledgeUploadRecord.file_hash == digest)) is not None:
        raise KnowledgeImportError("这份文档已经上传，请在文档列表中查看。", 409)
    name, suffix, body = extract_document(filename, data)
    title = metadata.title or PurePosixPath(name).stem[:200]
    source_name = metadata.source_name or name[:180]
    row = KnowledgeUploadRecord(title=title, filename=name, file_type=suffix[1:],
        file_size=len(data), file_hash=digest, original_file=data, extracted_text=body,
        source_name=source_name, source_url=metadata.source_url, uploaded_by=admin_id)
    db.add(row)
    db.flush()
    parts = split_document(body)
    for index, part in enumerate(parts, start=1):
        values = {
            "document_key": f"upload:{digest}:{index:04d}", "source_type": "external",
            "exercise_id": None, "title": f"{title} · 第{index}段",
            "source_name": source_name, "source_url": metadata.source_url,
            "source_published_at": None, "content_rights": "admin_uploaded",
            "target_muscles": [], "equipment": [], "tags": ["管理员上传", FORMATS[suffix]],
        }
        db.add(ExerciseKnowledgeDocumentRecord(**values, upload_id=row.id, body=part,
            content_hash=_document_hash(part, values), source_retrieved_at=date.today(),
            review_status="approved"))
    db.flush()
    return row, len(parts)


def index_document_rows(rows):
    from langchain_openai import OpenAIEmbeddings
    key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("missing_embedding_key")
    embedder = OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        check_embedding_ctx_length=False, request_timeout=45, max_retries=1)
    collection = get_vector_collection()
    for start in range(0, len(rows), 10):
        batch = rows[start:start + 10]
        texts = [row["title"] + "\n" + row["body"] for row in batch]
        vectors = embedder.embed_documents(texts)
        if len(vectors) != len(batch):
            raise RuntimeError("incomplete_embeddings")
        collection.upsert(ids=[row["document_key"] for row in batch], documents=texts, embeddings=vectors,
            metadatas=[{"source_type": row["source_type"], "content_hash": row["content_hash"],
                        "embedding_model": EMBEDDING_MODEL} for row in batch])
