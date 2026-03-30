import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_remote_session, get_local_session
from app.models import Employee, Position, Department, Goal, KpiTimeseries, KpiCatalog, AiEvaluation
from pydantic import BaseModel, Field
from typing import Optional
from app.schemas import EvalRequest, EvalResponse, SmartScores, BatchEvalRequest, BatchEvalResponse, GoalEval, BatchSummary, AlertItem
from app.services.smart_evaluator import evaluate_goal
from app.services.alert_manager import check_goal_alerts, check_batch_alerts

router = APIRouter()


async def get_employee_context(employee_id: int, quarter: str, year: int, session: AsyncSession):
    """Fetch employee info, manager goals, KPIs from remote DB. Reused across endpoints."""
    q = (
        select(
            Employee,
            Position.name.label("pos_name"),
            Department.name.label("dept_name"),
            Department.id.label("dept_id"),
        )
        .join(Position, Employee.position_id == Position.id)
        .join(Department, Employee.department_id == Department.id)
        .where(Employee.id == employee_id)
    )
    result = await session.execute(q)
    row = result.first()
    if not row:
        return None

    emp, pos_name, dept_name, dept_id = row

    # Queries 2, 3, 4 are independent — run in parallel
    async def _manager_goals():
        if not emp.manager_id:
            return []
        mg = await session.execute(
            select(Goal.goal_text)
            .where(Goal.employee_id == emp.manager_id, Goal.quarter == quarter, Goal.year == year)
        )
        return [r[0] for r in mg.all()]

    async def _kpis():
        kpi_result = await session.execute(
            select(KpiCatalog.title, KpiTimeseries.value_num, KpiCatalog.unit)
            .join(KpiTimeseries, KpiCatalog.metric_key == KpiTimeseries.metric_key)
            .where(KpiTimeseries.department_id == dept_id)
            .order_by(KpiTimeseries.period_date.desc())
            .limit(10)
        )
        return [{"title": r[0], "value": float(r[1]), "unit": r[2]} for r in kpi_result.all()]

    async def _historical():
        hist_result = await session.execute(
            select(Goal.goal_text)
            .join(Employee, Goal.employee_id == Employee.id)
            .where(Employee.position_id == emp.position_id, Goal.year < year)
            .order_by(Goal.created_at.desc())
            .limit(5)
        )
        return [r[0] for r in hist_result.all()]

    manager_goals, kpis, historical = await asyncio.gather(
        _manager_goals(), _kpis(), _historical()
    )

    return {
        "employee": emp,
        "position": pos_name,
        "department": dept_name,
        "department_id": dept_id,
        "manager_goals": manager_goals,
        "kpis": kpis,
        "historical_goals": historical,
    }


