"""Bodies for creating and reading platform reference data."""

from datetime import date
from typing import Optional

from pydantic import Field

from app.schemas.common import ApiModel


class BoardCreate(ApiModel):
    board_code: str = Field(max_length=30)
    board_name: str = Field(max_length=150)
    region: Optional[str] = None


class BoardOut(BoardCreate):
    board_id: int
    record_status: str


class GradeCreate(ApiModel):
    grade_code: str = Field(max_length=10)
    grade_label: str = Field(max_length=50)
    sort_order: int = 0


class GradeOut(GradeCreate):
    board_grade_id: int
    board_id: int


class SubjectCreate(ApiModel):
    board_grade_id: int
    subject_name: str = Field(max_length=150)
    periods_per_week: Optional[int] = None
    sort_order: int = 0


class SubjectOut(SubjectCreate):
    board_subject_id: int
    board_id: int


class CalendarCreate(ApiModel):
    # A calendar is not owned by a board. Link it afterwards.
    calendar_code: str = Field(max_length=40)
    calendar_name: str = Field(max_length=150)
    academic_year: str = Field(max_length=9)
    region: Optional[str] = None


class CalendarOut(CalendarCreate):
    calendar_id: int


class BoardCalendarLink(ApiModel):
    calendar_id: int
    is_default: bool = False


class BoardCalendarOut(BoardCalendarLink):
    board_calendar_id: int
    board_id: int


class BlockCreate(ApiModel):
    block_name: str = Field(max_length=50)
    block_seq: int
    start_date: date
    end_date: date
    working_days: int


class BlockOut(BlockCreate):
    block_id: int
    calendar_id: int
    academic_year: str


class SpanCreate(ApiModel):
    block_id: int
    periods_in_block: Optional[int] = None
    segment_seq: int
    period_capacity: Optional[int] = None
    placement: str = "planned"


class SpanOut(SpanCreate):
    item_block_id: int
    item_id: int


class SyllabusItemCreate(ApiModel):
    board_id: int
    academic_year: str = Field(max_length=9)
    board_grade_id: int
    board_subject_id: int
    topic_name: str = Field(max_length=300)
    topic_seq: int
    periods_estimated: Optional[int] = None
    # Omit to let the server split the topic across the board's default calendar.
    spans: Optional[list[SpanCreate]] = None


class SyllabusItemOut(ApiModel):
    item_id: int
    board_id: int
    academic_year: str
    board_grade_id: int
    board_subject_id: int
    topic_name: str
    topic_seq: int
    periods_estimated: Optional[int]


class AssessmentCreate(ApiModel):
    board_id: int
    academic_year: str = Field(max_length=9)
    assessment_name: str = Field(max_length=100)
    assessment_seq: int = 1
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    max_marks: Optional[int] = None


class AssessmentOut(AssessmentCreate):
    template_id: int


class AssessmentBlockCreate(ApiModel):
    block_id: int


class AssessmentBlockOut(ApiModel):
    assessment_block_id: int
    template_id: int
    block_id: int
    block_name: Optional[str] = None
