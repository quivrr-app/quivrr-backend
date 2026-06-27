# Quivrr Backend Architecture

## Purpose

`quivrr-backend` is the production backend for Quivrr catalogue search, manufacturer direct availability, retailer inventory ingestion, and market intelligence jobs. It serves the public API used by the Quivrr frontend and provides scheduled ingestion pipelines that keep SQL-backed catalogue and inventory data current.

The Bodhi board guide API is a separate service. It can use Quivrr catalogue and inventory data in later phases, but it is not hosted or run from this backend repository.

## Platform Map

Quivrr currently spans frontend, backend, data, scheduled jobs, AI, email, and monitoring services.

| Area | Runtime | Main resources or paths | Purpose |
| --- | --- | --- | --- |
| Main frontend | Azure Static Web Apps | `quivrr-frontend` | User-facing Quivrr app. |
| Surf frontend | Azure Static Web Apps | `quivrr-surf-frontend` | Surf/Bodhi-oriented frontend experience. |
| Backend API | Azure App Service | `quivrr-backend-api`, `app.py`, `startup.sh` | Read-oriented catalogue and inventory API. |
| Data tier | Azure SQL | `quivrr-sql-prod`, `quivrr-db-prod` | System of record for catalogue, MFA, retailer inventory, and market intelligence tables. |
| Scheduled jobs | Azure Container Apps Jobs | AU and EU retailer/MFA jobs, weekly catalogue, and market intelligence jobs | Scheduled ingestion and reporting workloads. |
| Container image | Azure Container Registry | `quivrracrprod.azurecr.io/quivrr-inventory-job:latest` | Shared image for scheduled job workloads. |
| AI board guide | Azure App Service + Azure OpenAI | `quivrr-board-guide-api`, `quivrr-board-guide-openai` | Separate Bodhi board guide service. |
| Email | Azure Communication Services | `quivrr-communication`, `quivrr-email` | Market intelligence report email delivery. |
| Monitoring | Log Analytics | `workspace-quivrrproductionrgUkqI` | Container Apps and platform observability. |

## Observability Architecture

Quivrr uses stdout JSON structured logs for scheduled jobs and Bodhi API events. Azure Log Analytics ingests those events without adding new infrastructure or creating a second monitoring stack.

Operational health combines:

- structured job state from the latest successful or failed run
- SQL freshness and link-quality checks
- region leakage checks
- Board Guide API dependency checks

Europe remains the Gen 3 reference architecture for dashboards, alert rules, and future monitoring rollout patterns. Sprint 7 standardises AU and ID onto the same shared regional linkage and observability model, with US already following the Gen 3 path.

## Azure Resource Map

The platform is split across two resource groups.

`rg-quivrr-aue-prod` contains the frontend and data tier:

- `quivrr-frontend` - main Static Web App.
- `quivrr-surf-frontend` - surf Static Web App.
- `quivrr-sql-prod` - Azure SQL Server.
- `quivrr-db-prod` - Azure SQL production database.

`quivrr-production-rg` contains backend runtime, jobs, AI, email, and monitoring:

- `quivrr-backend-plan` - App Service plan.
- `quivrr-backend-api` - backend FastAPI App Service.
- `quivrracrprod` - Azure Container Registry.
- `quivrr-jobs-env` - Container Apps managed environment.
- `quivrr-nightly-au-inventory` - scheduled AU retailer inventory job.
- `quivrr-nightly-eu-inventory` - scheduled EU retailer inventory job.
- `quivrr-weekly-brand-catalogues` - scheduled weekly catalogue job.
- `quivrr-mfr-availability` - scheduled AU manufacturer direct availability job.
- `quivrr-eu-mfr-availability` - scheduled EU manufacturer direct availability job.
- `quivrr-market-intelligence` - scheduled market intelligence job.
- `workspace-quivrrproductionrgUkqI` - Log Analytics workspace.
- `quivrr-communication` - Azure Communication Services resource.
- `quivrr-email` and `quivrr-email/AzureManagedDomain` - email service and domain.
- `quivrr-board-guide-api` - separate Bodhi API App Service.
- `quivrr-board-guide-openai` - Azure OpenAI resource used by Bodhi.

