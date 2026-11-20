"""A day this school is closed that the board calendar did not already list."""

from sqlalchemy import BigInteger, Column, Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


class SchoolHoliday(Base):
    __tablename__ = "school_holiday"

    holiday_id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=False), nullable=False, index=True)
    school_year_id = Column(BigInteger, ForeignKey("school_year.school_year_id"), nullable=False)
    holiday_date = Column(Date, nullable=False)
    reason = Column(String(150), nullable=False)
