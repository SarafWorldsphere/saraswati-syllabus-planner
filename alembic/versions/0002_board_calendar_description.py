"""Add the long description on board and calendar.

board_name and calendar_name stay the short labels the dropdown shows.
school_year keeps storing board_id and calendar_id.

Revision ID: 0002
Revises: 0001
"""

from app.db.rls import ensure_descriptions

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from alembic import op

    ensure_descriptions(op.get_bind())


def downgrade() -> None:
    from alembic import op
    from sqlalchemy import text

    bind = op.get_bind()
    bind.execute(text("ALTER TABLE platform.board DROP COLUMN IF EXISTS description"))
    bind.execute(text("ALTER TABLE platform.calendar DROP COLUMN IF EXISTS description"))
