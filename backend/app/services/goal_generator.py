import json
import asyncio
import google.generativeai as genai
from app.config import settings
from app.services.rag_pipeline import search_vnd
from app.services.smart_evaluator import evaluate_goal, _ensure_configured

GENERATE_PROMPT = """Ты HR-эксперт в нефтегазовой компании КМГ.
На основе предоставленных данных сгенерируй {count} целей для сотрудника в формате SMART.

Каждая цель ОБЯЗАТЕЛЬНО должна:
1. Быть привязана к конкретному ВНД-документу (укажи название и цитату)
2. Иметь количественную метрику достижения
3. Иметь конкретный дедлайн в рамках квартала
4. Быть типа "output" или "impact" (НЕ "activity")
5. Быть связана со стратегией компании или KPI подразделения
6. Суммарный weight всех целей должен быть равен 100

Для каждой цели выполни SMART-оценку (0.0-1.0 по каждому критерию):
- specific: конкретность формулировки
- measurable: наличие количественной метрики
- achievable: реалистичность для данной должности
- relevant: связь с KPI подразделения и стратегией
- time_bound: наличие конкретного срока
- smart_index: среднее арифметическое 5 критериев

Если smart_index какой-либо цели ниже 0.7, переформулируй её до уровня >= 0.7.

Для каждой цели ОБЯЗАТЕЛЬНО укажи поле "rationale" — 1-2 предложения, объясняющие ПОЧЕМУ предложена именно эта цель (какой KPI, ВНД или цель руководителя стали основой).

Ответ СТРОГО в JSON формате:
{{
  "goals": [
    {{
      "text": "Формулировка цели в SMART формате",
      "metric": "Количественный показатель достижения",
      "deadline": "YYYY-MM-DD",
      "weight": 20,
      "source_doc": "Название ВНД документа",
      "source_quote": "Конкретная цитата из документа",
      "goal_type": "output",
      "strategic_alignment": {{
        "level": "strategic",
        "source": "Название KPI или стратегического приоритета"
      }},
      "smart_scores": {{
        "specific": 0.9,
        "measurable": 0.85,
        "achievable": 0.8,
        "relevant": 0.9,
        "time_bound": 0.95
      }},
      "smart_index": 0.88,
      "rationale": "Цель основана на KPI 'Сокращение издержек' и п.3.2 Политики управления затратами"
    }}
  ]
}}"""


def build_generation_context(
    position: str,
    department: str,
    quarter: str,
    year: int,
    rag_chunks: list[dict],
    manager_goals: list[str],
    kpis: list[dict],
    focus_area: str | None = None,
    existing_count: int = 0,
    historical_goals: list[str] | None = None,
) -> str:
    parts = [
        f"Сотрудник: {position}, подразделение: {department}",
        f"Период: {quarter} {year}",
    ]

    if focus_area:
        parts.append(f"Фокус-направление: {focus_area}")

    if manager_goals:
        parts.append("\nЦели руководителя:")
        for g in manager_goals:
            parts.append(f"  - {g}")

    if kpis:
        parts.append("\nKPI подразделения:")
        for k in kpis:
            parts.append(f"  - {k['title']}: {k['value']} {k['unit']}")

    if historical_goals:
        parts.append("\nПримеры целей аналогичных ролей за предыдущие периоды (для оценки реалистичности):")
        for g in historical_goals[:5]:
            parts.append(f"  - {g}")

    if rag_chunks:
        parts.append("\nРелевантные фрагменты ВНД:")
        for ch in rag_chunks:
            parts.append(f"\n[{ch['doc_title']}] (релевантность: {ch['score']:.2f})")
            parts.append(ch["text"][:500])

    if existing_count > 0:
        parts.append(f"\nУ сотрудника уже есть {existing_count} целей за этот период.")

    return "\n".join(parts)


