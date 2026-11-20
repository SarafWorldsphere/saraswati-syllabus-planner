"""What was actually taught.

The unique key is tenant, class, date, and period. Posting the same day
again updates the row, so a correction in the evening does not create a second log.
not_taken is an honest mark. It is not a missed day.
"""

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import Caller
from app.models.school_holiday import SchoolHoliday
from app.models.syllabus_plan import SyllabusPlan
from app.models.teaching_log import TeachingLog
from app.schemas.school import TeachingDay, TeachingEntry
from app.services.school_year_service import SchoolYearService
from app.services.syllabus_plan_service import SyllabusPlanService

ALLOWED_STATUS = {"taught", "partly", "not_taken"}


class TeachingLogService:
    def __init__(self, db: Session, caller: Caller):
        self.db = db
        self.caller = caller
        self.years = SchoolYearService(db, caller)
        self.plans = SyllabusPlanService(db, caller)

    def today(self, log_date: date) -> dict:
        year = self.years.active()
        holiday = (
            self.db.query(SchoolHoliday)
            .filter(
                SchoolHoliday.school_year_id == year.school_year_id,
                SchoolHoliday.holiday_date == log_date,
            )
            .first()
        )
        # Monday is 0 in Python. Sunday is closed. Saturday stays open unless the school listed it.
        is_working = log_date.weekday() != 6 and holiday is None
        logs = (
            self.db.query(TeachingLog)
            .filter(
                TeachingLog.tenant_id == self.caller.tenant_id,
                TeachingLog.log_date == log_date,
                TeachingLog.teacher_id == self.caller.user_id,
            )
            .order_by(TeachingLog.period_no)
            .all()
        )
        items = [self._out(row) for row in logs]
        slots = self._timetable_slots(log_date)
        seen = {(item["class_id"], item["period_no"]) for item in items}
        for slot in slots:
            key = (slot["class_id"], slot["period_no"])
            if key not in seen:
                items.append(slot)
        items.sort(key=lambda item: item["period_no"])
        return {"log_date": log_date, "is_working_day": is_working, "items": items, "total": len(items)}

    def save_day(self, body: TeachingDay) -> dict:
        if not body.entries:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="entries is required")
        year = self.years.active()
        for entry in body.entries:
            self._upsert(year.school_year_id, body.log_date, entry)
        self.db.commit()
        return self.today(body.log_date)

    def history(self, class_id: int | None, start: date | None, end: date | None) -> list[dict]:
        query = self.db.query(TeachingLog).filter(TeachingLog.tenant_id == self.caller.tenant_id)
        if class_id:
            query = query.filter(TeachingLog.class_id == class_id)
        if start:
            query = query.filter(TeachingLog.log_date >= start)
        if end:
            query = query.filter(TeachingLog.log_date <= end)
        return [self._out(row) for row in query.order_by(TeachingLog.log_date, TeachingLog.period_no).all()]

    def _upsert(self, school_year_id: int, log_date: date, entry: TeachingEntry) -> None:
        if entry.status not in ALLOWED_STATUS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="status must be taught, partly, or not_taken",
            )
        if entry.plan_id:
            plan = self.db.get(SyllabusPlan, entry.plan_id)
            if plan is None or plan.tenant_id != self.caller.tenant_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found for this period")
        existing = (
            self.db.query(TeachingLog)
            .filter(
                TeachingLog.tenant_id == self.caller.tenant_id,
                TeachingLog.class_id == entry.class_id,
                TeachingLog.log_date == log_date,
                TeachingLog.period_no == entry.period_no,
            )
            .first()
        )
        if existing:
            existing.subject_id = entry.subject_id
            existing.plan_id = entry.plan_id
            existing.status = entry.status
            existing.remarks = entry.remarks
            existing.teacher_id = self.caller.user_id
            existing.school_year_id = school_year_id
            return
        self.db.add(
            TeachingLog(
                tenant_id=self.caller.tenant_id,
                school_year_id=school_year_id,
                plan_id=entry.plan_id,
                class_id=entry.class_id,
                subject_id=entry.subject_id,
                teacher_id=self.caller.user_id,
                log_date=log_date,
                period_no=entry.period_no,
                status=entry.status,
                remarks=entry.remarks,
            )
        )

    def _out(self, row: TeachingLog) -> dict:
        topic = None
        if row.plan_id:
            plan = self.db.get(SyllabusPlan, row.plan_id)
            topic = plan.topic_name if plan else None
        return {
            "log_id": row.log_id,
            "log_date": row.log_date,
            "period_no": row.period_no,
            "class_id": row.class_id,
            "subject_id": row.subject_id,
            "plan_id": row.plan_id,
            "topic_name": topic,
            "status": row.status,
            "remarks": row.remarks,
            "teacher_id": row.teacher_id,
        }

    def _timetable_slots(self, log_date: date) -> list[dict]:
        # Timetable is the school's existing table. A fresh syllabus database does not have it.
        if not self.plans._has_table("timetable"):
            return []
        # date.weekday() is Monday=0. The timetable stores Monday=1 through Saturday=6.
        day = log_date.weekday() + 1
        if day > 6:
            return []
        from sqlalchemy import text

        rows = self.db.execute(
            text(
                "SELECT class_id, period_no, subject_name FROM timetable "
                "WHERE day_of_week = :day AND teacher_id = :teacher AND class_id IS NOT NULL"
            ),
            {"day": day, "teacher": self.caller.user_id},
        ).fetchall()
        slots = []
        for class_id, period_no, subject_name in rows:
            slots.append(
                {
                    "log_id": None,
                    "log_date": log_date,
                    "period_no": period_no,
                    "class_id": class_id,
                    "subject_id": self._subject_id(class_id, subject_name),
                    "plan_id": None,
                    "topic_name": None,
                    "status": None,
                    "remarks": None,
                    "teacher_id": self.caller.user_id,
                }
            )
        return slots

    def _subject_id(self, class_id: int, subject_name: str | None) -> int:
        if not subject_name or not self.plans._has_table("subject_master"):
            return 0
        from sqlalchemy import text

        row = self.db.execute(
            text(
                "SELECT subject_id FROM subject_master "
                "WHERE class_id = :class_id AND LOWER(subject_name) = LOWER(:name) LIMIT 1"
            ),
            {"class_id": class_id, "name": subject_name},
        ).first()
        return row[0] if row else 0
