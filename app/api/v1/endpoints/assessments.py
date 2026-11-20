"""Assessment windows published by a board, and the blocks each one covers."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Caller, get_caller, get_session, require_plan_writer
from app.schemas.common import ItemList
from app.schemas.platform import AssessmentBlockCreate, AssessmentBlockOut, AssessmentCreate, AssessmentOut
from app.services.platform_data import PlatformData
from app.utils.lists import item_list

router = APIRouter(prefix="/assessment-templates", tags=["assessments"])


@router.post("", response_model=AssessmentOut, status_code=201, summary="Create an assessment template")
def create_assessment(
    body: AssessmentCreate,
    db: Session = Depends(get_session),
    _: Caller = Depends(require_plan_writer),
):
    return PlatformData(db).create_assessment(body)


@router.get("", response_model=ItemList[AssessmentOut], summary="List assessment templates")
def list_assessments(
    board_id: int | None = None,
    academic_year: str | None = None,
    db: Session = Depends(get_session),
    _: Caller = Depends(get_caller),
):
    return item_list(PlatformData(db).list_assessments(board_id, academic_year))


@router.post(
    "/{template_id}/blocks",
    response_model=AssessmentBlockOut,
    status_code=201,
    summary="Mark a block as covered by this assessment",
)
def add_block(
    template_id: int,
    body: AssessmentBlockCreate,
    db: Session = Depends(get_session),
    _: Caller = Depends(require_plan_writer),
):
    link = PlatformData(db).add_assessment_block(template_id, body)
    return {
        "assessment_block_id": link.assessment_block_id,
        "template_id": link.template_id,
        "block_id": link.block_id,
        "block_name": None,
    }


@router.get("/{template_id}/blocks", response_model=ItemList[AssessmentBlockOut], summary="Blocks an assessment covers")
def list_blocks(template_id: int, db: Session = Depends(get_session), _: Caller = Depends(get_caller)):
    return item_list(PlatformData(db).list_assessment_blocks(template_id))
