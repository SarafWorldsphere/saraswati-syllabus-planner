"""Row-level security for school tables.

Platform rows have no tenant_id, so they are not covered. School rows are.
The function matches the tenant kit: app.tenant_id is set per transaction
by apply_rls, and a superuser still bypasses the policy.
"""

from sqlalchemy import text

SCHOOL_TABLES = (
    "school_year",
    "school_holiday",
    "syllabus_plan",
    "syllabus_plan_segment",
    "syllabus_plan_audit",
    "teaching_log",
    "marking_review",
)

# Kept as two statements. Some drivers refuse a script with more than one command.
SCHEMA_SQL = "CREATE SCHEMA IF NOT EXISTS platform"

TENANT_FUNCTION = """
CREATE OR REPLACE FUNCTION platform.current_tenant_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
    SELECT NULLIF(current_setting('app.tenant_id', true), '')::uuid
$$
"""


def ensure_platform(connection) -> None:
    connection.execute(text(SCHEMA_SQL))
    connection.execute(text(TENANT_FUNCTION))


def ensure_descriptions(connection) -> None:
    # create_all does not add a column to a table that already exists.
    connection.execute(text("ALTER TABLE platform.board ADD COLUMN IF NOT EXISTS description text"))
    connection.execute(text("ALTER TABLE platform.calendar ADD COLUMN IF NOT EXISTS description text"))


def install_rls(connection) -> None:
    ensure_platform(connection)
    for table in SCHOOL_TABLES:
        connection.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        connection.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        connection.execute(text(f"DROP POLICY IF EXISTS tenant_isolation ON {table}"))
        connection.execute(
            text(
                f"""
                CREATE POLICY tenant_isolation ON {table}
                    USING (tenant_id = (SELECT platform.current_tenant_id()))
                    WITH CHECK (tenant_id = (SELECT platform.current_tenant_id()))
                """
            )
        )
