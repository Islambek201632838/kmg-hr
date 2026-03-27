from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict

from app.database import get_remote_session, get_local_session
from app.models import Department, Employee, Goal, AiEvaluation

router = APIRouter()

CRITERION_KEYS = ("specific", "measurable", "achievable", "relevant", "time_bound")
CRITERION_RU = {
    "specific": "Конкретность",
    "measurable": "Измеримость",
    "achievable": "Достижимость",
    "relevant": "Релевантность",
    "time_bound": "Сроки",
}


async def _get_base_data(remote, local):
    """Fetch only needed columns, filter employees to those with evaluations."""
    # 1. Departments — only id + name
    dept_result = await remote.execute(
        select(Department.id, Department.name).where(Department.is_active == True)
    )
    departments = dept_result.all()

    # 2. Evaluations — only needed columns (skip heavy JSON where not needed)
    evals_result = await local.execute(
        select(
            AiEvaluation.id,
            AiEvaluation.employee_id,
            AiEvaluation.goal_id,
            AiEvaluation.overall_index,
            AiEvaluation.alignment_level,
            AiEvaluation.goal_type,
            AiEvaluation.scores_json,
        )
    )
    evals = evals_result.all()

    # 3. Employees — only those who have evaluations
    eval_emp_ids = list({ev.employee_id for ev in evals})
    emp_to_dept = {}
    if eval_emp_ids:
        emp_result = await remote.execute(
            select(Employee.id, Employee.department_id)
            .where(Employee.id.in_(eval_emp_ids))
        )
        emp_to_dept = {r.id: r.department_id for r in emp_result.all()}

    # 4. Group evals by department
    dept_evals = defaultdict(list)
    for ev in evals:
        dept_id = emp_to_dept.get(ev.employee_id)
        if dept_id:
            dept_evals[dept_id].append(ev)

    return departments, emp_to_dept, evals, dept_evals


async def _get_goal_quarter_map(remote, year: int) -> dict:
    """goal_id (str) -> quarter mapping for a given year."""
    result = await remote.execute(
        select(Goal.goal_id, Goal.quarter).where(Goal.year == year)
    )
    return {str(r.goal_id): r.quarter for r in result.all()}


def _calc_criterion_avgs(d_evals):
    """Calculate average per SMART criterion."""
    criterion_avgs = {}
    for k in CRITERION_KEYS:
        vals = [e.scores_json.get(k, 0) for e in d_evals if e.scores_json]
        criterion_avgs[k] = sum(vals) / len(vals) if vals else 0
    return criterion_avgs


