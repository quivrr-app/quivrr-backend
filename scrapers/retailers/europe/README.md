# Quivrr Europe Retailer Onboarding

## Region And Currency

- `RegionCode = EU`
- `PriceCurrency = EUR`
- UK is excluded. UK fulfilment must use `RegionCode = UK` and must not be grouped into EU.

EU means the mainland European Union fulfilment market. Country values such as Portugal, Spain, France, Germany, and the Netherlands are source metadata, not primary `RegionCode` values.

## Current State

This folder is an active EU regional rollout workspace with live retailer discovery, guarded SQL import paths, and production Azure jobs.

EU remains region-scoped and must still be validated separately for retailer relevance, shipping, tax, duty, currency, and data quality, but it is no longer just a scaffold. AU remains the production reference implementation for rollout process.

## Top 20 Targets

| Retailer | Country | Priority | Surfboard category |
| --- | --- | --- | --- |
| Mundo Surf | Spain | Wave 1 | https://www.mundo-surf.com/en/45-surfboards |
| Single Quiver | Spain | Wave 1 | https://www.singlequiver.com/en/surfboards/ |
| Pukas Surf Shop | Spain | Wave 1 | https://pukassurfshop.com/ |
| Full & Cas | Spain | Wave 1 | https://www.fullandcas.com/ |
| Tablas Surf Shop | Spain | Wave 1 | https://www.tablassurfshop.com/ |
| 58 Surf | Portugal | Wave 1 | https://58surf.com/prt/surfboards |
| Bell Surf | Portugal | Wave 1 | https://bellsurf.com/collections/surfboards |
| Board Exchange | Portugal | Wave 1 | https://boardexchange.pt/collections/surfboards |
| Guincho Wind Factory | Portugal | Wave 1 | https://www.guinchowindfactory.com/collections/boards-surf |
| Ericeira Surf & Skate | Portugal | Wave 1 | https://www.ericeirasurfskate.pt/ |
| Deeply | Portugal | Wave 2 | https://deeply.com/ |
| HawaiiSurf | France | Wave 1 | https://www.hawaiisurf.com/ |
| Glisshop | France | Wave 2 | https://www.glisshop.com/ |
| Flysurf | France | Wave 2 | https://www.flysurf.com/ |
| Surfshop.fr | France | Wave 2 | https://www.surfshop.fr/ |
| Hart Beach | Netherlands | Wave 1 | https://hartbeach.nl/collections/surfboards |
| Warehouse One | Germany | Wave 2 | https://www.warehouse-one.de/ |
| SantoLoco | Germany | Wave 2 | https://www.santoloco.com/ |
| Surf Pirates | Germany | Wave 2 | https://www.surfpirates.de/en/surfbords |
| Blue Tomato | EU / Austria / Germany fulfilment | Wave 2 | https://www.blue-tomato.com/ |

The source register is `eu_retailer_targets.json`. Retailers remain disabled until reviewed and explicitly activated, but multiple Wave 1 targets are already live in the current EU runtime.

## Discovery Tooling

Run discovery from the backend repository root only when a light external fetch is intended:

```powershell
venv\Scripts\python.exe scrapers/retailers/europe/discover_eu_retailer_platforms.py
```

The script reads:

- `scrapers/retailers/europe/eu_retailer_targets.json`

It writes discovery output only:

- `scrapers/retailers/europe/output/eu_retailer_discovery.json`

The discovery script does not import to SQL, write production tables, create Azure resources, or enable retailer scrapers.

## Wave 1 Platform Groups

Shopify discovery is kept under `shopify/`. Additional disabled discovery adapters are grouped by source platform:

| Platform | Folder | Retailers |
| --- | --- | --- |
| WooCommerce | `woocommerce/` | Surf Boss |
| PrestaShop | `prestashop/` | Mundo Surf, Single Quiver |
| Magento/html | `magento/` | 58 Surf |
| Structured/custom | `custom/` | Surf Pirates |
| Cloudflare deferred | `custom/` | Surfshop Deutschland |

Each adapter writes only to its own ignored `output/` folder and is discovery-only. The output shape is intended to remain compatible with future generic EU normalisation, but no SQL importer or `RetailerInventory` write path is enabled here.

## Cloudflare Handling Policy

Do not attempt to bypass CAPTCHA, Cloudflare managed challenges, browser integrity checks, or anti-bot protection. If a site returns challenge markers such as `Just a moment`, `__cf_chl`, `cf_chl`, or `Enable JavaScript and cookies to continue`, record `blocked_by_cloudflare` with the URL, HTTP status, and short reason, then stop.

Allowed fallback paths are official public APIs, `sitemap.xml`, robots-allowed URLs, structured JSON-LD already present in public HTML, RSS/product feeds, normal rendering where no challenge is presented, manual review notes, and future retailer partnership/API access.

## Deferred Retailers

- Surfshop Deutschland: deferred because manual research returned Cloudflare managed challenge markers.
- Ericeira Surf & Skate: deferred because the online surfboard catalogue is unclear or unstable from current testing.
- Deeply: deferred/removed from the surfboard wave because the site appears focused on clothing, wetsuits, and accessories rather than surfboard inventory.

## Next Step

After discovery, review Wave 1 platform results and choose the first EU scraper candidates. Any scraper implementation should stay disabled until:

- output fields are reviewed for EU inventory shape
- `RegionCode = EU` is verified
- `PriceCurrency = EUR` or native source currency handling is verified
- UK sources are confirmed excluded
- a non-production import path is explicitly approved

## Generated Output Hygiene

Generated EU output should not be committed unless intentionally promoted to a reviewed fixture or seed file.

Treat these as generated:

- `output/*.json`
- raw downloaded pages
- probe outputs
- temporary inspection files
- local logs
