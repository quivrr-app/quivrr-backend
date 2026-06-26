# Quivrr Operations Dashboard

## Purpose

Sprint 6 adds an operator-facing Quivrr operations dashboard path built around Azure Monitor Workbooks, Azure SQL production metrics, and the existing structured logging model.

This dashboard is for Quivrr engineering operations. It is not a public product surface.

Current delivery path:

- local JSON metrics builder
- protected backend endpoint: `GET /api/ops/dashboard`
- Azure Workbook scaffold
- internal frontend scaffold at `quivrr-frontend/operations/index.html`

## Primary Data Sources

- Azure SQL production
  - `dbo.RetailerInventory`
  - `dbo.ManufacturerInventory`
  - `dbo.Brands`
  - `dbo.BoardModels`
- Existing linkage reporting logic
  - `scripts/run_supported_inventory_linkage_backfill.py`
- Existing structured logging and job state
  - `output/observability/job_state/*.json`
- Log Analytics / Application Insights for search and runtime telemetry

## Metric Builder

Local metric builder:

```powershell
python scripts/observability/build_operations_dashboard_metrics.py
```

The builder emits JSON with these top-level sections:

- `generatedAtUtc`
- `version`
- `jobHealth`
- `jobHealthByRegion`
- `regionOverview`
- `mfaHealth`
- `retailerHealth`
- `retailerHealthByRegion`
- `inventoryCounts`
- `searchQuality`
- `coverageGaps`
- `alerts`
- `alertSummary`
- `regionDetails`
- `sourceExpectations`
- `linkQuality`

## Protected Backend Endpoint

Backend endpoint:

```text
GET /api/ops/dashboard
```

Authentication model for Sprint 6:

- server-side env var: `OPS_DASHBOARD_API_KEY`
- accepted request headers:
  - `Authorization: Bearer <key>`
  - `x-ops-dashboard-key: <key>`
- missing or incorrect request key returns `403`
- missing server key disables the endpoint with `503`

Caching:

- env var: `OPS_DASHBOARD_CACHE_TTL_SECONDS`
- default: `300`
- response field: `cacheStatus = hit|miss`

The endpoint reuses `observability.operations_dashboard.build_operations_dashboard_metrics()` and does not duplicate SQL aggregation logic.

Live API note:

- the protected API now returns a summary-first payload sized for the MVP portal
- coverage gap rows are count-based in the live response rather than full per-model sample lists
- heavy internal sections such as full expectation config and full retailer / manufacturer linkage breakdown stay in the local builder path rather than the browser payload
- retailer health is now region-first for the portal:
- `retailerHealthByRegion.<REGION>.summary`
- `retailerHealthByRegion.<REGION>.retailers`
- `jobHealthByRegion.<REGION>.summary`
- `jobHealthByRegion.<REGION>.jobs`
- alerts are now grouped and trimmed:
  - `alerts` returns the top actionable items
  - `alertSummary.summary` returns grouped counts
  - `alertSummary.allAlerts` retains the full in-memory list for the current payload
  - `regionDetails.<REGION>.alerts` supports the region drill-in view

## Status Colours

- `green`
  Healthy and expected.
- `yellow`
  Partial, planned, degraded, or stale between 24 and 48 hours.
- `red`
  Expected and failing, stale beyond 48 hours, or unexpectedly zero-row.
- `grey`
  Not applicable or intentionally not configured.

## Job Health

Sprint 6.1 adds job health visibility to the operations payload and portal.

Current source model:

- Azure job registry is maintained in `config/azure_container_jobs.json`
- live freshness comes from Azure SQL-backed timestamps where available
- local or runner-emitted state comes from `output/observability/job_state/*.json`

Each job row includes:

- `region`
- `jobName`
- `jobType`
- `status`
- `statusLabel`
- `statusReason`
- `schedule`
- `expectedRegion`
- `lastStartedUtc`
- `lastSucceededUtc`
- `lastFailedUtc`
- `durationSeconds`
- `rowsInserted`
- `rowsUpdated`
- `activeRowsAfter`
- `structuredLogEventName`
- `azureContainerAppJobName`

Current configured job registry:

- `quivrr-weekly-brand-catalogues`
- `quivrr-market-intelligence`
- `quivrr-nightly-au-inventory`
- `quivrr-mfr-availability`
- `quivrr-nightly-eu-inventory`
- `quivrr-eu-mfr-availability`
- `quivrr-nightly-id-inventory`
- `quivrr-id-mfr-availability`
- `quivrr-nightly-us-inventory`
- `quivrr-us-mfr-availability`

Region drill-in behaviour:

- selected region shows only that region's jobs plus shared global jobs
- mobile uses stacked cards
- desktop uses a scrollable table

## AU Job Recovery

AU stale retailer and MFA status in late June 2026 mapped to real Azure job failures.

Observed failure signature in Azure Container Apps logs:

- `ModuleNotFoundError: No module named 'utils'`
- failing entrypoints:
  - `scripts/run_nightly_inventory_refresh.py`
  - `scripts/manufacturer_availability/run_au_manufacturer_availability_pipeline.py`

Root cause:

- AU runner entrypoints were invoked as script paths inside the shared job image
- they did not insert the repository root into `sys.path`
- the updated shared image therefore could not import `utils.structured_logging`

Recovery pattern:

1. Build and publish the shared `quivrr-inventory-job:latest` image with the runner bootstrap fix.
2. Manually start:
   - `az containerapp job start --resource-group quivrr-production-rg --name quivrr-nightly-au-inventory`
   - `az containerapp job start --resource-group quivrr-production-rg --name quivrr-mfr-availability`
