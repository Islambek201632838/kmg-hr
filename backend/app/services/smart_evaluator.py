import json
import google.generativeai as genai
from app.config import settings

_configured = False


def _ensure_configured():
    global _configured
    if not _configured:
        genai.configure(api_key=settings.gemini_api_key)
        _configured = True


SYSTEM_PROMPT = """Ты HR-эксперт по оценке целей сотрудников в нефтегазовой компании КМГ.
Оцени цель сотрудника по методологии SMART.

Для каждого критерия SMART дай оценку от 0.0 до 1.0.

Также определи:
- goal_type: "activity" (действие), "output" (результат) или "impact" (влияние на бизнес)
- strategic_alignment: уровень связки цели со стратегией:
  - level: "strategic" / "functional" / "operational"
  - source: название KPI, цель руководителя или стратегический документ

Рекомендации: только по слабым критериям (score < 0.8), начинай каждую с метки критерия (S:, M:, A:, R:, T:).

Если smart_index < 0.7 — предложи improved_goal: переформулировку в SMART-формате (output/impact, с метрикой и сроком).
Если smart_index >= 0.7 — improved_goal: null.

Ответ СТРОГО в JSON:
{
  "smart_scores": {
    "specific": 0.0,
    "measurable": 0.0,
    "achievable": 0.0,
    "relevant": 0.0,
    "time_bound": 0.0
  },
  "smart_index": 0.0,
  "goal_type": "output",
  "strategic_alignment": {"level": "operational", "source": ""},
  "recommendations": ["S: ...", "M: ..."],
  "improved_goal": null
}"""


def build_user_prompt(
    goal_text: str,
    position: str,
    department: str,
    manager_goals: list[str],
    kpis: list[dict],
    historical_goals: list[str] | None = None,
) -> str:
    parts = [f"Цель сотрудника: \"{goal_text}\""]
    parts.append(f"Должность: {position}")
    parts.append(f"Подразделение: {department}")

    if manager_goals:
        parts.append("Цели руководителя на этот квартал:")
        for g in manager_goals:
            parts.append(f"  - {g}")

    if kpis:
        parts.append("KPI подразделения:")
        for k in kpis:
            parts.append(f"  - {k['title']}: {k['value']} {k['unit']}")

    if historical_goals:
        parts.append("Примеры целей аналогичных ролей (для оценки достижимости):")
        for g in historical_goals[:5]:
            parts.append(f"  - {g}")

    return "\n".join(parts)


async def evaluate_goal(
    goal_text: str,
    position: str,
    department: str,
    manager_goals: list[str],
    kpis: list[dict],
    historical_goals: list[str] | None = None,
) -> dict:
    """Call Gemini to evaluate a goal. Returns parsed JSON dict."""
    _ensure_configured()

    user_prompt = build_user_prompt(
        goal_text, position, department, manager_goals, kpis, historical_goals
    )

    model = genai.GenerativeModel("gemini-3-flash-preview")
    response = await model.generate_content_async(
        [
            {"role": "user", "parts": [SYSTEM_PROMPT + "\n\n" + user_prompt]},
        ],
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.3,
        ),
    )

    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        return _fallback_result()

    # Ensure smart_scores exists with defaults
    scores = result.setdefault("smart_scores", {})
    for key in ("specific", "measurable", "achievable", "relevant", "time_bound"):
        scores.setdefault(key, 0.5)

    # Recompute smart_index from scores
    vals = [scores[k] for k in ("specific", "measurable", "achievable", "relevant", "time_bound")]
    result["smart_index"] = round(sum(vals) / len(vals), 2)

    result.setdefault("goal_type", "output")
    result.setdefault("strategic_alignment", {"level": "operational", "source": ""})
    result.setdefault("recommendations", [])
    result.setdefault("improved_goal", None)

    return result


def _fallback_result() -> dict:
    """Fallback if Gemini returns unparseable response."""
    return {
        "smart_scores": {"specific": 0.5, "measurable": 0.5, "achievable": 0.5, "relevant": 0.5, "time_bound": 0.5},
        "smart_index": 0.5,
        "goal_type": "output",
        "strategic_alignment": {"level": "operational", "source": ""},
        "recommendations": ["Повторите оценку позже"],
        "improved_goal": None,
    }
