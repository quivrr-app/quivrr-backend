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

## Operations Dashboard

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
- explicit regional source applicability from `config/region_source_expectations.json`
- Log Analytics workbook queries for search/runtime telemetry

Current dashboard semantics:

- `green`: healthy and expected
- `yellow`: partial, planned, degraded, or stale within the warning window
- `red`: expected and failing, stale, or unexpectedly zero-row
- `grey`: not applicable or intentionally dealer-network-only

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
