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
- `US` = United States fulfilment market.
- `UK` = United Kingdom fulfilment market.

AU, EU, ID, and US are valid runtime values in code. UK remains planned. `RegionCode` is mandatory for regional retailer and manufacturer availability rows; `NULL`, missing, and unsupported values must fail closed and must never be silently converted to AU.

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

Sprint 6 adds a shared operations layer for all active runtime regions:

- source expectations:
  `config/region_source_expectations.json`
- metrics builder:
  `scripts/observability/build_operations_dashboard_metrics.py`
- protected internal endpoint:
  `GET /api/ops/dashboard`
- Azure Workbook guide:
  `docs/azure/quivrr-operations-dashboard.md`

That dashboard path is now the preferred way to compare retailer freshness, MFA freshness, and linkage quality across `AU`, `EU`, `ID`, and `US` without ad hoc SQL.

## AU Current State

AU is the mature production region and now the Gen 3 reference implementation.

- `RegionCode = AU`.
- Main retailer refresh runs through `scripts/run_nightly_inventory_refresh.py`.
- AU manufacturer direct availability runs through `scripts/manufacturer_availability/run_au_manufacturer_availability_pipeline.py`.
- AU catalogue and availability jobs are represented in Azure Container Apps Jobs.
- Existing AU retailer source, dealer registry flow, discovery engine, platform detection, qualification process, platform packs, active targets, import behavior, Azure validation, Operations Centre checks, and search validation are the reference implementation for future regions.

AU assumptions must not be copied into other regions blindly, but the AU rollout workflow should now be copied first and then adapted only where region-specific evidence requires it.

## Standard Coverage Workflow

Future regional coverage work should move every retailer through the same sequence:

1. Dealer Registry
2. Discovery Engine
3. Platform Detection
4. Qualification
5. Platform Pack
6. Azure Validation
7. Operations Centre
8. Search

This is now the standard Quivrr coverage process. Regions should not bypass it with direct one-off scraper onboarding unless a task explicitly documents why.

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

## Global Linkage Framework

Sprint 5 is complete and Sprint 6 linkage uplift is active through one shared supported-catalogue linker:

- `python scripts/run_supported_inventory_linkage_backfill.py dry-run`
- `python scripts/run_supported_inventory_linkage_backfill.py apply --confirm-apply APPLY_SUPPORTED_LINKS`

The shared linker applies across `AU`, `EU`, `ID`, and `US` and scopes quality reporting to supported Quivrr manufacturers only. Unsupported brands, retailer house brands, and unsupported longboard catalogues are excluded from platform linkage quality metrics.

Current supported-manufacturer linkage state after Sprint 5.2 shared alias and parser recovery:

- Global model linkage: `83.09%`
- Global canonical size family linkage: `53.45%`
- Global exact `BoardSizeId` linkage: `34.89%`

Per-region supported linkage:

- `AU`: model `90.97%`, size family `53.36%`, exact size `28.49%`
- `EU`: model `76.87%`, size family `48.06%`, exact size `32.69%`
- `ID`: model `86.61%`, size family `70.48%`, exact size `63.70%`
- `US`: model `80.22%`, size family `56.58%`, exact size `37.37%`

Current shared blockers after Sprint 5.2:

- Missing model linkage remains the largest blocker: `3,484` supported rows.
- Rows ambiguous at exact `BoardSizeId` level: `3,253`.
- Rows blocked by missing construction where multiple canonical construction families exist at the same length: `2,624`.
- Rows still missing a usable length signal: `130`.

Sprint 5.2 shared recoveries now include:

- Brand-specific deterministic aliases for real canonical models such as `CI 2.Pro`, `The Wolverine`, `Mini Driver (Re Issue)`, `RNF Redux`, `Machadocado`, and `Feb's Fish`.
- Shared title cleanup that strips embedded dimensions, fin-box metadata, stock IDs, condition prefixes, and leading construction labels before model scoring.
- Construction-family preference that selects a more specific title construction such as `Spine-Tek` over a generic stored family such as `EPS` when the title clearly contains both.

Known remaining ceiling:

- Many of the top remaining unmatched rows do not have a safe canonical home today because the canonical model is missing entirely, for example `Voodoo Child`, `Baby Buggy`, `T-Low`, `DFR`, `Fred Rubble`, `Rocket 9`, `Balloon`, and `Tasty Treat`.
- Other high-volume misses remain intentionally unlinked because the retailer title collapses multiple canonical models into one ambiguous family, for example `Driver 3.0`, `The Ripper`, `Pocket Rocket`, and `F1` without a safe round or squash discriminator.

Shared search experience is now:

- Manufacturer Direct
- Exact Retailer Matches
- Close Matches
- Other Models Available

`Other Models Available` remains in incident-safe posture. The response shape is preserved, but the live API currently returns `otherModelMatches = []` under `searchVersion = search_timeout_fix_v2` until the fallback is explicitly re-proven safe.

