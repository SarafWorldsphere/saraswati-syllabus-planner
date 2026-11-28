"""A teacher alert is derived. Only the headmaster's decision is stored.

A miss is a working day on which the timetable gave the teacher a period
and the teaching log has nothing for that day. not_taken is a real mark, so
it ends the run. Consecutive misses are one streak. missed_days is the
length of that run, counted at read time. The stored row is created the
first time the run reaches three days, and it is not rewritten every night.
"""

from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import Caller
from app.models.marking_review import MarkingReview
from app.models.school_holiday import SchoolHoliday
from app.models.teaching_log import TeachingLog
from app.services.school_year_service import SchoolYearService
from app.services.syllabus_plan_service import SyllabusPlanService

STREAK_LIMIT = 3


class AlertService:
    def __init__(self, db: Session, caller: Caller):
        self.db = db
        self.caller = caller
        self.years = SchoolYearService(db, caller)
        self.plans = SyllabusPlanService(db, caller)

    def list_open(self) -> list[dict]:
        year = self.years.active()
        holidays = {
            row.holiday_date
            for row in self.db.query(SchoolHoliday).filter(SchoolHoliday.school_year_id == year.school_year_id).all()
        }
        if not self.plans._has_table("timetable"):
            # Without a timetable we cannot tell a free day from a missed day.
            # Returning nothing is safer than flagging every teacher.
            return self._existing(include_closed=False)
        teachers = self.db.execute(text("SELECT DISTINCT teacher_id FROM timetable WHERE teacher_id IS NOT NULL")).fetchall()
        today = date.today()
        for (teacher_id,) in teachers:
            streak_start, missed = self._streak(teacher_id, today, holidays, year.start_date)
            if missed < STREAK_LIMIT or streak_start is None:
                continue
            existing = (
                self.db.query(MarkingReview)
                .filter(
                    MarkingReview.tenant_id == self.caller.tenant_id,
                    MarkingReview.teacher_id == teacher_id,
                    MarkingReview.streak_started_on == streak_start,
                )
                .first()
            )
            if existing is None:
                self.db.add(
                    MarkingReview(
                        tenant_id=self.caller.tenant_id,
                        teacher_id=str(teacher_id),
                        streak_started_on=streak_start,
                        status="open",
                    )
                )
        self.db.commit()
        return self._existing(include_closed=False)

    def mine(self) -> list[dict]:
        """
        This teacher's own open marking alerts.

        list_open() sweeps every teacher and is for the headmaster; a teacher
        may only see their own, so this computes the streak for the caller
        alone. Same rule, same holiday handling — the only difference is who
        it looks at.

        It raises the alert as well as reading it, for the same reason
        list_open does: nothing runs this on a schedule, so the streak is
        worked out when someone asks. A teacher opening their dashboard is
        therefore the first thing that can tell them they have fallen behind.
        """
        teacher_id = self.caller.user_id
        if not teacher_id:
            return []

        year = self.years.active()
        holidays = {
            row.holiday_date
            for row in self.db.query(SchoolHoliday)
            .filter(SchoolHoliday.school_year_id == year.school_year_id)
            .all()
        }

        # Without a timetable there is no way to tell a free day from a
        # missed one, so say nothing rather than accuse everybody.
        if self.plans._has_table("timetable"):
            streak_start, missed = self._streak(teacher_id, date.today(), holidays, year.start_date)
            if missed >= STREAK_LIMIT and streak_start is not None:
                existing = (
                    self.db.query(MarkingReview)
                    .filter(
                        MarkingReview.tenant_id == self.caller.tenant_id,
                        MarkingReview.teacher_id == str(teacher_id),
                        MarkingReview.streak_started_on == streak_start,
                    )
                    .first()
                )
                if existing is None:
                    self.db.add(
                        MarkingReview(
                            tenant_id=self.caller.tenant_id,
                            teacher_id=str(teacher_id),
                            streak_started_on=streak_start,
                            status="open",
                        )
                    )
                    self.db.commit()

        rows = (
            self.db.query(MarkingReview)
            .filter(
                MarkingReview.tenant_id == self.caller.tenant_id,
                MarkingReview.teacher_id == str(teacher_id),
                MarkingReview.status != "closed",
            )
            .order_by(MarkingReview.raised_at.desc())
            .all()
        )
        return [self._out(row, self._missed_now(row)) for row in rows]

    def update(self, alert_id: int, new_status: str, reason: str | None) -> dict:
        if new_status not in {"open", "acknowledged", "closed"}:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="status must be open, acknowledged, or closed")
        row = self.db.get(MarkingReview, alert_id)
        if row is None or row.tenant_id != self.caller.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        row.status = new_status
        if new_status == "acknowledged":
            row.acknowledged_at = datetime.now(timezone.utc)
        if new_status == "closed":
            row.closed_at = datetime.now(timezone.utc)
            row.closed_by = self.caller.user_id
            row.closed_reason = reason
        self.db.commit()
        self.db.refresh(row)
        missed = self._missed_now(row)
        return self._out(row, missed)

    def _existing(self, include_closed: bool) -> list[dict]:
        query = self.db.query(MarkingReview).filter(MarkingReview.tenant_id == self.caller.tenant_id)
        if not include_closed:
            query = query.filter(MarkingReview.status != "closed")
        rows = query.order_by(MarkingReview.raised_at.desc()).all()
        return [self._out(row, self._missed_now(row)) for row in rows]

    def _missed_now(self, row: MarkingReview) -> int:
        # Counted here, not stored. A teacher who marked this evening shows 0
        # while the alert stays open for the headmaster to close.
        if not self.plans._has_table("timetable"):
            return 0
        year = self.years.active()
        holidays = {
            holiday.holiday_date
            for holiday in self.db.query(SchoolHoliday).filter(SchoolHoliday.school_year_id == year.school_year_id).all()
        }
        _start, missed = self._streak(row.teacher_id, date.today(), holidays, year.start_date)
        if _start != row.streak_started_on:
            return 0
        return missed

    def _streak(self, teacher_id: str, today: date, holidays: set[date], year_start: date) -> tuple[date | None, int]:
        missed = 0
        start = None
        cursor = today
        while cursor >= year_start and (today - cursor).days < 60:
            if self._is_expected(cursor, teacher_id, holidays) and not self._marked(cursor, teacher_id):
                missed += 1
                start = cursor
            elif self._is_expected(cursor, teacher_id, holidays):
                break
            cursor -= timedelta(days=1)
        return start, missed

    def _is_expected(self, day: date, teacher_id: str, holidays: set[date]) -> bool:
        if day.weekday() == 6 or day in holidays:
            return False
        timetable_day = day.weekday() + 1
        if timetable_day > 6:
            return False
        row = self.db.execute(
            text(
                "SELECT 1 FROM timetable WHERE teacher_id = :teacher AND day_of_week = :day LIMIT 1"
            ),
            {"teacher": teacher_id, "day": timetable_day},
        ).first()
        return row is not None

    def _marked(self, day: date, teacher_id: str) -> bool:
        return (
            self.db.query(TeachingLog)
            .filter(TeachingLog.teacher_id == teacher_id, TeachingLog.log_date == day)
            .first()
            is not None
        )

    def _out(self, row: MarkingReview, missed_days: int) -> dict:
        return {
            "alert_id": row.review_id,
            "teacher_id": row.teacher_id,
            "alert_type": "not_marking",
            "first_missed_date": row.streak_started_on,
            "missed_days": missed_days,
            "status": row.status,
            "raised_at": row.raised_at,
        }
