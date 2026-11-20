"""Create the tables and load a small AP-shaped dataset.

Safe to run again. If the AP SCERT board is already there, the sample is
left as it is. The calendar has no board_id. The Maths topic starts in the
first block and continues in the second. The plan row is version 1.
"""

import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from sqlalchemy import text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.rls import ensure_descriptions, ensure_platform, install_rls  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.models.assessment_block import AssessmentBlock  # noqa: E402
from app.models.assessment_template import AssessmentTemplate  # noqa: E402
from app.models.board import Board  # noqa: E402
from app.models.board_calendar import BoardCalendar  # noqa: E402
from app.models.board_grade import BoardGrade  # noqa: E402
from app.models.board_subject import BoardSubject  # noqa: E402
from app.models.calendar import Calendar  # noqa: E402
from app.models.calendar_block import CalendarBlock  # noqa: E402
from app.models.school_year import SchoolYear  # noqa: E402
from app.models.syllabus_item import SyllabusItem  # noqa: E402
from app.models.syllabus_item_block import SyllabusItemBlock  # noqa: E402
from app.models.syllabus_plan import SyllabusPlan  # noqa: E402
from app.models.syllabus_plan_audit import SyllabusPlanAudit  # noqa: E402
from app.models.syllabus_plan_segment import SyllabusPlanSegment  # noqa: E402

import app.models  # noqa: E402, F401

BOARD_CODE = "AP_SCERT"
TENANT = settings.DEV_TENANT_ID
BOARD_DESCRIPTION = (
    "State curriculum published by the Andhra Pradesh SCERT for classes 1 to 10. "
    "A school stores board_id on the year. The screen shows board_name."
)
CALENDAR_DESCRIPTION = (
    "June to April term dates for Andhra Pradesh, 2026-27. Working days sit on each block. "
    "Any board can recommend this calendar. The calendar row has no board_id. "
    "The screen shows calendar_name and stores calendar_id."
)


def create_tables() -> None:
    with engine.begin() as connection:
        ensure_platform(connection)
        Base.metadata.create_all(bind=connection)
        ensure_descriptions(connection)
        install_rls(connection)


