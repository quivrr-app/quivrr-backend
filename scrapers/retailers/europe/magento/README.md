# EU Magento/html Discovery

Discovery-only scaffold for Magento/html EU surfboard retailers.

## Targets

- 58 Surf (`58_surf`)

## Run

```powershell
venv\Scripts\python.exe scrapers\retailers\europe\magento\discover_eu_magento_products.py --run-enabled --target 58_surf
```

Output stays under `scrapers/retailers/europe/magento/output/`. The script does not import to SQL, write `RetailerInventory`, create Azure jobs, or change AU/ID behaviour.

The adapter discovers English category routes from the Surfboards navigation and uses
Adobe Commerce Live Search `current_page`/`page_size` pagination until every category is
exhausted. `--max-pages` is an optional diagnostic cap; the default has no page cap.

Cloudflare challenge pages are recorded as `blocked_by_cloudflare` and are not bypassed.
