"""One row per write of a syllabus plan, kept at the version the write produced.

The plan row itself only shows the latest version. This table is how a
developer sees what it used to say.
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


class SyllabusPlanAudit(Base):
    __tablename__ = "syllabus_plan_audit"

    audit_id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=False), nullable=False, index=True)
    plan_id = Column(BigInteger, ForeignKey("syllabus_plan.plan_id"), nullable=False, index=True)
    version_no = Column(Integer, nullable=False)
    action = Column(String(20), nullable=False)
    changed_by = Column(String(50), nullable=False)
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # JSON object of the fields written on this version.
    changes = Column(Text, nullable=False)
