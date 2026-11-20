"""The year a school is in: one board (what is taught) and one calendar (when)."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import Caller
from app.models.board import Board
from app.models.calendar import Calendar
from app.models.school_holiday import SchoolHoliday
from app.models.school_year import SchoolYear
from app.schemas.school import HolidayCreate, SchoolYearCreate


class SchoolYearService:
    def __init__(self, db: Session, caller: Caller):
        self.db = db
        self.caller = caller

    def active(self) -> SchoolYear:
        row = (
            self.db.query(SchoolYear)
            .filter(SchoolYear.tenant_id == self.caller.tenant_id, SchoolYear.is_active.is_(True))
            .first()
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year has not been set up")
        return row

    def read(self) -> dict:
        year = self.active()
        return self._out(year)

    def open_year(self, body: SchoolYearCreate) -> dict:
        if self.db.get(Board, body.board_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
        if self.db.get(Calendar, body.calendar_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")
        (
            self.db.query(SchoolYear)
            .filter(SchoolYear.tenant_id == self.caller.tenant_id, SchoolYear.is_active.is_(True))
            .update({SchoolYear.is_active: False})
        )
        row = SchoolYear(tenant_id=self.caller.tenant_id, is_active=True, **body.model_dump())
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._out(row)

    def list_holidays(self) -> list[SchoolHoliday]:
        year = self.active()
        return (
            self.db.query(SchoolHoliday)
            .filter(SchoolHoliday.school_year_id == year.school_year_id)
            .order_by(SchoolHoliday.holiday_date)
            .all()
        )

    def add_holiday(self, body: HolidayCreate) -> SchoolHoliday:
        year = self.active()
        row = SchoolHoliday(
            tenant_id=self.caller.tenant_id,
            school_year_id=year.school_year_id,
            holiday_date=body.holiday_date,
            reason=body.reason,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_holiday(self, holiday_id: int) -> None:
        row = self.db.get(SchoolHoliday, holiday_id)
        if row is None or row.tenant_id != self.caller.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holiday not found")
        self.db.delete(row)
        self.db.commit()

    def _out(self, year: SchoolYear) -> dict:
        board = self.db.get(Board, year.board_id)
        calendar = self.db.get(Calendar, year.calendar_id)
        return {
            "school_year_id": year.school_year_id,
            "board_id": year.board_id,
            "calendar_id": year.calendar_id,
            "academic_year": year.academic_year,
            "start_date": year.start_date,
            "end_date": year.end_date,
            "is_active": year.is_active,
            "board_name": board.board_name if board else None,
            "calendar_name": calendar.calendar_name if calendar else None,
        }
