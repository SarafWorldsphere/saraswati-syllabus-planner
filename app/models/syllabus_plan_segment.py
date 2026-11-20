"""The periods of one plan row that fall in one calendar block.

Copied from the board span, then editable when the school is behind.
placement "continues" means this block holds the part that did not fit earlier.
"""

from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


class SyllabusPlanSegment(Base):
    __tablename__ = "syllabus_plan_segment"
    __table_args__ = (UniqueConstraint("plan_id", "block_id", name="uq_plan_block"),)

    segment_id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=False), nullable=False, index=True)
    plan_id = Column(BigInteger, ForeignKey("syllabus_plan.plan_id"), nullable=False)
    block_id = Column(BigInteger, ForeignKey("platform.calendar_block.block_id"), nullable=False)
    planned_periods = Column(Integer, nullable=True)
    segment_seq = Column(Integer, nullable=False)
    period_capacity = Column(Integer, nullable=True)
    placement = Column(String(20), nullable=False, default="planned")
