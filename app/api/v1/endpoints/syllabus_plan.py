"""The school syllabus plan.

Headmaster and Admin create and edit it. Every other role only reads it.
class_id is a query or a body field. This service does not read X-Class-Id,
and it does not yet check which class the role is allowed to see.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Caller, get_caller, get_session, require_plan_writer
from app.schemas.common import ItemList
from app.schemas.school import (
    AuditOut,
    CoveredTopic,
    PlanCreate,
    PlanGenerate,
    PlanGenerateResult,
    PlanOut,
    PlanPatch,
)
from app.services.coverage_service import CoverageService
from app.services.syllabus_plan_service import SyllabusPlanService
from app.utils.lists import item_list

router = APIRouter(prefix="/syllabus-plan", tags=["syllabus plan"])


@router.post("/generate", response_model=PlanGenerateResult, summary="Build the plan from the board")
def generate(
    body: PlanGenerate,
    db: Session = Depends(get_session),
    caller: Caller = Depends(require_plan_writer),
):
    """Copies stored spans. A topic with no span is split across blocks. Existing rows are left alone."""
    return SyllabusPlanService(db, caller).generate(body.class_id, body.subject_id)


@router.get("/mine", response_model=ItemList[PlanOut], summary="Read the plan")
def mine(
    class_id: int | None = None,
    subject_id: int | None = None,
    db: Session = Depends(get_session),
    caller: Caller = Depends(get_caller),
):
    """The teacher's view of the plan. Any known role may read. Nobody writes from this route."""
    return item_list(SyllabusPlanService(db, caller).list_plans(class_id, subject_id, None))


@router.get("/unmatched", response_model=ItemList[PlanOut], summary="Topics with no chapter match")
def unmatched(
    class_id: int | None = None,
    subject_id: int | None = None,
    db: Session = Depends(get_session),
    caller: Caller = Depends(require_plan_writer),
):
    return item_list(SyllabusPlanService(db, caller).unmatched(class_id, subject_id))


@router.get("/covered", response_model=ItemList[CoveredTopic], summary="Topics already taught")
def covered(
    class_id: int,
    subject_id: int,
    template_id: int | None = None,
    db: Session = Depends(get_session),
    caller: Caller = Depends(get_caller),
):
    """What auto test should ask for. template_id limits the list to the blocks that assessment covers."""
    return item_list(CoverageService(db, caller).covered_topics(class_id, subject_id, template_id))


@router.get("", response_model=ItemList[PlanOut], summary="List the plan for a class and subject")
def list_plans(
    class_id: int | None = None,
    subject_id: int | None = None,
    block_id: int | None = None,
    db: Session = Depends(get_session),
    caller: Caller = Depends(get_caller),
):
    return item_list(SyllabusPlanService(db, caller).list_plans(class_id, subject_id, block_id))


@router.post("", response_model=PlanOut, status_code=201, summary="Add a topic the board never listed")
def add_topic(
    body: PlanCreate,
    db: Session = Depends(get_session),
    caller: Caller = Depends(require_plan_writer),
):
    """source is admin and syllabus_item_id is null. The row starts at version 1."""
    return SyllabusPlanService(db, caller).add_admin_topic(body)


@router.patch("/{plan_id}", response_model=PlanOut, summary="Edit a plan row")
def update_plan(
    plan_id: int,
    body: PlanPatch,
    db: Session = Depends(get_session),
    caller: Caller = Depends(require_plan_writer),
):
    """Send the version_no you last read. An older version is rejected. is_active false turns a chapter off."""
    return SyllabusPlanService(db, caller).update(plan_id, body)


@router.get("/{plan_id}/audit", response_model=ItemList[AuditOut], summary="Versions of one plan row")
def audit(plan_id: int, db: Session = Depends(get_session), caller: Caller = Depends(get_caller)):
    return item_list(SyllabusPlanService(db, caller).audit(plan_id))