3. Confirm fresh SQL timestamps for AU retailer and AU MFA rows.
4. Reload `/operations` and confirm AU job health moves from red to green or yellow.

Manual verification targets:

- `ContainerAppConsoleLogs_CL`
- `ContainerAppSystemLogs_CL`
- `dbo.RetailerInventory` latest AU timestamps
- `dbo.ManufacturerInventory` latest AU timestamps

Special handling:

- `Lost` MFA is `dealer_network_only` for every current region until genuine direct manufacturer stock exists.
- `Simon Anderson` is treated as Australia-only applicability.
- AU retailer expectations are legacy-root-runtime aware, so active AU retailer rows are treated as expected operational coverage even where there is no modern Gen 3 target registry yet.

## Workbook Assets

Workbook scaffold:

- [docs/azure/workbooks/quivrr-operations-workbook.json](/C:/Projects/quivrr.app/quivrr-backend/docs/azure/workbooks/quivrr-operations-workbook.json)

The workbook is intended to be imported into Azure Monitor Workbooks and then pointed at:

- Resource group: `quivrr-production-rg`
- Log Analytics workspace: `workspace-quivrrproductionrgUkqI`
- Backend App Service: `quivrr-backend-api`
- Application Insights: use the Application Insights resource connected to `quivrr-backend-api` if present in the portal
- Azure SQL source: `quivrr-sql-prod` / `quivrr-db-prod` via the existing operator SQL workflow, not embedded workbook secrets

Import steps:

1. Open Azure Portal.
2. Go to `Monitor`.
3. Open `Workbooks`.
4. Choose `+ New` then `Advanced Editor`.
5. Paste the contents of [docs/azure/workbooks/quivrr-operations-workbook.json](/C:/Projects/quivrr.app/quivrr-backend/docs/azure/workbooks/quivrr-operations-workbook.json).
6. Save as `Quivrr Operations Dashboard`.
7. Set the workbook resource context to `workspace-quivrrproductionrgUkqI`.
8. Confirm the KQL tables resolve against production App Service / job telemetry.
9. Pin the saved workbook to the Azure Portal dashboard named `Quivrr Operations` if a team dashboard is being maintained.

Expected Azure location after import:

- `Azure Portal -> Monitor -> Workbooks -> Quivrr Operations Dashboard`
- Optional pin target:
  `Azure Portal -> Dashboard -> Quivrr Operations`

## Current Dashboard Scope

The current workbook and JSON metric builder support:

- regional health overview
- MFA freshness and coverage matrix
- retailer freshness and linkage matrix
- current inventory row counts by region
- search linkage quality by region
- stock and coverage gap views
- alert summary rollup

For the live browser endpoint, the MVP favours:

- regional status cards
- grouped alert posture
- inventory counts
- search linkage summaries
- count-based coverage gaps
- MFA and retailer health matrices
- region-first retailer operating tables
- alert rollups

The current SQL builder does **not** yet persist or aggregate historical search latency, 5xx, timeout, or thin-fallback counts. Those should come from Log Analytics workbook queries rather than SQL.

## Internal Frontend Scaffold

An internal static viewer can be served from the frontend repo at:

- `quivrr-frontend/operations/index.html`

It is intentionally simple and mobile-friendly:

- region status cards stack on narrow screens
- alerts appear near the top
- MFA and retailer matrices allow horizontal scrolling when needed

The page must not be treated as a public operational portal. It still depends on the protected backend key and should remain behind proper hosting authentication in a later phase.

Current live internal access path:

- [https://quivrr.app/operations/](https://quivrr.app/operations/)

Frontend key handling for the MVP:

- prompts once for the operations key
- stores the key in browser `localStorage`
- allows the key to be cleared without exposing it in source
- must never hardcode `OPS_DASHBOARD_API_KEY`

## Operational Use

The dashboard should let an operator answer:

- Which regions are healthy?
- Which MFA sources are stale?
- Which retailers are stale?
- Which regions have poor linkage quality?
- Which supported models have no stock in a region?
- Which brands are not applicable rather than broken?

## Onboarding a New Region

1. Add the new region code to [config/region_source_expectations.json](/C:/Projects/quivrr.app/quivrr-backend/config/region_source_expectations.json).
2. Add expected MFA brands and retailer targets with `expected`, `planned`, `dealer_network_only`, or `not_applicable`.
3. Ensure inventory and MFA rows write the new `RegionCode`.
4. Re-run:

```powershell
python scripts/observability/build_operations_dashboard_metrics.py
```

5. Update the workbook parameter defaults if the new region should appear prominently.

## Security Model

Do not expose operational data publicly without authentication.

Sprint 6 safe posture:

- Azure Workbook access through Azure portal permissions
- backend endpoint protected by `OPS_DASHBOARD_API_KEY`
- static frontend scaffold may exist, but it is only useful with the protected key

Current backend deployment requirement:

- set `OPS_DASHBOARD_API_KEY` in the `quivrr-backend-api` App Service settings
- optionally set `OPS_DASHBOARD_CACHE_TTL_SECONDS=300`

Preferred future posture:

- `ops.quivrr.app`
- protected by Microsoft Entra ID, GitHub OAuth, or Static Web Apps authentication with allow-listed users

## Recommended Next Alerts

- expected MFA source stale > 48h
- expected retailer source stale > 48h
- region inventory row count drop > 50%
- App Service search p95 latency > 10s
- search 5xx spike
- container job failure
