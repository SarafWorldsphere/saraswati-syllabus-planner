"""One planning window inside a calendar: a month for AP, a term for CBSE.

The block belongs to the calendar, not to a board. A lesson is not stored
here. A topic that runs past the window is a later syllabus_item_block row.
"""

from sqlalchemy import BigInteger, Column, Date, ForeignKey, Integer, String, UniqueConstraint

from app.db.session import Base


class CalendarBlock(Base):
    __tablename__ = "calendar_block"
    __table_args__ = (
        UniqueConstraint("calendar_id", "block_seq", name="uq_calendar_block_seq"),
        {"schema": "platform"},
    )

    block_id = Column(BigInteger, primary_key=True, autoincrement=True)
    calendar_id = Column(BigInteger, ForeignKey("platform.calendar.calendar_id"), nullable=False)
    academic_year = Column(String(9), nullable=False)
    block_name = Column(String(50), nullable=False)
    block_seq = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    # Taken from the published calendar. Not derived from the date span.
    working_days = Column(Integer, nullable=False)
