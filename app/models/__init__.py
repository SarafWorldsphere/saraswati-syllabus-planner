"""Import every model so create_all and Alembic see the full schema."""

from app.models.assessment_block import AssessmentBlock
from app.models.assessment_template import AssessmentTemplate
from app.models.board import Board
from app.models.board_calendar import BoardCalendar
from app.models.board_grade import BoardGrade
from app.models.board_subject import BoardSubject
from app.models.calendar import Calendar
from app.models.calendar_block import CalendarBlock
from app.models.marking_review import MarkingReview
from app.models.school_holiday import SchoolHoliday
from app.models.school_year import SchoolYear
from app.models.syllabus_item import SyllabusItem
from app.models.syllabus_item_block import SyllabusItemBlock
from app.models.syllabus_plan import SyllabusPlan
from app.models.syllabus_plan_audit import SyllabusPlanAudit
from app.models.syllabus_plan_segment import SyllabusPlanSegment
from app.models.teaching_log import TeachingLog

__all__ = [
    "AssessmentBlock",
    "AssessmentTemplate",
    "Board",
    "BoardCalendar",
    "BoardGrade",
    "BoardSubject",
    "Calendar",
    "CalendarBlock",
    "MarkingReview",
    "SchoolHoliday",
    "SchoolYear",
    "SyllabusItem",
    "SyllabusItemBlock",
    "SyllabusPlan",
    "SyllabusPlanAudit",
    "SyllabusPlanSegment",
    "TeachingLog",
]
