"模型只能调用此白名单；工具参数没有 user_id，所有数据查询固定当前会话账号。"
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable
from pydantic import BaseModel, ConfigDict, Field
from fastapi import HTTPException
from .coach_data import CoachData
from .coach_actions import prepare_diet, prepare_plan
from .exercise_knowledge import retrieve_documents

class EmptyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

class DateInput(EmptyInput):
    selected_date: date | None = Field(default=None, description="查询日期；省略时使用当前页面日期")

class PeriodInput(EmptyInput):
    days: int = Field(default=7, ge=1, le=84, description="截至页面日期的回溯天数，1至84天")

class SearchInput(EmptyInput):
    query: str = Field(min_length=1, max_length=160, description="具体动作名称、肌群或要领关键词")

@dataclass
class ToolSpec:
    name: str
    label: str
    description: str
    schema: type[BaseModel]
    handler: Callable

class CoachToolbox:
    def __init__(self, data: CoachData, exercises, knowledge_rows, documents):
        self.data = data
        self.exercises = {row.id: row for row in exercises}
        self.knowledge_rows = knowledge_rows
        self.documents = {row["document_key"]: row for row in documents}
        self.exercise_ids = {row["exercise_id"] for row in documents if row.get("exercise_id")}
        self.proposals = {}
        self.trace = []
        self.blocked = data.latest_stop()
        self.specs = {spec.name: spec for spec in [
            ToolSpec("get_week_plan", "查询周计划", "读取指定日期所在周的真实训练计划及当日安排。", DateInput, self.plan),
            ToolSpec("get_training_summary", "查询训练记录", "读取近期完成情况、RPE及动作组次重量；未记录不可推断。", PeriodInput, data.training),
            ToolSpec("get_recovery_summary", "查询恢复打卡", "读取酸痛、睡眠、精神与风险信号。", PeriodInput, data.recovery),
            ToolSpec("get_diet_summary", "查询饮食与目标", "读取当日已记录营养小计、未知项、饮水和规则计算目标。", DateInput, self.diet),
            ToolSpec("get_shaping_trend", "查询身体变化", "读取近期围度、体重与身体成分测量及日期；样本不足应说明。", PeriodInput, data.shaping),
            ToolSpec("search_exercise_knowledge", "检索动作知识", "从动作库与已审核资料检索要领或替代动作，保留来源。", SearchInput, self.search),
            ToolSpec("prepare_diet_target", "生成今日饮食草案", "仅在用户提出调整或采纳需求时生成规则计算的今日目标草案；不会采纳目标。", EmptyInput, lambda: self.prepare("diet_target")),
            ToolSpec("prepare_next_week_plan", "生成下周调整草案", "仅在用户要求调整下周计划时生成规则预览；只评估本周已到来的训练日，不保存周计划。", EmptyInput, lambda: self.prepare("plan_adjustment")),
        ]}

    def definitions(self):
        return [{"type": "function", "function": {"name": s.name, "description": s.description,
                "parameters": s.schema.model_json_schema()}} for s in self.specs.values()]

    def check_day(self, selected_date):
        if selected_date and not self.data.day - timedelta(days=365) <= selected_date <= date.today() + timedelta(days=7):
            raise ValueError("查询日期超出允许范围。")

    def plan(self, selected_date=None):
        self.check_day(selected_date)
        return self.data.plan(selected_date.isoformat() if selected_date else None)

    def diet(self, selected_date=None):
        self.check_day(selected_date)
        return self.data.diet(selected_date.isoformat() if selected_date else None)

    def search(self, query):
        docs, note = retrieve_documents(query, self.knowledge_rows, allow_semantic=True, top_k=5)
        self.documents.update({row["document_key"]: row for row in docs})
        self.exercise_ids.update(row["exercise_id"] for row in docs if row.get("exercise_id"))
        return {"source": "approved_exercise_knowledge", "retrieval_note": note,
                "documents": [{k: row[k] for k in ("document_key", "title", "body", "source_name")} for row in docs]}

    def prepare(self, kind):
        if self.blocked:
            raise HTTPException(409, "最近恢复记录存在风险，暂停相关调整建议。")
        proposal = prepare_diet(self.data) if kind == "diet_target" else prepare_plan(self.data)
        key = kind
        self.proposals[key] = proposal
        return {"proposal_id": key, "title": proposal["title"], "summary": proposal["summary"],
                "impact": proposal["impact"], "details": proposal["details"], "status": "awaiting_confirmation",
                "message": "仅生成草案；必须由用户在界面上确认，当前没有修改目标或计划。"}

    def execute(self, name, arguments):
        spec = self.specs.get(name)
        if spec is None:
            return {"status": "error", "message": "工具不在白名单内。"}
        try:
            params = spec.schema.model_validate(arguments).model_dump()
            return spec.handler(**params)
        except HTTPException as error:
            return {"status": "error", "message": str(error.detail)}
        except ValueError:
            return {"status": "error", "message": "工具参数无效，请修正日期、天数或查询关键词。"}
