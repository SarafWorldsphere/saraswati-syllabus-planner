"""Which calendars a board recommends. The calendar row itself stays unowned."""

from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, UniqueConstraint

from app.db.session import Base


class BoardCalendar(Base):
    __tablename__ = "board_calendar"
    __table_args__ = (
        UniqueConstraint("board_id", "calendar_id", name="uq_board_calendar"),
        {"schema": "platform"},
    )

    board_calendar_id = Column(BigInteger, primary_key=True, autoincrement=True)
    board_id = Column(BigInteger, ForeignKey("platform.board.board_id"), nullable=False)
    calendar_id = Column(BigInteger, ForeignKey("platform.calendar.calendar_id"), nullable=False)
    is_default = Column(Boolean, nullable=False, default=False)
