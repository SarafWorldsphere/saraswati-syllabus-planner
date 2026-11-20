"""A dated year, shared by any board that follows those dates.

No board_id. A CBSE school in Andhra can use the state dates with the CBSE
syllabus. The link from a board to a calendar it recommends is board_calendar.
"""

from sqlalchemy import BigInteger, Column, String, Text

from app.db.session import Base


class Calendar(Base):
    __tablename__ = "calendar"
    __table_args__ = {"schema": "platform"}

    calendar_id = Column(BigInteger, primary_key=True, autoincrement=True)
    calendar_code = Column(String(40), nullable=False, unique=True)
    # What the dropdown shows. school_year stores calendar_id, not this text.
    calendar_name = Column(String(150), nullable=False)
    # Longer note: the span of the year, and that any board may share these dates.
    description = Column(Text, nullable=True)
    academic_year = Column(String(9), nullable=False)
    region = Column(String(100), nullable=True)