## FastAPI API

The API entrypoint is `app.py`. It creates a FastAPI application, configures CORS, opens Azure SQL connections with SQLAlchemy over ODBC, and exposes read-oriented endpoints.

Primary endpoints:

- `GET /` returns service status.
- `GET /api/brands` lists active brands.
- `GET /api/models/{brand_id}` lists active board models for a brand.
- `GET /api/constructions/{model_id}` lists constructions for a board model.
- `GET /api/sizes/{model_id}/{construction}` lists canonical board sizes.
- `GET /api/search` searches manufacturer direct and retailer inventory for a selected board size and region.
- `GET /api/test-db` validates database connectivity.

The API should not run scrapers, catalogue imports, or database mutation jobs. Those workloads belong in scripts and scheduled jobs.

`region` or `regionCode` is required for regional inventory behavior and must resolve to an active runtime region: `AU`, `EU`, `ID`, or `US`. Invalid values must be rejected or fail closed; they must not silently fall back to AU.

## Azure SQL Dependency

Azure SQL is the system of record for runtime catalogue, manufacturer direct availability, retailer inventory, and market intelligence data. Runtime database access is configured through:

- `SQL_SERVER`
- `SQL_DATABASE`
- `SQL_USERNAME`
- `SQL_PASSWORD`
- `SQL_DRIVER`, usually `ODBC Driver 18 for SQL Server`

The API and jobs rely on tables including brands, board models, board sizes, manufacturer inventory, retailer inventory, retailers, retailer inventory snapshots, and retailer inventory deltas.

The migration `sql/migrations/20260612_add_retailer_region_currency.sql` adds regional and currency fields to retailer tables and backfills AU defaults. It is important for regional rollout because `RegionCode`, `PriceAmount`, and `PriceCurrency` are used by search and Indonesia ingestion.

## Catalogue Pipeline

The canonical catalogue describes what brands make: brands, models, constructions, dimensions, volumes, and official product metadata. It is authoritative for board identity.

The weekly orchestrator is:

```powershell
python scripts/run_all_brand_catalogues.py
```

It runs brand pipelines such as JS Industries, Channel Islands, Pyzel, DHD, Lost, Rusty, Firewire, Haydenshapes, Sharp Eye, Misfit, Chemistry, Pukas, Simon Anderson, Chilli, Album, and Christenson. Brand-specific builders live under `scrapers/brands/**`; importers and orchestrators live under `scripts/`.

The weekly job writes `scrapers/brands/output/weekly_brand_catalogue_report.json` and does not trigger regional MFA or retailer import paths. Brand failures are guarded independently so one degraded canonical source does not silently weaken or clear another brand's canonical truth.

Current Tier 1 source policy:

- JS Industries canonical uses the official `https://jsindustries.com/products/{model}` parent model pages as the primary source. The builder extracts embedded official product data, official descriptions, and images from the page HTML instead of relying on brittle rendered text blocks.
- Channel Islands canonical uses the official global `https://cisurfboards.com/collections/board-models` and `https://cisurfboards.com/collections/shortboards` collections as primary discovery, with the official AU site only as a fallback when the global site omits a valid product page.
- Neither brand may fall back to retailer inventory for canonical truth.

## Manufacturer Direct Availability

Manufacturer direct availability, abbreviated MFA, means current manufacturer direct stock. MFA is not the canonical catalogue. Catalogue data describes what exists; MFA describes what is currently available directly from manufacturers.

The canonical catalogue is global, while manufacturer availability is regional. Manufacturer-direct cards must select `ManufacturerInventory` using the requested `RegionCode`. When a regional MFA row exists, its regional `ProductUrl`, image, price, currency, and stock state take precedence over canonical manufacturer metadata. Canonical manufacturer URLs are fallback references only. EU and ID requests must never fall back to AU manufacturer inventory or AU URLs.

The AU MFA orchestrator is:

```powershell
python scripts/manufacturer_availability/run_au_manufacturer_availability_pipeline.py
```

