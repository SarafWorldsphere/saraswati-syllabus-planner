"""Create the syllabus tables from the models, then turn on tenant isolation.

Platform tables have no tenant_id. School tables do, and they use the same
tenant_isolation policy as the tenant kit.
"""

from alembic import op

from app.db.rls import ensure_platform, install_rls
from app.db.session import Base

import app.models  # noqa: F401

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # Schema first. create_all will not invent the platform schema on its own.
    ensure_platform(bind)
    Base.metadata.create_all(bind=bind)
    install_rls(bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
