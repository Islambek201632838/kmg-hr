from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_remote_session
from app.services.smart_evaluator import evaluate_goal
from app.api.evaluate import get_employee_context

router = APIRouter()

# Эталонный датасет: цели с экспертной оценкой
BENCHMARK_GOALS = [
    {
        "goal_text": "Улучшить работу",
        "expert_index": 0.15,
        "expert_type": "activity",
        "expert_align": "operational",
        "comment": "Размытая формулировка, нет метрики, срока, конкретики",
    },
    {
        "goal_text": "Проводить еженедельные встречи с командой",
        "expert_index": 0.40,
        "expert_type": "activity",
        "expert_align": "operational",
        "comment": "Activity-цель, нет результата, нет метрики",
    },
    {
        "goal_text": "Повысить эффективность процессов в подразделении",
        "expert_index": 0.30,
        "expert_type": "activity",
        "expert_align": "functional",
        "comment": "Размытая, нет метрики и срока, но связана с подразделением",
    },
    {
        "goal_text": "Снизить количество дефектов после релиза на 20%",
        "expert_index": 0.70,
        "expert_type": "output",
        "expert_align": "functional",
        "comment": "Есть метрика (20%), но нет конкретного срока",
    },
    {
        "goal_text": "Подготовить отчёт по итогам квартала",
        "expert_index": 0.35,
        "expert_type": "activity",
        "expert_align": "operational",
        "comment": "Activity, нет метрики результата, размытый срок",
    },
    {
        "goal_text": "Сократить среднее время закрытия заявок на 15% (с 19 до 16 часов) к 30.09.2025",
        "expert_index": 0.90,
        "expert_type": "output",
        "expert_align": "functional",
        "comment": "SMART: конкретная метрика, срок, связь с KPI",
    },
    {
        "goal_text": "Сократить задержку обновления ETL-витрин с 136 до 109 минут к 30.09.2025 за счёт оптимизации пайплайнов DWH",
        "expert_index": 0.92,
        "expert_type": "output",
        "expert_align": "strategic",
        "comment": "Сильная SMART-цель с точными цифрами и сроком",
    },
    {
        "goal_text": "Обеспечить снижение доли неуспешных изменений с 5.6% до 4.5% к концу Q3 2025 через внедрение автоматизированного тестирования",
        "expert_index": 0.95,
        "expert_type": "impact",
        "expert_align": "strategic",
        "comment": "Impact-цель с метрикой, сроком, механизмом достижения",
    },
    {
        "goal_text": "Изучить новые технологии машинного обучения",
        "expert_index": 0.20,
        "expert_type": "activity",
        "expert_align": "operational",
        "comment": "Activity, нет метрики, срока, результата, связки",
    },
    {
        "goal_text": "Увеличить охват сотрудников обучением по информационной безопасности с 60% до 90% к 30.09.2025",
        "expert_index": 0.88,
        "expert_type": "output",
        "expert_align": "functional",
        "comment": "SMART: чёткая метрика, срок, связь с KPI обучения",
    },
]


@router.get(
    "/benchmark",
    summary="Бенчмарк AI-оценки vs экспертная разметка",
    response_description="MAE, корреляция Спирмена, точность типа цели и стратегической связки",
)
async def run_benchmark(
    employee_id: int = 269,
    remote: AsyncSession = Depends(get_remote_session),
):
    """
    Прогоняет эталонный датасет из 10 целей через AI-оценку
    и сравнивает с экспертной разметкой.
    """
    ctx = await get_employee_context(employee_id, "Q3", 2025, remote)
    if not ctx:
        return {"error": "Сотрудник не найден"}

    results = []
    total_diff = 0.0
    type_match = 0
    align_match = 0

    for item in BENCHMARK_GOALS:
        try:
            ai = await evaluate_goal(
                goal_text=item["goal_text"],
                position=ctx["position"],
                department=ctx["department"],
                manager_goals=ctx["manager_goals"],
                kpis=ctx["kpis"],
            )

            ai_index = ai["smart_index"]
            ai_type = ai.get("goal_type", "output")
            ai_align = ai.get("strategic_alignment", {}).get("level", "operational")

            diff = abs(ai_index - item["expert_index"])
            total_diff += diff
            t_match = ai_type == item["expert_type"]
            a_match = ai_align == item["expert_align"]
            if t_match:
                type_match += 1
            if a_match:
                align_match += 1

            results.append({
                "goal_text": item["goal_text"][:80],
                "expert_index": item["expert_index"],
                "ai_index": ai_index,
                "diff": round(diff, 2),
                "expert_type": item["expert_type"],
                "ai_type": ai_type,
                "type_match": t_match,
                "expert_align": item["expert_align"],
                "ai_align": ai_align,
                "align_match": a_match,
                "comment": item["comment"],
            })
        except Exception as e:
            results.append({
                "goal_text": item["goal_text"][:80],
                "error": str(e),
            })

    n = len(BENCHMARK_GOALS)
    mae = round(total_diff / n, 3) if n else 0
    type_accuracy = round(type_match / n * 100, 1) if n else 0
    align_accuracy = round(align_match / n * 100, 1) if n else 0

    # Корреляция: Спирмен
    expert_scores = [item["expert_index"] for item in BENCHMARK_GOALS]
    ai_scores = [r.get("ai_index", 0) for r in results if "ai_index" in r]
    correlation = _spearman(expert_scores, ai_scores) if len(ai_scores) == len(expert_scores) else 0

    return {
        "total_goals": n,
        "metrics": {
            "mae": mae,
            "spearman_correlation": correlation,
            "type_accuracy": type_accuracy,
            "align_accuracy": align_accuracy,
        },
        "interpretation": {
            "mae": f"Средняя абсолютная ошибка: {mae} (чем ниже, тем лучше; < 0.15 — отлично)",
            "correlation": f"Корреляция Спирмена: {correlation} (> 0.8 — сильная, > 0.6 — умеренная)",
            "type_accuracy": f"Точность определения типа цели: {type_accuracy}%",
            "align_accuracy": f"Точность определения стратегической связки: {align_accuracy}%",
        },
        "results": results,
    }


def _spearman(x: list[float], y: list[float]) -> float:
    """Ранговая корреляция Спирмена без scipy."""
    n = len(x)
    if n < 3:
        return 0.0

    def ranks(arr):
        sorted_idx = sorted(range(n), key=lambda i: arr[i])
        r = [0.0] * n
        for rank, idx in enumerate(sorted_idx):
            r[idx] = rank + 1
        return r

    rx = ranks(x)
    ry = ranks(y)
    d_sq = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    rho = 1 - (6 * d_sq) / (n * (n ** 2 - 1))
    return round(rho, 3)