"""Coverage compared with the plan. Nothing here is stored.

on_track is 90 percent or above, behind is 70 to 89, critical is below 70.
Headmaster and Admin read it. A teacher does not.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Caller, get_session, require_plan_writer
from app.schemas.common import ItemList
from app.schemas.school import CoverageDetail, CoverageRow
from app.services.coverage_service import CoverageService
from app.utils.lists import item_list

router = APIRouter(prefix="/coverage", tags=["coverage"])


@router.get("", response_model=ItemList[CoverageRow], summary="Coverage by class and subject")
def grid(
    block_id: int | None = None,
    db: Session = Depends(get_session),
    caller: Caller = Depends(require_plan_writer),
):
    """against_board counts board topics whose first block has ended and that are still open."""
    return item_list(CoverageService(db, caller).grid(block_id))


@router.get("/detail", response_model=CoverageDetail, summary="Topics inside one class and subject")
def detail(
    class_id: int,
    subject_id: int,
    block_id: int | None = None,
    db: Session = Depends(get_session),
    caller: Caller = Depends(require_plan_writer),
):
    return CoverageService(db, caller).detail(class_id, subject_id, block_id)
