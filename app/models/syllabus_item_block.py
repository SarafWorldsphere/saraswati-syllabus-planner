"""How many periods of one topic fall in one calendar block.

segment_seq 1 is the start. A later segment is the part that did not fit.
placement is "planned" or "continues".
"""

from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String, UniqueConstraint

from app.db.session import Base


class SyllabusItemBlock(Base):
    __tablename__ = "syllabus_item_block"
    __table_args__ = (
        UniqueConstraint("item_id", "block_id", name="uq_item_block"),
        {"schema": "platform"},
    )

    item_block_id = Column(BigInteger, primary_key=True, autoincrement=True)
    item_id = Column(BigInteger, ForeignKey("platform.syllabus_item.item_id"), nullable=False)
    block_id = Column(BigInteger, ForeignKey("platform.calendar_block.block_id"), nullable=False)
    periods_in_block = Column(Integer, nullable=True)
    segment_seq = Column(Integer, nullable=False)
    # Stored so a later read does not recompute a school week the board never published.
    period_capacity = Column(Integer, nullable=True)
    placement = Column(String(20), nullable=False, default="planned")
