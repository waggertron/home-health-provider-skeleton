"""Move reporting tables into their own `reporting` schema and grant a
read-only `metabase_ro` role on it (post-v1 #3).

Two operations:

1. Create the `reporting` schema and `ALTER TABLE ... SET SCHEMA` the
   two reporting tables into it. `state_operations` tells Django the
   model state has changed without re-running DDL.
2. Create a `metabase_ro` Postgres role with USAGE on the schema and
   SELECT on its tables; default privileges grant SELECT on any future
   table created in the schema.

The role is idempotent (DO block); if it already exists from a prior
test-DB cycle the migration re-applies grants. Reverse drops the role
after revoking grants so re-running migrations from scratch is safe.
"""

from django.db import migrations


_FORWARD_SCHEMA = """
CREATE SCHEMA IF NOT EXISTS reporting;

ALTER TABLE reporting_dailyclinicianstats SET SCHEMA reporting;
ALTER TABLE reporting.reporting_dailyclinicianstats RENAME TO daily_clinician_stats;

ALTER TABLE reporting_dailyagencystats SET SCHEMA reporting;
ALTER TABLE reporting.reporting_dailyagencystats RENAME TO daily_agency_stats;
"""

_REVERSE_SCHEMA = """
ALTER TABLE reporting.daily_agency_stats RENAME TO reporting_dailyagencystats;
ALTER TABLE reporting.reporting_dailyagencystats SET SCHEMA public;

ALTER TABLE reporting.daily_clinician_stats RENAME TO reporting_dailyclinicianstats;
ALTER TABLE reporting.reporting_dailyclinicianstats SET SCHEMA public;

DROP SCHEMA IF EXISTS reporting;
"""


_FORWARD_ROLE = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'metabase_ro') THEN
        CREATE ROLE metabase_ro LOGIN PASSWORD 'metabase_ro_demo';
    END IF;
END $$;

GRANT USAGE ON SCHEMA reporting TO metabase_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA reporting TO metabase_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA reporting
    GRANT SELECT ON TABLES TO metabase_ro;
"""

_REVERSE_ROLE = """
ALTER DEFAULT PRIVILEGES IN SCHEMA reporting
    REVOKE SELECT ON TABLES FROM metabase_ro;
REVOKE SELECT ON ALL TABLES IN SCHEMA reporting FROM metabase_ro;
REVOKE USAGE ON SCHEMA reporting FROM metabase_ro;
DROP ROLE IF EXISTS metabase_ro;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("reporting", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=_FORWARD_SCHEMA,
            reverse_sql=_REVERSE_SCHEMA,
            state_operations=[
                migrations.AlterModelTable(
                    name="dailyclinicianstats",
                    table='reporting"."daily_clinician_stats',
                ),
                migrations.AlterModelTable(
                    name="dailyagencystats",
                    table='reporting"."daily_agency_stats',
                ),
            ],
        ),
        migrations.RunSQL(
            sql=_FORWARD_ROLE,
            reverse_sql=_REVERSE_ROLE,
        ),
    ]
