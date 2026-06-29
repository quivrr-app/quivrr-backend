# US Retailer Discovery

## RegionCode

`RegionCode = US`

US means United States fulfilment. US rollout work must stay region-scoped and must not mutate AU, EU, or ID logic.

## Current State

This folder is the USA Gen 3 retailer rollout workspace. It follows the EU regional structure closely and currently supports discovery plus guarded readiness validation.

The current production-ready dry-run set is limited to retailers that fit an existing lightweight regional adapter safely and that now produce validated normalised rows:

- Surf Station
- Jack's Surfboards
- Real Watersports
- Cleanline Surf
- Hawaiian South Shore
- Bird's Surf Shed
- Island Water Sports
- Surf N Sea
- Kimo's Surf Hut
- Moment Surf Co
- Degree 33 Surfboards
- Surfboard Broker
- Infinity Surfboards
- Walden Surfboards
- Stewart Surfboards
- Bing Surfboards
- Robert August Surf Company
- Dark Arts Surf
- Catalyst Surf Shop
- Warm Winds
- Reddog Surf Shop
- Cinnamon Rainbows
- Huntington Surf & Sport

Hansen Surfboards and Encinitas Surfboards remain documented follow-up targets. Their storefronts are reachable, but the existing Shopify adapter does not yet recover safe surfboard rows from their exposed feeds.

WooCommerce, blocked, or opaque retailers remain documented in the target registry but disabled until a reviewed regional adapter path is available.

The US stack now supports guarded apply and live production-beta execution once validation is complete.

## Rollout Summary

Implemented runnable retailers:

- Surf Station
- Jack's Surfboards
- Real Watersports
- Cleanline Surf
- Hawaiian South Shore
- Bird's Surf Shed
- Island Water Sports
- Surf N Sea
- Kimo's Surf Hut
- Moment Surf Co
- Degree 33 Surfboards
- Surfboard Broker
- Infinity Surfboards
- Walden Surfboards
- Stewart Surfboards
- Bing Surfboards
- Robert August Surf Company
- Dark Arts Surf
- Catalyst Surf Shop
- Warm Winds
- Reddog Surf Shop
- Cinnamon Rainbows
- Huntington Surf & Sport

Reviewed but still disabled in the master target registry:

- Ron Jon Surf Shop: blocked by challenge responses during lightweight inspection.
- Hansen Surfboards: Shopify storefront reachable, but current feeds do not yield safe surfboard rows through the existing adapter.
- ET Surf: WooCommerce markers detected, but no safe surfboard category/store API path was confirmed.
- Encinitas Surfboards: board-room path is reachable, but current feeds surface too much non-board merchandise for safe activation.
- Froghouse Surf Shop: no stable supported commerce feed exposed during lightweight inspection.
- Heritage Surf & Sport: WooCommerce Store API is reachable, but lightweight validation did not recover a safe surfboard-only row set.
- 808 Boards: WooCommerce markers were detected, but no safe surfboard inventory path was confirmed.

Backlog candidates captured in `scrapers/retailers/usa/us_retailer_candidate_backlog.json`:

- 42 USA retailer candidates remain in backlog and are region-scoped to `US`.
- Remaining backlog platform split: 11 `shopify`, 2 `woocommerce`, 9 `magento`, 20 `unknown`.
- Remaining backlog detection status split: 18 `needs_review`, 11 `opaque`, 13 `blocked`.
- These backlog entries are intentionally non-runnable until an existing adapter is validated end-to-end or a small isolated US-only adapter is reviewed.

Skipped for this pass:

- Hansen Surfboards and Encinitas Surfboards remain disabled by instruction until a specific extraction path is proven.
- Boardshop UK remains outside the USA rollout and is not part of this regional stack.
- WooCommerce support now includes Store API handling, but no WooCommerce backlog retailer met the promotion bar in this pass.

Expected row uplift from this pass:

- Dry-run baseline before this pass: 5,226 importable rows across 18 runnable retailers.
- Current validated dry-run result: 8,291 importable rows across 23 runnable retailers.
- Net uplift from this pass: +3,065 importable rows.

## Platform Status

- Shopify: config-driven and live for 18 runnable retailers.
- BigCommerce: reusable US adapter now wired into the runner; Catalyst Surf Shop is promoted and validated.
- Magento or category-html: reusable US adapter now wired into the runner; Warm Winds is promoted and validated.
- Custom/high-value: reusable US custom runner now supports Reddog Surf Shop through its public board-inventory pages, Cinnamon Rainbows through Squarespace used-board pages, and Huntington Surf & Sport through its public surfboard stocklist JSON asset.
- WooCommerce: reusable US adapter now supports category and Store API paths, but no backlog retailer was safe to promote in this pass.

## Implemented Retailer Paths

- Shopify discovery:
  `scrapers/retailers/usa/shopify/us_shopify_targets.json`
- BigCommerce discovery:
  `scrapers/retailers/usa/bigcommerce/us_bigcommerce_targets.json`
- Magento discovery:
  `scrapers/retailers/usa/magento/us_magento_targets.json`
- Custom/high-value discovery:
  `scrapers/retailers/usa/custom/us_custom_targets.json`
- WooCommerce discovery scaffold:
  `scrapers/retailers/usa/woocommerce/us_woocommerce_targets.json`
- Master target registry:
  `scrapers/retailers/usa/us_retailer_targets.json`
- Candidate backlog registry:
  `scrapers/retailers/usa/us_retailer_candidate_backlog.json`
- Orchestration:
  `scrapers/retailers/usa/run_us_retailer_discovery.py`
- Dry-run scheduled wrapper:
  `scripts/usa/run_us_retailer_inventory_refresh.py`

## Safety Rules

- every accepted row must carry `RegionCode = US`
- US discovery must not default rows to AU
- this scaffold must not apply SQL without an explicit future importer review
- blocked or unsupported retailers stay documented but disabled
