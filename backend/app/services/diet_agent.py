"""受控的 LangGraph 饮食建议工作流；营养目标计算仍由后端负责。"""
from __future__ import annotations

import os
import re
import logging
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)


class MealAdvice(BaseModel):
    day_index: int = Field(ge=0, le=6)
    meal: Literal["早餐", "午餐", "晚餐", "加餐"]
    example: str = Field(min_length=8, max_length=420)


class DietAdvice(BaseModel):
    overview: str = Field(min_length=10, max_length=500)
    change_summary: str = Field(min_length=8, max_length=420)
    diagnosis: list[str] = Field(min_length=1, max_length=5)
    food_examples: list[MealAdvice] = Field(min_length=28, max_length=28)
    habit_to_keep: str = Field(min_length=5, max_length=500)
    priority_adjustment: str = Field(min_length=5, max_length=700)
    training_timing_advice: list[str] = Field(min_length=1, max_length=4)
    tracking_period: str = Field(min_length=5, max_length=300)
    next_data: list[str] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def require_each_day_has_each_meal_once(self):
        expected = {"早餐", "午餐", "晚餐", "加餐"}
        actual = [(item.day_index, item.meal) for item in self.food_examples]
        if len(set(actual)) != 28 or any({item.meal for item in self.food_examples if item.day_index == day} != expected for day in range(7)):
            raise ValueError("AI 必须为一周每天的早餐、午餐、晚餐和加餐各提供一条建议。")
        return self


class DietAgentState(TypedDict, total=False):
    input_data: dict[str, Any]
    advice: DietAdvice


class DietAgentConfigurationError(RuntimeError):
    """模型服务尚未配置。"""


class DietAgentGenerationError(RuntimeError):
    """模型响应不可用或未通过安全校验。"""


SYSTEM_PROMPT = """你是健身饮食记录分析助手。你只根据输入数据总结记录并给出可执行的一般饮食建议，不提供医疗诊断或处方。

必须遵守：
1. 只使用输入中出现的用户资料、记录和后端目标；不得编造缺失数据、食物营养值或用户习惯。
2. 输入中的热量和三大营养素目标由后端计算。不要重算、修改或输出新的每日/每餐数值目标；分餐数字会由后端展示。
3. 诊断应引用输入中已有的记录事实。记录不完整时明确说明证据有限，不把未记录当作零。
4. 食物建议必须避开输入的过敏源、忌口和饮食偏好冲突；不要在建议正文中重复列出过敏源/忌口名称。不确定时请用户核对包装过敏原标签，不要保证食品绝对安全。
5. 示例只给常见食材组合和可执行替换，不虚构克数、热量或营养数据。加餐可以说明不饿时可不安排。
6. 不推荐补剂品牌，不承诺减重结果，不鼓励极端节食。记录显示摄入长期低于 BMR 时，优先提醒记录可能不完整并建议咨询专业人士。
7. 不输出 Markdown 围栏；严格按给定的结构化字段作答，使用简体中文。
"""


def _forbidden_terms(input_data: dict[str, Any]) -> list[str]:
    profile = input_data.get("profile", {})
    values = [profile.get("allergies"), profile.get("avoid_foods")]
    terms: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        for item in re.split(r"[,，、;；\n/]+", value):
            term = re.sub(r"[（(].*?[）)]", "", item.strip())
            term = re.sub(r"^(对|不吃|避免|忌食|忌口|不能吃)+", "", term)
            term = re.sub(r"(过敏|不耐受|禁忌|忌口)+$", "", term).strip()
            if len(term) >= 2 and term.casefold() not in {"无", "没有", "无过敏", "无忌口", "无已知过敏", "none", "no", "n/a"}:
                terms.add(term.casefold())
    return sorted(terms)


def _contains_forbidden_food(term: str, example: str) -> bool:
    """仅在实际餐食示例中拦截禁忌食材；明确的排除或替代表达不算摄入建议。"""
    normalized_example = re.sub(r"\s+", "", example).casefold()
    normalized_term = re.sub(r"\s+", "", term).casefold()
    for match in re.finditer(re.escape(normalized_term), normalized_example):
        preceding = normalized_example[max(0, match.start() - 12):match.start()]
        if re.search(r"(?:不含|无添加|不添加|不加|不放|不使用|不用|不要|避免|避开|忌用|不食用|不摄入|不要添加|替换为|替换成|替换掉|代替|替代|换成|改成|改用|去掉|剔除|排除)$", preceding):
            continue
        return True
    return False


