"""What the teacher marked today.

Faculty writes this. The unique key is the school, the class, the date, and
the period, so a correction updates the same row. not_taken is a real mark.
class_id is on each entry. It is not a header.
"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Caller, get_session, require_faculty
from app.schemas.common import ItemList
from app.schemas.school import TeachingDay, TeachingLogOut, TodayOut
from app.services.teaching_log_service import TeachingLogService
from app.utils.lists import item_list

router = APIRouter(prefix="/teaching-log", tags=["teaching log"])


@router.get("/today", response_model=TodayOut, summary="Periods to mark today")
def today(
    log_date: date | None = None,
    db: Session = Depends(get_session),
    caller: Caller = Depends(require_faculty),
):
    """Prefills from the timetable when that table exists. A Sunday or a school holiday is not a working day."""
    return TeachingLogService(db, caller).today(log_date or date.today())


@router.post("", response_model=TodayOut, summary="Save today's marks")
def save_day(
    body: TeachingDay,
    db: Session = Depends(get_session),
    caller: Caller = Depends(require_faculty),
):
    """Upserts on class, date, and period. status is taught, partly, or not_taken."""
    return TeachingLogService(db, caller).save_day(body)


@router.get("", response_model=ItemList[TeachingLogOut], summary="Teaching history")
def history(
    class_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_session),
    caller: Caller = Depends(require_faculty),
):
    return item_list(TeachingLogService(db, caller).history(class_id, start, end))
