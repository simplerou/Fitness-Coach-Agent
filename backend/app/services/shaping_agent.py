"""保留规则分流与本地降级；授权后由 LangGraph ReAct 循环调用受控业务工具。"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CoachAnswer(BaseModel):
    answer: str = Field(min_length=10, max_length=1200)
    safety_note: str | None = Field(default=None, max_length=300)
    referenced_exercise_ids: list[int] = Field(default_factory=list, max_length=4)
    referenced_source_keys: list[str] = Field(default_factory=list, max_length=6)
    action_ids: list[str] = Field(default_factory=list, max_length=2)


MEDICAL_TERMS = ("疼痛", "关节痛", "膝盖疼", "胸闷", "受伤", "骨折", "诊断", "治疗", "肿胀", "锐痛", "胸痛", "头晕", "疾病", "康复")


def route_question(question: str) -> Literal["medical", "substitution", "technique", "schedule"]:
    text = question.casefold()
    if any(term in text for term in MEDICAL_TERMS): return "medical"
    if any(term in text for term in ("替代", "器械没", "没有器械", "居家", "占用")): return "substitution"
    if any(term in text for term in ("怎么做", "动作", "姿势", "呼吸", "发力", "要领", "错误")): return "technique"
    return "schedule"


def retrieve_exercises(question: str, exercises: list[Any], limit: int = 4) -> list[Any]:
    tokens = [item for item in re.split(r"[\s，。！？、]+", question.casefold()) if item]
    scored = []
    for exercise in exercises:
        fields = [exercise.name.casefold(), exercise.slug.casefold(), exercise.category.casefold(),
                  *(str(value).casefold() for value in exercise.target_muscles)]
        score = sum(3 if token in fields[0] else 1 for token in tokens if any(token in field for field in fields))
        if exercise.name in question: score += 8
        if score: scored.append((score, exercise))
    return [row[1] for row in sorted(scored, key=lambda item: (-item[0], item[1].id))[:limit]]


def _fallback_answer(intent: str, matches: list[Any], plan_context: dict[str, Any] | None = None) -> CoachAnswer:
    if intent == "schedule" and isinstance(plan_context, dict):
        sessions = [row for row in plan_context.get("sessions", []) if isinstance(row, dict)]
        if sessions:
            summary = "；".join(f"{row.get('day', '训练日')}：{row.get('title', '训练安排')}" for row in sessions)
            return CoachAnswer(answer=f"当前周计划为：{summary}。请优先按原计划执行；需要调整时一次只改一个变量，并结合最近恢复打卡决定是否减量。")
    if not matches:
        return CoachAnswer(answer="当前动作库里没有检索到足够匹配的数据。请补充具体动作名或目标肌群，我会只依据动作库继续查找。")
    item = matches[0]
    cues = "；".join(item.cues)
    alternatives = "、".join(f"{row['name']}（{row['scene']}）" for row in item.alternatives) or "动作库暂无替代动作"
    if intent == "substitution":
        answer = f"{item.name}主要训练{'、'.join(item.target_muscles)}。同目标肌群可考虑：{alternatives}。退阶：{'、'.join(item.regressions) or '暂无'}；进阶：{'、'.join(item.progressions) or '暂无'}。"
    else:
        answer = f"{item.name}的动作要领：{cues}。常见错误：" + "；".join(f"{row['error']}，可用{row['correction']}修正" for row in item.common_errors)
    return CoachAnswer(answer=answer, safety_note="动作应在无痛、可控制范围内完成；出现关节疼痛、锐痛或肿胀时停止。",
                       referenced_exercise_ids=[item.id])


def answer_coach_question(question: str, exercises: list[Any], plan_context: dict[str, Any] | None = None,
                          retrieved_documents: list[dict[str, Any]] | None = None,
                          retrieval_note: str | None = None, allow_llm: bool = False,
                          toolbox=None, history: list[dict] | None = None, page_context: dict | None = None,
                          recovery_stop: bool = False) -> dict[str, Any]:
    intent = route_question(question)
    retrieved_documents = retrieved_documents or []
    exercise_ids = {row.get("exercise_id") for row in retrieved_documents if row.get("source_type") == "exercise"}
    matches = [row for row in exercises if row.id in exercise_ids]
    if intent == "medical":
        result = CoachAnswer(answer="这个问题涉及疼痛、受伤或疾病，我不能做诊断或给出康复处方。请先停止引发不适的动作，并咨询医生或具备资质的专业人士。",
                             safety_note="若症状明显、持续或加重，请及时就医。")
        return {"intent": intent, "answer": result.model_dump(), "used_llm": False, "matches": [],
                "retrieved_documents": [], "fallback_reason": "问题涉及疼痛、受伤或疾病，本次按安全规则跳过云端模型。"}
    if recovery_stop or (toolbox and toolbox.blocked):
        result = CoachAnswer(answer="最近一次恢复打卡存在关节疼痛、锐痛或肿胀等风险信号，暂不提供训练安排或进阶建议。请停止引发不适的动作，并咨询专业人士。",
                             safety_note="若症状明显、持续或加重，请及时就医。")
        return {"intent": intent, "answer": result.model_dump(), "used_llm": False, "matches": [],
                "retrieved_documents": [], "fallback_reason": "根据最近恢复记录执行安全提示，未调用云端模型。"}
    if not matches and not any(row.get("source_type") == "external" for row in retrieved_documents):
        matches = retrieve_exercises(question, exercises)
    fallback = _fallback_answer(intent, matches, plan_context)
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not allow_llm or not api_key:
        external_docs = [row for row in retrieved_documents if row.get("source_type") in {"external", "web"}]
        if external_docs:
            excerpts = "\n".join(f"{row['title']}（{row['source_name']}）：{row['body'][:360]}"
                                  for row in external_docs[:2])
            fallback = CoachAnswer(answer=f"本地检索到以下参考资料摘要：\n{excerpts}\n\n这些内容是一般训练信息，具体安排仍需结合个人目标、训练经验和恢复情况。",
                                   referenced_source_keys=[row["document_key"] for row in external_docs[:2]])
        fallback_reason = ("未勾选云端模型授权，本次使用本地 BM25 检索与动作库规则回答。"
                           if not allow_llm else "后端未读取到 DASHSCOPE_API_KEY，本次使用本地规则并展示已检索来源。")
        return {"intent": intent, "answer": fallback.model_dump(), "used_llm": False, "matches": matches,
                "retrieved_documents": retrieved_documents,
                "fallback_reason": fallback_reason}
    try:
        from langchain_openai import ChatOpenAI

        context = {"exercises": [{"id": row.id, "name": row.name, "category": row.category,
                    "target_muscles": row.target_muscles, "cues": row.cues, "common_errors": row.common_errors,
                    "regressions": row.regressions, "progressions": row.progressions,
                    "alternatives": row.alternatives} for row in matches], "knowledge_documents": [
                    {"document_key": row["document_key"], "title": row["title"], "source_type": row["source_type"],
                     "body": row["body"], "source_name": row["source_name"], "source_url": row["source_url"]}
                    for row in retrieved_documents], "plan": plan_context or {}}
        model = ChatOpenAI(model=os.getenv("SHAPING_AGENT_MODEL", os.getenv("DIET_AGENT_MODEL", "qwen-plus")),
            api_key=api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", temperature=0.1,
            timeout=25, max_retries=0, max_tokens=1800)

        from .coach_react import run_react
        from .coach_tools import CoachToolbox
        if toolbox is None:
            # 保持旧服务调用兼容；正式HTTP入口使用绑定登录账号的工具箱。
            class NoTools:
                trace = []
                proposals = {}
                def definitions(self): return []
            toolbox = NoTools()
        context["page_context"] = page_context or {}
        result, trace, stop_reason = run_react(model, toolbox, context, question, history or [], CoachAnswer)
        if isinstance(toolbox, CoachToolbox):
            retrieved_documents = list(toolbox.documents.values())
            matches = list({row.id: row for row in matches + [
                toolbox.exercises[key] for key in toolbox.exercise_ids if key in toolbox.exercises]}.values())
        valid_ids = {row.id for row in matches}
        valid_source_keys = {row["document_key"] for row in retrieved_documents}
        result.referenced_exercise_ids = [item for item in result.referenced_exercise_ids if item in valid_ids]
        result.referenced_source_keys = [item for item in result.referenced_source_keys if item in valid_source_keys]
        result.action_ids = list(dict.fromkeys(key for key in result.action_ids if key in toolbox.proposals))[:2]
        return {"tool_trace": trace, "stop_reason": stop_reason, "intent": intent, "answer": result.model_dump(), "used_llm": True, "matches": matches,
                "retrieved_documents": retrieved_documents,
                "fallback_reason": None}
    except Exception as exc:
        error_type = type(exc).__name__
        logger.warning("Shaping coach model call failed (%s; module=%s).", error_type, getattr(exc, "name", None))
        if isinstance(exc, ImportError):
            missing_module = getattr(exc, "name", None)
            if missing_module:
                reason = f"Agent 运行时导入模块 {missing_module} 失败；请检查该模块与当前环境中的 LangChain 依赖版本是否兼容。"
            else:
                reason = f"Agent 运行时导入失败（{error_type}）；请查看后端终端中的模块错误详情。"
        elif error_type in {"AuthenticationError", "PermissionDeniedError"}:
            reason = "云端模型认证失败，请检查 DASHSCOPE_API_KEY 是否有效及是否有调用权限。"
        elif error_type == "RateLimitError":
            reason = "云端模型请求频率或额度受限，请检查 DashScope 配额后重试。"
        elif error_type in {"APIConnectionError", "APITimeoutError", "TimeoutError"}:
            reason = "连接云端模型失败或请求超时，请检查网络后重试。"
        elif error_type == "BadRequestError":
            reason = "云端模型拒绝了请求，请核对 SHAPING_AGENT_MODEL 配置和模型支持情况。"
        else:
            reason = f"云端模型调用失败（{error_type}），本次已回退到动作库规则回答。"
        return {"tool_trace": getattr(toolbox, "trace", []), "stop_reason": "error",
                "intent": intent, "answer": fallback.model_dump(), "used_llm": False, "matches": matches,
                "retrieved_documents": retrieved_documents, "fallback_reason": reason}