async def generate_goals(
    position: str,
    department: str,
    department_id: int,
    quarter: str,
    year: int,
    manager_goals: list[str],
    kpis: list[dict],
    existing_goals: list[str],
    focus_area: str | None = None,
    historical_goals: list[str] | None = None,
) -> dict:
    """Generate goals using RAG + Gemini with built-in SMART scoring (1 LLM call)."""
    _ensure_configured()

    # 1. RAG retrieval
    query = f"{position} {department} {quarter} {year} цели"
    if focus_area:
        query += f" {focus_area}"
    rag_chunks = await search_vnd(query, department_id=department_id, top_k=5)

    # 2. Determine count
    existing_count = len(existing_goals)
    needed = max(3, min(5, 5 - existing_count))

    # 3. Build context and call Gemini (generation + self-scoring in 1 call)
    context_text = build_generation_context(
        position, department, quarter, year,
        rag_chunks, manager_goals, kpis, focus_area, existing_count, historical_goals,
    )

    prompt = GENERATE_PROMPT.format(count=needed) + "\n\n" + context_text

    model = genai.GenerativeModel("gemini-2.0-flash")
    response = await model.generate_content_async(
        [{"role": "user", "parts": [prompt]}],
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.5,
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
        return {"goals": [], "context": _empty_context(kpis, manager_goals, rag_chunks), "warnings": ["Ошибка генерации. Попробуйте снова."]}

    goals = result.get("goals", [])

    # 4. Ensure defaults + compute smart_index if missing
    for goal in goals:
        goal.setdefault("text", "")
        goal.setdefault("metric", "")
        goal.setdefault("deadline", "")
        goal.setdefault("weight", 20)
        goal.setdefault("source_doc", "")
        goal.setdefault("source_quote", "")
        goal.setdefault("goal_type", "output")
        goal.setdefault("strategic_alignment", {"level": "functional", "source": ""})
        goal.setdefault("rationale", "")

        # Compute smart_index from smart_scores if present
        scores = goal.get("smart_scores", {})
        if scores:
            vals = [scores.get(k, 0.5) for k in ("specific", "measurable", "achievable", "relevant", "time_bound")]
            goal["smart_index"] = round(sum(vals) / len(vals), 2)
        else:
            goal.setdefault("smart_index", 0.7)

    # 5. Only reformulate weak goals (smart_index < 0.7) — parallel
    weak_goals = [g for g in goals if g["smart_index"] < 0.7]
    if weak_goals:
        async def reformulate(goal):
            try:
                eval_result = await evaluate_goal(
                    goal["text"], position, department, manager_goals, kpis,
                )
                if eval_result.get("improved_goal"):
                    goal["text"] = eval_result["improved_goal"]
                    goal["smart_index"] = eval_result["smart_index"]
            except Exception:
                pass

        await asyncio.gather(*[reformulate(g) for g in weak_goals])

    # 6. Warnings
    warnings = []
    total = existing_count + len(goals)
    if total < 3:
        warnings.append(f"Всего целей: {total}, рекомендуется минимум 3")
    if total > 5:
        warnings.append(f"Всего целей: {total}, рекомендуется максимум 5")

    total_weight = sum(g.get("weight", 0) for g in goals)
    if goals and abs(total_weight - 100) > 1:
        warnings.append(f"Суммарный вес сгенерированных целей: {total_weight}%, ожидается 100%")

    context_info = _empty_context(kpis, manager_goals, rag_chunks)

    return {"goals": goals, "context": context_info, "warnings": warnings}


def _empty_context(kpis, manager_goals, rag_chunks):
    scores = [ch["score"] for ch in rag_chunks]
    return {
        "manager_goals_used": len(manager_goals) > 0,
        "kpis_used": [k["title"] for k in kpis],
        "vnd_docs_used": len(set(ch["doc_id"] for ch in rag_chunks)),
        "rag_chunks": [
            {
                "doc_title": ch["doc_title"],
                "doc_type": ch.get("doc_type", ""),
                "score": round(ch["score"], 3),
                "text_preview": ch["text"][:200],
            }
            for ch in rag_chunks
        ],
        "avg_rag_score": round(sum(scores) / len(scores), 3) if scores else 0.0,
    }
