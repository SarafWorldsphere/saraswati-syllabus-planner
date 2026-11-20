"""Calendars and the blocks that divide them.

A calendar body has no board_id. Two boards can recommend the same dates.
A block is a planning window. It does not own a lesson.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Caller, get_caller, get_session, require_plan_writer
from app.schemas.common import ItemList
from app.schemas.platform import BlockCreate, BlockOut, CalendarCreate, CalendarOut
from app.services.platform_data import PlatformData
from app.utils.lists import item_list

router = APIRouter(tags=["calendars"])


@router.post("/calendars", response_model=CalendarOut, status_code=201, summary="Create a calendar")
def create_calendar(
    body: CalendarCreate,
    db: Session = Depends(get_session),
    _: Caller = Depends(require_plan_writer),
):
    """Dates for a year and a region. Do not send a board_id."""
    return PlatformData(db).create_calendar(body)


@router.get("/calendars", response_model=ItemList[CalendarOut], summary="List calendars")
def list_calendars(
    academic_year: str | None = None,
    region: str | None = None,
    db: Session = Depends(get_session),
    _: Caller = Depends(get_caller),
):
    """Filter by year and region without going through a board."""
    return item_list(PlatformData(db).list_calendars(academic_year, region))


@router.post("/calendars/{calendar_id}/blocks", response_model=BlockOut, status_code=201, summary="Add a block")
def create_block(
    calendar_id: int,
    body: BlockCreate,
    db: Session = Depends(get_session),
    _: Caller = Depends(require_plan_writer),
):
    return PlatformData(db).create_block(calendar_id, body)


@router.get("/calendars/{calendar_id}/blocks", response_model=ItemList[BlockOut], summary="List blocks")
def list_blocks(calendar_id: int, db: Session = Depends(get_session), _: Caller = Depends(get_caller)):
    return item_list(PlatformData(db).list_blocks(calendar_id))
