"""The year this school is teaching: one board and one calendar, plus local holidays.

Headmaster and Admin open the year. Other roles only read it.
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import Caller, get_caller, get_session, require_plan_writer
from app.schemas.common import ItemList
from app.schemas.school import HolidayCreate, HolidayOut, SchoolYearCreate, SchoolYearOut
from app.services.school_year_service import SchoolYearService
from app.utils.lists import item_list

router = APIRouter(tags=["academic year"])


@router.post("/academic-year", response_model=SchoolYearOut, status_code=201, summary="Open the school year")
def open_year(
    body: SchoolYearCreate,
    db: Session = Depends(get_session),
    caller: Caller = Depends(require_plan_writer),
):
    """Stores board_id (what is taught) and calendar_id (when). The previous active year is closed."""
    return SchoolYearService(db, caller).open_year(body)


@router.get("/academic-year", response_model=SchoolYearOut, summary="Read the active school year")
def read_year(db: Session = Depends(get_session), caller: Caller = Depends(get_caller)):
    return SchoolYearService(db, caller).read()


@router.post("/holidays", response_model=HolidayOut, status_code=201, summary="Add a local holiday")
def add_holiday(
    body: HolidayCreate,
    db: Session = Depends(get_session),
    caller: Caller = Depends(require_plan_writer),
):
    return SchoolYearService(db, caller).add_holiday(body)


@router.get("/holidays", response_model=ItemList[HolidayOut], summary="List local holidays")
def list_holidays(db: Session = Depends(get_session), caller: Caller = Depends(get_caller)):
    return item_list(SchoolYearService(db, caller).list_holidays())


@router.delete("/holidays/{holiday_id}", status_code=204, summary="Remove a local holiday")
def delete_holiday(
    holiday_id: int,
    db: Session = Depends(get_session),
    caller: Caller = Depends(require_plan_writer),
):
    SchoolYearService(db, caller).delete_holiday(holiday_id)
    return Response(status_code=204)
