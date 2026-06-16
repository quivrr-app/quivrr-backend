# EU Structured/custom Discovery

Discovery-only scaffold for EU structured/custom surfboard retailers.

## Targets

- Surf Pirates (`surf_pirates`)
- Surfshop Deutschland (`surfshop_deutschland`) is disabled and deferred because current testing returns Cloudflare managed challenge markers.

## Run

```powershell
venv\Scripts\python.exe scrapers\retailers\europe\custom\discover_eu_custom_products.py --run-enabled --target surf_pirates --max-pages 1
```

To confirm a disabled Cloudflare target without bypassing it:

```powershell
venv\Scripts\python.exe scrapers\retailers\europe\custom\discover_eu_custom_products.py --confirm-blocked --target surfshop_deutschland
```

Output stays under `scrapers/retailers/europe/custom/output/`. No SQL writes, `RetailerInventory` writes, Azure changes, or production scraper activation are performed.

Cloudflare challenge pages are recorded as `blocked_by_cloudflare`; the script does not use stealth plugins, CAPTCHA solving, or challenge workarounds.
