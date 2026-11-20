"""Coverage status lives in one place so every screen agrees.

on_track at 90 percent or above, behind from 70 to 89, critical below 70.
"""


def coverage_status(percent: int) -> str:
    if percent >= 90:
        return "on_track"
    if percent >= 70:
        return "behind"
    return "critical"


def percent_of(covered: int, planned: int) -> int:
    if planned <= 0:
        return 100
    return round(100 * covered / planned)