@router.get(
    "/dashboard/department-quality",
    summary="Качество целей по подразделениям",
    response_description="Средний SMART-индекс, стратегическая связка, слабый критерий по каждому подразделению",
)
async def department_quality(
    year: int = 2025,
    remote: AsyncSession = Depends(get_remote_session),
    local: AsyncSession = Depends(get_local_session),
):
    """
    Агрегирует AI-оценки всех сотрудников по подразделениям.
    Возвращает средний SMART-индекс, долю стратегических целей,
    слабейший критерий и общий org_avg по компании.
    """
    departments, emp_to_dept, evals, dept_evals = await _get_base_data(remote, local)
    goal_quarter_map = await _get_goal_quarter_map(remote, year)

    # Goals count per dept
    goals_q = (
        select(Goal.department_id, func.count(Goal.goal_id).label("cnt"))
        .where(Goal.year == year)
        .group_by(Goal.department_id)
    )
    goals_result = await remote.execute(goals_q)
    dept_total = {r.department_id: r.cnt for r in goals_result.all()}

    # Build eval → quarter mapping
    eval_quarter_map = {}
    for ev in evals:
        if ev.goal_id and ev.goal_id in goal_quarter_map:
            eval_quarter_map[ev.id] = goal_quarter_map[ev.goal_id]

    dept_list = []
    all_indices = []

    for dept in departments:
        d_evals = dept_evals.get(dept.id, [])

        avg_index = 0.0
        strategic_ratio = 0.0
        weakest = "specific"

        if d_evals:
            avg_index = sum(e.overall_index for e in d_evals) / len(d_evals)
            strategic_count = sum(1 for e in d_evals if e.alignment_level == "strategic")
            strategic_ratio = strategic_count / len(d_evals)

            criterion_avgs = _calc_criterion_avgs(d_evals)
            if any(criterion_avgs.values()):
                weakest = min(criterion_avgs, key=criterion_avgs.get)

        # Quarterly breakdown via prebuilt dict
        eval_by_q = defaultdict(list)
        for e in d_evals:
            q = eval_quarter_map.get(e.id)
            if q:
                eval_by_q[q].append(e)

        quarters_data = {}
        for q_name in ["Q1", "Q2", "Q3", "Q4"]:
            q_evals = eval_by_q.get(q_name, [])
            quarters_data[q_name] = round(
                sum(e.overall_index for e in q_evals) / len(q_evals), 2
            ) if q_evals else None

        dept_list.append({
            "id": dept.id,
            "name": dept.name,
            "avg_smart_index": round(avg_index, 2),
            "total_goals": dept_total.get(dept.id, 0),
            "strategic_ratio": round(strategic_ratio, 2),
            "weakest_criterion": weakest,
            "quarters": quarters_data,
        })

        if avg_index > 0:
            all_indices.append(avg_index)

    org_avg = round(sum(all_indices) / len(all_indices), 2) if all_indices else 0.0

    top_issues = []
    if evals:
        n = len(evals)
        activity_pct = sum(1 for e in evals if e.goal_type == "activity") * 100 // n
        if activity_pct > 0:
            top_issues.append(f"{activity_pct}% целей сформулированы как активности")
        no_strat_pct = sum(1 for e in evals if e.alignment_level != "strategic") * 100 // n
        if no_strat_pct > 0:
            top_issues.append(f"{no_strat_pct}% целей без стратегической связки")

    return {"departments": dept_list, "org_avg": org_avg, "top_issues": top_issues}


@router.get(
    "/dashboard/maturity",
    summary="Индекс зрелости целеполагания подразделения (F-22)",
    response_description="Матрица зрелости: SMART-качество, стратегическая связка, типы целей, рекомендации",
)
async def department_maturity(
    department_id: int,
    remote: AsyncSession = Depends(get_remote_session),
    local: AsyncSession = Depends(get_local_session),
):
    """F-22: Индекс зрелости целеполагания подразделения."""
    # Fetch only this department
    dept_res = await remote.execute(
        select(Department.id, Department.name).where(Department.id == department_id)
    )
    dept = dept_res.first()
    if not dept:
        raise HTTPException(404, "Подразделение не найдено")

    # Get employee IDs for this department only
    emp_res = await remote.execute(
        select(Employee.id).where(Employee.department_id == department_id)
    )
    emp_ids = [r.id for r in emp_res.all()]

    # Evaluations for these employees only
    d_evals = []
    if emp_ids:
        evals_res = await local.execute(
            select(
                AiEvaluation.overall_index,
                AiEvaluation.alignment_level,
                AiEvaluation.goal_type,
                AiEvaluation.scores_json,
            ).where(AiEvaluation.employee_id.in_(emp_ids))
        )
        d_evals = evals_res.all()

    if not d_evals:
        return {
            "department": dept.name,
            "maturity_index": 0.0,
            "evaluated_goals": 0,
            "breakdown": {
                "smart_quality": 0.0,
                "strategic_ratio": 0.0,
                "goal_type_distribution": {"impact": 0, "output": 0, "activity": 0},
                "weakest_criteria": [],
                "criterion_scores": {},
            },
            "recommendations": ["Нет оценённых целей. Выполните пакетную оценку для сотрудников подразделения."],
        }

    n = len(d_evals)
    smart_quality = sum(e.overall_index for e in d_evals) / n
    strategic_count = sum(1 for e in d_evals if e.alignment_level == "strategic")
    strategic_ratio = strategic_count / n

    type_counts = {"impact": 0, "output": 0, "activity": 0}
    for e in d_evals:
        t = e.goal_type or "output"
        if t in type_counts:
            type_counts[t] += 1
    type_dist = {k: round(v / n, 2) for k, v in type_counts.items()}

    criterion_avgs = {}
    for k in CRITERION_KEYS:
        vals = [e.scores_json.get(k, 0) for e in d_evals if e.scores_json]
        criterion_avgs[k] = sum(vals) / len(vals) if vals else 0

    sorted_criteria = sorted(criterion_avgs.items(), key=lambda x: x[1])
    weakest = [k for k, v in sorted_criteria[:2]]

    maturity = round(
        0.40 * smart_quality +
        0.30 * strategic_ratio +
        0.20 * (1 - type_dist.get("activity", 0)) +
        0.10 * (1 - (1 if sorted_criteria[0][1] < 0.5 else 0)),
        2,
    )

    recs = []
    if type_dist.get("activity", 0) > 0.2:
        recs.append(f"{int(type_dist['activity'] * 100)}% целей — активности. Переформулируйте в output/impact")
    if strategic_ratio < 0.5:
        recs.append(f"Только {int(strategic_ratio * 100)}% целей связаны со стратегией")
    if criterion_avgs.get("measurable", 1) < 0.6:
        recs.append("Низкая измеримость — добавьте количественные метрики")
    if criterion_avgs.get("time_bound", 1) < 0.6:
        recs.append("Низкий показатель сроков — укажите конкретные дедлайны")

    return {
        "department": dept.name,
        "maturity_index": maturity,
        "evaluated_goals": n,
        "breakdown": {
            "smart_quality": round(smart_quality, 2),
            "strategic_ratio": round(strategic_ratio, 2),
            "goal_type_distribution": type_dist,
            "weakest_criteria": [CRITERION_RU.get(k, k) for k in weakest],
            "criterion_scores": {CRITERION_RU.get(k, k): round(v, 2) for k, v in criterion_avgs.items()},
        },
        "recommendations": recs,
    }


