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

Market intelligence email/reporting may also use:

- `ACS_EMAIL_CONNECTION_STRING`
- `QUIVRR_REPORT_SENDER`
- `QUIVRR_REPORT_RECIPIENT`
- `QUIVRR_SMTP_HOST`
- `QUIVRR_SMTP_PORT`
- `QUIVRR_SMTP_USERNAME`
- `QUIVRR_SMTP_PASSWORD`

Bodhi is a separate service. Its Azure OpenAI and allowed-origin settings belong to the board guide API runtime, not this backend.

## Run The API Locally

Compile-check the API before running it:

```powershell
venv\Scripts\python.exe -m py_compile app.py
```

Run the API locally with Uvicorn:

```powershell
venv\Scripts\python.exe -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Production-style startup uses:

```bash
./startup.sh
```

The `/api/test-db` endpoint and `check_sql_connectivity.py` both touch the configured database. Use them only when SQL connectivity validation is intended.

## SQL Migration And DB Connectivity Notes

SQL Server and database are in `rg-quivrr-aue-prod` as `quivrr-sql-prod` and `quivrr-db-prod`.

The migration `sql/migrations/20260612_add_retailer_region_currency.sql` adds:

- `Retailers.RegionCode`
- `RetailerInventory.RegionCode`
- `RetailerInventory.PriceAmount`
- `RetailerInventory.PriceCurrency`

It also backfills AU defaults. Apply SQL migrations deliberately and verify against the target environment before running import jobs.

For local database access, confirm:

- The correct SQL env vars are loaded.
- Microsoft ODBC Driver 18 is installed or `SQL_DRIVER` points to an installed driver.
- Your client IP is allowed by Azure SQL firewall rules.
- You are not pointing local experiments at production unintentionally.

## Run Catalogue Pipeline

The weekly catalogue orchestrator is:

```powershell
venv\Scripts\python.exe scripts/run_all_brand_catalogues.py
```

This command runs live brand catalogue builders and importers. Only run it when database writes and external brand fetches are intended.

Source policy notes for current Tier 1 canonical brands:

- JS Industries should be validated from the Azure job context, not local only. The maintained builder reads embedded official product payloads from the parent model pages so it can preserve model coverage, descriptions, images, and official URLs even when rendered size tables change.
- Channel Islands canonical discovery should prefer the official global collections on `cisurfboards.com`, with the AU official site used only as a fallback when the global source omits a valid model page.
- Do not lower canonical completeness or deactivation guards just to make the weekly dashboard green. Investigate Azure-visible source behaviour first.

For syntax-only validation:

```powershell
venv\Scripts\python.exe -m py_compile scripts/run_all_brand_catalogues.py
```

## Run AU MFA Pipeline

MFA means manufacturer direct availability. Run the AU MFA pipeline with:

```powershell
venv\Scripts\python.exe scripts/manufacturer_availability/run_au_manufacturer_availability_pipeline.py
```

This command can fetch current manufacturer stock and import availability into SQL. Only run it with approval in production-connected environments.

For syntax-only validation:

```powershell
venv\Scripts\python.exe -m py_compile scripts/manufacturer_availability/run_au_manufacturer_availability_pipeline.py
```

## Run ID MFA Pipeline

Indonesia manufacturer direct availability is separate from AU:

```powershell
venv\Scripts\python.exe scripts/manufacturer_availability/run_id_manufacturer_availability_pipeline.py
```

This currently runs JS Industries Indonesia availability and imports rows with `RegionCode = 'ID'` and IDR pricing. Treat it as a live external fetch and SQL import.

## Run EU MFA Pipeline

EU manufacturer direct availability is separate from AU and ID:

```powershell
venv\Scripts\python.exe scripts/manufacturer_availability/run_eu_manufacturer_availability_pipeline.py dry-run
venv\Scripts\python.exe scripts/manufacturer_availability/run_eu_manufacturer_availability_pipeline.py apply
```

The implemented EU brands are JS Industries, Pyzel, Firewire, Haydenshapes, Rusty, Sharp Eye, and DHD. Apply mode writes only `RegionCode = 'EU'` / `AvailabilitySource = 'manufacturer_direct'`, uses batch SQL operations, and must fail closed on AU, ID, or `NULL` region drift.

## Run Nightly Retailer Refresh

The nightly AU retailer inventory orchestrator is:

```powershell
venv\Scripts\python.exe scripts/run_nightly_inventory_refresh.py
```

This command runs live retailer scrapers, generates local output, and imports inventory. It should not be used as a lightweight validation step.

For syntax-only validation:

```powershell
venv\Scripts\python.exe -m py_compile scripts/run_nightly_inventory_refresh.py
```

The EU retailer runner is separate:

```powershell
venv\Scripts\python.exe scripts/europe/run_eu_retailer_inventory_refresh.py dry-run
venv\Scripts\python.exe scripts/europe/run_eu_retailer_inventory_refresh.py apply
```

It covers 58 Surf, Pukas, Mundo Surf, Bell Surf, Surf Boss, Surf Corner, and Single Quiver. It must not invoke or mutate AU or ID paths.

## Run Indonesia Retailer Import

Indonesia retailer ingestion lives under `scrapers/retailers/indonesia/`.

The main import script is:

```powershell
venv\Scripts\python.exe scrapers/retailers/indonesia/import_indonesia_retailer_inventory.py
```

This runs Indonesia retailer scrapers, loads generated output, upserts Indonesia retailers, deactivates previous ID inventory, and inserts new ID retailer inventory. Run only with explicit approval because it fetches live sites and writes to SQL.

## Run Market Intelligence

The scheduled market intelligence entrypoint is:

```powershell
venv\Scripts\python.exe run_market_intelligence_job.py
```

This calls `market_intelligence/reporting/run_daily_market_report.py`, which snapshots active retailer inventory, calculates deltas, and sends a report email through Azure Communication Services.

Related commands:

```powershell
venv\Scripts\python.exe market_intelligence/sql/bootstrap_tables.py
venv\Scripts\python.exe market_intelligence/retailer_deltas/run_daily_delta_pipeline.py
venv\Scripts\python.exe market_intelligence/reporting/run_daily_market_report.py
```

All of these touch SQL, and the report path may send email. Use with care.

## Regional Rollout Procedure

AU, EU, and ID are active runtime regions. `RegionCode` is mandatory on regional inventory and availability rows. Invalid or missing values must fail closed; they must never silently fall back to AU.

For any region work:

1. Confirm `RegionCode` support in `app.py`.
2. Confirm SQL fields exist for region and currency.
3. Confirm retailer source files, output paths, importers, and currency behavior.
4. Confirm whether search matching should be strict or relaxed for that region.
5. Compile-check relevant scripts before any live run.
6. Run live scrapers/imports only after explicit approval and with the correct SQL target.
7. Print region counts before and after, and fail if protected region counts drift or a `NULL` region appears.

For Indonesia specifically, verify IDR pricing, `PriceAmount`, `PriceCurrency`, and `RegionCode = 'ID'`. Do not assume AU `PriceAud` behavior.

For EU specifically, verify EUR pricing where a price exists, `RegionCode = 'EU'`, regional manufacturer and retailer URLs, and no AU fallback. Exact dimension matching may equate fractional and decimal inches and decimal-comma or decimal-point litres within bounded tolerances.

The legacy AU retailer importer previously caused a Sev 1 incident by deleting all `RetailerInventory` rows and inserting AU rows without `RegionCode`. The supported AU importer must delete only `WHERE RegionCode = 'AU'` and every insert must explicitly set `RegionCode = 'AU'`. Keep the region guardrail tests in the validation suite.

## Deployment Notes

The API deploy workflow is `.github/workflows/deploy-backend-api.yml`. It deploys to Azure App Service `quivrr-backend-api` using the `AZURE_CREDENTIALS` GitHub secret.

The inventory/job image workflow is `.github/workflows/build-inventory-job.yml`. It builds and pushes:

```text
quivrracrprod.azurecr.io/quivrr-inventory-job:latest
```

Container Apps Jobs then run that image with job-specific commands and args.

This matters for weekly canonical fixes: changes to `scrapers/brands/**` do not affect the live Azure Container Apps Jobs until the inventory-job image workflow finishes and a new job execution starts from that refreshed image.

The API process is started by `startup.sh`, which runs `app:app` through Gunicorn with Uvicorn workers.

The WebJob folder `App_Data/jobs/triggered/au-inventory-refresh/` still exists. Confirm the active production runtime before operating it, because Azure Container Apps Jobs are the primary scheduled runtime documented in the current Azure export.

## Production Jobs

| Job | Command | Purpose |
| --- | --- | --- |
| `quivrr-nightly-au-inventory` | `python scripts/run_nightly_inventory_refresh.py` | AU retailer inventory refresh. |
| `quivrr-nightly-eu-inventory` | `python scripts/europe/run_eu_retailer_inventory_refresh.py apply` | EU retailer inventory refresh at `30 19 * * *`. |
| `quivrr-weekly-brand-catalogues` | `python scripts/run_all_brand_catalogues.py` | Weekly canonical catalogue refresh. |
| `quivrr-mfr-availability` | `python scripts/manufacturer_availability/run_au_manufacturer_availability_pipeline.py` | AU manufacturer direct availability refresh. |
| `quivrr-eu-mfr-availability` | `python scripts/manufacturer_availability/run_eu_manufacturer_availability_pipeline.py apply` | EU manufacturer direct availability refresh at `30 20 * * *`. |
| `quivrr-market-intelligence` | `python run_market_intelligence_job.py` | Inventory snapshot, delta calculation, and report email. |

## Azure Resource Map

Frontend and SQL resources:

- `rg-quivrr-aue-prod`
- `quivrr-frontend`
- `quivrr-surf-frontend`
- `quivrr-sql-prod`
- `quivrr-db-prod`

Backend, jobs, AI, email, and monitoring resources:

- `quivrr-production-rg`
- `quivrr-backend-plan`
- `quivrr-backend-api`
- `quivrracrprod`
- `quivrr-jobs-env`
- `quivrr-nightly-au-inventory`
- `quivrr-nightly-eu-inventory`
- `quivrr-weekly-brand-catalogues`
- `quivrr-mfr-availability`
- `quivrr-eu-mfr-availability`
- `quivrr-market-intelligence`
- `workspace-quivrrproductionrgUkqI`
- `quivrr-communication`
- `quivrr-email`
- `quivrr-board-guide-api`
- `quivrr-board-guide-openai`

Keep resource names and credentials in environment configuration, GitHub secrets, or Azure app settings. Do not hard-code secrets in source.

## Operational Runbook Items

Before changing code:

```powershell
git status --short
git branch --show-current
```

For documentation-only or cleanup changes:

```powershell
venv\Scripts\python.exe -m py_compile app.py
venv\Scripts\python.exe -m py_compile scripts/run_all_brand_catalogues.py
venv\Scripts\python.exe -m py_compile scripts/manufacturer_availability/run_au_manufacturer_availability_pipeline.py
venv\Scripts\python.exe -m py_compile scripts/run_nightly_inventory_refresh.py
```

For deployment checks, inspect GitHub Actions workflow results and Azure App Service or Container Apps Job logs. For SQL issues, check env vars, firewall rules, ODBC driver availability, and the target database before changing code.

Do not run live scrapers, imports, market intelligence jobs, or database migrations unless the task explicitly calls for it.

## Generated Output Hygiene

Generated output is common in this repo. Treat these as generated unless explicitly documented as fixtures or canonical seed data:

- `scrapers/products/output/`
- `scrapers/brands/output/`
- `scrapers/manufacturers/availability/output/`
- `scrapers/retailers/**/output/`
- `market_intelligence/output/`
- local logs
- `__pycache__/` and `*.pyc`

The current `.gitignore` ignores several generated paths but not every nested regional output folder. Check `git status --short --untracked-files=all` before committing so generated JSON does not slip into a docs or code cleanup commit.

## Temporary Script Hygiene

Root-level `inspect_*`, `probe_*`, `patch_*`, `fix_*`, `debug_*`, and `dump_*` scripts should be treated as temporary investigation tools unless documented as supported entrypoints.

Temporary scripts should be moved to a quarantine folder or an explicit archive after use. Reusable tools should live under a clear package or tool folder:

- `scripts/` for supported operational importers and orchestrators
- `scripts/tools/` for reusable operational tools
- `scrapers/**` for maintained scraper implementations
- `market_intelligence/**` for reporting, deltas, analytics, and SQL support

Avoid leaving one-off scripts in the repository root.

## Bodhi And Board Intelligence Boundary

Bodhi lives in the separate `quivrr-board-guide-api` service and uses Azure OpenAI. This backend should not host Bodhi request handling or run Bodhi LLM calls.

Bodhi is deployed on `quivrr.surf`. It uses global canonical profiles, manufacturer descriptions, deterministic board intelligence, rider-fit guidance, and explicit region-aware inventory results. It may claim stock only when the backend returns that stock for the selected region.

The architecture boundaries are:

- canonical catalogue and board intelligence are global
- `ManufacturerInventory` and `RetailerInventory` are regional
- board identity, descriptions, categories, wave fit, and surfer fit do not vary by region
- stock, price, currency, source, URL, and location do vary by region

Intelligence precedence is manufacturer metadata, Quivrr-reviewed overrides, generated factual intelligence, then retailer descriptions only as non-authoritative fallback. Retailer descriptions must never become canonical board truth.

## Files That Should Not Be Committed

Do not commit:

- `.env` files or credentials
- `venv/`, `.venv/`, `__pycache__/`, or `*.pyc`
- generated scraper output unless intentionally promoted
- local logs
- ad hoc investigation scripts in the repository root
- temporary patch scripts after their changes have been reviewed
- local Azure export archives unless requested

## Validate Before Pushing

Use syntax validation for cleanup and documentation-only changes:

```powershell
git status --short
venv\Scripts\python.exe -m py_compile app.py
venv\Scripts\python.exe -m py_compile scripts/run_all_brand_catalogues.py
venv\Scripts\python.exe -m py_compile scripts/manufacturer_availability/run_au_manufacturer_availability_pipeline.py
venv\Scripts\python.exe -m py_compile scripts/run_nightly_inventory_refresh.py
```

For changes that affect scrapers, imports, SQL writes, matching behavior, or region rollout, add targeted dry-run or fixture-based checks before any live job. Do not run live scrapers or database imports without explicit approval.
