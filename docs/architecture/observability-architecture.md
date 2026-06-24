# Observability Architecture

## Scope

This Markdown source is the production-safe architecture update for the next compiled Quivrr documentation release.

## Observability Architecture

- Jobs and APIs emit single-line JSON events to stdout.
- Azure Log Analytics ingests stdout for Container Apps Jobs and App Services.
- Lightweight local state files capture the latest run result for freshness-aware reporting.
- SQL remains the source of truth for live inventory, MFA coverage, link quality, and freshness checks.

## Monitoring Architecture

- Inventory health is measured from `RetailerInventory`.
- MFA health is measured from `ManufacturerInventory`.
- Catalogue health is measured from canonical model/size tables and weekly catalogue job state.
- Bodhi health is measured from the Board Guide health endpoint and structured error events.

## Alerting Architecture

- Critical alerts focus on API, SQL, and OpenAI availability.
- High alerts focus on freshness failure, repeated job failure, inventory drops, and region leakage.
- Medium alerts focus on quality degradation rather than outages.

## Dashboard Architecture

- Azure Workbook queries consume the structured event taxonomy.
- Region-level health tiles should always separate `AU`, `EU`, and `ID`.
- Europe remains the Gen 3 reference view for new dashboard development.

## Reporting Architecture

- Daily observability report summarizes operational health and open issues.
- Weekly platform report summarizes trends, risks, and recommended actions.
- Both reports use the existing ACS email delivery path.

## Operational Ownership

- Backend/API ownership: platform engineering
- Retailer inventory ownership: ingestion engineering
- MFA ownership: ingestion engineering
- Bodhi ownership: board-guide engineering
- Alert triage ownership: shared production operations

## Future Region Monitoring

- New regions should be onboarded by adding region-aware freshness windows, SQL health queries, and dashboard filters.
- Shared event taxonomy should remain unchanged so dashboards and alerts scale without query rewrites.
