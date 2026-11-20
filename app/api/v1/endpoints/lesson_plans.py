"""A lesson plan for the current topic only.

The body is class_id and subject_id. There is no chapter name. The current
topic is the first active plan row, in plan_seq, that is not fully taught.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Caller, get_session, require_faculty
from app.schemas.school import CurrentLessonOut, CurrentLessonRequest
from app.services.current_lesson_service import CurrentLessonService

router = APIRouter(prefix="/lesson-plans", tags=["lesson plans"])


@router.post("/current", response_model=CurrentLessonOut, summary="Lesson plan for the current topic")
def current(
    body: CurrentLessonRequest,
    db: Session = Depends(get_session),
    caller: Caller = Depends(require_faculty),
):
    """A later topic cannot be requested. When AI_SERVICE_URL is empty, the plan is still for this topic."""
    return CurrentLessonService(db, caller).generate(body.class_id, body.subject_id)
