"""Board topics, and the blocks a topic occupies when it does not fit in one.

syllabus_item has no block_id. The span rows say where the periods fall.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Caller, get_caller, get_session, require_plan_writer
from app.schemas.common import ItemList
from app.schemas.platform import SpanCreate, SpanOut, SyllabusItemCreate, SyllabusItemOut
from app.services.platform_data import PlatformData
from app.utils.lists import item_list

router = APIRouter(prefix="/syllabus-items", tags=["syllabus items"])


@router.post("", response_model=SyllabusItemOut, status_code=201, summary="Create a syllabus item")
def create_item(
    body: SyllabusItemCreate,
    db: Session = Depends(get_session),
    _: Caller = Depends(require_plan_writer),
):
    """Omit spans to split the topic across the board's default calendar for that year."""
    return PlatformData(db).create_item(body)


@router.get("", response_model=ItemList[SyllabusItemOut], summary="List syllabus items")
def list_items(
    board_id: int | None = None,
    academic_year: str | None = None,
    db: Session = Depends(get_session),
    _: Caller = Depends(get_caller),
):
    return item_list(PlatformData(db).list_items(board_id, academic_year))


@router.get("/{item_id}/spans", response_model=ItemList[SpanOut], summary="Blocks this topic occupies")
def list_spans(item_id: int, db: Session = Depends(get_session), _: Caller = Depends(get_caller)):
    return item_list(PlatformData(db).list_item_spans(item_id))


@router.post("/{item_id}/spans", response_model=SpanOut, status_code=201, summary="Add a span")
def add_span(
    item_id: int,
    body: SpanCreate,
    db: Session = Depends(get_session),
    _: Caller = Depends(require_plan_writer),
):
    """segment_seq 1 is the start. A later segment is the remainder that continues."""
    return PlatformData(db).add_span(item_id, body)
