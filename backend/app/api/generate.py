from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_remote_session, get_local_session
from app.models import Goal, AiGeneratedGoals, AcceptedGoals
from app.schemas import GenerateRequest, GenerateResponse, GeneratedGoal, GenerateContext, StrategicAlignment, AcceptRequest
from app.services.goal_generator import generate_goals
from app.services.dedup_checker import check_duplicates
from app.api.evaluate import get_employee_context

router = APIRouter()


@router.post(
    "/generate-goals",
    response_model=GenerateResponse,
    summary="AI-генерация целей через RAG + LLM (F-09..F-15)",
    response_description="3–5 целей с SMART-скором, источником ВНД и контекстом ретривала",
)
async def generate_goals_endpoint(
    req: GenerateRequest,
    remote: AsyncSession = Depends(get_remote_session),
    local: AsyncSession = Depends(get_local_session),
):
    """
    Генерирует предложения целей для сотрудника в 3 шага:

    1. **RAG retrieval** — семантический поиск по корпоративным ВНД в Qdrant
       (фильтрация по подразделению + fallback без фильтра)
    2. **Contextualization** — добавляются цели руководителя, KPI, исторические данные
    3. **LLM generation** — Gemini формирует 3–5 целей в SMART-формате с встроенной
       самооценкой (`smart_scores`). Слабые цели (< 0.7) автоматически переформулируются.

    После генерации выполняется проверка дублирования (cosine similarity > 0.85)
    и верификация source_doc относительно реально извлечённых чанков.
    """
    ctx = await get_employee_context(req.employee_id, req.quarter, req.year, remote)
    if not ctx:
        raise HTTPException(404, "Сотрудник не найден")

    # Existing goals
    existing_result = await remote.execute(
        select(Goal.goal_text)
        .where(Goal.employee_id == req.employee_id, Goal.quarter == req.quarter, Goal.year == req.year)
    )
    existing_goals = [r[0] for r in existing_result.all()]

    # Generate
    gen_result = await generate_goals(
        position=ctx["position"],
        department=ctx["department"],
        department_id=ctx["department_id"],
        quarter=req.quarter,
        year=req.year,
        manager_goals=ctx["manager_goals"],
        kpis=ctx["kpis"],
        existing_goals=existing_goals,
        focus_area=req.focus_area,
        historical_goals=ctx["historical_goals"],
    )

    # Dedup check
    new_texts = [g["text"] for g in gen_result["goals"]]
    if existing_goals and new_texts:
        dedup = await check_duplicates(new_texts, existing_goals)
        for d in dedup:
            if d["is_duplicate"]:
                gen_result["warnings"].append(
                    f"Цель #{d['index']+1} похожа на существующую "
                    f"(сходство: {d['similarity']:.0%}): {d['similar_to'][:60]}..."
                )

    # Build response — verify source_doc against retrieved chunks
    retrieved_titles = {
        ch["doc_title"].lower().strip()
        for ch in gen_result["context"].get("rag_chunks", [])
        if ch.get("doc_title")
    }

    goals = []
    for g in gen_result["goals"]:
        alignment = g.get("strategic_alignment", {"level": "functional", "source": ""})
        if isinstance(alignment, dict):
            alignment = StrategicAlignment(**alignment)

        source_doc = g.get("source_doc", "")
        # Grounding check: warn if source not found in retrieved chunks
        if source_doc and source_doc.lower().strip() not in retrieved_titles and retrieved_titles:
            gen_result["warnings"].append(
                f"Источник «{source_doc[:60]}» не найден среди извлечённых ВНД — возможна галлюцинация"
            )

        goals.append(GeneratedGoal(
            text=g["text"],
            metric=g.get("metric", ""),
            deadline=g.get("deadline", ""),
            weight=g.get("weight"),
            source_doc=source_doc,
            source_quote=g.get("source_quote", ""),
            smart_index=g.get("smart_index", 0.0),
            goal_type=g.get("goal_type", "output"),
            strategic_alignment=alignment,
        ))

    context = GenerateContext(**gen_result["context"])

    # Save to local DB
    record = AiGeneratedGoals(
        employee_id=req.employee_id,
        quarter=req.quarter,
        year=req.year,
        goals_json=[g.model_dump() for g in goals],
        context_json=context.model_dump(),
        warnings=gen_result["warnings"],
    )
    local.add(record)
    await local.commit()

    return GenerateResponse(goals=goals, context=context, warnings=gen_result["warnings"])


@router.post("/accept-goals", summary="Принятие выбранных целей сотрудником (F-13)")
async def accept_goals_endpoint(
    req: AcceptRequest,
    local: AsyncSession = Depends(get_local_session),
):
    """F-13: Сохраняет выбранные сотрудником цели из предложенного AI-набора в локальную БД."""
    record = AcceptedGoals(
        employee_id=req.employee_id,
        quarter=req.quarter,
        year=req.year,
        goals_json=[g.model_dump() for g in req.goals],
        accepted_count=len(req.goals),
    )
    local.add(record)
    await local.commit()
    return {"accepted": len(req.goals), "message": f"Принято {len(req.goals)} целей"}