def generate_diet_advice(input_data: dict[str, Any]) -> dict[str, Any]:
    """运行校验 → 单次结构化生成 → 约束检查的 LangGraph 工作流。"""
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise DietAgentConfigurationError("AI 饮食规划尚未配置 DASHSCOPE_API_KEY，请在项目 .env 中设置通义千问 API Key。")

    try:
        from langchain_openai import ChatOpenAI
        from langgraph.graph import END, START, StateGraph

        model = ChatOpenAI(
            model=os.getenv("DIET_AGENT_MODEL", "qwen-plus").strip() or "qwen-plus",
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            temperature=0.2,
            timeout=max(30, int(os.getenv("DIET_AGENT_TIMEOUT_SECONDS", "120"))),
            max_retries=1,
        ).with_structured_output(DietAdvice, method="function_calling")

        def check_input(state: DietAgentState) -> dict[str, Any]:
            data = state.get("input_data")
            if not isinstance(data, dict) or not data.get("target") or not data.get("profile"):
                raise ValueError("缺少已校验的档案或营养目标。")
            return {}

        def generate(state: DietAgentState) -> dict[str, Any]:
            from langchain_core.messages import HumanMessage, SystemMessage

            import json

            response = model.invoke([
                SystemMessage(content=SYSTEM_PROMPT + "\n本次请生成一周执行建议：planning_days 提供按日期排序的 7 天和对应训练/休息安排；day_index 0-6 必须严格对应 planning_days 的顺序（0 为计划首日，6 为第七日）。food_examples 必须恰好提供 28 项，每个 day_index 各有早餐、午餐、晚餐、加餐一项。结合训练日与休息日安排食物例子，尽量与 recent_meals 和 previous_plan 的菜品错开。change_summary 需说明这是首次计划，或结合哪些近期记录调整了哪些安排。只给常见食物搭配与可执行分量描述，不得编造热量、宏量营养数值，所有数值目标由后端计算。\n饮水分析补充规则：water_target_ml 若存在，是用户自行设置的个人参考值，不是医疗处方；只能描述其设置值与记录概况。若缺少目标或记录，不得自行编造目标、把未记录当作零、诊断脱水或宣称饮水不足。训练、天气与疾病等情况可能影响饮水需要，不能仅凭日志作医疗判断。"),
                HumanMessage(content="请基于以下已校验资料生成饮食分析建议：\n" + json.dumps(state["input_data"], ensure_ascii=False)),
            ])
            advice = response if isinstance(response, DietAdvice) else DietAdvice.model_validate(response)
            return {"advice": advice}

        def check_output(state: DietAgentState) -> dict[str, Any]:
            advice = state["advice"]
            examples = [item.example for item in advice.food_examples]
            conflicts = [
                term for term in _forbidden_terms(state["input_data"])
                if any(_contains_forbidden_food(term, example) for example in examples)
            ]
            if conflicts:
                raise ValueError("AI 餐食示例包含档案中标记的过敏源或忌口。")
            return {}

        workflow = StateGraph(DietAgentState)
        workflow.add_node("check_input", check_input)
        workflow.add_node("generate_advice", generate)
        workflow.add_node("check_output", check_output)
        workflow.add_edge(START, "check_input")
        workflow.add_edge("check_input", "generate_advice")
        workflow.add_edge("generate_advice", "check_output")
        workflow.add_edge("check_output", END)
        result = workflow.compile().invoke({"input_data": input_data})
        return result["advice"].model_dump()
    except DietAgentConfigurationError:
        raise
    except ImportError as exc:
        raise DietAgentConfigurationError("AI Agent 依赖尚未安装，请在项目目录运行 pip install -r backend/requirements.txt 后重启后端。") from exc
    except Exception as exc:
        root_cause = exc
        while root_cause.__cause__ is not None:
            root_cause = root_cause.__cause__
        safe_detail = re.sub(r"sk-[A-Za-z0-9._-]{8,}", "[已隐藏密钥]", str(root_cause))
        logger.error("饮食 AI 生成失败（%s）：%s", type(root_cause).__name__, safe_detail)
        raise DietAgentGenerationError("AI 饮食规划暂时无法生成，请稍后重试；本次未保存规划快照。") from exc
