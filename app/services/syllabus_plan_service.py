"""The school syllabus plan.

Headmaster and Admin write it. Other roles only read it, enforced on the
routes. Every write stores version_no and a syllabus_plan_audit row.
A topic that already has board spans is copied. Otherwise it is split across
the calendar when the estimate does not fit in one block.
"""

import json
from datetime import datetime, timezone
from difflib import SequenceMatcher

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import Caller
from app.models.calendar_block import CalendarBlock
from app.models.syllabus_item import SyllabusItem
from app.models.syllabus_item_block import SyllabusItemBlock
from app.models.syllabus_plan import SyllabusPlan
from app.models.syllabus_plan_audit import SyllabusPlanAudit
from app.models.syllabus_plan_segment import SyllabusPlanSegment
from app.schemas.school import PlanCreate, PlanPatch
from app.services.school_year_service import SchoolYearService
from app.utils.spans import split_topic


class SyllabusPlanService:
    def __init__(self, db: Session, caller: Caller):
        self.db = db
        self.caller = caller
        self.years = SchoolYearService(db, caller)

    def generate(self, class_id: int | None, subject_id: int | None) -> dict:
        year = self.years.active()
        classes = self._class_ids(class_id)
        subjects = self._subject_ids(subject_id, class_id)
        items = (
            self.db.query(SyllabusItem)
            .filter(SyllabusItem.board_id == year.board_id, SyllabusItem.academic_year == year.academic_year)
            .order_by(SyllabusItem.topic_seq)
            .all()
        )
        created = 0
        skipped = 0
        for one_class in classes:
            for one_subject in subjects:
                chosen = self._items_for_subject(items, one_subject)
                for item in chosen:
                    exists = (
                        self.db.query(SyllabusPlan)
                        .filter(
                            SyllabusPlan.tenant_id == self.caller.tenant_id,
                            SyllabusPlan.school_year_id == year.school_year_id,
                            SyllabusPlan.class_id == one_class,
                            SyllabusPlan.subject_id == one_subject,
                            SyllabusPlan.syllabus_item_id == item.item_id,
                        )
                        .first()
                    )
                    if exists:
                        skipped += 1
                        continue
                    self._create_from_item(year, one_class, one_subject, item)
                    created += 1
        self.db.commit()
        return {"created": created, "skipped": skipped}

    def list_plans(self, class_id: int | None, subject_id: int | None, block_id: int | None) -> list[dict]:
        year = self.years.active()
        query = self.db.query(SyllabusPlan).filter(
            SyllabusPlan.tenant_id == self.caller.tenant_id,
            SyllabusPlan.school_year_id == year.school_year_id,
        )
        if class_id:
            query = query.filter(SyllabusPlan.class_id == class_id)
        if subject_id:
            query = query.filter(SyllabusPlan.subject_id == subject_id)
        rows = query.order_by(SyllabusPlan.plan_seq).all()
        if block_id:
            plan_ids = {
                segment.plan_id
                for segment in self.db.query(SyllabusPlanSegment)
                .filter(SyllabusPlanSegment.block_id == block_id)
                .all()
            }
            rows = [row for row in rows if row.plan_id in plan_ids]
        return [self._out(row) for row in rows]

    def unmatched(self, class_id: int | None, subject_id: int | None) -> list[dict]:
        rows = [
            row
            for row in self.list_plans(class_id, subject_id, None)
            if row["chapter_id"] is None and row["is_active"]
        ]
        for row in rows:
            suggested_id, suggested_name = self._suggest_chapter(row["topic_name"], row["subject_id"])
            row["suggested_chapter_id"] = suggested_id
            row["suggested_chapter_name"] = suggested_name
        return rows

    def add_admin_topic(self, body: PlanCreate) -> dict:
        # A topic the board never listed. source and syllabus_item_id are set here, not by the client.
        year = self.years.active()
        if self.db.get(CalendarBlock, body.block_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar block not found")
        row = SyllabusPlan(
            tenant_id=self.caller.tenant_id,
            school_year_id=year.school_year_id,
            class_id=body.class_id,
            subject_id=body.subject_id,
            syllabus_item_id=None,
            chapter_id=body.chapter_id,
            planned_periods=body.planned_periods,
            plan_seq=body.plan_seq,
            is_active=True,
            source="admin",
            topic_name=body.topic_name,
            version_no=1,
            created_by=self.caller.user_id,
            updated_by=self.caller.user_id,
        )
        self.db.add(row)
        self.db.flush()
        self.db.add(
            SyllabusPlanSegment(
                tenant_id=self.caller.tenant_id,
                plan_id=row.plan_id,
                block_id=body.block_id,
                planned_periods=body.planned_periods,
                segment_seq=1,
                placement="planned",
            )
        )
        self._audit(row, "created", self._snapshot(row))
        self.db.commit()
        self.db.refresh(row)
        return self._out(row)

    def update(self, plan_id: int, body: PlanPatch) -> dict:
        row = self._owned(plan_id)
        if row.version_no != body.version_no:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Plan is at version {row.version_no}. Reload it and send that version.",
            )
        changes = {}
        for field in ("chapter_id", "planned_periods", "plan_seq", "is_active"):
            value = getattr(body, field)
            if value is not None:
                setattr(row, field, value)
                changes[field] = value
        row.version_no += 1
        row.updated_by = self.caller.user_id
        row.updated_at = datetime.now(timezone.utc)
        self._audit(row, "updated", changes or {"note": "version bumped with no field change"})
        self.db.commit()
        self.db.refresh(row)
        return self._out(row)

    def audit(self, plan_id: int) -> list[SyllabusPlanAudit]:
        self._owned(plan_id)
        return (
            self.db.query(SyllabusPlanAudit)
            .filter(SyllabusPlanAudit.plan_id == plan_id)
            .order_by(SyllabusPlanAudit.version_no)
            .all()
        )

    def _create_from_item(self, year, class_id: int, subject_id: int, item: SyllabusItem) -> None:
        spans = (
            self.db.query(SyllabusItemBlock)
            .filter(SyllabusItemBlock.item_id == item.item_id)
            .order_by(SyllabusItemBlock.segment_seq)
            .all()
        )
        planned = item.periods_estimated
        if spans:
            numbers = [span.periods_in_block for span in spans if span.periods_in_block]
            if numbers:
                planned = sum(numbers)
        row = SyllabusPlan(
            tenant_id=self.caller.tenant_id,
            school_year_id=year.school_year_id,
            class_id=class_id,
            subject_id=subject_id,
            syllabus_item_id=item.item_id,
            chapter_id=None,
            planned_periods=planned,
            plan_seq=item.topic_seq,
            is_active=True,
            source="board",
            topic_name=item.topic_name,
            version_no=1,
            created_by=self.caller.user_id,
            updated_by=self.caller.user_id,
        )
        self.db.add(row)
        self.db.flush()
        if not spans:
            spans = self._synthetic_spans(year, item)
        for span in spans:
            self.db.add(
                SyllabusPlanSegment(
                    tenant_id=self.caller.tenant_id,
                    plan_id=row.plan_id,
                    block_id=span["block_id"] if isinstance(span, dict) else span.block_id,
                    planned_periods=span["periods_in_block"] if isinstance(span, dict) else span.periods_in_block,
                    segment_seq=span["segment_seq"] if isinstance(span, dict) else span.segment_seq,
                    period_capacity=span["period_capacity"] if isinstance(span, dict) else span.period_capacity,
                    placement=span["placement"] if isinstance(span, dict) else span.placement,
                )
            )
        self._audit(row, "created", self._snapshot(row))

    def _synthetic_spans(self, year, item: SyllabusItem) -> list[dict]:
        blocks = (
            self.db.query(CalendarBlock)
            .filter(CalendarBlock.calendar_id == year.calendar_id)
            .order_by(CalendarBlock.block_seq)
            .all()
        )
        subject = item.board_subject_id
        from app.models.board_subject import BoardSubject

        board_subject = self.db.get(BoardSubject, subject)
        weekly = board_subject.periods_per_week if board_subject else None
        payload = [
            {"block_id": block.block_id, "block_seq": block.block_seq, "working_days": block.working_days}
            for block in blocks
        ]
        return split_topic(item.periods_estimated, payload, weekly)

    def _items_for_subject(self, items: list[SyllabusItem], subject_id: int) -> list[SyllabusItem]:
        name = self._subject_name(subject_id)
        if not name:
            return items
        from app.models.board_subject import BoardSubject

        matched = []
        for item in items:
            board_subject = self.db.get(BoardSubject, item.board_subject_id)
            if board_subject and board_subject.subject_name.lower() == name.lower():
                matched.append(item)
        # No name match means the school subject is not tied to a board subject yet.
        # Keep every topic rather than generating an empty plan with no explanation.
        return matched or items

    def _class_ids(self, class_id: int | None) -> list[int]:
        if class_id:
            return [class_id]
        found = self._column("class_master", "class_id")
        if not found:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="class_id is required until class_master is available in this database",
            )
        return found

    def _subject_ids(self, subject_id: int | None, class_id: int | None) -> list[int]:
        if subject_id:
            return [subject_id]
        if class_id:
            found = self._column("subject_master", "subject_id", "class_id", class_id)
        else:
            found = self._column("subject_master", "subject_id")
        if not found:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="subject_id is required until subject_master is available in this database",
            )
        return found

    def _has_table(self, table: str) -> bool:
        # Look before querying. A missing master must not abort the transaction
        # that is in the middle of generating plan rows.
        row = self.db.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = :name"
            ),
            {"name": table},
        ).first()
        return row is not None

    def _column(self, table: str, column: str, filter_column: str | None = None, filter_value: int | None = None) -> list[int]:
        # These masters belong to the school and may not exist in a fresh syllabus database.
        if not self._has_table(table):
            return []
        if filter_column:
            rows = self.db.execute(
                text(f"SELECT {column} FROM {table} WHERE {filter_column} = :value"),
                {"value": filter_value},
            ).fetchall()
        else:
            rows = self.db.execute(text(f"SELECT {column} FROM {table}")).fetchall()
        return [row[0] for row in rows if row[0] is not None]

    def _subject_name(self, subject_id: int) -> str | None:
        if not self._has_table("subject_master"):
            return None
        row = self.db.execute(
            text("SELECT subject_name FROM subject_master WHERE subject_id = :id"),
            {"id": subject_id},
        ).first()
        return row[0] if row else None

    def _suggest_chapter(self, topic_name: str, subject_id: int) -> tuple[int | None, str | None]:
        if not self._has_table("chapter_master"):
            return None, None
        rows = self.db.execute(
            text(
                "SELECT chapter_id, chapter_name FROM chapter_master "
                "WHERE subject_id = :subject_id AND chapter_name IS NOT NULL"
            ),
            {"subject_id": subject_id},
        ).fetchall()
        best_id = None
        best_name = None
        best_score = 0.0
        for chapter_id, chapter_name in rows:
            score = SequenceMatcher(None, topic_name.lower(), (chapter_name or "").lower()).ratio()
            if score > best_score:
                best_score = score
                best_id = chapter_id
                best_name = chapter_name
        # A weak guess is worse than no guess: the screen pre-selects this value.
        if best_score < 0.45:
            return None, None
        return best_id, best_name

    def _owned(self, plan_id: int) -> SyllabusPlan:
        row = self.db.get(SyllabusPlan, plan_id)
        if row is None or row.tenant_id != self.caller.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Syllabus plan not found")
        return row

    def _audit(self, row: SyllabusPlan, action: str, changes: dict) -> None:
        self.db.add(
            SyllabusPlanAudit(
                tenant_id=self.caller.tenant_id,
                plan_id=row.plan_id,
                version_no=row.version_no,
                action=action,
                changed_by=self.caller.user_id,
                changes=json.dumps(changes, default=str),
            )
        )

    def _snapshot(self, row: SyllabusPlan) -> dict:
        return {
            "topic_name": row.topic_name,
            "class_id": row.class_id,
            "subject_id": row.subject_id,
            "planned_periods": row.planned_periods,
            "plan_seq": row.plan_seq,
            "source": row.source,
            "chapter_id": row.chapter_id,
        }

    def _out(self, row: SyllabusPlan) -> dict:
        segment = (
            self.db.query(SyllabusPlanSegment)
            .filter(SyllabusPlanSegment.plan_id == row.plan_id)
            .order_by(SyllabusPlanSegment.segment_seq)
            .first()
        )
        block_name = None
        if segment:
            block = self.db.get(CalendarBlock, segment.block_id)
            block_name = block.block_name if block else None
        return {
            "plan_id": row.plan_id,
            "class_id": row.class_id,
            "subject_id": row.subject_id,
            "syllabus_item_id": row.syllabus_item_id,
            "chapter_id": row.chapter_id,
            "topic_name": row.topic_name,
            "planned_periods": row.planned_periods,
            "plan_seq": row.plan_seq,
            "is_active": row.is_active,
            "source": row.source,
            "version_no": row.version_no,
            "created_by": row.created_by,
            "updated_by": row.updated_by,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "block_name": block_name,
            "suggested_chapter_id": None,
            "suggested_chapter_name": None,
        }
