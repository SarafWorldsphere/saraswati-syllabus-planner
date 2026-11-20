"""Boards, the grades they print, and the subjects under a grade.

Platform rows have no tenant. Admin and Headmaster write them. Any signed-in
role can read them. A calendar is not created here: linking one is a separate call.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Caller, get_caller, get_session, require_plan_writer
from app.schemas.common import ItemList
from app.schemas.platform import (
    BoardCalendarLink,
    BoardCalendarOut,
    BoardCreate,
    BoardOut,
    CalendarOut,
    GradeCreate,
    GradeOut,
    SubjectCreate,
    SubjectOut,
)
from app.services.platform_data import PlatformData
from app.utils.lists import item_list

router = APIRouter(prefix="/boards", tags=["boards"])


@router.post("", response_model=BoardOut, status_code=201, summary="Create a board")
def create_board(
    body: BoardCreate,
    db: Session = Depends(get_session),
    _: Caller = Depends(require_plan_writer),
):
    """A curriculum authority such as AP SCERT or CBSE. This does not create a calendar."""
    return PlatformData(db).create_board(body)


@router.get("", response_model=ItemList[BoardOut], summary="List boards")
def list_boards(db: Session = Depends(get_session), _: Caller = Depends(get_caller)):
    rows = PlatformData(db).list_boards()
    return item_list(rows)


@router.get("/{board_id}", response_model=BoardOut, summary="Read one board")
def get_board(board_id: int, db: Session = Depends(get_session), _: Caller = Depends(get_caller)):
    return PlatformData(db).get_board(board_id)


@router.post("/{board_id}/grades", response_model=GradeOut, status_code=201, summary="Add a grade")
def create_grade(
    board_id: int,
    body: GradeCreate,
    db: Session = Depends(get_session),
    _: Caller = Depends(require_plan_writer),
):
    return PlatformData(db).create_grade(board_id, body)


@router.get("/{board_id}/grades", response_model=ItemList[GradeOut], summary="List grades")
def list_grades(board_id: int, db: Session = Depends(get_session), _: Caller = Depends(get_caller)):
    return item_list(PlatformData(db).list_grades(board_id))


@router.post("/{board_id}/subjects", response_model=SubjectOut, status_code=201, summary="Add a subject")
def create_subject(
    board_id: int,
    body: SubjectCreate,
    db: Session = Depends(get_session),
    _: Caller = Depends(require_plan_writer),
):
    return PlatformData(db).create_subject(board_id, body)


@router.get("/{board_id}/subjects", response_model=ItemList[SubjectOut], summary="List subjects")
def list_subjects(board_id: int, db: Session = Depends(get_session), _: Caller = Depends(get_caller)):
    return item_list(PlatformData(db).list_subjects(board_id))


@router.post(
    "/{board_id}/calendars",
    response_model=BoardCalendarOut,
    status_code=201,
    summary="Recommend a calendar to a board",
)
def link_calendar(
    board_id: int,
    body: BoardCalendarLink,
    db: Session = Depends(get_session),
    _: Caller = Depends(require_plan_writer),
):
    """The calendar already exists and has no board_id. This only records the recommendation."""
    return PlatformData(db).link_board_calendar(board_id, body)


@router.get("/{board_id}/calendars", response_model=ItemList[CalendarOut], summary="Calendars a board recommends")
def calendars_for_board(
    board_id: int,
    academic_year: str | None = None,
    db: Session = Depends(get_session),
    _: Caller = Depends(get_caller),
):
    return item_list(PlatformData(db).calendars_for_board(board_id, academic_year))
