"""One period actually taken. The date does not have to fall inside the suggested block.

A July topic taught on 4 August is slippage, recorded here, not a bad row.
Unique on tenant, class, date, and period so a correction at 6pm updates the
same row instead of inserting a second one.
status is taught, partly, or not_taken. not_taken is coverage, not a missed marking.
"""

from sqlalchemy import BigInteger, Column, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


class TeachingLog(Base):
    __tablename__ = "teaching_log"
    __table_args__ = (
        UniqueConstraint("tenant_id", "class_id", "log_date", "period_no", name="uq_teaching_slot"),
    )

    log_id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=False), nullable=False, index=True)
    school_year_id = Column(BigInteger, ForeignKey("school_year.school_year_id"), nullable=False)
    plan_id = Column(BigInteger, ForeignKey("syllabus_plan.plan_id"), nullable=True)
    class_id = Column(BigInteger, nullable=False)
    subject_id = Column(BigInteger, nullable=False)
    teacher_id = Column(String(50), nullable=False)
    log_date = Column(Date, nullable=False)
    period_no = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)
    remarks = Column(String(300), nullable=True)
