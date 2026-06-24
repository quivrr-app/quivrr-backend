# US Retailer Discovery

## RegionCode

`RegionCode = US`

US means United States fulfilment. US rollout work must stay region-scoped and must not mutate AU, EU, or ID logic.

## Current State

This folder is the USA Phase 1 Gen 3 scaffold. It follows the EU regional structure closely, but it is discovery-only in this phase.

Phase 1 currently enables only retailers that fit the existing lightweight regional Shopify path safely. WooCommerce, BigCommerce, blocked, or opaque retailers are documented in the target registry but remain disabled until a reviewed regional adapter path is available.

There is no production US SQL importer or deployment step enabled from this scaffold.

## Implemented Retailer Paths

- Shopify discovery:
  `scrapers/retailers/usa/shopify/us_shopify_targets.json`
- WooCommerce discovery scaffold:
  `scrapers/retailers/usa/woocommerce/us_woocommerce_targets.json`
- Master target registry:
  `scrapers/retailers/usa/us_retailer_targets.json`
- Orchestration:
  `scrapers/retailers/usa/run_us_retailer_discovery.py`
- Dry-run scheduled wrapper:
  `scripts/usa/run_us_retailer_inventory_refresh.py`

## Safety Rules

- every accepted row must carry `RegionCode = US`
- US discovery must not default rows to AU
- this scaffold must not apply SQL in Phase 1
- blocked or unsupported retailers stay documented but disabled
