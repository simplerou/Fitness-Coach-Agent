"""独立 SQLite 集成测试：不连接、不写入开发者的 PostgreSQL 数据。"""
import base64
import json
import sys
import unittest
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app, SESSION_SECRET_KEY
from app.database import AccountUserRecord, Base, BodyWeightHistoryRecord
from app.models.shaping import ShapePhotoRecord
from app.services.shaping_service import progress_percent


class ShapingIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine, expire_on_commit=False)
        with self.session() as db:
            for user_id in (1, 2):
                db.add(AccountUserRecord(id=user_id, username=f"test{user_id}", display_name="test", password_hash="test", password_salt="test"))
            db.commit()
        self.main_patch = patch("app.main.SessionLocal", self.session)
        self.shape_patch = patch("app.api.shaping.SessionLocal", self.session)
        self.main_patch.start()
        self.shape_patch.start()
        # 不进入 TestClient 的 lifespan：真实数据库初始化不会运行。
        self.client = TestClient(app)
        self.login(1)

    def tearDown(self):
        self.client.close()
        self.shape_patch.stop()
        self.main_patch.stop()
        self.engine.dispose()

    def login(self, user_id):
        encoded = base64.b64encode(json.dumps({"user_id": user_id}).encode())
        self.client.cookies.set("fitness_coach_session", TimestampSigner(SESSION_SECRET_KEY).sign(encoded).decode())

    def measurement(self, day, **values):
        return self.client.put("/api/shaping/measurement", json={"recorded_on": str(day), **values})

    def data(self):
        response = self.client.get("/api/shaping")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def image(self):
        image = Image.new("RGB", (2000, 1000), (80, 120, 60))
        output = BytesIO()
        exif = Image.Exif()
        exif[270] = "private metadata"
        image.save(output, "JPEG", exif=exif)
        return "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode()

    def test_authentication_and_measurement_isolation(self):
        self.assertEqual(self.measurement(date.today(), waist_cm=90).status_code, 200)
        self.login(2)
        self.assertEqual(self.data()["measurements"], [])
        self.assertEqual(self.client.delete(f"/api/shaping/measurement/{date.today()}").status_code, 404)
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/api/shaping").status_code, 401)
        self.assertEqual(self.measurement(date.today(), waist_cm=70).status_code, 401)

    def test_same_day_upsert_and_missing_values(self):
        self.assertEqual(self.measurement(date.today(), waist_cm=90, hip_cm=100).status_code, 200)
        self.assertEqual(self.measurement(date.today(), waist_cm=89).status_code, 200)
        rows = self.data()["measurements"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["waist_cm"], 89)
        self.assertIsNone(rows[0]["hip_cm"])
        self.assertIsNone(rows[0]["body_fat_percent"])

    def test_validation_and_future_dates(self):
        self.assertEqual(self.measurement(date.today() + timedelta(days=1), waist_cm=90).status_code, 422)
        self.assertEqual(self.measurement(date.today()).status_code, 422)
        self.assertEqual(self.measurement(date.today(), waist_cm=1).status_code, 422)
        self.assertEqual(self.measurement(date.today(), body_fat_percent=25).status_code, 422)
        self.assertEqual(self.measurement(date.today(), body_fat_percent=25, composition_source="scale_reading").status_code, 200)

    def test_two_week_reminders_per_body_part(self):
        self.measurement(date.today() - timedelta(days=14), waist_cm=90)
        self.measurement(date.today() - timedelta(days=13), hip_cm=100)
        self.measurement(date.today(), body_fat_percent=25, composition_source="manual")
        reminders = {item["metric"]: item for item in self.data()["reminders"]}
        self.assertTrue(reminders["waist_cm"]["due"])
        self.assertFalse(reminders["hip_cm"]["due"])
        self.assertIsNone(reminders["arm_cm"]["last_measured_on"])
        self.measurement(date.today(), waist_cm=89)
        self.assertFalse(next(item for item in self.data()["reminders"] if item["metric"] == "waist_cm")["due"])

    def test_directional_progress_and_milestone_deduplication(self):
        start = date.today() - timedelta(days=14)
        self.measurement(start, waist_cm=90)
        self.assertEqual(self.client.put("/api/shaping/target", json={"metric": "waist_cm", "target_value": 80}).status_code, 200)
        result = self.measurement(date.today(), waist_cm=85).json()
        self.assertEqual(len(result["milestone_messages"]), 1)
        target = self.data()["targets"][0]
        self.assertEqual(target["progress_percent"], 50)
        self.assertEqual(target["milestones"], [25, 50])
        self.assertEqual(self.measurement(date.today(), waist_cm=85).json()["milestone_messages"], [])
        self.measurement(date.today(), waist_cm=88)
        self.assertEqual(self.data()["targets"][0]["progress_percent"], 20)
        self.assertEqual(self.data()["targets"][0]["milestones"], [25, 50])
        self.client.put("/api/shaping/target", json={"metric": "waist_cm", "target_value": 82})
        self.assertEqual(self.data()["targets"][0]["baseline_value"], 88)
        self.assertEqual(self.data()["targets"][0]["milestones"], [])
        self.assertEqual(progress_percent(80, 90, 85), 50)
        self.assertEqual(progress_percent(80, 90, 75), 0)
        self.assertEqual(progress_percent(90, 80, 70), 100)

    def test_target_requires_real_reading_and_missing_after_deletion(self):
        self.assertEqual(self.client.put("/api/shaping/target", json={"metric": "waist_cm", "target_value": 80}).status_code, 409)
        self.measurement(date.today(), waist_cm=90)
        self.client.put("/api/shaping/target", json={"metric": "waist_cm", "target_value": 80})
        self.client.delete(f"/api/shaping/measurement/{date.today()}")
        self.assertIsNone(self.data()["targets"][0]["current_value"])
        self.assertIsNone(self.data()["targets"][0]["progress_percent"])
        self.login(2)
        self.client.delete("/api/shaping/target/waist_cm")
        self.login(1)
        self.assertEqual(len(self.data()["targets"]), 1)

    def test_same_day_weight_only_no_imputation(self):
        previous = date.today() - timedelta(days=1)
        with self.session() as db:
            db.add(BodyWeightHistoryRecord(user_id=1, recorded_on=previous, weight_kg=80))
            db.commit()
        self.measurement(date.today(), waist_cm=90)
        self.assertIsNone(self.data()["measurements"][0]["weight_kg"])
        self.assertEqual(len(self.data()["weight_history"]), 1)

    def test_photo_upsert_isolation_reencoding_and_delete(self):
        payload = {"recorded_on": str(date.today()), "view": "front", "image_data": self.image()}
        self.assertEqual(self.client.put("/api/shaping/photo", json=payload).status_code, 200)
        first = self.data()["photos"][0]
        self.assertEqual(self.client.put("/api/shaping/photo", json=payload).status_code, 200)
        self.assertEqual(len(self.data()["photos"]), 1)
        self.assertEqual(self.data()["photos"][0]["id"], first["id"])
        response = self.client.get(f"/api/shaping/photo/{first['id']}/image")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        with Image.open(BytesIO(response.content)) as saved:
            self.assertLessEqual(saved.width, 1600)
            self.assertEqual(len(saved.getexif()), 0)
        self.login(2)
        self.assertEqual(self.data()["photos"], [])
        self.assertEqual(self.client.get(f"/api/shaping/photo/{first['id']}/image").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/shaping/photo/{first['id']}").status_code, 404)
        self.login(1)
        self.assertEqual(self.client.delete(f"/api/shaping/photo/{first['id']}").status_code, 200)
        self.assertEqual(self.data()["photos"], [])

    def test_invalid_and_future_photo_rejected(self):
        payload = {"recorded_on": str(date.today()), "view": "back", "image_data": "data:image/jpeg;base64," + "a" * 60}
        self.assertEqual(self.client.put("/api/shaping/photo", json=payload).status_code, 422)
        payload["image_data"] = self.image()
        payload["recorded_on"] = str(date.today() + timedelta(days=1))
        self.assertEqual(self.client.put("/api/shaping/photo", json=payload).status_code, 422)
        self.assertEqual(self.data()["photos"], [])


if __name__ == "__main__":
    unittest.main()
