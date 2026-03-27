from pydantic import BaseModel, Field
from typing import Optional


# ========== Evaluate ==========

class EvalRequest(BaseModel):
    goal_text: str = Field(..., description="Формулировка цели для оценки", min_length=5)
    employee_id: int = Field(..., description="ID сотрудника из HR-системы")
    quarter: str = Field(..., description="Квартал: Q1, Q2, Q3 или Q4", pattern="^Q[1-4]$")
    year: int = Field(..., description="Год", ge=2020, le=2030)


class StrategicAlignment(BaseModel):
    level: str = Field(..., description="Уровень связки: strategic / functional / operational")
    source: str = Field("", description="Источник связки: KPI, цель руководителя или стратегический документ")


class SmartScores(BaseModel):
    specific: float = Field(..., description="Specific / Конкретность (0.0–1.0)")
    measurable: float = Field(..., description="Measurable / Измеримость (0.0–1.0)")
    achievable: float = Field(..., description="Achievable / Достижимость (0.0–1.0)")
    relevant: float = Field(..., description="Relevant / Релевантность (0.0–1.0)")
    time_bound: float = Field(..., description="Time-bound / Ограниченность во времени (0.0–1.0)")


class AlertItem(BaseModel):
    level: str = Field(..., description="Уровень: critical / warning / info")
    code: str = Field(..., description="Код алерта: SMART_LOW, F16_TOO_FEW, F17_NO_STRATEGIC_LINK и др.")
    message: str = Field(..., description="Текст предупреждения на русском")


class EvalResponse(BaseModel):
    goal_id: Optional[str] = Field(None, description="ID записи оценки в локальной БД (eval-{id})")
    goal_text: str = Field(..., description="Оцениваемая формулировка цели")
    smart_scores: SmartScores = Field(..., description="Скоры по 5 критериям SMART (0.0–1.0)")
    smart_index: float = Field(..., description="Среднее арифметическое 5 SMART-скоров", ge=0, le=1)
    recommendations: list[str] = Field(..., description="Рекомендации по слабым критериям (S:/M:/A:/R:/T:)")
    improved_goal: Optional[str] = Field(None, description="Переформулировка в SMART, если smart_index < 0.7")
    alerts: list[AlertItem] = Field([], description="Системные алерты по F-16..F-21")


# ========== Batch Evaluate ==========

class BatchEvalRequest(BaseModel):
    employee_id: int = Field(..., description="ID сотрудника из HR-системы")
    quarter: str = Field(..., description="Квартал: Q1, Q2, Q3 или Q4", pattern="^Q[1-4]$")
    year: int = Field(..., description="Год", ge=2020, le=2030)


class GoalEval(BaseModel):
    goal_id: str = Field(..., description="UUID цели из remote DB")
    goal_text: str = Field(..., description="Полный текст цели")
    overall_index: float = Field(..., description="SMART-индекс (0.0–1.0)")
    goal_type: str = Field(..., description="Тип: activity / output / impact")
    alignment_level: str = Field(..., description="Связка: strategic / functional / operational")
    smart_scores: Optional[SmartScores] = Field(None, description="Скоры по 5 SMART-критериям")


class BatchSummary(BaseModel):
    avg_index: float = Field(..., description="Средний SMART-индекс по всем целям")
    total_goals: int = Field(..., description="Количество оценённых целей")
    total_weight: float = Field(..., description="Суммарный вес целей (%)")
    weakest_criterion: str = Field(..., description="Самый слабый SMART-критерий")
    warnings: list[str] = Field([], description="Предупреждения уровня набора целей")


class BatchEvalResponse(BaseModel):
    employee_name: str = Field(..., description="ФИО сотрудника")
    department: str = Field(..., description="Название подразделения")
    goals: list[GoalEval] = Field(..., description="Оценки по каждой цели")
    summary: BatchSummary = Field(..., description="Сводка по набору целей")


# ========== Generate ==========

class GenerateRequest(BaseModel):
    employee_id: int = Field(..., description="ID сотрудника из HR-системы")
    quarter: str = Field(..., description="Квартал: Q1, Q2, Q3 или Q4", pattern="^Q[1-4]$")
    year: int = Field(..., description="Год планирования", ge=2020, le=2030)
    focus_area: Optional[str] = Field(None, description="Фокус-направление, напр. 'цифровизация', 'снижение затрат'")