@router.post(
    "/evaluate-goal",
    response_model=EvalResponse,
    summary="Оценка цели по SMART (F-09..F-21)",
    response_description="SMART-скоры, тип цели, стратегическая связка, алерты, переформулировка",
)
async def evaluate_goal_endpoint(
    req: EvalRequest,
    remote: AsyncSession = Depends(get_remote_session),
    local: AsyncSession = Depends(get_local_session),
):
    """
    Оценивает произвольную формулировку цели по методологии SMART.

    - Возвращает скоры по 5 критериям (S/M/A/R/T) от 0.0 до 1.0
    - Определяет тип цели: **activity** / **output** / **impact**
    - Присваивает уровень стратегической связки: **strategic** / **functional** / **operational**
    - Если `smart_index < 0.7` — предлагает переформулировку (`improved_goal`)
    - Генерирует алерты по F-16..F-19 (вес, количество, тип, связка)
    """
    ctx = await get_employee_context(req.employee_id, req.quarter, req.year, remote)
    if not ctx:
        raise HTTPException(404, "Сотрудник не найден")

    # RAG: fetch relevant VND chunks for strategic alignment context
    from app.services.rag_pipeline import search_vnd
    rag_chunks = await search_vnd(
        f"{ctx['position']} {ctx['department']} {req.goal_text[:100]}",
        department_id=ctx["department_id"], top_k=3,
    )

    # Run Gemini + alert DB queries in parallel (Gemini ~3-5s, DB ~20ms)
    async def _gemini():
        return await evaluate_goal(
            goal_text=req.goal_text,
            position=ctx["position"],
            department=ctx["department"],
            manager_goals=ctx["manager_goals"],
            kpis=ctx["kpis"],
            historical_goals=ctx["historical_goals"],
            rag_chunks=rag_chunks,
        )

    async def _alert_data():
        emp = ctx["employee"]
        # Stats query
        stats_res = await remote.execute(
            select(func.count(Goal.goal_id), func.coalesce(func.sum(Goal.weight), 0))
            .where(Goal.employee_id == req.employee_id, Goal.quarter == req.quarter, Goal.year == req.year)
        )
        goals_count, total_weight = stats_res.one()

        # F-20: historical avg — use all evaluations from local DB
        # (no cross-DB join needed, just avg of all non-self evaluations)
        historical_avg_index = None
        hist_avg_res = await local.execute(
            select(func.avg(AiEvaluation.overall_index))
            .where(AiEvaluation.employee_id != req.employee_id)
        )
        hist_avg = hist_avg_res.scalar()
        if hist_avg is not None:
            historical_avg_index = float(hist_avg)

        return int(goals_count), float(total_weight), historical_avg_index

    result, (goals_count, total_weight, historical_avg_index) = await asyncio.gather(
        _gemini(), _alert_data()
    )

    goal_type = result.get("goal_type", "output")
    alignment_level = result.get("strategic_alignment", {}).get("level", "operational")
    smart_scores = result["smart_scores"]
    smart_index = result["smart_index"]

    raw_alerts = check_goal_alerts(
        overall_index=smart_index,
        alignment_level=alignment_level,
        goal_type=goal_type,
        goals_count=int(goals_count),
        total_weight=float(total_weight),
        historical_avg_index=historical_avg_index,
    )
    alerts = [AlertItem(**a) for a in raw_alerts]

    # evaluate-goal — превью-инструмент, НЕ сохраняем в БД
    # (только evaluate-batch сохраняет реальные цели для дашборда)

    alignment = result.get("strategic_alignment", {})
    from app.schemas import StrategicAlignment
    return EvalResponse(
        goal_id=None,
        goal_text=req.goal_text,
        smart_scores=SmartScores(**smart_scores),
        smart_index=smart_index,
        goal_type=goal_type,
        strategic_alignment=StrategicAlignment(**alignment) if alignment else None,
        recommendations=result.get("recommendations", []),
        improved_goal=result.get("improved_goal"),
        alerts=alerts,
    )


class SaveEvalRequest(BaseModel):
    employee_id: int = Field(..., description="ID сотрудника")
    goal_text: str = Field(..., description="Формулировка цели")
    smart_scores: SmartScores = Field(..., description="SMART-скоры")
    smart_index: float = Field(..., description="SMART-индекс", ge=0, le=1)
    goal_type: str = Field("output", description="Тип цели")
    alignment_level: str = Field("operational", description="Уровень связки")
    alignment_source: str = Field("", description="Источник связки")
    recommendations: list[str] = Field([], description="Рекомендации")
    improved_goal: Optional[str] = Field(None, description="Переформулировка")


@router.post(
    "/save-evaluation",
    summary="Сохранить одобренную цель (smart_index >= 0.7)",
    response_description="ID сохранённой оценки",
)
async def save_evaluation(
    req: SaveEvalRequest,
    local: AsyncSession = Depends(get_local_session),
):
    """
    Сохраняет оценку цели в БД только если smart_index >= 0.7 (проходной порог).
    Используется после превью через /evaluate-goal — сотрудник нажимает «Сохранить».
    """
    if req.smart_index < 0.7:
        raise HTTPException(400, f"SMART-индекс ({req.smart_index:.2f}) ниже порога 0.7 — сохранение невозможно")

    # ACID: SELECT FOR UPDATE → DELETE → INSERT → single COMMIT
    # Lock rows first to prevent race condition on concurrent saves
    await local.execute(
        select(AiEvaluation.id)
        .where(AiEvaluation.employee_id == req.employee_id, AiEvaluation.goal_text == req.goal_text)
        .with_for_update()
    )
    await local.execute(
        delete(AiEvaluation).where(
            AiEvaluation.employee_id == req.employee_id,
            AiEvaluation.goal_text == req.goal_text,
        )
    )
    evaluation = AiEvaluation(
        employee_id=req.employee_id,
        goal_text=req.goal_text,
        scores_json=req.smart_scores.model_dump(),
        overall_index=req.smart_index,
        goal_type=req.goal_type,
        alignment_level=req.alignment_level,
        alignment_source=req.alignment_source,
        recommendations=req.recommendations,
        reformulation=req.improved_goal,
    )
    local.add(evaluation)
    await local.commit()
    await local.refresh(evaluation)
    return {"saved": True, "eval_id": evaluation.id, "smart_index": req.smart_index}


