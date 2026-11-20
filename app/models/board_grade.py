"""A grade label as that board prints it. Class 8 on AP is not the same row as Grade 8 on CBSE."""

from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String, UniqueConstraint

from app.db.session import Base


class BoardGrade(Base):
    __tablename__ = "board_grade"
    __table_args__ = (
        UniqueConstraint("board_id", "grade_code", name="uq_board_grade_code"),
        {"schema": "platform"},
    )

    board_grade_id = Column(BigInteger, primary_key=True, autoincrement=True)
    board_id = Column(BigInteger, ForeignKey("platform.board.board_id"), nullable=False)
    grade_code = Column(String(10), nullable=False)
    grade_label = Column(String(50), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
