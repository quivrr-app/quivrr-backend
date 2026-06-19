# Europe Retailer Inventory

This folder contains the active EU retailer inventory importer, audit tools, linkers, and scheduled-job runner.

## Runtime Contract

- Region: `RegionCode = 'EU'`
- Native currency: EUR where price exists
- Dry-run is the default for operational tools where supported
- Apply mode must reject AU, ID, or `NULL` rows
- AU and ID counts are protected before and after EU transactions
- No delete or truncate may affect another region

Active EU retailers are 58 Surf, Pukas, Mundo Surf, Bell Surf, Surf Boss, Surf Corner, and Single Quiver. Discovery and normalization remain under `scrapers/retailers/europe/`; generated outputs are not source files and should not be committed casually.

## Import And Scheduled Runner

Dry run:

```powershell
venv\Scripts\python.exe scripts/europe/import_eu_retailer_inventory.py
venv\Scripts\python.exe scripts/europe/run_eu_retailer_inventory_refresh.py dry-run
```

Apply:

```powershell
venv\Scripts\python.exe scripts/europe/import_eu_retailer_inventory.py --apply
venv\Scripts\python.exe scripts/europe/run_eu_retailer_inventory_refresh.py apply
```

The scheduled runner backs Azure Container Apps Job `quivrr-nightly-eu-inventory`, scheduled at `30 19 * * *`. It uses the existing production image, environment, and secret references and must exit non-zero on AU/ID drift, unexpected EU loss, or `NULL` regions.

## Matching And Diagnostics

Raw retail rows can remain importable while canonical linking is incomplete. Diagnostics report fetched products, likely surfboards, normalized/importable rows, model and size links, and unresolved reasons.

Exact matching accepts equivalent representations:

- fractional and decimal inches
- decimal-comma and decimal-point litres
- bounded width, thickness, and volume differences
- title evidence where canonical IDs are missing

For 58 Surf, the Magento discovery path fetches product-detail attributes. Width, thickness, volume, construction, and fin setup are retained through normalization and SQL import. Exact classification may use equivalent dimensions even when `BoardSizeId` is `NULL` because duplicate equivalent canonical sizes make a unique size link unsafe.

## Region Incident Guardrail

The legacy AU importer once ran an unscoped `DELETE FROM dbo.RetailerInventory` and recreated AU-shaped rows with `NULL` regions. The repaired AU path deletes only `RegionCode = 'AU'` and explicitly inserts AU on every row. Region guardrail tests prevent unscoped deletes and inserts without `RegionCode`; EU work must preserve those protections.

Validated June 2026 `RetailerInventory` baseline: AU 11,746; EU 9,105; ID 1,998; NULL 0.