Brand-specific MFA builders live under `scrapers/manufacturers/availability/**`. Importers live under `scripts/manufacturer_availability/`.

The Indonesia MFA path is currently separate:

```powershell
python scripts/manufacturer_availability/run_id_manufacturer_availability_pipeline.py
```

At present this routes through JS Industries Indonesia via `run_js_id_availability_pipeline.py`.

EU manufacturer direct availability is implemented for JS Industries, Pyzel, Firewire, Haydenshapes, Rusty, Sharp Eye, and DHD. EU rows are built and imported through the EU MFA pipeline with `RegionCode = 'EU'`, regional URLs, EUR pricing where a price exists, and `AvailabilitySource = 'manufacturer_direct'`.

Manufacturer inventory is regional. A matching regional `ManufacturerInventory.ProductUrl` wins; the canonical manufacturer URL is reference fallback only. There is no AU inventory or URL fallback for EU or ID. For example, EU JS Industries Monsta CarboTune 5'11 / 28L resolves to available manufacturer-direct inventory in EUR using the `jsindustries.eu` variant URL.

## Retailer Inventory Pipeline

Retailer inventory is a separate availability source from both the canonical catalogue and MFA. Retailer inventory is scraped from retailer websites, normalized, indexed, quality-checked, and imported into SQL.

The AU nightly orchestrator is:

```powershell
python scripts/run_nightly_inventory_refresh.py
```

The AU pipeline detects retailer platforms, builds active scrape targets, runs platform-specific scrapers, filters likely surfboards, normalizes data, matches JS inventory to catalogue records, builds grouped inventory indexes, builds retailer quality reports, and imports retailer inventory.

Supported runtime scraper families include Shopify, WooCommerce, BigCommerce, Magento, Neto/Maropost, Squarespace, Wix, Ecwid, and specific retailer integrations such as Coopers Board Store.

The active EU retailer set is 58 Surf, Pukas, Mundo Surf, Bell Surf, Surf Boss, Surf Corner, and Single Quiver. EU discovery and import remain isolated from AU and ID paths.

Exact retailer matching accepts equivalent dimensions, including fractional and decimal inch representations, decimal-comma or decimal-point litres, and bounded width, thickness, and volume comparisons. For 58 Surf, discovery fetches product-detail attributes and retains width, thickness, volume, construction, and fin information through normalization and import. An exact result can therefore pass through equivalent dimensions even when `BoardSizeId` remains `NULL` because duplicate equivalent canonical sizes make deterministic size linking ambiguous.

## Regional Rollout

`RegionCode` is mandatory for regional inventory and availability. AU, EU, and ID are active runtime regions. Search and imports must never coerce an invalid, missing, or unsupported region to AU.

AU is the mature production region. Existing retailer master data, active scrape targets, and nightly inventory jobs are AU-oriented unless a file explicitly says otherwise.

ID is active in code but less mature operationally. `app.py` contains Indonesia-specific matching behavior for `regionCode=ID`, including relaxed construction, length, and volume constraints in retailer search. Indonesia inventory uses `RegionCode = 'ID'`, `Country = 'Indonesia'`, `PriceCurrency = 'IDR'`, and `PriceAmount` for native currency amounts.

US is active in Production Beta using the Gen 3 regional runtime. Manufacturer direct and retailer inventory remain region-scoped with `RegionCode = 'US'`, and the same backend search pipeline is shared across all four runtime regions.

Regional counts must be protected independently. Importers and scheduled jobs fail closed if AU or ID counts drift during EU work, if EU unexpectedly decreases, or if a `NULL` `RegionCode` is introduced.

## Production Inventory Baseline

Validated production baseline as of June 2026:

| Table | AU | EU | ID | NULL |
| --- | ---: | ---: | ---: | ---: |
| `RetailerInventory` | 11,746 | 9,105 | 1,998 | 0 |
| `ManufacturerInventory` | 6,498 | 2,736 | 185 | 0 |

These are operational reference counts, not hard-coded application expectations. Any import must print before/after counts and explain expected movement.

## Retailer Region Incident And Guardrails

