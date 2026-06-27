# Quivrr Observability Framework

## Purpose

Quivrr now emits single-line JSON structured logs to stdout for scheduled jobs and platform reporting workflows. Azure Log Analytics can ingest these events without adding new infrastructure or increasing platform sprawl.

Europe remains the Gen 3 reference runtime. AU and ID continue to operate independently, with region included on every regional event.

## Event Taxonomy

Core fields:

- `event`
- `service`
- `region`
- `status`
- `timestamp_utc`

Optional fields:

- `rows`
- `rows_loaded`
- `rows_inserted`
- `model_links`
- `size_links`
- `linked_model_rows`
- `linked_size_rows`
- `duration_seconds`
- `error_type`
- `error_message`

Protected fields:

- Secrets such as passwords, tokens, API keys, and connection strings are redacted.
- Bodhi user message text and page-context text are redacted.

## Runtime Coverage

Structured logs are emitted by:

- AU, EU, and ID retailer inventory refresh entrypoints
- AU, EU, and ID MFA refresh entrypoints
- Weekly catalogue orchestration
- Market intelligence daily pipeline
- Inventory link health reporting
- Daily and weekly observability reports
- Bodhi API request and response lifecycle

Inventory link health report:

- Command: `python scripts/run_inventory_link_health_report.py`
- Event `inventory_link_health_snapshot` emits region-level active `RetailerInventory` coverage using `BoardModelId` and `BoardSizeId` linkage.
- Event `inventory_link_health_retailer` emits retailer-level active-row coverage for the same region.
- `canonical_size_linked_rows` and `canonical_size_linked_pct` are the primary `BoardSizeId IS NOT NULL` metrics.
- `searchable_rows` and `searchable_pct` remain as backward-compatible aliases for the same `BoardSizeId`-linked counts and percentages. They do not imply universal searchability across every region runtime.
- The script queries `dbo.RetailerInventory` and `dbo.Retailers` directly and includes every active `RegionCode` present in live retailer inventory.
- AU legacy retailer search can still return valid results even when `RetailerInventory.BoardModelId` and `RetailerInventory.BoardSizeId` are not populated.
- EU and ID link quality should be tracked primarily through `BoardModelId` and `BoardSizeId` coverage on active rows.
- USA uses the same canonical link health model as EU and ID once `RegionCode = 'US'` rows are present in `RetailerInventory`.
- The inventory link health report now sorts `EU`, `AU`, `ID`, and `US` as explicit regional snapshots when those active rows exist.
- Before SQL activation from a blocked local environment, the operational readiness signals are the US dry-run normalised row count, importable row count, retailer count, and per-retailer coverage from `scripts/usa/run_us_retailer_inventory_refresh.py`.

Supported catalogue linkage backfill:

- Command: `python scripts/run_supported_inventory_linkage_backfill.py dry-run`
- Apply: `python scripts/run_supported_inventory_linkage_backfill.py apply --confirm-apply APPLY_SUPPORTED_LINKS`
- The report scopes metrics to supported Quivrr manufacturers only and ignores unsupported or house-brand inventory when measuring platform linkage quality.
- The backfill uses one shared parser and canonical matcher across `AU`, `EU`, `ID`, and `US`.
- Used inventory is eligible when it belongs to a supported manufacturer and links to an existing canonical model or size.
- The report emits before/after supported-row linkage coverage globally and per region, retailer, and manufacturer, plus top remaining unmatched models and alias opportunities.
- The primary size metric is now `linkedSizeFamilyPctAfter`, which reflects confident canonical model + construction family + length linkage even when an exact `BoardSizeId` remains ambiguous.
- Exact canonical size linkage remains `linkedSizePctAfter` and continues to require a conservative unique `BoardSizeId`.
- The report also emits blocker counts for `ambiguousBoardSizeRowsAfter`, `missingLengthRowsAfter`, `missingConstructionRowsAfter`, and `missingModelRowsAfter`.
- Sprint 5.2 shared recovery added brand-aware safe aliases and title cleanup for supported manufacturers only. Observable recovered examples include `CI 2.Pro`, `The Wolverine`, `Mini Driver (Re Issue)`, `RNF Redux`, `Machadocado`, and `Feb's Fish`.
- Remaining top unmatched aliases should be treated as a catalogue or ambiguity backlog unless a real canonical model exists and the retailer title safely disambiguates it. High-volume examples include `Driver 3.0`, `The Ripper`, `Voodoo Child`, `Baby Buggy`, `T-Low`, `DFR`, and `Tasty Treat`.

## Health Model

The observability health module calculates:

- Platform Health
- Region Health
- Catalogue Health
- Inventory Health
- MFA Health
- Bodhi Health

Status model:

- `Healthy`: latest successful data is within freshness window
- `Warning`: latest run failed but freshness still holds
- `High`: freshness window missed or repeated recent failures
- `Critical`: API, SQL, or OpenAI dependency unavailable

The framework prefers latest-state and freshness logic over historical failure counts, which keeps alert noise down when an old failure has already been superseded by a later success.

## Quivrr Operations Centre

Sprint 6 adds a first-pass operator dashboard path for Quivrr:

- metric builder:
  `python scripts/observability/build_operations_dashboard_metrics.py`
- expectation config:
  `config/region_source_expectations.json`
- workbook guide:
  `docs/azure/quivrr-operations-dashboard.md`
