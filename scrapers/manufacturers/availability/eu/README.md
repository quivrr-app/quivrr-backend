# EU Manufacturer Direct Availability

EU manufacturer direct availability is active and uses `RegionCode = 'EU'`.

Implemented brands:

- JS Industries
- Pyzel
- Firewire
- Haydenshapes
- Rusty
- Sharp Eye
- DHD

Builders write reviewed brand-specific JSON beneath `scrapers/manufacturers/availability/<brand>/output/`. The orchestrator is `scripts/manufacturer_availability/run_eu_manufacturer_availability_pipeline.py`; the bulk importer is `scripts/manufacturer_availability/import_eu_manufacturer_availability.py`.

```powershell
venv\Scripts\python.exe scripts/manufacturer_availability/run_eu_manufacturer_availability_pipeline.py dry-run
venv\Scripts\python.exe scripts/manufacturer_availability/run_eu_manufacturer_availability_pipeline.py apply
```

The importer batches rows, commits once per brand, and deletes only the target brand where `RegionCode = 'EU'` and `AvailabilitySource = 'manufacturer_direct'`. It must reject AU, ID, and `NULL` regions and non-EUR prices where a price exists.

Manufacturer inventory is regional. Regional `ProductUrl`, image, price, currency, and stock status win. The canonical manufacturer URL is fallback reference metadata only; EU and ID requests must never display AU direct stock or AU URLs.

Example: EU JS Industries Monsta CarboTune 5'11 / 28L returns manufacturer-direct availability in EUR using a `jsindustries.eu` variant URL.

Azure Container Apps Job `quivrr-eu-mfr-availability` runs at `30 20 * * *` using the shared production image, environment, and secret references. It must fail closed on AU/ID drift, unexpected EU loss, invalid availability source/currency, or any `NULL` region.

Validated June 2026 `ManufacturerInventory` baseline: AU 6,498; EU 2,736; ID 185; NULL 0.
