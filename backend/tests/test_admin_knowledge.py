"""Document ingestion and administrator boundaries; no cloud calls or live database writes."""
import hashlib
from io import BytesIO
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
from zipfile import ZIP_DEFLATED, ZipFile
from datetime import date, datetime, timedelta, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import HTTPException, Request
from sqlalchemy import func, select
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
import test_admin
from app.api.admin_knowledge import create_admin_knowledge_router
from app.models.knowledge import KnowledgeUploadRecord
from app.models.training_intelligence import ExerciseKnowledgeDocumentRecord
from app.services import knowledge_import
from app.services.exercise_knowledge import retrieve_documents


def word_file(text):
    output = BytesIO()
    xml = ('<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           '<w:body><w:p><w:r><w:t>' + text + '</w:t></w:r></w:p></w:body></w:document>')
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", xml)
    return output.getvalue()


def pdf_file(text="", encrypted=False):
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    if text:
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                 NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(("BT /F1 12 Tf 20 200 Td (" + text + ") Tj ET").encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("test-password")
    output = BytesIO(); writer.write(output)
    return output.getvalue()


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.base = test_admin.AdminTests()
        self.base.setUp()
        self.client, self.factory = self.base.client, self.base.factory
        def authenticate(request: Request):
            user_id = request.session.get("user_id")
            if not isinstance(user_id, int):
                raise HTTPException(401, "请登录")
            return user_id
        self.client.app.include_router(create_admin_knowledge_router(authenticate, self.factory))
        with self.factory() as db:
            row = ExerciseKnowledgeDocumentRecord(document_key="seed:test", source_type="external",
                title="原有公开资料", body="原有训练知识内容。", source_name="测试公开资料",
                source_retrieved_at=date.today(), content_hash="a" * 64,
                target_muscles=[], equipment=[], tags=[], review_status="approved")
            db.add(row); db.commit(); self.seed_id = row.id

    def tearDown(self):
        self.base.tearDown()

    def login(self, username="admin_test"):
        return self.base.login(username)

    def upload(self, content="离心节奏特征训练资料。保持动作控制与适宜训练量。", filename="训练资料.txt", **fields):
        self.login()
        content = content.encode() if isinstance(content, str) else content
        return self.client.post("/api/admin/knowledge/uploads",
            files={"file": (filename, content, "application/octet-stream")}, data=fields)

    def test_all_knowledge_actions_require_current_admin_role(self):
        for username, expected in [(None, 401), ("member_test", 403)]:
            self.client.cookies.clear()
            if username: self.login(username)
            for url in ["/documents", "/documents/1", "/uploads/1", "/uploads/1/file"]:
                self.assertEqual(self.client.get("/api/admin/knowledge" + url).status_code, expected)
            result = self.client.post("/api/admin/knowledge/uploads", files={"file": ("a.txt", b"test data")})
            self.assertEqual(result.status_code, expected)
            with patch("app.api.admin_knowledge.index_document_rows") as indexer:
                result = self.client.post("/api/admin/knowledge/uploads/1/index", json={"cloud_consent": True})
                self.assertEqual(result.status_code, expected)
                indexer.assert_not_called()
        with self.factory() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(KnowledgeUploadRecord)), 0)

    def test_upload_is_atomic_grouped_and_immediately_retrievable_without_cloud(self):
        with patch("app.api.admin_knowledge.index_document_rows") as indexer:
            response = self.upload(("离心节奏特征训练资料，保持动作控制。\n" * 200), title="训练节奏说明", source_name="教练资料")
            indexer.assert_not_called()
        self.assertEqual(response.status_code, 201, response.text)
        doc = response.json()["document"]
        self.assertGreater(doc["chunk_count"], 1)
        self.assertEqual(doc["index_status"], "not_indexed")
        with self.factory() as db:
            rows = db.scalars(select(ExerciseKnowledgeDocumentRecord)).all()
            hits, _ = retrieve_documents("离心节奏特征", rows, allow_semantic=False)
            self.assertTrue(any(item["document_key"].startswith("upload:") for item in hits))
            self.assertEqual(db.get(ExerciseKnowledgeDocumentRecord, self.seed_id).body, "原有训练知识内容。")
            chunks = db.scalars(select(ExerciseKnowledgeDocumentRecord).where(
                ExerciseKnowledgeDocumentRecord.upload_id == doc["id"])).all()
            self.assertTrue(all(item.source_type == "external" and item.review_status == "approved" for item in chunks))
        listing = self.client.get("/api/admin/knowledge/documents").json()
        self.assertEqual(listing["total"], 2)
        self.assertEqual(listing["summary"]["uploads"], 1)
        self.assertNotIn("original_file", str(listing))
        self.assertNotIn("extracted_text", str(listing))
        self.assertEqual(self.client.get("/api/admin/knowledge/documents?kind=uploaded").json()["total"], 1)
        self.assertEqual(self.client.get("/api/admin/knowledge/documents?q=节奏").json()["total"], 1)
        self.assertEqual(self.client.get("/api/admin/knowledge/documents?q=%25").json()["total"], 0)
        self.assertEqual(self.client.get("/api/admin/knowledge/documents?page_size=101").status_code, 422)

    def test_original_and_text_preview_are_admin_only_and_unicode_filename_is_safe(self):
        content = "UTF8 文档内容：保持适宜训练量。".encode()
        response = self.upload(content, filename="../../训练资料.txt")
        doc = response.json()["document"]
        self.assertEqual(doc["filename"], "训练资料.txt")
        detail = self.client.get("/api/admin/knowledge/uploads/" + str(doc["id"]))
        self.assertIn("保持适宜训练量", detail.json()["body"])
        self.assertIn("no-store", detail.headers["cache-control"])
        download = self.client.get(f"/api/admin/knowledge/uploads/{doc['id']}/file")
        self.assertEqual(download.content, content)
        self.assertIn("attachment", download.headers["content-disposition"])
        self.assertNotIn("../", download.headers["content-disposition"])
        self.login("member_test")
        self.assertEqual(self.client.get(f"/api/admin/knowledge/uploads/{doc['id']}/file").status_code, 403)
        self.assertEqual(self.client.get(f"/api/admin/knowledge/uploads/{doc['id']}").status_code, 403)

    def test_duplicate_and_invalid_files_do_not_add_documents(self):
        self.assertEqual(self.upload("训练资料去重测试内容。").status_code, 201)
        self.assertEqual(self.upload("训练资料去重测试内容。", filename="other.txt").status_code, 409)
        for content, filename in [(b"", "empty.txt"), (b"executable", "bad.exe"),
                                  (b"not a pdf", "bad.pdf"), (b"\x00\x01\x02", "bad.txt"),
                                  (b"%PDF-fake", "wrong.txt")]:
            self.assertEqual(self.upload(content, filename).status_code, 422)
        with patch.object(knowledge_import, "MAX_FILE_BYTES", 20):
            self.assertEqual(self.upload(b"x" * 21, "large.txt").status_code, 413)
        self.assertEqual(self.upload("invalid source document", source_url="javascript:alert(1)").status_code, 422)
        with self.factory() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(KnowledgeUploadRecord)), 1)

    def test_docx_pdf_encoding_and_empty_scan_handling(self):
        for data, filename, expected in [
            (word_file("深蹲训练：保持脚掌稳定。"), "guide.docx", "保持脚掌稳定"),
            (pdf_file("Training guidance and controlled movement"), "guide.pdf", "controlled movement"),
            ("弹力带训练资料".encode("gb18030"), "legacy.txt", "弹力带训练资料"),
            ("恢复记录资料".encode("utf-16"), "utf16.txt", "恢复记录资料"),
        ]:
            response = self.upload(data, filename)
            self.assertEqual(response.status_code, 201, response.text)
            self.assertIn(expected, response.json()["document"]["body"])
        self.assertEqual(self.upload(pdf_file(), "scan.pdf").status_code, 422)
        self.assertEqual(self.upload(pdf_file("Training", encrypted=True), "locked.pdf").status_code, 422)
        with patch.object(knowledge_import, "MAX_DOCX_XML_BYTES", 10):
            self.assertEqual(self.upload(word_file("不同的Word大文件"), "large.docx").status_code, 422)
        attack = BytesIO()
        with ZipFile(attack, "w") as archive:
            archive.writestr("word/document.xml", '<!DOCTYPE test [<!ENTITY x "unsafe">]><test>&x;</test>')
        self.assertEqual(self.upload(attack.getvalue(), "unsafe.docx").status_code, 422)

    def test_explicit_cloud_consent_required_and_index_failure_keeps_local_knowledge(self):
        uploaded = self.upload().json()["document"]
        url = f"/api/admin/knowledge/uploads/{uploaded['id']}/index"
        with patch("app.api.admin_knowledge.index_document_rows") as indexer:
            self.assertEqual(self.client.post(url, json={"cloud_consent": False}).status_code, 422)
            indexer.assert_not_called()
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": ""}):
            self.assertEqual(self.client.post(url, json={"cloud_consent": True}).status_code, 503)
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "synthetic-test-key"}):
            with patch("app.api.admin_knowledge.index_document_rows", side_effect=RuntimeError("provider failure")):
                self.assertEqual(self.client.post(url, json={"cloud_consent": True}).status_code, 502)
            detail = self.client.get(f"/api/admin/knowledge/uploads/{uploaded['id']}").json()
            self.assertEqual(detail["index_status"], "failed")
            self.assertIn("离心节奏", detail["body"])
            with patch("app.api.admin_knowledge.index_document_rows") as indexer:
                response = self.client.post(url, json={"cloud_consent": True})
                self.assertEqual(response.status_code, 200, response.text)
                indexer.assert_called_once()
                self.assertEqual(response.json()["document"]["index_status"], "indexed")
                self.assertTrue(indexer.call_args.args[0][0]["content_hash"])

    def test_role_revocation_and_index_in_progress_guards(self):
        uploaded = self.upload().json()["document"]
        with self.factory() as db:
            row = db.get(KnowledgeUploadRecord, uploaded["id"])
            row.index_status = "indexing"; row.index_started_at = datetime.now(timezone.utc)
            db.commit()
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "synthetic-test-key"}):
            self.assertEqual(self.client.post(f"/api/admin/knowledge/uploads/{uploaded['id']}/index",
                json={"cloud_consent": True}).status_code, 409)
        with self.factory() as db:
            from app.database import AccountUserRecord
            db.get(AccountUserRecord, 1).is_admin = False
            db.commit()
        self.assertEqual(self.client.get("/api/admin/knowledge/documents").status_code, 403)
        self.assertEqual(self.client.post("/api/admin/knowledge/uploads",
            files={"file": ("other.txt", b"new content")}).status_code, 403)

    def test_vector_metadata_matches_existing_hybrid_retriever(self):
        rows = [{"document_key": "upload:test:1", "title": "训练资料", "body": "训练正文",
                 "source_type": "external", "content_hash": "c" * 64}]
        collection = Mock()
        embedder = Mock()
        embedder.embed_documents.return_value = [[0.1, 0.2]]
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "synthetic-test-key"}), \
             patch("langchain_openai.OpenAIEmbeddings", return_value=embedder), \
             patch("app.services.knowledge_import.get_vector_collection", return_value=collection):
            knowledge_import.index_document_rows(rows)
        args = collection.upsert.call_args.kwargs
        self.assertEqual(args["metadatas"][0]["content_hash"], "c" * 64)
        self.assertIn("embedding_model", args["metadatas"][0])
        self.assertEqual(args["ids"], ["upload:test:1"])

    def test_cli_index_updates_uploaded_document_status(self):
        import importlib.util
        response = self.upload()
        self.assertEqual(response.status_code, 201)
        upload_id = response.json()["document"]["id"]
        spec = importlib.util.spec_from_file_location("knowledge_index_test", Path(__file__).resolve().parents[1] / "scripts/index_exercise_knowledge.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        collection = Mock()
        collection.get.return_value = {"ids": [], "metadatas": []}
        embedder = Mock()
        embedder.embed_documents.side_effect = lambda texts: [[0.1, 0.2] for _ in texts]
        with patch.object(module, "SessionLocal", self.factory), patch.object(module, "initialize_database"), patch.object(module, "get_vector_collection", return_value=collection), patch("langchain_openai.OpenAIEmbeddings", return_value=embedder), patch.dict(os.environ, {"DASHSCOPE_API_KEY": "isolated-test-key"}), patch.object(sys, "argv", ["index_exercise_knowledge.py"]):
            self.assertEqual(module.main(), 0)
        with self.factory() as db:
            record = db.get(KnowledgeUploadRecord, upload_id)
            self.assertEqual(record.index_status, "indexed")
            self.assertEqual(record.index_model, module.EMBEDDING_MODEL)
            self.assertIsNotNone(record.indexed_at)
        collection.upsert.assert_called_once()


if __name__ == "__main__":
    unittest.main()
