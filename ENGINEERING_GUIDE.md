# Quivrr Backend Engineering Guide

## Local Development Setup

Use Python 3.11. Create a virtual environment and install dependencies from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Some scraper paths use Playwright. Install browser assets before running scraper jobs that require browser automation:

```powershell
python -m playwright install chromium
```

ODBC-backed SQL access requires Microsoft ODBC Driver 18 for SQL Server, or a compatible driver named by `SQL_DRIVER`.

## Required Environment Variables

The API, importers, and SQL-backed jobs require:

- `SQL_SERVER`
- `SQL_DATABASE`
- `SQL_USERNAME`
- `SQL_PASSWORD`
- `SQL_DRIVER`, optional when the default `ODBC Driver 18 for SQL Server` is available

Market intelligence email/reporting tooling may also use:

- `ACS_EMAIL_CONNECTION_STRING`
- `QUIVRR_REPORT_SENDER`
- `QUIVRR_REPORT_RECIPIENT`
- `QUIVRR_SMTP_HOST`
- `QUIVRR_SMTP_PORT`
- `QUIVRR_SMTP_USERNAME`
- `QUIVRR_SMTP_PASSWORD`

Do not commit `.env` files, credentials, generated reports, local logs, or scraper output unless explicitly required.

## Run The API Locally

Compile-check the API before running it:

```powershell
python -m py_compile app.py
```

Run the API locally with Uvicorn:

```powershell
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Production-style startup uses:

```bash
./startup.sh
```

The `/api/test-db` endpoint validates SQL connectivity but does touch the configured database.

## Run Catalogue Pipeline

The weekly catalogue orchestrator is:

```powershell
python scripts/run_all_brand_catalogues.py
```

This command runs live brand catalogue builders and importers. Only run it when database writes and external brand fetches are intended.

For syntax-only validation:

```powershell
python -m py_compile scripts/run_all_brand_catalogues.py
```

## Run AU MFA Pipeline

MFA means manufacturer direct availability. Run the AU MFA pipeline with:

```powershell
python scripts/manufacturer_availability/run_au_manufacturer_availability_pipeline.py
```

This command can fetch current manufacturer stock and import availability into SQL. Only run it with approval in production-connected environments.

For syntax-only validation:

```powershell
python -m py_compile scripts/manufacturer_availability/run_au_manufacturer_availability_pipeline.py
```

## Run Nightly Retailer Refresh

The nightly AU retailer inventory orchestrator is:

```powershell
python scripts/run_nightly_inventory_refresh.py
```

This command runs live retailer scrapers, generates local output, and imports inventory. It should not be used as a lightweight validation step.

For syntax-only validation:

```powershell
python -m py_compile scripts/run_nightly_inventory_refresh.py
```

## Deployment Notes

The API process is started by `startup.sh`, which runs `app:app` through Gunicorn with Uvicorn workers.

The nightly AU retailer refresh is also represented as an Azure WebJob under `App_Data/jobs/triggered/au-inventory-refresh/`.

The weekly brand catalogue job is represented by `weekly-brand-catalogues-job.json` and runs as an Azure Container Apps scheduled job.

The `Dockerfile` installs:

- Python dependencies from `requirements.txt`
- Microsoft SQL Server ODBC dependencies
- Playwright Chromium dependencies
- application source

GitHub Actions workflows live in `.github/workflows/`.

## Azure Resources Referenced

Project files reference these Azure resource patterns:

- Azure SQL Server and database through `SQL_SERVER` and `SQL_DATABASE`
- Azure App Service or WebJob runtime for triggered inventory refresh
- Azure Container Apps jobs for scheduled catalogue and availability jobs
- Azure Container Registry for container images
- Azure Communication Services for report email delivery

Keep resource names and credentials in environment configuration or deployment settings, not in committed source files.

## Temporary Script Hygiene

Root-level `inspect_*`, `probe_*`, `patch_*`, `fix_*`, `debug_*`, and `dump_*` scripts should be treated as temporary investigation tools unless they are documented as supported entrypoints.

Temporary scripts should be moved to a quarantine folder or an explicit archive after use. Reusable tools should live under a clear package or tool folder, such as:

- `scripts/` for supported operational importers and orchestrators
- `scripts/tools/` for reusable operational tools
- `scrapers/**` for maintained scraper implementations
- `market_intelligence/**` for reporting, deltas, analytics, and SQL support

Avoid leaving one-off scripts in the repository root.

## Files That Should Not Be Committed

Do not commit:

- `.env` files or credentials
- `venv/`, `.venv/`, `__pycache__/`, or `*.pyc`
- generated scraper output unless it is an intentional fixture or canonical checked-in data file
- local logs
- ad hoc investigation scripts in the repository root
- temporary patch scripts after their changes have been reviewed

## Validate Before Pushing

Use syntax validation for cleanup and documentation-only changes:

```powershell
git status --short
python -m py_compile app.py
python -m py_compile scripts/run_all_brand_catalogues.py
python -m py_compile scripts/manufacturer_availability/run_au_manufacturer_availability_pipeline.py
python -m py_compile scripts/run_nightly_inventory_refresh.py
```

For changes that affect scrapers, imports, SQL writes, or matching behavior, add a targeted dry run or fixture-based check before running live jobs. Do not run live scrapers or database imports without explicit approval.