## Sprint 6 Operations Dashboard

Operational visibility now has a first Azure-native dashboard path:

- region/source expectation config:
  `config/region_source_expectations.json`
- metrics builder:
  `scripts/observability/build_operations_dashboard_metrics.py`
- workbook guide:
  `docs/azure/quivrr-operations-dashboard.md`

The dashboard is designed to answer:

- which regions are healthy
- which retailer or MFA sources are stale
- current inventory row counts by region
- current supported-model, size-family, and exact-size linkage quality
- which supported models have no stock in a region

Future regions should appear automatically once `RegionCode` rows exist in inventory tables and the new region is added to the expectations config.

Exact retailer matches remain strict. Close matches now treat same-model, compatible-construction, same-length boards as legitimate canonical size-family matches even when width, thickness, or litres drift enough to make an exact `BoardSizeId` unsafe.

## UK Planned State

UK is planned as the United Kingdom fulfilment market.

- Planned `RegionCode = UK`.
- UK must not be grouped into EU.
- UK retailer scraper notes live under `scrapers/retailers/united-kingdom/`.
- Future UK MFA builders should live under `scrapers/manufacturers/availability/uk/`.
- Future non-live target examples live in `scrapers/manufacturers/availability/config/uk_manufacturer_availability_targets.example.json`.

No UK live scraper, importer, search behavior, or Azure production job is active from this scaffold alone.

## US Current State

US is now a Production Beta region following the EU Gen 3 structure.

- `RegionCode = US`.
- Frontend regional route exists at `/united-states`.
- Retailer discovery and normalisation live under `scrapers/retailers/usa/`.
- US Shopify discovery is now config-driven from `scrapers/retailers/usa/shopify/us_shopify_targets.json` rather than a hardcoded allowlist in the runner.
- US BigCommerce discovery is now wired through `scrapers/retailers/usa/bigcommerce/` and currently validates Catalyst Surf Shop safely.
- US Magento or category-html discovery is now wired through `scrapers/retailers/usa/magento/` and currently validates Warm Winds safely.
- US WooCommerce discovery now supports category and Store API paths, but no WooCommerce retailer has yet been promoted from backlog.
- The current production-ready dry-run retailer set is Surf Station, Jack's Surfboards, Real Watersports, Cleanline Surf, Hawaiian South Shore, Bird's Surf Shed, Island Water Sports, Surf N Sea, Kimo's Surf Hut, Moment Surf Co, Degree 33 Surfboards, Surfboard Broker, Infinity Surfboards, Walden Surfboards, Stewart Surfboards, Bing Surfboards, Robert August Surf Company, Dark Arts Surf, Catalyst Surf Shop, and Warm Winds.
- Hansen Surfboards and Encinitas Surfboards remain documented follow-up targets because the existing Shopify path does not yet recover safe surfboard inventory from their exposed feeds.
- US MFA now has a guarded regional pipeline through `scripts/manufacturer_availability/run_us_manufacturer_availability_pipeline.py`.
- The currently validated US MFA brand set is JS Industries, Channel Islands, Pyzel, Firewire, Album, Haydenshapes, DHD, Rusty, Sharp Eye, Christenson, Misfit Shapes, Chilli, and Pukas.
- The US MFA builder started as a Shopify-oriented shared path, but now also includes a safe US HTML stock parser for Christenson, an adapted Shopify-plus-canonical-size path for Misfit Shapes, an adapted ShaperBuddy-plus-US-storefront path for Chilli, and an adapted Shopify title parser for Pukas while preserving `RegionCode = US`.
- Lost is intentionally excluded from US MFA after architectural review. The public US site currently behaves as a catalogue plus dealer-routing surface, not a manufacturer-direct purchasable inventory feed. Chemistry remains degraded and Simon Anderson remains explicitly AU-only.
- Worldwide US MFA sources now preserve native source currency where that is the only trustworthy published price and expose shipping metadata so the frontend can warn when manufacturer-direct stock may ship from another region.
- `scripts/manufacturer_availability/import_us_manufacturer_availability.py` is US-only, requires explicit confirmation for apply mode, and protects AU, EU, ID, and `NULL` region counts.
- USA Azure Container Apps Jobs are now live:
  - `quivrr-us-mfr-availability` at `0 21 * * *`
  - `quivrr-nightly-us-inventory` at `30 21 * * *`
- The current live SQL baseline is:
  - `ManufacturerInventory`: 4,141 active US rows across 9 brands
  - `RetailerInventory`: 7,812 active US rows across 20 retailers
- `scripts/run_inventory_link_health_report.py` now reports US beside AU, EU, and ID.
- US remains beta because canonical linking quality is still uneven across several longboard and house-brand retailers even though operations are now live and region-scoped.

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

- US manufacturer direct availability.
- US retailer inventory.
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
