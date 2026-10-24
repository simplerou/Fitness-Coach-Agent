"""Authorization and tenant isolation checks against an independent in-memory database."""
import sys
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, AccountUserRecord, BodyProfileRecord, DietMealRecord
from app.models.shaping import ShapePhotoRecord
from app.models.training_intelligence import ExerciseLibraryRecord
from app.api.admin import create_admin_router, DATASETS
from app.api.auth import create_auth_router
from app.core.security import hash_password


class AdminTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        salt, digest = hash_password("TestPassword2026!")
        with self.factory() as db:
            db.add_all([AccountUserRecord(id=1, username="admin_test", display_name="管理员",
                                         password_hash=digest, password_salt=salt, is_admin=True),
                        AccountUserRecord(id=2, username="member_test", display_name="普通用户",
                                         password_hash=digest, password_salt=salt)])
            db.flush()
            db.add(ExerciseLibraryRecord(id=8, slug="goblet-squat", name="高脚杯深蹲", category="腿", target_muscles=["股四头肌"], equipment=["dumbbells"], cues=[], common_errors=[], regressions=[], progressions=[], alternatives=[]))
            db.add_all([DietMealRecord(user_id=1, log_date=date.today(),
                                      meal_type="lunch", description="管理员餐食"),
                        DietMealRecord(user_id=2, log_date=date.today(),
                                      meal_type="lunch", description="普通用户餐食"),
                        ShapePhotoRecord(id=1, user_id=2, recorded_on=date.today(),
                                         view="front", image_data=b"jpeg-test")])
            db.commit()
        app = FastAPI()
        app.add_middleware(SessionMiddleware, secret_key="isolated-admin-test-secret")
        def authenticate(request: Request):
            uid = request.session.get("user_id")
            if not isinstance(uid, int):
                raise HTTPException(401, "请登录")
            return uid
        app.include_router(create_auth_router(authenticate, self.factory))
        app.include_router(create_admin_router(authenticate, self.factory))
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.engine.dispose()

    def login(self, name):
        result = self.client.post("/api/auth/login", json={"username": name, "password": "TestPassword2026!"})
        self.assertEqual(result.status_code, 200)
        return result.json()["user"]

    def test_all_admin_endpoints_deny_anonymous(self):
        for path in ["/api/admin/users", "/api/admin/users/2",
                     "/api/admin/users/2/records/diet_meals", "/api/admin/users/2/photos/1"]:
            self.assertEqual(self.client.get(path).status_code, 401)

    def test_member_cannot_read_other_users_or_assign_role(self):
        self.assertFalse(self.login("member_test")["is_admin"])
        for path in ["/api/admin/users", "/api/admin/users/1",
                     "/api/admin/users/1/records/diet_meals", "/api/admin/users/2/photos/1"]:
            self.assertEqual(self.client.get(path).status_code, 403)
        result = self.client.post("/api/auth/register", json={
            "username": "injected", "password": "TestPassword2026!", "is_admin": True})
        self.assertEqual(result.status_code, 422)
        result = self.client.post("/api/auth/register", json={
            "username": "injected", "password": "TestPassword2026!", "role": "admin"})
        self.assertEqual(result.status_code, 422)

    def test_admin_directory_and_tenant_filtered_records(self):
        self.assertTrue(self.login("admin_test")["is_admin"])
        self.assertTrue(self.client.get("/api/auth/me").json()["user"]["is_admin"])
        listing = self.client.get("/api/admin/users?page_size=1").json()
        self.assertEqual(listing["total"], 2)
        self.assertEqual(len(listing["items"]), 1)
        result = self.client.get("/api/admin/users?q=member_test")
        self.assertIn("no-store", result.headers["cache-control"])
        self.assertEqual(result.json()["total"], 1)
        self.assertEqual(self.client.get("/api/admin/users?q=%25").json()["total"], 0)
        details = self.client.get("/api/admin/users/2").json()
        self.assertEqual(len(details["datasets"]), len(DATASETS))
        self.assertNotIn("password_hash", str(details))
        self.assertNotIn("password_salt", str(details))
        for dataset in DATASETS:
            response = self.client.get("/api/admin/users/2/records/" + dataset)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertFalse({"password_hash", "password_salt", "image_data"} & set(response.json()["columns"]))
        result = self.client.get("/api/admin/users/2/records/diet_meals").json()
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["description"], "普通用户餐食")
        self.assertEqual(result["exercise_names"]["8"], "高脚杯深蹲")
        self.assertEqual(self.client.get("/api/admin/users/999").status_code, 404)
        self.assertEqual(self.client.get("/api/admin/users/2/records/account_users").status_code, 404)
        self.assertEqual(self.client.get("/api/admin/users?page=0").status_code, 422)
        self.assertEqual(self.client.get("/api/admin/users?page_size=101").status_code, 422)

    def test_photos_are_scoped_and_binary_is_not_in_records(self):
        self.login("admin_test")
        data = self.client.get("/api/admin/users/2/records/shape_photos").json()
        self.assertNotIn("image_data", data["columns"])
        self.assertNotIn("jpeg-test", str(data))
        self.assertEqual(self.client.get("/api/admin/users/1/photos/1").status_code, 404)
        image = self.client.get("/api/admin/users/2/photos/1")
        self.assertEqual(image.content, b"jpeg-test")
        self.assertIn("no-store", image.headers["cache-control"])

    def test_role_revocation_takes_effect_on_existing_session(self):
        self.login("admin_test")
        with self.factory() as db:
            db.get(AccountUserRecord, 1).is_admin = False
            db.commit()
        self.assertEqual(self.client.get("/api/admin/users").status_code, 403)
        self.assertFalse(self.client.get("/api/auth/me").json()["user"]["is_admin"])

    def test_deleted_admin_session_is_rejected(self):
        self.login("admin_test")
        with self.factory() as db:
            db.delete(db.get(AccountUserRecord, 1))
            db.commit()
        self.assertEqual(self.client.get("/api/admin/users").status_code, 401)


if __name__ == "__main__":
    unittest.main()
