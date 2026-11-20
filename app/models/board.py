"""A curriculum authority. AP SCERT and CBSE are rows, not branches in the code."""

from sqlalchemy import BigInteger, Column, DateTime, String, func

from app.db.session import Base


class Board(Base):
    __tablename__ = "board"
    __table_args__ = {"schema": "platform"}

    board_id = Column(BigInteger, primary_key=True, autoincrement=True)
    board_code = Column(String(30), nullable=False, unique=True)
    board_name = Column(String(150), nullable=False)
    # Null for a national board such as CBSE. A state board names its state.
    region = Column(String(100), nullable=True)
    record_status = Column(String(20), nullable=False, default="Active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
