# PostgreSQL Migration Risk Check

PostgreSQL Migration Risk Check is a small Python CLI I built to review SQL migration files for changes that can surprise a production database.

The recent projects in this repo focused on Kubernetes, Terraform, and alerting. This one moves closer to release support: a quick local check before a migration gets merged.

## Problem

Database migrations can pass syntax review and still create operational risk. A migration might take a heavy lock, drop data, build an index in a blocking way, or add a `NOT NULL` constraint before the data is ready.

I wanted a small scanner that catches those obvious patterns early without needing a running database.

## What It Does

- reads a PostgreSQL `.sql` migration file
- flags `DROP TABLE`, `DROP COLUMN`, and `TRUNCATE`
- flags explicit `LOCK TABLE` statements
- flags `CREATE INDEX` statements that do not use `CONCURRENTLY`
- flags `ADD COLUMN ... NOT NULL` when there is no default value
- flags `ALTER COLUMN ... SET NOT NULL` so a reviewer can confirm the backfill path

## Tech Stack

- Python 3.10+
- Python standard library only
- `unittest` for verification

## Folder Structure

```text
.
|-- README.md
|-- postgres_migration_risk_check.py
|-- samples
|   |-- risky_migration.sql
|   `-- safe_migration.sql
`-- tests
    `-- test_postgres_migration_risk_check.py
```

## How to Run

From this project folder:

```bash
python3 postgres_migration_risk_check.py samples/risky_migration.sql
```

Expected result:

```text
FLAGGED: 6 PostgreSQL migration risk pattern(s)
```

Check the safer sample:

```bash
python3 postgres_migration_risk_check.py samples/safe_migration.sql
```

Expected result:

```text
PASS: no PostgreSQL migration risk patterns detected
```

Return JSON instead:

```bash
python3 postgres_migration_risk_check.py samples/risky_migration.sql --format json
```

## Example

The bundled risky sample includes:

- a blocking index build
- a `NOT NULL` column add before a default or backfill
- a `SET NOT NULL` constraint change that needs reviewer attention
- an explicit table lock
- destructive column and table drops

Those are the kinds of changes I would want called out before a migration reaches a production deploy.

## Tests

```bash
python3 -m py_compile postgres_migration_risk_check.py
PYTHONPATH=. python3 -m unittest discover -s tests
```

## Notes

- This is a narrow pre-review scanner, not a full SQL parser.
- It strips simple comments and scans normalized statements so it can stay dependency-free.
- Some `SET NOT NULL` changes are safe after a backfill. The scanner flags them because they deserve an explicit review note.
