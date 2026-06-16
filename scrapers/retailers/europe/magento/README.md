# EU Magento/html Discovery

Discovery-only scaffold for Magento/html EU surfboard retailers.

## Targets

- 58 Surf (`58_surf`)

## Run

```powershell
venv\Scripts\python.exe scrapers\retailers\europe\magento\discover_eu_magento_products.py --run-enabled --target 58_surf --max-pages 1
```

Output stays under `scrapers/retailers/europe/magento/output/`. The script does not import to SQL, write `RetailerInventory`, create Azure jobs, or change AU/ID behaviour.

Cloudflare challenge pages are recorded as `blocked_by_cloudflare` and are not bypassed.