@router.delete(
    "/evaluation/{eval_id}",
    summary="Удалить ручную оценку цели из локальной БД",
)
async def delete_evaluation(
    eval_id: int,
    local: AsyncSession = Depends(get_local_session),
):
    """Удаляет оценку по ID. Используется для удаления целей с низким SMART-индексом."""
    result = await local.execute(
        select(AiEvaluation).where(AiEvaluation.id == eval_id).with_for_update()
    )
    evaluation = result.scalar_one_or_none()
    if not evaluation:
        raise HTTPException(404, "Оценка не найдена")
    await local.execute(delete(AiEvaluation).where(AiEvaluation.id == eval_id))
    await local.commit()
    return {"deleted": True, "eval_id": eval_id}


@router.post(
    "/evaluate-batch",
    response_model=BatchEvalResponse,
    summary="Пакетная оценка всех целей сотрудника за квартал",
    response_description="Оценки по каждой цели, сводка, алерты батча",
)
async def evaluate_batch_endpoint(
    req: BatchEvalRequest,
    remote: AsyncSession = Depends(get_remote_session),
    local: AsyncSession = Depends(get_local_session),
):
    """
    Оценивает все цели сотрудника за указанный квартал параллельно (asyncio.gather).

    - Все цели оцениваются одновременно — время ответа ~7-10с независимо от кол-ва
    - Возвращает сводку: средний SMART-индекс, слабый критерий, суммарный вес
    - Алерты уровня набора: F-16 (кол-во), F-17 (связка), F-18 (вес), F-19 (тип)
    - Сохраняет результаты в локальную БД для дашборда
    """
    ctx = await get_employee_context(req.employee_id, req.quarter, req.year, remote)
    if not ctx:
        raise HTTPException(404, "Сотрудник не найден")

    # Get employee goals for this quarter
    goals_result = await remote.execute(
        select(Goal)
        .where(Goal.employee_id == req.employee_id, Goal.quarter == req.quarter, Goal.year == req.year)
    )
    goals = goals_result.scalars().all()

    if not goals:
        # Динамически показываем доступные периоды сотрудника
        periods_result = await remote.execute(
            select(Goal.quarter, Goal.year)
            .where(Goal.employee_id == req.employee_id)
            .group_by(Goal.quarter, Goal.year)
            .order_by(Goal.year, Goal.quarter)
        )
        periods = [f"{r.quarter} {r.year}" for r in periods_result.all()]
        available = ", ".join(periods) if periods else "нет данных"
        raise HTTPException(
            404,
            f"Цели за {req.quarter} {req.year} не найдены. Доступные периоды: {available}",
        )

    # 1. Check which goals already have AI evaluations in local DB
    goal_ids = [str(g.goal_id) for g in goals]
    existing_evals_result = await local.execute(
        select(AiEvaluation).where(AiEvaluation.goal_id.in_(goal_ids))
    )
    existing_by_goal_id = {e.goal_id: e for e in existing_evals_result.scalars().all()}

    # Also fetch manual evaluations (saved via save-evaluation, goal_id=NULL)
    manual_evals_result = await local.execute(
        select(AiEvaluation).where(
            AiEvaluation.employee_id == req.employee_id,
            AiEvaluation.goal_id.is_(None),
        )
    )
    manual_evals = manual_evals_result.scalars().all()

    # 2. Split: goals with existing eval (skip AI) vs new goals (need AI)
    goals_to_evaluate = [g for g in goals if str(g.goal_id) not in existing_by_goal_id]

    # 3. Evaluate only new goals in parallel
    new_results = {}
    if goals_to_evaluate:
        ai_results = await asyncio.gather(*[
            evaluate_goal(
                goal_text=goal.goal_text,
                position=ctx["position"],
                department=ctx["department"],
                manager_goals=ctx["manager_goals"],
                kpis=ctx["kpis"],
            )
            for goal in goals_to_evaluate
        ])
        for goal, result in zip(goals_to_evaluate, ai_results):
            new_results[str(goal.goal_id)] = result

    # 4. Build response + save new evaluations
    evals = []
    db_records = []
    all_scores = {"specific": [], "measurable": [], "achievable": [], "relevant": [], "time_bound": []}
    total_weight = 0.0
    activity_count = 0
    no_strategic_count = 0

    for goal in goals:
        gid = str(goal.goal_id)
        if gid in existing_by_goal_id:
            # Use cached evaluation
            e = existing_by_goal_id[gid]
            smart_scores = e.scores_json
            smart_index = e.overall_index
            goal_type = e.goal_type or "output"
            alignment_level = e.alignment_level or "operational"
        else:
            # Use fresh AI result
            result = new_results[gid]
            smart_scores = result["smart_scores"]
            smart_index = result["smart_index"]
            goal_type = result.get("goal_type", "output")
            alignment_level = result.get("strategic_alignment", {}).get("level", "operational")

            db_records.append(AiEvaluation(
                goal_id=gid,
                employee_id=req.employee_id,
                goal_text=goal.goal_text,
                scores_json=smart_scores,
                overall_index=smart_index,
                goal_type=goal_type,
                alignment_level=alignment_level,
                alignment_source=result.get("strategic_alignment", {}).get("source"),
                recommendations=result.get("recommendations", []),
                reformulation=result.get("improved_goal"),
            ))

        evals.append(GoalEval(
            goal_id=gid,
            goal_text=goal.goal_text,
            overall_index=smart_index,
            goal_type=goal_type,
            alignment_level=alignment_level,
            smart_scores=SmartScores(**smart_scores),
        ))

        for key in all_scores:
            all_scores[key].append(smart_scores.get(key, 0) if isinstance(smart_scores, dict) else getattr(smart_scores, key, 0))

        total_weight += float(goal.weight or 0)
        if goal_type == "activity":
            activity_count += 1
        if alignment_level != "strategic":
            no_strategic_count += 1

    # 5. Append manual evaluations (saved via /save-evaluation)
    for me in manual_evals:
        scores = me.scores_json or {}
        evals.append(GoalEval(
            goal_id=f"manual-{me.id}",
            goal_text=me.goal_text,
            overall_index=me.overall_index,
            goal_type=me.goal_type or "output",
            alignment_level=me.alignment_level or "operational",
            smart_scores=SmartScores(**scores) if scores else None,
        ))
        for key in all_scores:
            all_scores[key].append(scores.get(key, 0))
        if me.goal_type == "activity":
            activity_count += 1
        if (me.alignment_level or "operational") != "strategic":
            no_strategic_count += 1

    # ACID: DELETE old + INSERT new in single transaction (one commit)
    if db_records:
        new_goal_ids = [r.goal_id for r in db_records if r.goal_id]
        if new_goal_ids:
            await local.execute(
                delete(AiEvaluation).where(AiEvaluation.goal_id.in_(new_goal_ids))
            )
        local.add_all(db_records)
        await local.commit()

    # 6. Summary
    total_goals = len(evals)
    if not evals:
        raise HTTPException(404, "Нет целей для оценки")

    avg_per_criterion = {k: sum(v) / len(v) for k, v in all_scores.items() if v}
    weakest = min(avg_per_criterion, key=avg_per_criterion.get) if avg_per_criterion else "specific"
    avg_index = sum(e.overall_index for e in evals) / len(evals)

    alerts = check_batch_alerts(total_goals, total_weight, avg_index, activity_count, no_strategic_count)
    warnings = [a["message"] for a in alerts]
    if goals_to_evaluate:
        warnings.insert(0, f"{len(goals_to_evaluate)} из {len(goals)} целей оценены AI (остальные из кеша)")

    return BatchEvalResponse(
        employee_name=ctx["employee"].full_name,
        department=ctx["department"],
        goals=evals,
        summary=BatchSummary(
            avg_index=round(avg_index, 2),
            total_goals=len(goals),
            total_weight=total_weight,
            weakest_criterion=weakest,
            warnings=warnings,
        ),
    )
