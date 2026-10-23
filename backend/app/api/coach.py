"教练问答与草案确认；旧 /qa 路径不变，所有个人数据均按签名会话隔离。"
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from ..models.training_intelligence import ExerciseLibraryRecord, ExerciseKnowledgeDocumentRecord
from ..models.shaping_intelligence import QaLogRecord
from ..schemas.coach import CoachQuestionInput, CoachActionDecision
from ..services.coach_data import CoachData
from ..services.coach_tools import CoachToolbox
from ..services.coach_actions import save_drafts, decide_action
from ..services.exercise_knowledge import EMBEDDING_MODEL
from ..services.crag_retrieval import retrieve_with_crag
from ..services.shaping_agent import answer_coach_question, route_question

def create_coach_router(authenticate, session_factory):
    router = APIRouter(prefix="/api/shaping/intelligence", tags=["AI教练"])

    @router.post("/qa")
    def coach_qa(payload: CoachQuestionInput, user_id: int = Depends(authenticate)):
        day = payload.context.selected_date or date.today()
        if not date.today() - timedelta(days=365) <= day <= date.today() + timedelta(days=7):
            raise HTTPException(422, "页面日期超出教练可查询范围。")
        with session_factory() as db:
            exercises = db.scalars(select(ExerciseLibraryRecord).order_by(ExerciseLibraryRecord.id)).all()
            knowledge = db.scalars(select(ExerciseKnowledgeDocumentRecord).where(
                ExerciseKnowledgeDocumentRecord.review_status == "approved")).all()
            data = CoachData(db, user_id, day)
            docs, note = [], None
            crag = {"status": "not_run", "local_relevance": 0.0, "tavily_used": False}
            risk = route_question(payload.question) == "medical"
            recovery_stop = data.latest_stop() if not risk else False
            if not risk and not recovery_stop:
                docs, note, crag = retrieve_with_crag(
                    payload.question, knowledge,
                    allow_semantic=payload.privacy_consent,
                    allow_web_search=payload.privacy_consent,
                    consent_given=payload.privacy_consent,
                    top_k=8,
                )
            toolbox = CoachToolbox(data, exercises, knowledge, docs) if payload.privacy_consent and not risk else None
            plan = data.plan()["plan"]
            result = answer_coach_question(payload.question, exercises, plan,
                retrieved_documents=docs, retrieval_note=note, allow_llm=payload.privacy_consent,
                toolbox=toolbox, history=[item.model_dump() for item in payload.history] if payload.privacy_consent else [],
                page_context={"page": payload.context.page, "selected_date": day.isoformat()}, recovery_stop=recovery_stop)
            answer = result["answer"]
            actions = save_drafts(db, user_id, [toolbox.proposals[key] for key in answer.get("action_ids", [])
                if toolbox and key in toolbox.proposals]) if result["used_llm"] else []
            db.add(QaLogRecord(user_id=user_id, question=payload.question, answer=answer["answer"],
                intent=result["intent"], exercise_ids=answer["referenced_exercise_ids"], used_llm=result["used_llm"]))
            db.commit()
            references = {row.id: row for row in result["matches"]}
            documents = result["retrieved_documents"]
            return {"intent": result["intent"], **answer, "used_llm": result["used_llm"],
                "references": [{key: getattr(references[item], key) for key in (
                    "id", "slug", "name", "category", "target_muscles", "cues", "common_errors",
                    "regressions", "progressions", "alternatives", "demo_images", "demo_video_url")}
                    for item in answer["referenced_exercise_ids"] if item in references],
                "knowledge_sources": [{"document_key": row["document_key"], "title": row["title"],
                    "source_name": row["source_name"], "source_url": row["source_url"],
                    "source_published_at": row["source_published_at"], "retrieved_at": row["source_retrieved_at"],
                    "excerpt": row["body"][:520], "retrieval_channels": row["retrieval_channels"],
                    "bm25_score": row["bm25_score"], "vector_score": row["vector_score"]}
                    for row in documents if row["source_type"] in {"external", "web"}],
                "cited_source_keys": answer.get("referenced_source_keys", []),
                "embedding_model": EMBEDDING_MODEL,
                "vector_model_used": any("vector" in row["retrieval_channels"] for row in documents),
                "retrieval_method": ("BM25 + 向量 + RRF" if any("vector" in r["retrieval_channels"] for r in documents) else "中文 BM25")
                    + (" + Tavily" if crag["tavily_used"] else ""),
                "crag_status": crag["status"], "crag_local_relevance": crag["local_relevance"],
                "tavily_used": crag["tavily_used"],
                "model_note": "本次使用 ReAct Agent 按需查询并生成回答。" if result["used_llm"] else result.get("fallback_reason"),
                "retrieval_note": note, "agent_mode": "react" if result["used_llm"] else "local",
                "tool_trace": result.get("tool_trace", []), "stop_reason": result.get("stop_reason", "complete"),
                "actions": actions, "context_date": day.isoformat()}

    @router.put("/qa/actions/{action_id}")
    def confirm_action(action_id: int, payload: CoachActionDecision, user_id: int = Depends(authenticate)):
        with session_factory() as db:
            return decide_action(db, user_id, action_id, payload.decision)
    return router
