"""训练智能规则与接口使用内存 SQLite，不连接开发 PostgreSQL。"""
import base64
import json
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database import AccountUserRecord, Base, LocalProfileRecord, TrainingPreferencesRecord, WeeklyPlanRecord
from app.main import SESSION_SECRET_KEY, app
from app.models.training_intelligence import ExerciseAdviceRecord, ExerciseLibraryRecord
from app.services.exercise_library import SEED_EXERCISES, ensure_exercise_seed
from app.services.plan_adjustment_service import build_adjustment
from app.services.progressive_overload import progression_recommendation
from app.services.recovery_service import assess_recovery, needs_deload


def record(day: date, reps=10, maximum=12, weight=20, rpe=7):
    return {"training_date": day, "sets": 3, "reps": reps, "target_reps_min": 8,
            "target_reps_max": maximum, "weight_kg": weight, "rpe": rpe, "completion": "completed"}


class RuleTests(unittest.TestCase):
    def test_double_progression_and_one_variable(self):
        rows = [record(date.today()), record(date.today() - timedelta(days=7))]
        advice = progression_recommendation(rows, "beginner")
        self.assertEqual(advice["advice_type"], "reps")
        self.assertEqual(advice["prescription"], {"sets": 3, "reps": 12, "weight_kg": 20})
        top = [record(date.today(), reps=12), record(date.today() - timedelta(days=7), reps=12)]
        advice = progression_recommendation(top, "beginner")
        self.assertEqual(advice["advice_type"], "weight")
        self.assertEqual(advice["prescription"]["reps"], 8)
        self.assertGreater(advice["prescription"]["weight_kg"], 20)

    def test_progression_guards(self):
        rows = [record(date.today(), rpe=9), record(date.today() - timedelta(days=7))]
        self.assertIsNone(progression_recommendation(rows, "beginner"))
        self.assertIsNone(progression_recommendation([record(date.today()), record(date.today() - timedelta(days=7), weight=22)], "beginner"))
        self.assertIsNone(progression_recommendation([record(date.today()), record(date.today() - timedelta(days=7))], "beginner", warning_symptom="joint_pain"))

    def test_recovery_and_adjustment_rules(self):
        low = assess_recovery({"soreness": 5, "sleep_hours": 5, "sleep_quality": 2, "energy": 2, "is_sick": False, "warning_symptom": "none"}, True)
        self.assertEqual(low["status"], "insufficient")
        stop = assess_recovery({"soreness": 2, "sleep_hours": 8, "sleep_quality": 4, "energy": 4, "is_sick": False, "warning_symptom": "sharp_pain"}, False)
        self.assertFalse(stop["allow_progression"])
        self.assertTrue(needs_deload(4))
        original = {"training_weekdays": [1, 3, 5], "session_minutes": 45, "sessions": [{"duration_minutes": 45, "description": "原计划"}]}
        result = build_adjustment(original, {"completion_rate": .9, "average_rpe": 8.5, "recovery_status": "attention", "has_warning_symptom": False, "consecutive_training_weeks": 4, "tracked_exercises": 2, "progressed_exercises": 0})
        self.assertEqual(result["kind"], "deload")
        self.assertNotIn("deload", original["sessions"][0])

    def test_seed_coverage(self):
        self.assertGreaterEqual(len(SEED_EXERCISES), 20)
        self.assertEqual({"胸", "背", "腿", "肩", "臂", "核心"}, {row["category"] for row in SEED_EXERCISES})


class TrainingApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine, expire_on_commit=False)
        with self.session() as db:
            db.add(AccountUserRecord(id=1, username="tester", display_name="test", password_hash="x", password_salt="x"))
            db.add(LocalProfileRecord(user_id=1, registered_on=date.today() - timedelta(days=60)))
            db.add(TrainingPreferencesRecord(user_id=1, goal="strength", days_per_week=3, experience_level="beginner", equipment=["dumbbells"], session_minutes=30))
            ensure_exercise_seed(db); db.commit()
            self.exercise_id = db.scalar(select(ExerciseLibraryRecord.id).where(ExerciseLibraryRecord.slug == "dumbbell-bench-press"))
        self.main_patch = patch("app.main.SessionLocal", self.session)
        self.api_patch = patch("app.api.training_intelligence.SessionLocal", self.session)
        self.main_patch.start(); self.api_patch.start()
        self.client = TestClient(app)
        encoded = base64.b64encode(json.dumps({"user_id": 1}).encode())
        self.client.cookies.set("fitness_coach_session", TimestampSigner(SESSION_SECRET_KEY).sign(encoded).decode())

    def tearDown(self):
        self.client.close(); self.api_patch.stop(); self.main_patch.stop(); self.engine.dispose()

    def payload(self, day):
        return {"training_date": str(day), "completion": "completed", "rpe": 7, "skip_reason": None, "note": None,
                "exercises": [{"exercise_id": self.exercise_id, "sets": 3, "reps": 10, "target_reps_min": 8,
                               "target_reps_max": 12, "weight_kg": 20, "rpe": 7, "completion": "completed"}],
                "recovery": {"soreness": 2, "sleep_hours": 8, "sleep_quality": 4, "energy": 4,
                             "is_sick": False, "warning_symptom": "none", "note": None}}

    def test_two_successful_sessions_create_advice_and_decision(self):
        first = self.client.post("/api/training/logs", json=self.payload(date.today() - timedelta(days=14)))
        second = self.client.post("/api/training/logs", json=self.payload(date.today() - timedelta(days=7)))
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(len(second.json()["advice"]), 1)
        advice_id = second.json()["advice"][0]["id"]
        self.assertEqual(self.client.put(f"/api/training/advice/{advice_id}", json={"decision": "adopted"}).status_code, 200)
        with self.session() as db:
            self.assertEqual(db.get(ExerciseAdviceRecord, advice_id).status, "adopted")

    def test_warning_signal_blocks_advice(self):
        first = self.payload(date.today() - timedelta(days=14))
        second = self.payload(date.today() - timedelta(days=7))
        second["recovery"]["warning_symptom"] = "joint_pain"
        self.client.post("/api/training/logs", json=first)
        response = self.client.post("/api/training/logs", json=second)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["advice"], [])
        self.assertEqual(response.json()["recovery"]["status"], "stop")

    def test_week_preview_does_not_apply_until_confirmed(self):
        monday = date.today() - timedelta(days=date.today().weekday())
        next_monday = monday + timedelta(days=7)
        with self.session() as db:
            db.add(WeeklyPlanRecord(user_id=1, week_start=monday, plan_data={"training_weekdays": [1, 3, 5],
                "session_minutes": 30, "sessions": [], "goal": "strength", "focus": "力量基础",
                "days_per_week": 3, "rest_weekdays": [2, 4, 6, 7], "experience_level": "beginner",
                "equipment": ["dumbbells"], "body_profile_context": {}, "notice": "test"}))
            db.commit()
        preview = self.client.post(f"/api/training/adjustments/preview?week_of={monday}")
        self.assertEqual(preview.status_code, 200)
        with self.session() as db:
            self.assertIsNone(db.get(WeeklyPlanRecord, (1, next_monday)))
        decision = self.client.put(f"/api/training/adjustments/{preview.json()['id']}", json={"decision": "adopted"})
        self.assertEqual(decision.status_code, 200)
        with self.session() as db:
            self.assertIsNotNone(db.get(WeeklyPlanRecord, (1, next_monday)))


if __name__ == "__main__":
    unittest.main()
