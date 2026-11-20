"""SQLAlchemy session. apply_rls stamps the school from the host onto the transaction."""

import logging

from saraswati_tenant import apply_rls, bind_rls
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings
from app.db.pool import build_engine

log = logging.getLogger(__name__)

engine = build_engine(
    settings.DATABASE_URL,
    service="syllabus-planner",
    slots=settings.DB_SERVICE_SLOTS,
    reserve=settings.DB_RESERVE,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
bind_rls(SessionLocal)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        # A route reached with no school bound means the middleware did not run.
        apply_rls(db)
        yield db
    finally:
        db.close()