- workbook scaffold:
  `docs/azure/workbooks/quivrr-operations-workbook.json`
- protected API endpoint:
  `GET /api/ops/dashboard`

The dashboard combines:

- Azure SQL current-state inventory and MFA aggregates
- supported inventory linkage quality from `scripts/run_supported_inventory_linkage_backfill.py`
- canonical completeness from `scripts/audits/audit_canonical_catalogue_health.py`
- explicit regional source applicability from `config/region_source_expectations.json`
- explicit Azure job registry from `config/azure_container_jobs.json`
- Log Analytics workbook queries for search/runtime telemetry

Job health additions:

- top-level payload fields:
  - `jobHealth`
  - `jobHealthByRegion`
  - `jobContracts`
  - `jobContractsByRegion`
- region drill-in now includes:
  - `regionDetails.<REGION>.jobHealth.summary`
  - `regionDetails.<REGION>.jobHealth.jobs`
  - `regionDetails.<REGION>.jobContracts`
- job status is derived from:
  - configured Azure Container App Job metadata captured in `config/azure_container_jobs.json`
  - SQL freshness timestamps for retailer inventory, manufacturer inventory, and canonical catalogue where applicable
  - runner-emitted `output/observability/job_state/*.json` when available

Job contract additions:

- every configured job now declares:
  - `entryScript`
  - `readsTables`
  - `writesTables`
  - `writesFields`
  - `expectedSourceOutputs`
  - `contractLayer`
- the dashboard emits `contractStatus`, `contractLabel`, and `contractReason` per configured job
- current contract checks flag:
  - missing entry scripts
  - canonical jobs that attempt to invoke regional stock pipelines
  - MFA jobs that are still planning-only scaffolds
  - retailer or MFA jobs that declare canonical table writes

Current job types:

- `catalogue`
- `market_intelligence`
- `retailer_inventory`
- `manufacturer_availability`

Current scheduled-runner bootstrap hardening:

- AU inventory, AU MFA, ID MFA, weekly catalogue, and observability email entrypoints now add the repository root to `sys.path`
- this prevents shared job-image failures like:
  - `ModuleNotFoundError: No module named 'utils'`

Current dashboard semantics:

- `green`: healthy and expected
- `yellow`: partial, planned, degraded, or stale within the warning window
- `red`: expected and failing, stale, or unexpectedly zero-row
- `grey`: not applicable or intentionally dealer-network-only

Sprint 6.2 dashboard truth notes:

- operational status is now kept separate from data quality status
- AU legacy retailer runtime uses live active retailer counts when the explicit retailer registry is incomplete
- supported search quality now uses the shared supported linkage recovery path from `scripts/run_supported_inventory_linkage_backfill.py`
- market coverage now measures supported canonical models with no stock anywhere by region
- market coverage is reported separately from search/linkage data quality so stock scarcity is not presented like a parser or outage failure
- search quality thresholds are:
  - green: model `>= 85%` and size family `>= 60%`
  - yellow: model `75%` to `84.99%` or size family `40%` to `59.99%`
  - red: below those safe thresholds
- exact size linkage is displayed but does not trigger red search alerts on its own
- market coverage thresholds are:
  - green: no-stock-anywhere `< 20%`
  - yellow: `20%` to `40%`
  - red: `> 40%`
- market coverage alert wording should read as a supply limitation, for example `AU market coverage limited`, not as an infrastructure outage
- dashboard `job_state` telemetry that has not yet been mirrored into local `output/observability/job_state/*.json` is shown as `grey/telemetry_pending` and should be validated in Azure execution history rather than treated as a yellow failure

Sprint 7 Gen 3 standardisation additions:

- `regionalReadiness` scores every region across:
  - operational
  - search
  - coverage
  - catalogue
  - overall
- `canonicalCompleteness` exposes supported-brand catalogue health for the dashboard and engineering audit workflow
- canonical completeness now includes per-brand coverage for:
  - official descriptions
  - official product URLs
  - official images
  - board category
  - recommended wave range
  - recommended surfer weight
- `topUnmatchedModels` and `topUnmatchedRetailers` surface the highest-volume remaining supported-linkage backlog directly in the dashboard payload
- the supported linkage dry-run now exposes blocker counts for:
  - `missingModelRowsAfter`
  - `missingLengthRowsAfter`
  - `missingConstructionRowsAfter`
  - `ambiguousBoardSizeRowsAfter`
- `scripts/run_supported_inventory_linkage_backfill.py --regions AU ID` can be used to isolate AU/ID retrofit work without mutating other regions

Current expectation notes:

- `Lost` is treated as `dealer_network_only` in every live region until Quivrr has evidence of genuine manufacturer-direct stock, so it should not page as a failed MFA source.
- `Simon Anderson` remains Australia-only for direct manufacturer applicability.

Search latency, timeout, and 5xx rollups are intentionally left to Azure Monitor Workbook KQL queries rather than duplicated into a separate SQL metrics table.

Ops endpoint notes:

- Authentication uses `OPS_DASHBOARD_API_KEY`.
- Accepted request headers are `Authorization: Bearer <key>` or `x-ops-dashboard-key: <key>`.
- Missing or incorrect request key returns `403`.
- Missing server-side key keeps the endpoint disabled with `503`.
- The endpoint caches the dashboard payload for five minutes by default through `OPS_DASHBOARD_CACHE_TTL_SECONDS`.
