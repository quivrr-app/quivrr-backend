# Quivrr Regional Rollout

## Purpose

This guide defines how new Quivrr fulfilment and search markets should be introduced without accidentally changing production search behavior, running unvalidated scrapers, or mixing regional inventory semantics.

Regional rollout must be deliberate. A region is not production-ready just because a frontend page, folder, or scraper file exists.

## RegionCode Philosophy

`RegionCode` represents the fulfilment and search market, not just geography.

Active and planned primary `RegionCode` values:

- `AU` = Australia.
- `ID` = Indonesia.
- `EU` = mainland European Union fulfilment market.
- `UK` = United Kingdom fulfilment market.

AU, EU, and ID are active runtime values. UK remains planned. `RegionCode` is mandatory for regional retailer and manufacturer availability rows; `NULL`, missing, and unsupported values must fail closed and must never be silently converted to AU.

EU and UK must stay separate. EU covers mainland European Union fulfilment. UK must not be grouped into EU because tax, duty, fulfilment, currency, shipping rules, and retailer relevance differ.

Do not create `PT`, `ES`, or `FR` primary `RegionCode` values yet. Portugal, Spain, and France may become submarkets, source metadata, or retailer tags later, but they are not primary `RegionCode` values at this stage.

## Regional Maturity Model

| Stage | Meaning |
| --- | --- |
| Stage 0 | Region planned. |
| Stage 1 | Frontend region exists. |
| Stage 2 | Manufacturer catalogue mapped. |
| Stage 3 | Manufacturer direct availability enabled. |
| Stage 4 | Retailer inventory enabled. |
| Stage 5 | Market intelligence enabled. |
| Stage 6 | Production complete. |

A region should only move stages after data quality, operational ownership, and rollback behavior are understood.

## AU Current State

AU is the mature production region.

- `RegionCode = AU`.
- Main retailer refresh runs through `scripts/run_nightly_inventory_refresh.py`.
- AU manufacturer direct availability runs through `scripts/manufacturer_availability/run_au_manufacturer_availability_pipeline.py`.
- AU catalogue and availability jobs are represented in Azure Container Apps Jobs.
- Existing AU retailer source, platform detection, active targets, and import behavior are the reference implementation for future regions.

AU assumptions must not be copied into other regions without validation.

## ID Current State

ID is active in code but should still be treated as a maturing regional implementation.

- `RegionCode = ID`.
- Indonesia retailer ingestion lives under `scrapers/retailers/indonesia/`.
- Indonesia manufacturer direct availability currently exists for JS Industries through `scripts/manufacturer_availability/run_id_manufacturer_availability_pipeline.py`.
- ID inventory uses native currency fields such as `PriceAmount` and `PriceCurrency`, with IDR expected for Indonesia sources.
- `app.py` currently contains ID-aware search handling, including relaxed matching for Indonesia retailer data.

Do not assume the old Indonesia README text is authoritative if it says the folder is only reserved for future work. The code now contains active Indonesia scaffolding and import paths.

## EU Current State

EU is an active mainland European Union fulfilment market.

- `RegionCode = EU`.
- Initial market focus: Portugal, Spain, and France.
- UK is explicitly excluded.
- EU retailer discovery and normalization live under `scrapers/retailers/europe/`.
- The active EU retailers are 58 Surf, Pukas, Mundo Surf, Bell Surf, Surf Boss, Surf Corner, and Single Quiver.
- EU MFA supports JS Industries, Pyzel, Firewire, Haydenshapes, Rusty, Sharp Eye, and DHD.
- EU retailer and MFA importers are region-scoped, repeatable, and protect AU and ID counts.
- `quivrr-nightly-eu-inventory` runs at `30 19 * * *`.
- `quivrr-eu-mfr-availability` runs at `30 20 * * *`.

EU search must use only EU retailer and manufacturer inventory. Regional product URLs and EUR prices take precedence over canonical references; AU fallback is prohibited.

Exact matching normalizes fractional and decimal inches, decimal-comma and decimal-point litres, and bounded width/thickness/volume differences. 58 Surf product-detail enrichment retains dimensions so equivalent-dimension matching can classify a product as exact even where duplicate canonical sizes prevent assignment of a unique `BoardSizeId`.

## Production Baseline

Validated June 2026 counts:

| Table | AU | EU | ID | NULL |
| --- | ---: | ---: | ---: | ---: |
| `RetailerInventory` | 11,746 | 9,105 | 1,998 | 0 |
| `ManufacturerInventory` | 6,498 | 2,736 | 185 | 0 |

## UK Planned State

UK is planned as the United Kingdom fulfilment market.

- Planned `RegionCode = UK`.
- UK must not be grouped into EU.
- UK retailer scraper notes live under `scrapers/retailers/united-kingdom/`.
- Future UK MFA builders should live under `scrapers/manufacturers/availability/uk/`.
- Future non-live target examples live in `scrapers/manufacturers/availability/config/uk_manufacturer_availability_targets.example.json`.

No UK live scraper, importer, search behavior, or Azure production job is active from this scaffold alone.

## Rollout Checklist

Before activating a region:

- Confirm the primary `RegionCode` and keep it stable.
- Confirm whether the region is a fulfilment market, not merely a country list.
- Define allowed countries, currencies, retailer source rules, and shipping assumptions.
- Add or update SQL fields only through reviewed migrations.
- Add manufacturer availability target config as disabled example data first.
- Add scraper folders and READMEs before adding executable scrapers.
- Build fixture or sample output expectations before live scraping.
- Validate generated output format before writing importers.
- Validate import behavior against a non-production or explicitly approved SQL target.
- Confirm frontend region selection passes the correct `regionCode`.
- Confirm search behavior should change before editing `app.py`.
- Confirm market intelligence should include the region before scheduling reporting jobs.
- Add Azure job templates before creating or enabling Azure resources.

## Validation Checklist

For scaffold-only changes:

- Confirm only documentation, README, or disabled example config files changed.
- Run syntax checks only if Python code changed.
- Confirm no scraper or importer was run.
- Confirm no Azure resources were created or modified.
- Confirm generated output folders were not touched.
- Run `git status --short --untracked-files=all`.

Before a live region activation or material rollout change:

- Compile-check new scripts.
- Validate output JSON schema against expected importer fields.
- Validate `RegionCode`, `PriceAmount`, `PriceCurrency`, country, retailer, and brand fields.
- Run a small approved test import against the intended SQL target.
- Verify API search results with explicit `regionCode`.
- Verify frontend behavior does not leak one region into another.
- Define rollback steps for bad inventory or bad retailer activation.

## Azure Container Apps Job Notes

Regional jobs follow the existing Container Apps Jobs pattern:

- Use the shared inventory image unless a region requires a different runtime.
- Use explicit command and args, for example `python scripts/...`.
- Set a region-specific job name. Existing EU jobs are `quivrr-nightly-eu-inventory` and `quivrr-eu-mfr-availability`.
- Use a conservative schedule until data quality is proven.
- Set retry and timeout values based on observed scrape duration.
- Keep SQL credentials and secrets in Azure app/job settings, not source files.
- Send logs to the existing Log Analytics workspace.
- Disable or keep manual-only until validation is complete.

Suggested future job categories beyond the active AU/EU jobs:

- UK manufacturer direct availability.
- UK retailer inventory.
- EU market intelligence.
- UK market intelligence.

## Generated Output Hygiene

Regional scraper output should be treated as generated data unless deliberately promoted to a reviewed fixture or seed file.

Avoid committing:

- `scrapers/retailers/**/output/`
- `scrapers/manufacturers/availability/output/`
- raw downloaded pages
- local logs
- probe results
- temporary inspection files

If example files are needed, use `.example.json` and mark them as disabled/non-live.

## Guardrails

- Do not activate a region before catalogue, MFA, retailer, search, and currency behavior are validated.
- Do not group UK into EU.
- Do not add `PT`, `ES`, or `FR` as primary `RegionCode` values yet.
- Do not change `app.py` search behavior as part of scaffold work.
- Do not run live scrapers or database imports without explicit approval.
- Do not create additional regional Azure jobs until the command, schedule, region, output, and rollback behavior are reviewed.
- Do not let generated regional output slip into commits unintentionally.
- Never run an unscoped `DELETE FROM dbo.RetailerInventory`.
- Every regional insert must explicitly provide `RegionCode`.
- The AU importer may delete only `RegionCode = 'AU'`; this guardrail exists because an earlier Sev 1 unscoped delete removed EU/ID rows and recreated AU inventory with `NULL` regions.
- EU jobs must stop on AU or ID drift, unexpected EU loss, or any `NULL` region.