A production Sev 1 incident was caused by the legacy AU importer running an unscoped `DELETE FROM dbo.RetailerInventory` and recreating AU rows without `RegionCode`, which removed EU and ID inventory and produced AU-shaped `NULL` rows.

The corrected AU path deletes only `WHERE RegionCode = 'AU'`, and every AU insert explicitly supplies `RegionCode = 'AU'`. Region guardrail tests reject unscoped `RetailerInventory` deletes and insert paths that omit `RegionCode`. EU and ID importers must retain equivalent fail-closed protections.

## Indonesia Current State

Indonesia support exists in code even though some older README text still describes the folder as reserved for future work.

Current Indonesia components:

- `scrapers/retailers/indonesia/import_indonesia_retailer_inventory.py`
- `scrapers/retailers/indonesia/bgs_bali/build_bgs_bali_inventory.py`
- `scrapers/retailers/indonesia/white_monkey/build_white_monkey_inventory.py`
- `scrapers/retailers/indonesia/freefall/build_freefall_inventory.py`
- `scrapers/retailers/indonesia/onboard_store/build_onboard_store_inventory.py`
- `scrapers/retailers/indonesia/boardriders_bali/build_boardriders_bali_inventory.py`
- `scrapers/retailers/indonesia/drifter/build_drifter_inventory.py`
- `scrapers/manufacturers/availability/js_industries/build_js_id_availability.py`
- `scripts/manufacturer_availability/import_js_id_availability.py`
- `scripts/manufacturer_availability/run_js_id_availability_pipeline.py`
- `scripts/manufacturer_availability/run_id_manufacturer_availability_pipeline.py`

Indonesia output files under retailer folders are generated scraper artifacts and should be treated as generated output unless explicitly promoted to fixtures or seed data.

## Market Intelligence

The `market_intelligence/` package provides historical inventory analysis and reporting.

Primary flow:

1. `run_market_intelligence_job.py` calls `market_intelligence/reporting/run_daily_market_report.py`.
2. The report pipeline snapshots active retailer inventory into `dbo.RetailerInventorySnapshot`.
3. It calculates deltas into `dbo.RetailerInventoryDelta`.
4. It sends a daily email report through Azure Communication Services.

Primary package areas:

- `market_intelligence/sql` - bootstrap support for snapshot and delta tables.
- `market_intelligence/retailer_deltas` - snapshot and delta calculation logic.
- `market_intelligence/reporting` - report and email delivery.
- `market_intelligence/analytics` - future analytics area.
- `market_intelligence/output` - local generated output.

Market intelligence should read from normalized catalogue and inventory tables. It should not become a parallel ingestion source.

## Board Intelligence Platform And Bodhi

Bodhi, the board guide API, lives in the separate `quivrr-board-guide-api` service. The surf frontend calls `https://quivrr-board-guide-api.azurewebsites.net/api/board-guide/chat`.

Bodhi is deployed on `quivrr.surf`, integrates with Azure OpenAI through `quivrr-board-guide-openai`, and uses region-aware live inventory recommendations plus deterministic rider-fit volume guidance. It reads manufacturer descriptions and generated board intelligence but does not run backend scrapers or imports.

The intelligence flow is:

1. Manufacturer source metadata and descriptions.
2. Global canonical board profiles.
3. Global deterministic board-intelligence classification.
4. Rider-fit engine.
5. Board-equivalency engine.
6. Bodhi recommendation engine.
7. Explicitly regional MFA and retailer availability lookup.

Canonical catalogue identity and board intelligence are global. Region affects stock, price, currency, retailer/manufacturer source, product URL, and location. Region must not change board identity, description, category, wave fit, or surfer-fit taxonomy.

Intelligence source precedence is manufacturer descriptions and metadata, then Quivrr-reviewed overrides, then generated factual intelligence. Retailer descriptions are non-authoritative fallback context only and must never become canonical board truth.

Current knowledge coverage is 430 distinct described models across 513 profiles. Deterministic classification covers 192 of 513 models; 321 remain deliberately unclassified and 84 lack manufacturer descriptions.

The seven-phase platform roadmap is:

