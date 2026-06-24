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
