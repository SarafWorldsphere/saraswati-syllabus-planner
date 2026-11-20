"""School year, the syllabus plan, the teaching log, and coverage."""

from datetime import date, datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import ApiModel


class SchoolYearCreate(ApiModel):
    board_id: int
    calendar_id: int
    academic_year: str = Field(max_length=9)
    start_date: date
    end_date: date


class SchoolYearOut(SchoolYearCreate):
    school_year_id: int
    board_name: Optional[str] = None
    calendar_name: Optional[str] = None
    is_active: bool


class HolidayCreate(ApiModel):
    holiday_date: date
    reason: str = Field(max_length=150)


class HolidayOut(HolidayCreate):
    holiday_id: int


class PlanGenerate(ApiModel):
    class_id: Optional[int] = None
    subject_id: Optional[int] = None


class PlanGenerateResult(ApiModel):
    created: int
    skipped: int


class PlanCreate(ApiModel):
    class_id: int
    subject_id: int
    block_id: int
    topic_name: str = Field(max_length=300)
    chapter_id: Optional[int] = None
    planned_periods: Optional[int] = None
    plan_seq: int


class PlanPatch(ApiModel):
    # Required so a stale editor cannot overwrite a newer version.
    version_no: int
    chapter_id: Optional[int] = None
    planned_periods: Optional[int] = None
    plan_seq: Optional[int] = None
    is_active: Optional[bool] = None


class PlanOut(ApiModel):
    plan_id: int
    class_id: int
    subject_id: int
    syllabus_item_id: Optional[int]
    chapter_id: Optional[int]
    topic_name: str
    planned_periods: Optional[int]
    plan_seq: int
    is_active: bool
    source: str
    version_no: int
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
    block_name: Optional[str] = None
    suggested_chapter_id: Optional[int] = None
    suggested_chapter_name: Optional[str] = None


class AuditOut(ApiModel):
    audit_id: int
    plan_id: int
    version_no: int
    action: str
    changed_by: str
    changed_at: datetime
    changes: str


class TeachingEntry(ApiModel):
    period_no: int
    class_id: int
    subject_id: int
    plan_id: Optional[int] = None
    status: str
    remarks: Optional[str] = None


class TeachingDay(ApiModel):
    log_date: date
    entries: list[TeachingEntry]


class TeachingLogOut(ApiModel):
    log_id: Optional[int]
    log_date: date
    period_no: int
    class_id: int
    subject_id: int
    plan_id: Optional[int]
    topic_name: Optional[str]
    status: Optional[str]
    remarks: Optional[str] = None
    teacher_id: Optional[str] = None


class TodayOut(ApiModel):
    log_date: date
    is_working_day: bool
    items: list[TeachingLogOut]
    total: int


class CoverageRow(ApiModel):
    class_id: int
    subject_id: int
    planned_topics: int
    covered_topics: int
    percent: int
    status: str
    against_board: int
    admin_approved: int
    block_id: Optional[int] = None
    block_name: Optional[str] = None


class CoverageTopic(ApiModel):
    plan_id: int
    topic_name: str
    planned_periods: Optional[int]
    periods_used: int
    status: str
    last_taught_on: Optional[date]


class CoverageDetail(CoverageRow):
    topics: list[CoverageTopic]


class CoveredTopic(ApiModel):
    plan_id: int
    topic_name: str
    chapter_id: Optional[int]
    covered_on: Optional[date]


class AlertOut(ApiModel):
    alert_id: int
    teacher_id: str
    alert_type: str = "not_marking"
    first_missed_date: date
    missed_days: int
    status: str
    raised_at: datetime


class AlertPatch(ApiModel):
    status: str
    closed_reason: Optional[str] = None


class CurrentLessonRequest(ApiModel):
    class_id: int
    subject_id: int


class CurrentLessonOut(ApiModel):
    plan_id: int
    topic_name: str
    planned_periods: Optional[int]
    version_no: int
    plan: dict
