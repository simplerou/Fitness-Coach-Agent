"""基于 LangGraph 与通义千问生成受约束的每周训练安排。"""
from __future__ import annotations

import json
import os
from typing import Any, TypedDict

from pydantic import BaseModel, Field


class TrainingPlanConfigurationError(RuntimeError):
    """模型凭据或 Agent 依赖未配置。"""


class TrainingPlanGenerationError(RuntimeError):
    """模型输出不可用或不符合计划约束。"""


class SessionDraft(BaseModel):
    weekday: int = Field(ge=1, le=7)
    title: str = Field(min_length=2, max_length=40)
    focus: str = Field(min_length=2, max_length=40)
    description: str = Field(min_length=8, max_length=500)
    exercise_ids: list[int] = Field(default_factory=list, max_length=6)


class TrainingPlanDraft(BaseModel):
    sessions: list[SessionDraft] = Field(min_length=1, max_length=6)


class PlanAgentState(TypedDict, total=False):
    input_data: dict[str, Any]
    draft: TrainingPlanDraft


SYSTEM_PROMPT = """你是训练计划编排助手。请依据输入的用户偏好和动作库，为一周训练安排生成清晰、可执行的训练日内容。
规则：
1. sessions 必须对输入的每一个训练星期恰好生成一项，不能增加、遗漏或改动 weekday。
2. 动作只能从候选动作列表选取，exercise_ids 只能使用候选项中提供的 id；不能编造动作、器械、动作要领或组次数。候选动作可在不同训练日重复，但尽量合理分配。
3. 训练内容必须符合用户选择的训练目标、经验、器械和单次时长。用户偏好动作优先纳入合适的训练日。
4. title、focus、description 使用简体中文，描述简短、一般性、易执行；不得提供医疗诊断、康复方案、保证效果或要求用户忍痛训练。用户有不适时应停止相关活动并寻求专业意见。
5. 如安排轻松有氧或活动度日，可将 exercise_ids 留空，并在描述中提醒按舒适节奏活动。
6. 严格返回给定结构，不输出额外字段或 Markdown。
"""


def _validate_draft(draft: TrainingPlanDraft, input_data: dict[str, Any]) -> None:
    expected_weekdays = input_data["training_weekdays"]
    actual_weekdays = [session.weekday for session in draft.sessions]
    if len(actual_weekdays) != len(expected_weekdays) or set(actual_weekdays) != set(expected_weekdays):
        raise ValueError("模型生成的训练日与用户选择不一致。")
    candidate_ids = {item["id"] for item in input_data["candidate_exercises"]}
    for session in draft.sessions:
        if len(session.exercise_ids) != len(set(session.exercise_ids)):
            raise ValueError("模型重复分配了训练动作。")
        if any(exercise_id not in candidate_ids for exercise_id in session.exercise_ids):
            raise ValueError("模型引用了动作库之外的动作。")


def generate_training_plan(input_data: dict[str, Any]) -> list[dict[str, Any]]:
    """以受约束的动作候选为依据生成训练日安排，不保存任何数据。"""
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise TrainingPlanConfigurationError(
            "生成 AI 训练计划需要 DASHSCOPE_API_KEY，请检查项目根目录 .env 并重启后端。"
        )
    model_name = (
        os.getenv("TRAINING_PLAN_AGENT_MODEL", "").strip()
        or os.getenv("SHAPING_AGENT_MODEL", "").strip()
        or os.getenv("DIET_AGENT_MODEL", "qwen-plus").strip()
        or "qwen-plus"
    )
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI
        from langgraph.graph import END, START, StateGraph

        model = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            temperature=0.2,
            timeout=45,
            max_retries=1,
        ).with_structured_output(TrainingPlanDraft, method="function_calling")

        def check_input(state: PlanAgentState) -> dict[str, Any]:
            data = state.get("input_data")
            if not isinstance(data, dict) or not data.get("training_weekdays"):
                raise ValueError("缺少已校验的训练日安排。")
            return {}

        def compose(state: PlanAgentState) -> dict[str, Any]:
            response = model.invoke([
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content="请根据以下资料生成本周计划：\n" + json.dumps(state["input_data"], ensure_ascii=False)),
            ])
            draft = response if isinstance(response, TrainingPlanDraft) else TrainingPlanDraft.model_validate(response)
            return {"draft": draft}

        def validate_output(state: PlanAgentState) -> dict[str, Any]:
            _validate_draft(state["draft"], state["input_data"])
            return {}

        graph = StateGraph(PlanAgentState)
        graph.add_node("check_input", check_input)
        graph.add_node("compose", compose)
        graph.add_node("validate_output", validate_output)
        graph.add_edge(START, "check_input")
        graph.add_edge("check_input", "compose")
        graph.add_edge("compose", "validate_output")
        graph.add_edge("validate_output", END)
        result = graph.compile().invoke({"input_data": input_data})
        return [session.model_dump() for session in result["draft"].sessions]
    except TrainingPlanConfigurationError:
        raise
    except ImportError as exc:
        raise TrainingPlanConfigurationError(
            "AI 训练计划依赖尚未安装，请在项目目录运行 pip install -r backend/requirements.txt 后重启后端。"
        ) from exc
    except Exception as exc:
        raise TrainingPlanGenerationError(
            "千问暂时无法生成有效的训练计划，请检查模型配置或额度后重试；本次计划未保存。"
        ) from exc
