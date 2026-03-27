import time
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_remote_session
from app.models import Employee, Department, Position, Goal
from app.schemas import EmployeeShort

router = APIRouter()

# In-memory cache: {cache_key: (timestamp, data)}
_cache: dict[str, tuple[float, list]] = {}
CACHE_TTL = 300  # 5 minutes


def _get_cached(key: str):
    entry = _cache.get(key)
    if entry and (time.time() - entry[0]) < CACHE_TTL:
        return entry[1]
    return None


def _set_cached(key: str, data: list):
    _cache[key] = (time.time(), data)


@router.get(
    "/employees",
    response_model=list[EmployeeShort],
    summary="Список активных сотрудников (кеш 5 мин)",
    response_description="ФИО, должность, подразделение, кол-во целей",
)
async def list_employees(
    department_id: int | None = None,
    session: AsyncSession = Depends(get_remote_session),
):
    """
    Возвращает всех активных сотрудников из корпоративной HR-системы.
    Результат кешируется на 5 минут (сбрасывается при перезапуске).
    """
    cache_key = f"employees:{department_id or 'all'}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

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
    data = [
        EmployeeShort(
            id=r.id,
            full_name=r.full_name,
            position=r.position,
            department=r.department,
            goals_count=r.goals_count,
        )
        for r in result.all()
    ]

    _set_cached(cache_key, data)
    return data