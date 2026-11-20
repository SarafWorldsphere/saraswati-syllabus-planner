"""The year this school is teaching: which board, and which calendar dates."""

from sqlalchemy import BigInteger, Boolean, Column, Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


class SchoolYear(Base):
    __tablename__ = "school_year"

    school_year_id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=False), nullable=False, index=True)
    board_id = Column(BigInteger, ForeignKey("platform.board.board_id"), nullable=False)
    calendar_id = Column(BigInteger, ForeignKey("platform.calendar.calendar_id"), nullable=False)
    academic_year = Column(String(9), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    # One active year at a time. Enforced in the service, not by a partial index,
    # so a school can keep last year's row for the audit.
    is_active = Column(Boolean, nullable=False, default=True)