def seed() -> None:
    db = SessionLocal()
    try:
        # Session-scoped, so the school id survives the commits below.
        # A superuser bypasses the policy anyway. A restricted role does not.
        db.execute(text("SELECT set_config('app.tenant_id', :tenant_id, false)"), {"tenant_id": TENANT})
        existing = db.query(Board).filter(Board.board_code == BOARD_CODE).first()
        if existing:
            if not existing.description:
                existing.description = BOARD_DESCRIPTION
            calendar = db.query(Calendar).filter(Calendar.calendar_code == "AP_2026_27").first()
            if calendar is not None and not calendar.description:
                calendar.description = CALENDAR_DESCRIPTION
            db.commit()
            print("Sample already loaded. Tables are in place and nothing was duplicated.")
            return

        board = Board(
            board_code=BOARD_CODE,
            board_name="Andhra Pradesh SCERT",
            description=BOARD_DESCRIPTION,
            region="Andhra Pradesh",
        )
        db.add(board)
        db.flush()

        grade = BoardGrade(board_id=board.board_id, grade_code="8", grade_label="Class 8", sort_order=8)
        db.add(grade)
        db.flush()

        subject = BoardSubject(
            board_id=board.board_id,
            board_grade_id=grade.board_grade_id,
            subject_name="Mathematics",
            periods_per_week=8,
            sort_order=1,
        )
        db.add(subject)
        db.flush()

        # No board_id. The board recommends this calendar in the next row.
        calendar = Calendar(
            calendar_code="AP_2026_27",
            calendar_name="Andhra academic calendar 2026-27",
            description=CALENDAR_DESCRIPTION,
            academic_year="2026-27",
            region="Andhra Pradesh",
        )
        db.add(calendar)
        db.flush()

        july = CalendarBlock(
            calendar_id=calendar.calendar_id,
            academic_year="2026-27",
            block_name="July",
            block_seq=1,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            working_days=23,
        )
        august = CalendarBlock(
            calendar_id=calendar.calendar_id,
            academic_year="2026-27",
            block_name="August",
            block_seq=2,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
            working_days=21,
        )
        db.add_all([july, august])
        db.flush()

        db.add(BoardCalendar(board_id=board.board_id, calendar_id=calendar.calendar_id, is_default=True))

        item = SyllabusItem(
            board_id=board.board_id,
            academic_year="2026-27",
            board_grade_id=grade.board_grade_id,
            board_subject_id=subject.board_subject_id,
            topic_name="Real Numbers",
            topic_seq=1,
            periods_estimated=12,
        )
        db.add(item)
        db.flush()

        # Explicit spans. The weekly capacity (23 * 8) would never overflow one
        # topic, so the sample states the continuation instead of hoping the formula does.
        db.add_all(
            [
                SyllabusItemBlock(
                    item_id=item.item_id,
                    block_id=july.block_id,
                    periods_in_block=8,
                    segment_seq=1,
                    period_capacity=23 * 8,
                    placement="planned",
                ),
                SyllabusItemBlock(
                    item_id=item.item_id,
                    block_id=august.block_id,
                    periods_in_block=4,
                    segment_seq=2,
                    period_capacity=21 * 8,
                    placement="continues",
                ),
            ]
        )

        assessment = AssessmentTemplate(
            board_id=board.board_id,
            academic_year="2026-27",
            assessment_name="FA I",
            assessment_seq=1,
            start_date=date(2026, 7, 20),
            end_date=date(2026, 7, 25),
            max_marks=20,
        )
        db.add(assessment)
        db.flush()
        db.add(AssessmentBlock(template_id=assessment.template_id, block_id=july.block_id))

        year = SchoolYear(
            tenant_id=TENANT,
            board_id=board.board_id,
            calendar_id=calendar.calendar_id,
            academic_year="2026-27",
            start_date=date(2026, 6, 15),
            end_date=date(2027, 4, 30),
            is_active=True,
        )
        db.add(year)
        db.flush()

        plan = SyllabusPlan(
            tenant_id=TENANT,
            school_year_id=year.school_year_id,
            class_id=1,
            subject_id=1,
            syllabus_item_id=item.item_id,
            chapter_id=None,
            planned_periods=12,
            plan_seq=1,
            is_active=True,
            source="board",
            topic_name=item.topic_name,
            version_no=1,
            created_by="bootstrap",
            updated_by="bootstrap",
        )
        db.add(plan)
        db.flush()
        db.add_all(
            [
                SyllabusPlanSegment(
                    tenant_id=TENANT,
                    plan_id=plan.plan_id,
                    block_id=july.block_id,
                    planned_periods=8,
                    segment_seq=1,
                    period_capacity=23 * 8,
                    placement="planned",
                ),
                SyllabusPlanSegment(
                    tenant_id=TENANT,
                    plan_id=plan.plan_id,
                    block_id=august.block_id,
                    planned_periods=4,
                    segment_seq=2,
                    period_capacity=21 * 8,
                    placement="continues",
                ),
            ]
        )
        db.add(
            SyllabusPlanAudit(
                tenant_id=TENANT,
                plan_id=plan.plan_id,
                version_no=1,
                action="created",
                changed_by="bootstrap",
                changes='{"topic_name": "Real Numbers", "source": "board", "planned_periods": 12}',
            )
        )
        db.commit()
        print("Loaded AP SCERT, calendar AP_2026_27, Real Numbers across July and August.")
        print(f"plan_id={plan.plan_id} version={plan.version_no} class_id=1 subject_id=1")
        print("Swagger bearer tokens (APP_ENV=development): dev-admin, dev-headmaster, dev-faculty")
    finally:
        db.close()


if __name__ == "__main__":
    create_tables()
    seed()