@router.get(
    "/dashboard/quarterly-trend",
    summary="Квартальная динамика SMART-индекса подразделения",
    response_description="SMART-индекс и кол-во оценённых целей по кварталам",
)
async def quarterly_trend(
    department_id: int,
    year: int = 2025,
    remote: AsyncSession = Depends(get_remote_session),
    local: AsyncSession = Depends(get_local_session),
):
    """Квартальный тренд для линейного графика на дашборде."""
    # Fetch only this department
    dept_res = await remote.execute(
        select(Department.name).where(Department.id == department_id)
    )
    dept_name = dept_res.scalar()
    if not dept_name:
        raise HTTPException(404, "Подразделение не найдено")

    # Employee IDs + goal quarter map
    emp_res = await remote.execute(
        select(Employee.id).where(Employee.department_id == department_id)
    )
    emp_ids = [r.id for r in emp_res.all()]

    goal_quarter_map = await _get_goal_quarter_map(remote, year)

    # Evaluations for department employees
    d_evals = []
    if emp_ids:
        evals_res = await local.execute(
            select(
                AiEvaluation.id,
                AiEvaluation.goal_id,
                AiEvaluation.overall_index,
                AiEvaluation.alignment_level,
                AiEvaluation.scores_json,
            ).where(AiEvaluation.employee_id.in_(emp_ids))
        )
        d_evals = evals_res.all()

    # Group by quarter using prebuilt dict
    eval_by_q = defaultdict(list)
    for ev in d_evals:
        if ev.goal_id and ev.goal_id in goal_quarter_map:
            eval_by_q[goal_quarter_map[ev.goal_id]].append(ev)

    trend = []
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        q_evals = eval_by_q.get(q, [])
        if q_evals:
            avg_idx = round(sum(e.overall_index for e in q_evals) / len(q_evals), 2)
            strategic = round(sum(1 for e in q_evals if e.alignment_level == "strategic") / len(q_evals), 2)
            criterion_avgs = {}
            for k in CRITERION_KEYS:
                vals = [e.scores_json.get(k, 0) for e in q_evals if e.scores_json]
                criterion_avgs[CRITERION_RU[k]] = round(sum(vals) / len(vals), 2) if vals else 0.0
            trend.append({
                "quarter": q,
                "avg_smart_index": avg_idx,
                "evaluated_goals": len(q_evals),
                "strategic_ratio": strategic,
                "criterion_scores": criterion_avgs,
            })
        else:
            trend.append({"quarter": q, "avg_smart_index": None, "evaluated_goals": 0, "strategic_ratio": None, "criterion_scores": {}})

    return {"department": dept_name, "year": year, "trend": trend}