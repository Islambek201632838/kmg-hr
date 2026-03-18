from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_remote_session
from app.models import Employee, Department, Position, Goal
from app.schemas import EmployeeShort

router = APIRouter()


@router.get(
    "/employees",
    response_model=list[EmployeeShort],
    summary="Список активных сотрудников",
    response_description="ФИО, должность, подразделение, кол-во целей",
)
async def list_employees(
    department_id: int | None = None,
    session: AsyncSession = Depends(get_remote_session),
):
    """
    Возвращает всех активных сотрудников из корпоративной HR-системы.
    Опциональная фильтрация по `department_id`.
    Используется для выбора сотрудника во всех формах UI.
    """
    q = (
        select(
            Employee.id,
            Employee.full_name,
            Position.name.label("position"),
            Department.name.label("department"),
            func.count(Goal.goal_id).label("goals_count"),
        )
        .join(Position, Employee.position_id == Position.id)
        .join(Department, Employee.department_id == Department.id)
        .outerjoin(Goal, Employee.id == Goal.employee_id)
        .where(Employee.is_active == True)
        .group_by(Employee.id, Employee.full_name, Position.name, Department.name)
        .order_by(Employee.full_name)
    )

    if department_id:
        q = q.where(Employee.department_id == department_id)

    result = await session.execute(q)
    rows = result.all()

    return [
        EmployeeShort(
            id=r.id,
            full_name=r.full_name,
            position=r.position,
            department=r.department,
            goals_count=r.goals_count,
        )
        for r in rows
    ]
