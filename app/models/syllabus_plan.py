"""One board topic matched to one class and subject in this school.

Headmaster and Admin write these rows. Other roles only read them.
version_no starts at 1 and rises on every write. A write that quotes an
older version is rejected, so two editors cannot overwrite each other.
chapter_id points at the school's chapter master and is null until someone matches it.
"""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


class SyllabusPlan(Base):
    __tablename__ = "syllabus_plan"

    plan_id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=False), nullable=False, index=True)
    school_year_id = Column(BigInteger, ForeignKey("school_year.school_year_id"), nullable=False)
    class_id = Column(BigInteger, nullable=False)
    subject_id = Column(BigInteger, nullable=False)
    # Null when an admin added a topic the board never listed.
    syllabus_item_id = Column(BigInteger, ForeignKey("platform.syllabus_item.item_id"), nullable=True)
    chapter_id = Column(BigInteger, nullable=True)
    planned_periods = Column(Integer, nullable=True)
    plan_seq = Column(Integer, nullable=False)
    # Switching a chapter off. There is no delete: a missing row would look like it was never planned.
    is_active = Column(Boolean, nullable=False, default=True)
    # "board" or "admin" — who put the row here.
    source = Column(String(10), nullable=False)
    topic_name = Column(String(300), nullable=False)
    version_no = Column(Integer, nullable=False, default=1)
    created_by = Column(String(50), nullable=False)
    updated_by = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
