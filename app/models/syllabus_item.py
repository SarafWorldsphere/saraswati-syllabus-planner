"""A board topic for one grade and subject. It is not locked to one calendar block.

Where the topic sits in the year is syllabus_item_block. One topic can start
in July and continue in August.
"""

from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String

from app.db.session import Base


class SyllabusItem(Base):
    __tablename__ = "syllabus_item"
    __table_args__ = {"schema": "platform"}

    item_id = Column(BigInteger, primary_key=True, autoincrement=True)
    board_id = Column(BigInteger, ForeignKey("platform.board.board_id"), nullable=False)
    academic_year = Column(String(9), nullable=False)
    board_grade_id = Column(BigInteger, ForeignKey("platform.board_grade.board_grade_id"), nullable=False)
    board_subject_id = Column(BigInteger, ForeignKey("platform.board_subject.board_subject_id"), nullable=False)
    topic_name = Column(String(300), nullable=False)
    # Order through the year, not inside one month.
    topic_seq = Column(Integer, nullable=False)
    periods_estimated = Column(Integer, nullable=True)
