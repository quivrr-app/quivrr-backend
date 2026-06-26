# Gen 3 Region Playbook

## Purpose

Gen 3 regional rollout means Quivrr adds or uplifts a region by configuration and source onboarding, not by changing the core backend search architecture.

This playbook is the standard path for `AU`, `EU`, `ID`, `US`, and future regions after Sprint 7 regional standardisation.

## Gen 3 Principles

- Canonical board identity is global.
- Manufacturer availability and retailer inventory are regional.
- Every runtime write must carry an explicit `RegionCode`.
- Search behaviour must be identical across regions.
- Fallback behaviour must be fail-open and never hold the core search path hostage.
- Region onboarding should add sources, expectations, jobs, and tests, not bespoke backend branches.

## Minimum Region Checklist

1. Add region metadata to `config/region_source_expectations.json`.
2. Add retailer target or backlog config under the region scraper path.
3. Add manufacturer availability source expectations if direct stock exists.
4. Ensure regional importers set the correct `RegionCode` on every row.
5. Add the region to scheduled runner entrypoints and runtime guardrail tests.
6. Add observability expectations so the Operations Centre can classify source health.
7. Validate search API acceptance for the new `region` value.
8. Run linkage, availability, and search smoke tests before any SQL apply or Azure job creation.

## Required Deliverables

- Canonical catalogue coverage for supported brands in the region.
- Retailer inventory runner with dry-run and guarded apply behaviour.
- Manufacturer availability runner only for genuine direct manufacturer stock.
- Region-scoped observability and link health reporting.
- Search validation for:
  - manufacturer direct
  - exact retailer
  - close retailer
  - thin-result fallback

## Shared Quality Gates

- `RegionCode` isolation is enforced in every importer and search query.
- Supported manufacturer linkage is measured through `scripts/run_supported_inventory_linkage_backfill.py`.
- Canonical completeness is measured through `scripts/audits/audit_canonical_catalogue_health.py`.
- Regional stock and fallback eligibility are measured through `scripts/audits/audit_regional_availability_health.py`.
- Search decision-tree parity is measured through `scripts/audits/audit_search_behaviour_matrix.py`.
- Operations Centre readiness scores are reviewed before a region moves from rollout to stable.

## Rollout Sequence

1. Canonical catalogue readiness.
2. Manufacturer availability validation where applicable.
3. Retailer inventory dry-run.
4. Supported linkage uplift.
5. Search smoke validation.
6. Guarded SQL apply review.
7. Azure nightly job creation.
8. Operations Centre monitoring and readiness review.

## Region Notes

- `AU`: legacy retailer runtime, now retrofitted toward Gen 3 shared linkage.
- `EU`: reference Gen 3 architecture.
- `ID`: region-scoped runtime with retailer and JS direct availability constraints.
- `US`: Production Beta using the Gen 3 regional model.
