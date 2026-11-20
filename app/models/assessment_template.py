"""An assessment window published by a board: FA I, Term 1, and so on."""

from sqlalchemy import BigInteger, Column, Date, ForeignKey, Integer, String

from app.db.session import Base


class AssessmentTemplate(Base):
    __tablename__ = "assessment_template"
    __table_args__ = {"schema": "platform"}

    template_id = Column(BigInteger, primary_key=True, autoincrement=True)
    board_id = Column(BigInteger, ForeignKey("platform.board.board_id"), nullable=False)
    academic_year = Column(String(9), nullable=False)
    assessment_name = Column(String(100), nullable=False)
    assessment_seq = Column(Integer, nullable=False, default=1)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    max_marks = Column(Integer, nullable=True)
