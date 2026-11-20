"""Generate a lesson plan for the current topic only.

The caller does not send a chapter name. The current topic is the first
active plan row, in plan_seq, that is not yet fully taught. A later topic
cannot be requested from here.
"""

import httpx
from fastapi import HTTPException, status
from saraswati_tenant import current_school
from sqlalchemy.orm import Session

from app.api.deps import Caller
from app.core.config import settings
from app.models.syllabus_plan import SyllabusPlan
from app.models.teaching_log import TeachingLog
from app.services.school_year_service import SchoolYearService
from app.utils.current_topic import first_open


class CurrentLessonService:
    def __init__(self, db: Session, caller: Caller):
        self.db = db
        self.caller = caller
        self.years = SchoolYearService(db, caller)

    def generate(self, class_id: int, subject_id: int) -> dict:
        year = self.years.active()
        plans = (
            self.db.query(SyllabusPlan)
            .filter(
                SyllabusPlan.tenant_id == self.caller.tenant_id,
                SyllabusPlan.school_year_id == year.school_year_id,
                SyllabusPlan.class_id == class_id,
                SyllabusPlan.subject_id == subject_id,
            )
            .order_by(SyllabusPlan.plan_seq)
            .all()
        )
        taught = {
            plan.plan_id: self.db.query(TeachingLog)
            .filter(TeachingLog.plan_id == plan.plan_id, TeachingLog.status == "taught")
            .count()
            for plan in plans
        }
        current = first_open(plans, taught)
        if current is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No current topic. The plan is fully taught or empty.")
        body = self._plan_body(current, class_id, subject_id)
        return {
            "plan_id": current.plan_id,
            "topic_name": current.topic_name,
            "planned_periods": current.planned_periods,
            "version_no": current.version_no,
            "plan": body,
        }

    def _plan_body(self, plan: SyllabusPlan, class_id: int, subject_id: int) -> dict:
        periods = plan.planned_periods or 1
        header = {
            "topic": plan.topic_name,
            "class_id": class_id,
            "subject_id": subject_id,
            "no_of_periods": periods,
            "school_name": current_school().config.get("schoolName", ""),
        }
        if not settings.AI_SERVICE_URL:
            # The faculty generator is optional here. The contract of this
            # route is still met: the plan is for this topic and no other.
            return {
                **header,
                "source": "syllabus-planner",
                "lesson_plan": f"Teach {plan.topic_name} across {periods} period(s).",
            }
        payload = {
            "chapterId": plan.chapter_id or 0,
            "topic": plan.topic_name,
            "noOfPeriods": periods,
            "durationMinutes": periods * settings.PERIOD_MINUTES,
            "classLevel": f"Class {class_id}",
            "section": "Not specified",
            "subject": str(subject_id),
            "designation": "Teacher",
            "dateOfCommencement": "Not specified",
            "expectedCompletion": "Not specified",
            "actualCompletion": "",
        }
        try:
            response = httpx.post(
                f"{settings.AI_SERVICE_URL.rstrip('/')}/api/v1/ai/teacher/lesson-plan",
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Lesson plan service failed: {exc}") from exc
        return {**header, "source": "ai", "lesson_plan": data.get("lessonPlan", data)}
