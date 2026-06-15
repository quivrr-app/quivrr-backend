# EU Shopify Retailer Discovery

This folder contains disabled Shopify discovery scaffolding for the first EU retailer onboarding candidates.

## Scope

- `RegionCode = EU`
- Default `PriceCurrency = EUR`
- UK is excluded
- Targets are disabled by default
- Discovery output stays under `scrapers/retailers/europe/shopify/output/`
- No SQL imports, Azure jobs, production scraper activation, or AU/ID runtime changes are made from this scaffold

## Targets

The target register is `eu_shopify_targets.json`.

Initial disabled targets:

- Pukas Surf Shop
- Bell Surf
- Board Exchange
- Guincho Wind Factory
- HawaiiSurf
- Hart Beach
- Deeply
- SantoLoco

## Dry Run

By default the script is a dry run. It reads the target file and writes a summary without fetching Shopify products:

```powershell
venv\Scripts\python.exe scrapers\retailers\europe\shopify\discover_eu_shopify_products.py
```

## Enable One Target For Local Testing

Edit `eu_shopify_targets.json` and set exactly one reviewed target to:

```json
"enabled": true
```

Then run:

```powershell
venv\Scripts\python.exe scrapers\retailers\europe\shopify\discover_eu_shopify_products.py --run-enabled --target bell_surf --max-pages 1
```

The `--run-enabled` flag is required before any product fetches happen. The `--target` flag narrows the run to one enabled retailer.

## Output

Discovery writes:

```text
scrapers/retailers/europe/shopify/output/eu_shopify_product_discovery.json
```

For likely surfboard products, the output attempts to capture:

- retailer slug and name
- `regionCode`
- product title and URL
- product image URL
- vendor or brand
- price amount and currency
- variant availability signal
- option names and variant titles
- raw Shopify handle
- suspected surfboard flag
- parse confidence

## Filtering

The script applies conservative filtering for likely surfboards and excludes obvious non-board products such as fins, leashes, wax, traction pads, board bags, wetsuits, clothing, accessories, skateboards, snowboards, soft racks, and bodyboards unless a future reviewed rule explicitly allows them.

## Future Import Path

This discovery output is not an importer input yet. After review, a future EU `RetailerInventory` importer should consume reviewed rows only, preserve `RegionCode = EU`, preserve source pricing as `PriceAmount`, set `PriceCurrency`, and remain separate from AU and ID import behavior.
