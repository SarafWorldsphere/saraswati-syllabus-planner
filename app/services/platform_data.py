"""Create and read boards, calendars, topics, and assessments.

A calendar is stored with no board_id. Recommending it to a board is a
separate link, so two boards can share one set of dates.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.assessment_block import AssessmentBlock
from app.models.assessment_template import AssessmentTemplate
from app.models.board import Board
from app.models.board_calendar import BoardCalendar
from app.models.board_grade import BoardGrade
from app.models.board_subject import BoardSubject
from app.models.calendar import Calendar
from app.models.calendar_block import CalendarBlock
from app.models.syllabus_item import SyllabusItem
from app.models.syllabus_item_block import SyllabusItemBlock
from app.schemas.platform import (
    AssessmentBlockCreate,
    AssessmentCreate,
    BlockCreate,
    BoardCalendarLink,
    BoardCreate,
    CalendarCreate,
    GradeCreate,
    SpanCreate,
    SubjectCreate,
    SyllabusItemCreate,
)
from app.utils.spans import split_topic


class PlatformData:
    def __init__(self, db: Session):
        self.db = db

    def create_board(self, body: BoardCreate) -> Board:
        self._unique_board_code(body.board_code)
        row = Board(
            board_code=body.board_code,
            board_name=body.board_name,
            description=body.description,
            region=body.region,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_boards(self) -> list[Board]:
        return self.db.query(Board).order_by(Board.board_name).all()

    def get_board(self, board_id: int) -> Board:
        row = self.db.get(Board, board_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
        return row

    def create_grade(self, board_id: int, body: GradeCreate) -> BoardGrade:
        self.get_board(board_id)
        row = BoardGrade(board_id=board_id, **body.model_dump())
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_grades(self, board_id: int) -> list[BoardGrade]:
        self.get_board(board_id)
        return (
            self.db.query(BoardGrade)
            .filter(BoardGrade.board_id == board_id)
            .order_by(BoardGrade.sort_order)
            .all()
        )

    def create_subject(self, board_id: int, body: SubjectCreate) -> BoardSubject:
        self.get_board(board_id)
        grade = self.db.get(BoardGrade, body.board_grade_id)
        if grade is None or grade.board_id != board_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grade not found on this board")
        row = BoardSubject(board_id=board_id, **body.model_dump())
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_subjects(self, board_id: int) -> list[BoardSubject]:
        self.get_board(board_id)
        return (
            self.db.query(BoardSubject)
            .filter(BoardSubject.board_id == board_id)
            .order_by(BoardSubject.sort_order)
            .all()
        )

    def create_calendar(self, body: CalendarCreate) -> Calendar:
        # Deliberately no board_id. The year of dates is not the curriculum.
        existing = self.db.query(Calendar).filter(Calendar.calendar_code == body.calendar_code).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Calendar code already exists")
        row = Calendar(**body.model_dump())
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_calendars(self, academic_year: str | None, region: str | None) -> list[Calendar]:
        query = self.db.query(Calendar)
        if academic_year:
            query = query.filter(Calendar.academic_year == academic_year)
        if region:
            query = query.filter(Calendar.region == region)
        return query.order_by(Calendar.academic_year, Calendar.calendar_name).all()

    def link_board_calendar(self, board_id: int, body: BoardCalendarLink) -> BoardCalendar:
        self.get_board(board_id)
        calendar = self._calendar(body.calendar_id)
        existing = (
            self.db.query(BoardCalendar)
            .filter(BoardCalendar.board_id == board_id, BoardCalendar.calendar_id == calendar.calendar_id)
            .first()
        )
        if existing:
            existing.is_default = body.is_default
            self.db.commit()
            self.db.refresh(existing)
            return existing
        row = BoardCalendar(board_id=board_id, calendar_id=body.calendar_id, is_default=body.is_default)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def calendars_for_board(self, board_id: int, academic_year: str | None) -> list[Calendar]:
        self.get_board(board_id)
        query = (
            self.db.query(Calendar)
            .join(BoardCalendar, BoardCalendar.calendar_id == Calendar.calendar_id)
            .filter(BoardCalendar.board_id == board_id)
        )
        if academic_year:
            query = query.filter(Calendar.academic_year == academic_year)
        return query.order_by(Calendar.calendar_name).all()

    def create_block(self, calendar_id: int, body: BlockCreate) -> CalendarBlock:
        calendar = self._calendar(calendar_id)
        row = CalendarBlock(calendar_id=calendar_id, academic_year=calendar.academic_year, **body.model_dump())
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_blocks(self, calendar_id: int) -> list[CalendarBlock]:
        self._calendar(calendar_id)
        return (
            self.db.query(CalendarBlock)
            .filter(CalendarBlock.calendar_id == calendar_id)
            .order_by(CalendarBlock.block_seq)
            .all()
        )

    def create_item(self, body: SyllabusItemCreate) -> SyllabusItem:
        subject = self.db.get(BoardSubject, body.board_subject_id)
        if subject is None or subject.board_id != body.board_id or subject.board_grade_id != body.board_grade_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject does not belong to this board and grade")
        spans = body.spans
        row = SyllabusItem(**body.model_dump(exclude={"spans"}))
        self.db.add(row)
        self.db.flush()
        self._write_spans(row, subject, spans)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_items(self, board_id: int | None, academic_year: str | None) -> list[SyllabusItem]:
        query = self.db.query(SyllabusItem)
        if board_id:
            query = query.filter(SyllabusItem.board_id == board_id)
        if academic_year:
            query = query.filter(SyllabusItem.academic_year == academic_year)
        return query.order_by(SyllabusItem.topic_seq).all()

    def list_item_spans(self, item_id: int) -> list[SyllabusItemBlock]:
        self._item(item_id)
        return (
            self.db.query(SyllabusItemBlock)
            .filter(SyllabusItemBlock.item_id == item_id)
            .order_by(SyllabusItemBlock.segment_seq)
            .all()
        )

    def add_span(self, item_id: int, body: SpanCreate) -> SyllabusItemBlock:
        self._item(item_id)
        if self.db.get(CalendarBlock, body.block_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar block not found")
        row = SyllabusItemBlock(item_id=item_id, **body.model_dump())
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def create_assessment(self, body: AssessmentCreate) -> AssessmentTemplate:
        self.get_board(body.board_id)
        row = AssessmentTemplate(**body.model_dump())
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_assessments(self, board_id: int | None, academic_year: str | None) -> list[AssessmentTemplate]:
        query = self.db.query(AssessmentTemplate)
        if board_id:
            query = query.filter(AssessmentTemplate.board_id == board_id)
        if academic_year:
            query = query.filter(AssessmentTemplate.academic_year == academic_year)
        return query.order_by(AssessmentTemplate.assessment_seq).all()

    def add_assessment_block(self, template_id: int, body: AssessmentBlockCreate) -> AssessmentBlock:
        if self.db.get(AssessmentTemplate, template_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
        block = self.db.get(CalendarBlock, body.block_id)
        if block is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar block not found")
        row = AssessmentBlock(template_id=template_id, block_id=body.block_id)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_assessment_blocks(self, template_id: int) -> list[dict]:
        if self.db.get(AssessmentTemplate, template_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
        rows = (
            self.db.query(AssessmentBlock, CalendarBlock.block_name)
            .join(CalendarBlock, CalendarBlock.block_id == AssessmentBlock.block_id)
            .filter(AssessmentBlock.template_id == template_id)
            .all()
        )
        return [
            {
                "assessment_block_id": link.assessment_block_id,
                "template_id": link.template_id,
                "block_id": link.block_id,
                "block_name": name,
            }
            for link, name in rows
        ]

    def _write_spans(self, item: SyllabusItem, subject: BoardSubject, spans: list[SpanCreate] | None) -> None:
        if spans:
            for span in spans:
                if self.db.get(CalendarBlock, span.block_id) is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar block not found")
                self.db.add(SyllabusItemBlock(item_id=item.item_id, **span.model_dump()))
            return
        # No spans supplied: place the topic on the board's default calendar,
        # continuing into the next block when the estimate exceeds capacity.
        link = (
            self.db.query(BoardCalendar)
            .join(Calendar, Calendar.calendar_id == BoardCalendar.calendar_id)
            .filter(BoardCalendar.board_id == item.board_id, Calendar.academic_year == item.academic_year)
            .order_by(BoardCalendar.is_default.desc())
            .first()
        )
        if link is None:
            return
        blocks = (
            self.db.query(CalendarBlock)
            .filter(CalendarBlock.calendar_id == link.calendar_id)
            .order_by(CalendarBlock.block_seq)
            .all()
        )
        payload = [
            {"block_id": block.block_id, "block_seq": block.block_seq, "working_days": block.working_days}
            for block in blocks
        ]
        for piece in split_topic(item.periods_estimated, payload, subject.periods_per_week):
            self.db.add(SyllabusItemBlock(item_id=item.item_id, **piece))

    def _calendar(self, calendar_id: int) -> Calendar:
        row = self.db.get(Calendar, calendar_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")
        return row

    def _item(self, item_id: int) -> SyllabusItem:
        row = self.db.get(SyllabusItem, item_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Syllabus item not found")
        return row

    def _unique_board_code(self, code: str) -> None:
        if self.db.query(Board).filter(Board.board_code == code).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Board code already exists")