class GeneratedGoal(BaseModel):
    text: str = Field(..., description="Формулировка цели в SMART-формате")
    metric: str = Field("", description="Количественный показатель достижения")
    deadline: str = Field("", description="Срок достижения (YYYY-MM-DD или описание)")
    weight: Optional[int] = Field(None, description="Вес цели в наборе (%, суммарно 100)")
    source_doc: str = Field("", description="Название ВНД-документа — источника цели")
    source_quote: str = Field("", description="Цитата из ВНД-документа")
    smart_index: float = Field(0.0, description="Авто-SMART-оценка (0.0–1.0)")
    goal_type: str = Field("output", description="Тип: activity / output / impact")
    strategic_alignment: StrategicAlignment = Field(..., description="Уровень стратегической связки + источник")
    rationale: str = Field("", description="Обоснование: почему предложена именно эта цель (связь с KPI, ВНД, целью руководителя)")
    matched_chunks: list["RagChunk"] = Field([], description="Фрагменты ВНД, использованные для генерации этой конкретной цели")


class RagChunk(BaseModel):
    doc_title: str = Field(..., description="Название ВНД-документа")
    doc_type: str = Field("", description="Тип документа: vnd, instruction, standard, kpi_framework")
    score: float = Field(..., description="Cosine similarity score (0.0–1.0)")
    text_preview: str = Field("", description="Превью текста фрагмента (до 200 символов)")


class GenerateContext(BaseModel):
    manager_goals_used: bool = Field(..., description="Были ли использованы цели руководителя")
    kpis_used: list[str] = Field([], description="Названия KPI, включённых в контекст генерации")
    vnd_docs_used: int = Field(0, description="Количество уникальных ВНД-документов в RAG-результатах")
    rag_chunks: list[RagChunk] = Field([], description="Извлечённые фрагменты ВНД с релевантностью")
    avg_rag_score: float = Field(0.0, description="Средняя релевантность RAG-чанков (0.0–1.0)")


class GenerateResponse(BaseModel):
    goals: list[GeneratedGoal] = Field(..., description="Сгенерированные 3–5 целей в SMART-формате")
    context: GenerateContext = Field(..., description="Контекст генерации: источники, KPI, RAG-фрагменты")
    warnings: list[str] = Field([], description="Предупреждения: дублирование, вес, галлюцинация источника")


class AcceptRequest(BaseModel):
    employee_id: int = Field(..., description="ID сотрудника")
    quarter: str = Field(..., description="Квартал: Q1–Q4", pattern="^Q[1-4]$")
    year: int = Field(..., description="Год", ge=2020, le=2030)
    goals: list[GeneratedGoal] = Field(..., description="Выбранные цели из предложенного набора")


# ========== Dashboard ==========

class DeptQuality(BaseModel):
    id: int = Field(..., description="ID подразделения")
    name: str = Field(..., description="Название подразделения")
    avg_smart_index: float = Field(..., description="Средний SMART-индекс по подразделению")
    total_goals: int = Field(..., description="Общее количество целей за год")
    strategic_ratio: float = Field(..., description="Доля стратегически связанных целей (0.0–1.0)")
    weakest_criterion: str = Field(..., description="Самый слабый SMART-критерий")
    quarters: dict[str, float] = Field({}, description="SMART-индекс по кварталам: {Q1: 0.7, Q2: null, ...}")


class DashboardResponse(BaseModel):
    departments: list[DeptQuality] = Field(..., description="Данные по всем подразделениям")
    org_avg: float = Field(..., description="Средний SMART-индекс по организации")
    top_issues: list[str] = Field([], description="Топ-проблемы: % активностей, % без стратегии")


# ========== Employees ==========

class EmployeeShort(BaseModel):
    id: int = Field(..., description="ID сотрудника")
    full_name: str = Field(..., description="ФИО")
    position: str = Field(..., description="Должность")
    department: str = Field(..., description="Подразделение")
    goals_count: int = Field(0, description="Количество целей в системе")
