# Europe Retailer Import Scaffold

This folder contains the disabled EU retailer import dry-run scaffold.

## Scope

- Input: `scrapers/retailers/europe/output/eu_normalised_inventory.json`
- Output: `scripts/europe/output/eu_retailer_import_dry_run_report.json`
- Region: `RegionCode = EU`
- Currency: `PriceCurrency = EUR`
- Dry-run is the default
- No `RetailerInventory` writes unless a future run is explicitly approved with `--apply`
- No Azure resources or jobs
- No changes to AU or ID importers

## AU Reference

The AU production path runs through `scripts/run_nightly_inventory_refresh.py`.

Its importer, `scripts/import_retailer_inventory.py`, reads `scrapers/products/output/normalised_surfboards.json`, filters available rows, dedupes listings, maps retailers and brands through SQL, deletes existing retailer inventory, and inserts rows into `RetailerInventory`.

The EU scaffold mirrors the decision points without connecting to SQL:

- retailer mapping simulation
- brand mapping simulation from local seed data
- model mapping simulation from local catalogue outputs
- duplicate handling
- region and currency validation
- import readiness metrics

Raw retailer inventory can be importable even when canonical brand or model matching is incomplete. Canonical matching is reported separately through:

- `canonicalBrandMatched`
- `canonicalModelMatched`
- `matchedBrandName`
- `matchedModelName`
- `matchConfidence`
- `reviewReason`

Rows with complete raw retail data are marked `importableRaw: true`. Rows with unknown brands or models are marked `needsCanonicalReview: true` instead of being rejected.

True rejects are reserved for missing or invalid raw import fields, including missing URL, missing title, missing price, missing stock status, missing all dimensions, wrong region, or wrong currency.

## Discovery And Normalisation

Run the non-production EU discovery orchestration and normalisation:

```powershell
venv\Scripts\python.exe scrapers\retailers\europe\run_eu_retailer_discovery.py
```

This refreshes ignored discovery output files and writes:

```text
scrapers/retailers/europe/output/eu_normalised_inventory.json
```

## Dry Run Import

Run against all EU rows:

```powershell
venv\Scripts\python.exe scripts\europe\import_eu_retailer_inventory.py
```

Or narrow to one retailer:

```powershell
venv\Scripts\python.exe scripts\europe\import_eu_retailer_inventory.py --retailer board_exchange
```

The importer is dry-run by default. `--apply` performs idempotent EU-only upserts,
rejects non-EU or non-EUR input, and rolls back if protected AU or ID inventory
counts change during the transaction.

For the validated 58 Surf and Pukas combined input:

```powershell
venv\Scripts\python.exe scripts\europe\import_eu_retailer_inventory.py --apply
```

## Priority Retailer Audit

Run the file-only diagnostics after discovery and importer dry-run:

```powershell
venv\Scripts\python.exe scripts\europe\audit_eu_retailer_inventory.py
```

Add `--sql-read-only --expected-au <count> --expected-id <count>` during controlled
validation to report linked model/size rows and fail if either protected region count changes.

## Report

The dry-run report includes:

- raw importable rows
- canonical matched rows
- rows needing canonical review
- true rejects
- unknown brands
- unknown models
- missing dimensions
- missing prices
- duplicate rows removed
- review reason counts
- sample importable and review rows
- readiness recommendation

## Future SQL Importer Path

Before enabling SQL writes:

- decide EU brand alias rules
- decide whether retailer models must match canonical `BoardModels`
- clean model names generated from retailer titles
- use `PriceAmount` and `PriceCurrency`, not `PriceAud`
- preserve `RegionCode = EU`
- avoid deleting AU or ID inventory
- use idempotent upsert keys based on retailer slug, product URL, raw title, length, and volume
