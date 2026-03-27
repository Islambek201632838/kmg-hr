import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_remote_session, get_local_session
from app.models import Employee, Position, Department, Goal, KpiTimeseries, KpiCatalog, AiEvaluation
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

    # Manager goals
    manager_goals = []
    if emp.manager_id:
        mg = await session.execute(
            select(Goal.goal_text)
            .where(Goal.employee_id == emp.manager_id, Goal.quarter == quarter, Goal.year == year)
        )
        manager_goals = [r[0] for r in mg.all()]

    # Department KPIs
    kpi_q = (
        select(KpiCatalog.title, KpiTimeseries.value_num, KpiCatalog.unit)
        .join(KpiTimeseries, KpiCatalog.metric_key == KpiTimeseries.metric_key)
        .where(KpiTimeseries.department_id == dept_id)
        .order_by(KpiTimeseries.period_date.desc())
        .limit(10)
    )
    kpi_result = await session.execute(kpi_q)
    kpis = [{"title": r[0], "value": float(r[1]), "unit": r[2]} for r in kpi_result.all()]

    # Historical goals of similar position
    hist_q = (
        select(Goal.goal_text)
        .join(Employee, Goal.employee_id == Employee.id)
        .where(Employee.position_id == emp.position_id, Goal.year < year)
        .order_by(Goal.created_at.desc())
        .limit(5)
    )
    hist_result = await session.execute(hist_q)
    historical = [r[0] for r in hist_result.all()]

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

    result = await evaluate_goal(
        goal_text=req.goal_text,
        position=ctx["position"],
        department=ctx["department"],
        manager_goals=ctx["manager_goals"],
        kpis=ctx["kpis"],
        historical_goals=ctx["historical_goals"],
    )

    goal_type = result.get("goal_type", "output")
    alignment_level = result.get("strategic_alignment", {}).get("level", "operational")
    smart_scores = result["smart_scores"]
    smart_index = result["smart_index"]

    # Goals count + total weight for alerts
    stats_result = await remote.execute(
        select(func.count(Goal.goal_id), func.coalesce(func.sum(Goal.weight), 0))
        .where(Goal.employee_id == req.employee_id, Goal.quarter == req.quarter, Goal.year == req.year)
    )
    goals_count, total_weight = stats_result.one()

    # F-20: Historical avg for similar positions (cross-DB: remote employees + local evaluations)
    historical_avg_index = None
    emp = ctx["employee"]
    # Step 1: get employee_ids with same position from remote DB
    same_pos_result = await remote.execute(
        select(Employee.id).where(
            Employee.position_id == emp.position_id,
            Employee.id != req.employee_id,
        )
    )
    same_pos_ids = [r[0] for r in same_pos_result.all()]
    # Step 2: avg index from local AI evaluations for those employees
    if same_pos_ids:
        hist_avg_result = await local.execute(
            select(func.avg(AiEvaluation.overall_index))
            .where(AiEvaluation.employee_id.in_(same_pos_ids))
        )
        hist_avg = hist_avg_result.scalar()
        if hist_avg is not None:
            historical_avg_index = float(hist_avg)

    raw_alerts = check_goal_alerts(
        overall_index=smart_index,
        alignment_level=alignment_level,
        goal_type=goal_type,
        goals_count=int(goals_count),
        total_weight=float(total_weight),
        historical_avg_index=historical_avg_index,
    )
    alerts = [AlertItem(**a) for a in raw_alerts]

    # Save to local DB and get generated id
    evaluation = AiEvaluation(
        employee_id=req.employee_id,
        goal_text=req.goal_text,
        scores_json=smart_scores,
        overall_index=smart_index,
        goal_type=goal_type,
        alignment_level=alignment_level,
        alignment_source=result.get("strategic_alignment", {}).get("source"),
        recommendations=result.get("recommendations", []),
        reformulation=result.get("improved_goal"),
    )
    local.add(evaluation)
    await local.commit()
    await local.refresh(evaluation)

    return EvalResponse(
        goal_id=f"eval-{evaluation.id}",
        goal_text=req.goal_text,
        smart_scores=SmartScores(**smart_scores),
        smart_index=smart_index,
        recommendations=result.get("recommendations", []),
        improved_goal=result.get("improved_goal"),
        alerts=alerts,
    )


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
            .distinct()
            .order_by(Goal.year, Goal.quarter)
        )
        periods = [f"{r.quarter} {r.year}" for r in periods_result.all()]
        available = ", ".join(periods) if periods else "нет данных"
        raise HTTPException(
            404,
            f"Цели за {req.quarter} {req.year} не найдены. Доступные периоды: {available}",
        )

    # Evaluate all goals in parallel (было sequential — 5 целей × 5-8с = 25-40с)
    results = await asyncio.gather(*[
        evaluate_goal(
            goal_text=goal.goal_text,
            position=ctx["position"],
            department=ctx["department"],
            manager_goals=ctx["manager_goals"],
            kpis=ctx["kpis"],
        )
        for goal in goals
    ])

    evals = []
    all_scores = {"specific": [], "measurable": [], "achievable": [], "relevant": [], "time_bound": []}
    total_weight = 0.0
    activity_count = 0
    no_strategic_count = 0

    for goal, result in zip(goals, results):
        goal_type = result.get("goal_type", "output")
        alignment_level = result.get("strategic_alignment", {}).get("level", "operational")
        smart_scores = result["smart_scores"]
        smart_index = result["smart_index"]

        evals.append(GoalEval(
            goal_id=str(goal.goal_id),
            goal_text=goal.goal_text[:100],
            overall_index=smart_index,
            goal_type=goal_type,
            alignment_level=alignment_level,
            smart_scores=SmartScores(**smart_scores),
        ))

        for key in all_scores:
            all_scores[key].append(smart_scores[key])

        total_weight += float(goal.weight or 0)
        if goal_type == "activity":
            activity_count += 1
        if alignment_level != "strategic":
            no_strategic_count += 1

        local.add(AiEvaluation(
            goal_id=str(goal.goal_id),
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

    await local.commit()

    # Find weakest criterion
    avg_per_criterion = {k: sum(v) / len(v) for k, v in all_scores.items() if v}
    weakest = min(avg_per_criterion, key=avg_per_criterion.get)
    avg_index = sum(e.overall_index for e in evals) / len(evals)

    # Batch alerts
    alerts = check_batch_alerts(len(goals), total_weight, avg_index, activity_count, no_strategic_count)
    warnings = [a["message"] for a in alerts]

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
