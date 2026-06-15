# Quivrr Backend Architecture

## Purpose

`quivrr-backend` is the production backend for Quivrr's surfboard catalogue, manufacturer direct availability, retailer inventory, and market intelligence workflows. It serves the public API used by the Quivrr frontend and runs scheduled ingestion pipelines that keep catalogue and inventory data current.

The Bodhi board guide API is a separate service and is not part of this backend.

## FastAPI API

The API entrypoint is `app.py`. It creates a FastAPI application, configures permissive CORS for frontend access, and opens Azure SQL connections with SQLAlchemy over ODBC.

Primary endpoints:

- `GET /` returns a service status payload.
- `GET /api/brands` lists active brands.
- `GET /api/models/{brand_id}` lists active board models for a brand.
- `GET /api/constructions/{model_id}` lists constructions for a board model.
- `GET /api/sizes/{model_id}/{construction}` lists canonical board sizes.
- `GET /api/search` searches manufacturer and retailer inventory for a selected board size and region.
- `GET /api/test-db` validates database connectivity.

The API should remain read-oriented. Data ingestion and mutation belong in scripts and scheduled jobs, not request handlers.

## Azure SQL Dependency

The backend depends on Azure SQL as the system of record for catalogue and inventory data. Runtime database access is configured through environment variables:

- `SQL_SERVER`
- `SQL_DATABASE`
- `SQL_USERNAME`
- `SQL_PASSWORD`
- `SQL_DRIVER`, defaulting to `ODBC Driver 18 for SQL Server` where supported

Core tables referenced by the API and jobs include brands, board models, board sizes, manufacturer inventory, retailer inventory, and retailers. The API search logic expects these tables to preserve the distinction between canonical catalogue data, manufacturer direct availability, and retailer inventory.

## Catalogue Pipeline

The canonical catalogue pipeline builds and imports brand board catalogues. Brand-specific builders live under `scrapers/brands/**`; importers and orchestrators live under `scripts/`.

The main weekly orchestrator is:

```powershell
python scripts/run_all_brand_catalogues.py
```

This runs brand pipelines and writes a weekly catalogue report under `scrapers/brands/output/`. The canonical catalogue is authoritative for board models, constructions, and sizes. Search and matching logic should prefer canonical identifiers and fields over ad hoc scraped product titles.

## Manufacturer Direct Availability

Manufacturer direct availability, abbreviated as MFA in this repo, represents current manufacturer direct stock. MFA is separate from the canonical catalogue: catalogue data describes what a brand makes; MFA describes what is currently available direct from the manufacturer.

The AU MFA orchestrator is:

```powershell
python scripts/manufacturer_availability/run_au_manufacturer_availability_pipeline.py
```

Brand-specific MFA builders live under `scrapers/manufacturers/availability/**`. MFA importers live under `scripts/manufacturer_availability/`.

## Retailer Inventory Pipeline

Retailer inventory is separate from both the canonical catalogue and MFA. Retailer scrapers discover and normalize stock from retail websites, then import retailer availability into SQL.

The nightly AU retailer refresh is:

```powershell
python scripts/run_nightly_inventory_refresh.py
```

That orchestrator detects retailer platforms, builds active scrape targets, runs ecommerce platform scrapers, filters likely surfboards, normalizes records, builds grouped inventory indexes, generates quality reports, and imports retailer inventory.

Region rollout must respect `RegionCode`. New regions should not reuse AU assumptions without explicit regional configuration and validation.

## Market Intelligence

The `market_intelligence/` package contains historical inventory snapshots, retailer delta detection, reporting, analytics, and SQL bootstrap tooling.

Primary subpackages:

- `market_intelligence/sql` for bootstrap and schema support.
- `market_intelligence/retailer_deltas` for snapshot and delta pipelines.
- `market_intelligence/reporting` for report generation and email delivery.
- `market_intelligence/analytics` for trend and movement analysis.
- `market_intelligence/output` for generated local output.

Market intelligence should read from normalized catalogue and inventory data rather than becoming a second ingestion path.

## Deployment Model

The backend has three runtime boundaries:

- API runtime: `startup.sh` starts `app:app` with Gunicorn and Uvicorn workers.
- Azure WebJob runtime: `App_Data/jobs/triggered/au-inventory-refresh/run.cmd` runs the nightly AU retailer inventory refresh.
- Azure Container Apps jobs: scheduled jobs run containerized pipelines such as weekly brand catalogue refresh and manufacturer availability.

The `Dockerfile` installs Python dependencies, Microsoft ODBC dependencies, and Playwright browser dependencies needed by scraper jobs. GitHub Actions workflows under `.github/workflows/` build and deploy backend/API and inventory job artifacts.

## Architectural Principles

- The canonical catalogue is authoritative for brands, models, constructions, and sizes.
- MFA means current manufacturer direct stock and must remain distinct from catalogue definitions.
- Retailer inventory is a separate availability source and must not overwrite canonical catalogue meaning.
- `RegionCode` must be respected for regional rollout and search behavior.
- API request handlers should not run live scraper or import work.
- Temporary investigation scripts should be quarantined or archived, not left in the repository root.
- The Bodhi board guide API is separate from this backend.
