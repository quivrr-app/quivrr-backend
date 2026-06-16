# EU PrestaShop Discovery

Discovery-only scaffold for EU PrestaShop surfboard retailers.

## Targets

- Mundo Surf (`mundo_surf`)
- Single Quiver (`single_quiver`)

## Run

```powershell
venv\Scripts\python.exe scrapers\retailers\europe\prestashop\discover_eu_prestashop_products.py --run-enabled --target mundo_surf --max-pages 1
```

Output stays under `scrapers/retailers/europe/prestashop/output/` and is intended to remain compatible with a future generic EU normalisation step. There are no SQL writes or production imports.

Cloudflare challenge pages are recorded as `blocked_by_cloudflare` and are not bypassed.
