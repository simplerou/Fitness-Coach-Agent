"""使用真实LangGraph与内存SQLite验证Agent边界；模型为脚本替身，不调用千问或生产数据库。"""
import os
import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, Header
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, ToolMessage
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base
from app.models.user_profile import AccountUserRecord, BodyProfileRecord
from app.models.diet import DietProfileRecord, DietMealRecord
from app.models.training_plan import WeeklyPlanRecord
from app.models.training_log import TrainingLogRecord
from app.models.training_intelligence import RecoveryCheckinRecord
from app.models.shaping_intelligence import DietDayAdjustmentRecord
from app.models.coach import CoachActionDraftRecord
from app.api.coach import create_coach_router
from app.services.coach_data import CoachData
from app.services.coach_tools import CoachToolbox
from app.services.coach_react import run_react
from app.services.shaping_agent import CoachAnswer, answer_coach_question

class ScriptedModel:
    def __init__(self, calls=None, actions=None, repeat=False):
        self.calls, self.actions, self.repeat = list(calls or []), actions or [], repeat
        self.observed = []
        self.last_summary = None

    def bind_tools(self, definitions):
        self.definitions = definitions
        return self

    def invoke(self, messages, **kwargs):
        self.observed = [m for m in messages if isinstance(m, ToolMessage)]
        call = self.calls[0] if self.repeat and self.calls else self.calls.pop(0) if self.calls else None
        return AIMessage(content="", tool_calls=[{"id": "call_" + str(len(self.observed)),
            "name": call[0], "args": call[1], "type": "tool_call"}] if call else [])

    def with_structured_output(self, schema, **kwargs):
        parent = self
        class Output:
            def invoke(self, messages, **kwargs):
                parent.last_summary = messages[-1].content
                return schema(answer="以下结论仅依据本次实际查询的记录，未记录的数据不作推断，任何调整草案都尚未保存。",
                              action_ids=parent.actions)
        return Output()

class CoachTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.day = date.today()
        with self.factory() as db:
            for uid in (1, 2):
                db.add(AccountUserRecord(id=uid, username=f"tester{uid}", display_name="test",
                                        password_hash="x", password_salt="x"))
                db.add(BodyProfileRecord(user_id=uid, age_band="18_29", age_years=25, biological_sex="male",
                                         height_cm=175, weight_kg=75))
                db.add(DietProfileRecord(user_id=uid, goal="fat_loss", activity_level="moderate",
                                         health_reviewed=True, allergies_reviewed=True))
                monday = self.day - timedelta(days=self.day.weekday())
                db.add(WeeklyPlanRecord(user_id=uid, week_start=monday, plan_data={
                    "training_weekdays": [self.day.isoweekday()], "session_minutes": 30,
                    "sessions": [{"weekday": self.day.isoweekday(), "title": "力量训练", "exercises": []}]}))
            db.add(TrainingLogRecord(user_id=1, training_date=self.day, completion="completed", rpe=7))
            db.add(TrainingLogRecord(user_id=2, training_date=self.day, completion="skipped", rpe=None))
            db.add(DietMealRecord(user_id=1, log_date=self.day, meal_type="breakfast", description="test", calories_kcal=300))
            db.add(DietMealRecord(user_id=1, log_date=self.day, meal_type="lunch", description="unknown", calories_kcal=None))
            db.commit()
        app = FastAPI()
        def authenticate(x_user: int = Header(default=1)):
            return x_user
        app.include_router(create_coach_router(authenticate, self.factory))
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.engine.dispose()

    def toolbox(self, db):
        return CoachToolbox(CoachData(db, 1, self.day), [], [], [])

    def test_real_graph_observes_then_queries_again(self):
        model = ScriptedModel([("get_training_summary", {"days": 7}), ("get_recovery_summary", {"days": 7})])
        with self.factory() as db:
            answer, trace, reason = run_react(model, self.toolbox(db), {}, "看看训练和恢复", [], CoachAnswer)
        self.assertEqual([r["tool"] for r in trace], ["get_training_summary", "get_recovery_summary"])
        self.assertEqual(len(model.observed), 2)
        self.assertIn("not_recorded", model.last_summary)
        self.assertEqual(reason, "complete")
        self.assertTrue(answer.answer)

    def test_tenant_isolation_missing_data_and_argument_injection(self):
        with self.factory() as db:
            box = self.toolbox(db)
            result = box.execute("get_training_summary", {"days": 7})
            self.assertEqual(len(result["logs"]), 1)
            self.assertEqual(result["logs"][0]["completion"], "completed")
            self.assertEqual(box.execute("get_training_summary", {"user_id": 2})["status"], "error")
            self.assertEqual(box.execute("execute_sql", {"sql": "select 1"})["status"], "error")
            nutrients = box.execute("get_diet_summary", {})["intake"]
            self.assertEqual(nutrients["calories_kcal"], {"recorded_sum": 300.0, "unknown_meals": 1})
            self.assertIsNone(nutrients["protein_g"]["recorded_sum"])

    def test_repeated_calls_stop_at_budget(self):
        model = ScriptedModel([("get_training_summary", {})], repeat=True)
        with self.factory() as db:
            _, trace, reason = run_react(model, self.toolbox(db), {}, "训练", [], CoachAnswer, max_calls=4)
        self.assertEqual(len(trace), 4)
        self.assertEqual(reason, "tool_limit")

    def test_timeout_stops_without_tool_execution(self):
        with self.factory() as db:
            _, trace, reason = run_react(ScriptedModel(), self.toolbox(db), {}, "训练", [], CoachAnswer, max_seconds=0)
        self.assertEqual(trace, [])
        self.assertEqual(reason, "time_limit")

    def test_consent_and_medical_guard_never_invoke_model(self):
        with patch("langchain_openai.ChatOpenAI") as model:
            self.assertFalse(answer_coach_question("俯卧撑怎么做", [], allow_llm=False)["used_llm"])
            self.assertFalse(answer_coach_question("膝盖疼怎么办", [], allow_llm=True)["used_llm"])
            self.assertFalse(answer_coach_question("本周怎么练", [], allow_llm=True, recovery_stop=True)["used_llm"])
            model.assert_not_called()

    def create_diet_draft(self):
        model = ScriptedModel([("prepare_diet_target", {})], ["diet_target"])
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "synthetic-test-key"}), \
             patch("langchain_openai.ChatOpenAI", return_value=model), \
             patch("app.api.coach.retrieve_documents", return_value=([], None)):
            response = self.client.post("/api/shaping/intelligence/qa", json={
                "question": "按今天安排生成饮食目标草案", "privacy_consent": True,
                "context": {"page": "diet", "selected_date": self.day.isoformat()}})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["agent_mode"], "react")
        self.assertEqual(len(body["actions"]), 1)
        return body["actions"][0]["id"]

    def test_action_draft_confirmation_readback_and_replay(self):
        draft_id = self.create_diet_draft()
        with self.factory() as db:
            self.assertIsNone(db.get(DietDayAdjustmentRecord, (1, self.day)))
        url = f"/api/shaping/intelligence/qa/actions/{draft_id}"
        self.assertEqual(self.client.put(url, headers={"x-user": "2"}, json={"decision": "adopted"}).status_code, 404)
        result = self.client.put(url, json={"decision": "adopted"})
        self.assertEqual(result.status_code, 200, result.text)
        with self.factory() as db:
            item = db.get(DietDayAdjustmentRecord, (1, self.day))
            self.assertEqual(item.status, "adopted")
            self.assertGreater(item.suggestion["calories_kcal"], 0)
        self.assertEqual(self.client.put(url, json={"decision": "adopted"}).status_code, 200)

    def test_cancel_changes_no_active_target(self):
        draft_id = self.create_diet_draft()
        result = self.client.put(f"/api/shaping/intelligence/qa/actions/{draft_id}", json={"decision": "ignored"})
        self.assertEqual(result.status_code, 200)
        with self.factory() as db:
            self.assertIsNone(db.get(DietDayAdjustmentRecord, (1, self.day)))

    def test_plan_draft_preserves_current_week_and_saves_next_week(self):
        with self.factory() as db:
            log = db.scalar(select(TrainingLogRecord).where(TrainingLogRecord.user_id == 1))
            db.add(RecoveryCheckinRecord(user_id=1, log_id=log.id, checkin_date=self.day,
                soreness=2, sleep_hours=8, sleep_quality=4, energy=4, is_sick=False,
                warning_symptom="none", status="good", message="恢复良好"))
            source = self.day - timedelta(days=self.day.weekday())
            original = db.get(WeeklyPlanRecord, (1, source)).plan_data
            target = source + timedelta(days=7)
            db.commit()
        model = ScriptedModel([("prepare_next_week_plan", {})], ["plan_adjustment"])
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "synthetic-test-key"}), \
             patch("langchain_openai.ChatOpenAI", return_value=model), \
             patch("app.api.coach.retrieve_documents", return_value=([], None)):
            response = self.client.post("/api/shaping/intelligence/qa", json={
                "question": "生成下周训练调整草案", "privacy_consent": True})
        self.assertEqual(response.status_code, 200, response.text)
        draft = response.json()["actions"][0]
        with self.factory() as db:
            self.assertIsNone(db.get(WeeklyPlanRecord, (1, target)))
            self.assertEqual(db.get(WeeklyPlanRecord, (1, source)).plan_data, original)
        result = self.client.put(f"/api/shaping/intelligence/qa/actions/{draft['id']}", json={"decision": "adopted"})
        self.assertEqual(result.status_code, 200, result.text)
        with self.factory() as db:
            self.assertIsNotNone(db.get(WeeklyPlanRecord, (1, target)))
            self.assertEqual(db.get(WeeklyPlanRecord, (1, source)).plan_data, original)

    def test_partial_week_does_not_treat_unrecorded_days_as_failure(self):
        from app.services.coach_plan import compute_plan_adjustment
        with self.factory() as db:
            source = self.day - timedelta(days=self.day.weekday())
            plan = db.get(WeeklyPlanRecord, (1, source))
            updated = dict(plan.plan_data)
            updated["training_weekdays"] = [1, 2, 3, 4, 5, 6, 7]
            plan.plan_data = updated
            db.flush()
            preview = compute_plan_adjustment(db, 1, source, as_of=self.day)
            self.assertEqual(preview["stats"]["completion_rate"], 1)
            self.assertEqual(preview["stats"]["planned_days_evaluated"], 1)
            self.assertEqual(preview["stats"]["unrecorded_plan_days"], self.day.weekday())

    def test_stored_recovery_warning_blocks_cloud_model_even_without_key(self):
        with self.factory() as db:
            log = db.scalar(select(TrainingLogRecord).where(TrainingLogRecord.user_id == 1))
            db.add(RecoveryCheckinRecord(user_id=1, log_id=log.id, checkin_date=self.day,
                soreness=3, sleep_hours=8, sleep_quality=4, energy=4, is_sick=False,
                warning_symptom="sharp_pain", status="stop", message="暂停"))
            db.commit()
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": ""}), patch("langchain_openai.ChatOpenAI") as model:
            response = self.client.post("/api/shaping/intelligence/qa", json={
                "question": "本周怎么安排训练", "privacy_consent": True})
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.json()["used_llm"])
            self.assertEqual(response.json()["actions"], [])
            model.assert_not_called()

    def test_stale_or_expired_draft_is_rejected(self):
        draft_id = self.create_diet_draft()
        with self.factory() as db:
            db.scalar(select(BodyProfileRecord).where(BodyProfileRecord.user_id == 1)).weight_kg = 82
            db.commit()
        url = f"/api/shaping/intelligence/qa/actions/{draft_id}"
        self.assertEqual(self.client.put(url, json={"decision": "adopted"}).status_code, 409)
        with self.factory() as db:
            db.get(CoachActionDraftRecord, draft_id).created_at = datetime.now(timezone.utc) - timedelta(minutes=16)
            db.commit()
        self.assertEqual(self.client.put(url, json={"decision": "adopted"}).status_code, 409)

if __name__ == "__main__":
    unittest.main()
