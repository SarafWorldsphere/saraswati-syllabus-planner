"""Coverage is derived from the teaching log against the syllabus plan.

It is not a table. against_board counts board topics whose first block has
ended and that are still not fully taught. admin_approved counts topics an
admin added or switched off, so the screen can separate a decision from a delay.
"""

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import Caller
from app.models.assessment_block import AssessmentBlock
from app.models.calendar_block import CalendarBlock
from app.models.syllabus_plan import SyllabusPlan
from app.models.syllabus_plan_segment import SyllabusPlanSegment
from app.models.teaching_log import TeachingLog
from app.services.school_year_service import SchoolYearService
from app.utils.coverage import coverage_status, percent_of
from app.utils.current_topic import is_fully_taught


class CoverageService:
    def __init__(self, db: Session, caller: Caller):
        self.db = db
        self.caller = caller
        self.years = SchoolYearService(db, caller)

    def grid(self, block_id: int | None) -> list[dict]:
        year = self.years.active()
        plans = self._plans(year.school_year_id, None, None, block_id)
        groups: dict[tuple[int, int], list[SyllabusPlan]] = {}
        for plan in plans:
            groups.setdefault((plan.class_id, plan.subject_id), []).append(plan)
        block = self.db.get(CalendarBlock, block_id) if block_id else None
        rows = []
        for (class_id, subject_id), group in sorted(groups.items()):
            row = self._summarise(group)
            row["class_id"] = class_id
            row["subject_id"] = subject_id
            row["block_id"] = block_id
            row["block_name"] = block.block_name if block else None
            rows.append(row)
        return rows

    def detail(self, class_id: int, subject_id: int, block_id: int | None) -> dict:
        year = self.years.active()
        plans = self._plans(year.school_year_id, class_id, subject_id, block_id)
        summary = self._summarise(plans)
        summary["class_id"] = class_id
        summary["subject_id"] = subject_id
        topics = []
        for plan in plans:
            used = self._taught_count(plan.plan_id)
            last = (
                self.db.query(func.max(TeachingLog.log_date))
                .filter(TeachingLog.plan_id == plan.plan_id, TeachingLog.status == "taught")
                .scalar()
            )
            topics.append(
                {
                    "plan_id": plan.plan_id,
                    "topic_name": plan.topic_name,
                    "planned_periods": plan.planned_periods,
                    "periods_used": used,
                    "status": "covered" if is_fully_taught(plan.planned_periods, used) else "open",
                    "last_taught_on": last,
                }
            )
        summary["topics"] = topics
        summary["block_id"] = block_id
        block = self.db.get(CalendarBlock, block_id) if block_id else None
        summary["block_name"] = block.block_name if block else None
        return summary

    def covered_topics(self, class_id: int, subject_id: int, template_id: int | None) -> list[dict]:
        year = self.years.active()
        block_ids = None
        if template_id:
            # The assessment already says which blocks it covers. Limit the paper to those.
            block_ids = [
                row.block_id
                for row in self.db.query(AssessmentBlock).filter(AssessmentBlock.template_id == template_id).all()
            ]
        plans = self._plans(year.school_year_id, class_id, subject_id, None)
        covered = []
        for plan in plans:
            if block_ids is not None:
                segments = (
                    self.db.query(SyllabusPlanSegment)
                    .filter(SyllabusPlanSegment.plan_id == plan.plan_id)
                    .all()
                )
                if not any(segment.block_id in block_ids for segment in segments):
                    continue
            if self._taught_count(plan.plan_id) < 1:
                continue
            last = (
                self.db.query(func.max(TeachingLog.log_date))
                .filter(TeachingLog.plan_id == plan.plan_id, TeachingLog.status == "taught")
                .scalar()
            )
            covered.append(
                {
                    "plan_id": plan.plan_id,
                    "topic_name": plan.topic_name,
                    "chapter_id": plan.chapter_id,
                    "covered_on": last,
                }
            )
        return covered

    def _plans(self, school_year_id: int, class_id: int | None, subject_id: int | None, block_id: int | None):
        query = self.db.query(SyllabusPlan).filter(
            SyllabusPlan.tenant_id == self.caller.tenant_id,
            SyllabusPlan.school_year_id == school_year_id,
            SyllabusPlan.is_active.is_(True),
        )
        if class_id:
            query = query.filter(SyllabusPlan.class_id == class_id)
        if subject_id:
            query = query.filter(SyllabusPlan.subject_id == subject_id)
        rows = query.order_by(SyllabusPlan.plan_seq).all()
        if not block_id:
            return rows
        wanted = {
            segment.plan_id
            for segment in self.db.query(SyllabusPlanSegment).filter(SyllabusPlanSegment.block_id == block_id).all()
        }
        return [row for row in rows if row.plan_id in wanted]

    def _summarise(self, plans: list[SyllabusPlan]) -> dict:
        active = plans
        covered = 0
        against_board = 0
        admin_approved = 0
        today = date.today()
        for plan in active:
            taught = self._taught_count(plan.plan_id)
            done = is_fully_taught(plan.planned_periods, taught)
            if done:
                covered += 1
            if plan.source == "admin":
                admin_approved += 1
            elif not done and self._first_block_ended(plan.plan_id, today):
                against_board += 1
        planned = len(active)
        percent = percent_of(covered, planned)
        return {
            "planned_topics": planned,
            "covered_topics": covered,
            "percent": percent,
            "status": coverage_status(percent),
            "against_board": against_board,
            "admin_approved": admin_approved,
        }

    def _taught_count(self, plan_id: int) -> int:
        return (
            self.db.query(TeachingLog)
            .filter(TeachingLog.plan_id == plan_id, TeachingLog.status == "taught")
            .count()
        )

    def _first_block_ended(self, plan_id: int, today: date) -> bool:
        segment = (
            self.db.query(SyllabusPlanSegment)
            .filter(SyllabusPlanSegment.plan_id == plan_id)
            .order_by(SyllabusPlanSegment.segment_seq)
            .first()
        )
        if segment is None:
            return False
        block = self.db.get(CalendarBlock, segment.block_id)
        return bool(block and block.end_date < today)
