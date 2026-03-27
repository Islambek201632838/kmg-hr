def check_goal_alerts(
    overall_index: float,
    alignment_level: str,
    goal_type: str,
    goals_count: int,
    total_weight: float,
    has_duplicate: bool = False,
    duplicate_info: str | None = None,
    historical_avg_index: float | None = None,
) -> list[dict]:
    """
    Check alert conditions per TZ requirements.
    Returns list of {level, message, code}.
    Levels: critical, warning, info
    """
    alerts = []

    # SMART quality threshold
    if overall_index < 0.5:
        alerts.append({
            "level": "critical",
            "code": "SMART_LOW",
            "message": f"Низкий SMART-индекс ({overall_index:.2f}). Цель требует переработки",
        })
    elif overall_index < 0.7:
        alerts.append({
            "level": "warning",
            "code": "SMART_BELOW_THRESHOLD",
            "message": f"SMART-индекс ниже порога ({overall_index:.2f}). Рекомендуется переформулировка",
        })

    # F-17: Strategic alignment
    if alignment_level == "operational":
        alerts.append({
            "level": "warning",
            "code": "F17_NO_STRATEGIC_LINK",
            "message": "Цель не связана со стратегией компании или KPI подразделения",
        })

    # F-18: Weight sum
    if total_weight > 0 and abs(total_weight - 100) > 1:
        alerts.append({
            "level": "warning",
            "code": "F18_WEIGHT_MISMATCH",
            "message": f"Суммарный вес целей ({total_weight:.0f}%) отличается от 100%",
        })

    # F-16: Goal count
    if goals_count > 0 and goals_count < 3:
        alerts.append({
            "level": "warning",
            "code": "F16_TOO_FEW",
            "message": f"Целей ({goals_count}) меньше рекомендуемого минимума (3)",
        })
    elif goals_count > 5:
        alerts.append({
            "level": "warning",
            "code": "F16_TOO_MANY",
            "message": f"Целей ({goals_count}) больше рекомендуемого максимума (5)",
        })

    # F-19: Goal type
    if goal_type == "activity":
        alerts.append({
            "level": "info",
            "code": "F19_ACTIVITY_GOAL",
            "message": "Цель сформулирована как активность (activity). Рекомендуется переформулировать в результат (output/impact)",
        })

    # F-20: Historical achievability
    if historical_avg_index is not None and historical_avg_index > 0:
        deviation = abs(overall_index - historical_avg_index) / historical_avg_index
        if deviation > 0.30:
            direction = "выше" if overall_index > historical_avg_index else "ниже"
            alerts.append({
                "level": "warning",
                "code": "F20_ACHIEVABILITY",
                "message": (
                    f"SMART-индекс ({overall_index:.2f}) на {deviation:.0%} {direction} среднего "
                    f"для аналогичных ролей ({historical_avg_index:.2f}) — проверьте реалистичность"
                ),
            })

    # F-21: Duplicate
    if has_duplicate:
        msg = "Обнаружена цель с высокой степенью сходства с существующей"
        if duplicate_info:
            msg += f": {duplicate_info}"
        alerts.append({
            "level": "info",
            "code": "F21_DUPLICATE",
            "message": msg,
        })

    return alerts


def check_batch_alerts(
    goals_count: int,
    total_weight: float,
    avg_index: float,
    activity_count: int,
    no_strategic_count: int,
) -> list[dict]:
    """Batch-level alerts for evaluate-batch and dashboard."""
    alerts = []

    if goals_count > 0 and goals_count < 3:
        alerts.append({
            "level": "warning",
            "code": "F16_TOO_FEW",
            "message": f"У сотрудника {goals_count} целей, рекомендуется минимум 3",
        })
    elif goals_count > 5:
        alerts.append({
            "level": "warning",
            "code": "F16_TOO_MANY",
            "message": f"У сотрудника {goals_count} целей, рекомендуется максимум 5",
        })

    if total_weight > 0 and abs(total_weight - 100) > 1:
        alerts.append({
            "level": "warning",
            "code": "F18_WEIGHT_MISMATCH",
            "message": f"Суммарный вес целей ({total_weight:.0f}%) отличается от 100%",
        })

    if avg_index < 0.5:
        alerts.append({
            "level": "critical",
            "code": "BATCH_LOW_QUALITY",
            "message": f"Средний SMART-индекс ({avg_index:.2f}) критически низкий",
        })

    if activity_count > 0:
        alerts.append({
            "level": "info",
            "code": "F19_ACTIVITY_GOALS",
            "message": f"{activity_count} из {goals_count} целей — activity-based. Рекомендуется переформулировать",
        })

    if no_strategic_count > 0:
        alerts.append({
            "level": "warning",
            "code": "F17_BATCH_NO_STRATEGIC",
            "message": f"{no_strategic_count} из {goals_count} целей без стратегической связки",
        })

    return alerts
