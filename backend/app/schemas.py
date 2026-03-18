from pydantic import BaseModel, Field
from typing import Optional


# ========== Evaluate ==========

class EvalRequest(BaseModel):
    goal_text: str = Field(..., description="Формулировка цели для оценки", min_length=5)
    employee_id: int = Field(..., description="ID сотрудника из HR-системы")
    quarter: str = Field(..., description="Квартал: Q1, Q2, Q3 или Q4", pattern="^Q[1-4]$")
    year: int = Field(..., description="Год", ge=2020, le=2030)


class StrategicAlignment(BaseModel):
    level: str  # strategic / functional / operational
    source: str


class SmartScores(BaseModel):
    specific: float
    measurable: float
    achievable: float
    relevant: float
    time_bound: float


class AlertItem(BaseModel):
    level: str   # critical / warning / info
    code: str
    message: str


class EvalResponse(BaseModel):
    goal_id: Optional[str] = Field(None, description="ID записи оценки в локальной БД")
    goal_text: str = Field(..., description="Оцениваемая формулировка цели")
    smart_scores: SmartScores = Field(..., description="Скоры по 5 критериям SMART (0.0–1.0)")
    smart_index: float = Field(..., description="Среднее арифметическое 5 SMART-скоров", ge=0, le=1)
    recommendations: list[str] = Field(..., description="Рекомендации по слабым критериям (S:/M:/A:/R:/T:)")
    improved_goal: Optional[str] = Field(None, description="Переформулировка в SMART, если smart_index < 0.7")
    alerts: list[AlertItem] = Field([], description="Системные алерты по F-16..F-19")


# ========== Batch Evaluate ==========

class BatchEvalRequest(BaseModel):
    employee_id: int
    quarter: str
    year: int


class GoalEval(BaseModel):
    goal_id: str
    goal_text: str
    overall_index: float
    goal_type: str
    alignment_level: str
    smart_scores: Optional[SmartScores] = None


class BatchSummary(BaseModel):
    avg_index: float
    total_goals: int
    total_weight: float
    weakest_criterion: str
    warnings: list[str]


class BatchEvalResponse(BaseModel):
    employee_name: str
    department: str
    goals: list[GoalEval]
    summary: BatchSummary


# ========== Generate ==========

class GenerateRequest(BaseModel):
    employee_id: int = Field(..., description="ID сотрудника из HR-системы")
    quarter: str = Field(..., description="Квартал: Q1, Q2, Q3 или Q4", pattern="^Q[1-4]$")
    year: int = Field(..., description="Год планирования", ge=2020, le=2030)
    focus_area: Optional[str] = Field(None, description="Фокус-направление, напр. 'цифровизация', 'снижение затрат'")


class GeneratedGoal(BaseModel):
    text: str
    metric: str
    deadline: str
    weight: Optional[int] = None
    source_doc: str
    source_quote: str
    smart_index: float
    goal_type: str
    strategic_alignment: StrategicAlignment


class RagChunk(BaseModel):
    doc_title: str
    doc_type: str
    score: float
    text_preview: str


class GenerateContext(BaseModel):
    manager_goals_used: bool
    kpis_used: list[str]
    vnd_docs_used: int
    rag_chunks: list[RagChunk] = []
    avg_rag_score: float = 0.0


class GenerateResponse(BaseModel):
    goals: list[GeneratedGoal]
    context: GenerateContext
    warnings: list[str]


class AcceptRequest(BaseModel):
    employee_id: int
    quarter: str
    year: int
    goals: list[GeneratedGoal]


# ========== Dashboard ==========

class DeptQuality(BaseModel):
    id: int
    name: str
    avg_smart_index: float
    total_goals: int
    strategic_ratio: float
    weakest_criterion: str
    quarters: dict[str, float]


class DashboardResponse(BaseModel):
    departments: list[DeptQuality]
    org_avg: float
    top_issues: list[str]


# ========== Employees ==========

class EmployeeShort(BaseModel):
    id: int
    full_name: str
    position: str
    department: str
    goals_count: int