1. Architecture, documentation, and governance.
2. Manufacturer intelligence discovery audit.
3. Canonical intelligence harvesting.
4. Board classification engine.
5. Board equivalency engine.
6. Rider fit and intake workflow.
7. Full Bodhi recommendation integration with live regional inventory.

Live stock claims must always come from regional `ManufacturerInventory` or `RetailerInventory`, never from generated intelligence files.

## Production Jobs

| Job | Runtime | Command | Schedule from Azure export | Purpose |
| --- | --- | --- | --- | --- |
| `quivrr-nightly-au-inventory` | Azure Container Apps Job | `python scripts/run_nightly_inventory_refresh.py` | `30 16 * * *` | Refresh AU retailer inventory. |
| `quivrr-nightly-eu-inventory` | Azure Container Apps Job | `python scripts/europe/run_eu_retailer_inventory_refresh.py apply` | `30 19 * * *` | Refresh EU retailer inventory. |
| `quivrr-weekly-brand-catalogues` | Azure Container Apps Job | `python scripts/run_all_brand_catalogues.py` | `0 3 * * 1` | Refresh global canonical brand catalogues only. It must not trigger regional MFA or retailer stock writes. |
| `quivrr-mfr-availability` | Azure Container Apps Job | `python scripts/manufacturer_availability/run_au_manufacturer_availability_pipeline.py` | `0 17 * * *` | Refresh AU manufacturer direct availability. |
| `quivrr-eu-mfr-availability` | Azure Container Apps Job | `python scripts/manufacturer_availability/run_eu_manufacturer_availability_pipeline.py apply` | `30 20 * * *` | Refresh EU manufacturer direct availability. |
| `quivrr-market-intelligence` | Azure Container Apps Job | `python run_market_intelligence_job.py` | `0 18 * * *` | Snapshot inventory, calculate deltas, send report. |
| `au-inventory-refresh` | Azure WebJob folder | `App_Data/jobs/triggered/au-inventory-refresh/run.cmd` | `0 30 16 * * *` in `settings.job` | Legacy or App Service triggered representation of AU inventory refresh. Confirm active runtime before operating. |

## Deployment Model

The backend API is deployed to Azure App Service through `.github/workflows/deploy-backend-api.yml`. The workflow removes non-runtime files, logs into Azure using `AZURE_CREDENTIALS`, and deploys the repository package to `quivrr-backend-api`.

Scheduled jobs use the container image built by `.github/workflows/build-inventory-job.yml`. That workflow builds the Docker image and pushes `quivrracrprod.azurecr.io/quivrr-inventory-job:latest`.

The `Dockerfile` installs Python dependencies, Microsoft ODBC dependencies, Playwright browser dependencies, and application source. Its default command runs the nightly inventory refresh, but Container Apps Jobs override command and args per job.

## Architectural Principles

- The canonical catalogue is authoritative for brands, models, constructions, and sizes.
- Global canonical jobs may write `Brands`, `BoardModels`, and `BoardSizes`, including official descriptions, images, and official URLs, but must not write `ManufacturerInventory` or `RetailerInventory`.
- Canonical guards stay enabled even when a source degrades. `source_incomplete_guard` prevents partial brand scrapes from silently collapsing model coverage, and `deactivation_guard` prevents unsafe mass model retirement without explicit reviewed override.
- MFA means current manufacturer direct stock and must remain distinct from catalogue definitions.
- Regional MFA jobs may read canonical tables and write only `ManufacturerInventory`.
- Retailer inventory is a separate availability source and must not overwrite canonical catalogue meaning.
- Regional retailer jobs may read canonical tables and write only `Retailers` and `RetailerInventory`.
- `RegionCode` must be respected for every regional rollout and search path.
- Regional inventory rows must never have a `NULL` `RegionCode`; invalid regions fail closed rather than falling back to AU.
- Native currency should use `PriceAmount` and `PriceCurrency`; AU compatibility can use `PriceAud`.
- API request handlers should not run live scraper or import work.
- Temporary investigation scripts should be quarantined or archived, not left in the repository root.
- Bodhi is separate from this backend and may claim availability only from explicit region-scoped catalogue, MFA, and retailer API results.
