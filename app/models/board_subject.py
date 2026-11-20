"""A subject for one grade on one board. Class 8 Maths is not Class 10 Maths."""

from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String

from app.db.session import Base


class BoardSubject(Base):
    __tablename__ = "board_subject"
    __table_args__ = {"schema": "platform"}

    board_subject_id = Column(BigInteger, primary_key=True, autoincrement=True)
    board_id = Column(BigInteger, ForeignKey("platform.board.board_id"), nullable=False)
    board_grade_id = Column(BigInteger, ForeignKey("platform.board_grade.board_grade_id"), nullable=False)
    subject_name = Column(String(150), nullable=False)
    # From the board weightage table. Null when the board does not say.
    periods_per_week = Column(Integer, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
