"""The current topic is the first active plan row, in teaching order, that is not fully taught.

A row is fully taught when the number of periods marked taught reaches
planned_periods. A null planned_periods is fully taught by a single taught mark.
partly and not_taken do not finish the topic.
"""


def is_fully_taught(planned_periods: int | None, taught_periods: int) -> bool:
    if not planned_periods:
        return taught_periods >= 1
    return taught_periods >= planned_periods


def first_open(plans: list, taught_by_plan: dict[int, int]):
    """plans are already ordered by plan_seq. Each item has plan_id, planned_periods, is_active."""
    for plan in plans:
        if not plan.is_active:
            continue
        taught = taught_by_plan.get(plan.plan_id, 0)
        if not is_fully_taught(plan.planned_periods, taught):
            return plan
    return None
