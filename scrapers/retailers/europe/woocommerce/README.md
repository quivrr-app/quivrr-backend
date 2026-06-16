# EU WooCommerce Discovery

Discovery-only scaffold for EU WooCommerce surfboard retailers.

## Targets

- Surf Boss (`surf_boss`)

## Run

Dry run, no network fetches:

```powershell
venv\Scripts\python.exe scrapers\retailers\europe\woocommerce\discover_eu_woocommerce_products.py
```

One reviewed target, one page only:

```powershell
venv\Scripts\python.exe scrapers\retailers\europe\woocommerce\discover_eu_woocommerce_products.py --run-enabled --target surf_boss --max-pages 1
```

The script writes discovery output only under `scrapers/retailers/europe/woocommerce/output/`. It does not import to SQL, write `RetailerInventory`, create Azure resources, or alter AU/ID behaviour.

Cloudflare challenge pages are recorded as `blocked_by_cloudflare` and are not retried aggressively or bypassed.
