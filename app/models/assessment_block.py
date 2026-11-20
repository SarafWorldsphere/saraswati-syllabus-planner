"""Which calendar blocks an assessment covers. The board already publishes this."""

from sqlalchemy import BigInteger, Column, ForeignKey, UniqueConstraint

from app.db.session import Base


class AssessmentBlock(Base):
    __tablename__ = "assessment_block"
    __table_args__ = (
        UniqueConstraint("template_id", "block_id", name="uq_assessment_block"),
        {"schema": "platform"},
    )

    assessment_block_id = Column(BigInteger, primary_key=True, autoincrement=True)
    template_id = Column(BigInteger, ForeignKey("platform.assessment_template.template_id"), nullable=False)
    block_id = Column(BigInteger, ForeignKey("platform.calendar_block.block_id"), nullable=False)
