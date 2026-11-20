"""The headmaster's answer to one run of unmarked teaching days.

A streak is consecutive working days on which the timetable gave this
teacher a period and the teaching log has no row for that day. Sunday and
a school holiday are skipped: they do not count, and they do not break the
run. A day she did mark, including not_taken, ends it. streak_started_on is
the first unmarked day of that run, so a later run can raise its own row.

How many days the run has reached is counted when the alert list is read.
That number is not a column. A teacher who marks at 9pm would otherwise
still look absent. This table only keeps the decision: open, acknowledged,
or closed. The row is created the first time the run reaches three days.
"""

from sqlalchemy import BigInteger, Column, Date, DateTime, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


class MarkingReview(Base):
    __tablename__ = "marking_review"
    __table_args__ = (
        UniqueConstraint("tenant_id", "teacher_id", "streak_started_on", name="uq_marking_streak"),
    )

    review_id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=False), nullable=False, index=True)
    teacher_id = Column(String(50), nullable=False)
    # First unmarked working day of this run. Identifies the episode, not its length.
    streak_started_on = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="open")
    closed_reason = Column(String(300), nullable=True)
    closed_by = Column(String(50), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    raised_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
