# Australia Retailer Qualification

## Scope

Sprint 10 AU Coverage Factory broad triage for Australian dealer and retailer candidates.

This report now covers the wider AU retailer pool rather than a five-retailer shortlist.

## Inputs

- `config/dealer_source_policy.json`
- `scrapers/retailers/retailer_master.json`
- `scrapers/retailers/retailer_scrape_targets_classified.json`
- `scrapers/retailers/retailer_expansion_candidates_au.json`
- `scrapers/retailers/retailer_platform_detection_report.json`
- `docs/dealers/global-dealer-network-discovery.md`

Review date: `2026-06-28`

## AU Coverage Factory Summary

- AU candidates reviewed: `103`
- Already running: `30`
- Duplicate shells: `2`
- Manual review: `46`
- Manual review before discovery: `46`
- AU candidates re-analysed by discovery engine: `65`
- Recommended next pack: `BigCommerce Pack`
- Recommended next individual target: `Trigger Bros Surfboards`

### Classification Summary

- `already_running`: `30`
- `ready_shopify`: `4`
- `ready_woocommerce`: `1`
- `ready_bigcommerce`: `1`
- `ready_custom_high_value`: `9`
- `duplicate_shell`: `2`
- `no_online_boards`: `1`
- `shaper_only`: `2`
- `manual_review`: `46`
- `blocked`: `4`
- `unsupported`: `3`

### Platform Summary

- `bigcommerce`: `1`
- `custom`: `4`
- `magento`: `11`
- `shopify`: `32`
- `squarespace`: `1`
- `unknown`: `44`
- `woocommerce`: `10`

### Pack Group Summary

- `BigCommerce Pack`: `1`
- `Custom High Value Pack`: `9`
- `Duplicate Shells`: `2`
- `Exclude`: `10`
- `Manual Review`: `76`
- `Shopify Pack`: `4`
- `WooCommerce Pack`: `1`

## Already Running

- `Surfboard Empire` | `shopify` | active rows `4944`
- `The Board Lab` | `shopify` | active rows `1438`
- `Wicks Surf` | `shopify` | active rows `1420`
- `Natural Necessity` | `shopify` | active rows `969`
- `Beachin Surf` | `shopify` | active rows `909`
- `Surf Culture Bondi` | `shopify` | active rows `810`
- `Melbourne Surfboard Shop` | `shopify` | active rows `776`
- `Zink Surf` | `shopify` | active rows `610`
- `Onboard Store` | `shopify` | active rows `603`
- `Strapper Surf Torquay` | `woocommerce` | active rows `561`
- `Sanbah Surf Shop` | `shopify` | active rows `494`
- `Sideways Surf` | `shopify` | active rows `470`
- `Classic Malibu` | `woocommerce` | active rows `462`
- `Aloha Surf Manly` | `shopify` | active rows `350`
- `Star Surf and Skate` | `shopify` | active rows `346`
- `Powerhouse Surf` | `shopify` | active rows `210`
- `The Surfboard Warehouse` | `shopify` | active rows `185`
- `Surfection Bondi` | `shopify` | active rows `166`
- `Boards In The Bay` | `shopify` | active rows `150`
- `Noosa Longboards` | `shopify` | active rows `150`
- `NT Surfboards` | `shopify` | active rows `123`
- `Anglesea Surf Centre` | `woocommerce` | active rows `97`
- `Long Reef Surf Co` | `shopify` | active rows `92`
- `Extreme Boardriders` | `woocommerce` | active rows `47`
- `Manly Surfboards` | `woocommerce` | active rows `47`
- `Ocean Addicts` | `woocommerce` | active rows `41`
- `Surf FX` | `shopify` | active rows `33`
- `The Surfboard Studio` | `shopify` | active rows `8`
- `Beach Beat Alexandra Headland` | `woocommerce` | active rows `7`
- `Akwa Surf` | `shopify` | active rows `6`

## Duplicate Shells

- `Red Herring Surf` -> `Board Collective` | Board Collective shell. products.json empty, surfboard search returned zero, and the public shell resolves product links to boardcollective.com.au.
- `Saltwater Wine Port Macquarie` -> `Board Collective` | Board Collective shell. products.json empty, surfboard search returned zero, and the public shell resolves product links to boardcollective.com.au.

## Top 20 Implementation Candidates

| Retailer | Status | Platform | Approx board count | Priority score | Why now |
| --- | --- | --- | --- | --- | --- |
| City Beach | `manual_review` | `magento` | `80` | `96` | Keep in manual review until an AU-local inventory surface is confirmed. |
| Trigger Bros Surfboards | `ready_bigcommerce` | `bigcommerce` | `80` | `92` | Implement as the BigCommerce reference target and validate in Azure before adding more AU BigCommerce stores. |
| Overboard Surf | `ready_shopify` | `shopify` | `41` | `85` | Candidate for reusable AU Shopify onboarding. |
| Goodtime Surfboards | `ready_custom_high_value` | `magento` | `70` | `83` | Treat as a high-value custom follow-up after the BigCommerce pack, not before it. |
| Surf Boardroom | `ready_woocommerce` | `woocommerce` | `200` | `72` | Keep in the WooCommerce pack. Board surface is real, but parser work is still needed. |
| AWSM Surf | `ready_shopify` | `shopify` | `29` | `70` | Candidate for reusable AU Shopify onboarding. |
| Surf Shops Australia | `manual_review` | `unknown` | `0` | `55` | Keep in manual review until a clean public AU surfboard surface is reconfirmed. |
| Underground Surf | `ready_shopify` | `shopify` | `14` | `46` | Candidate for reusable AU Shopify onboarding. |
| Bells Beach Surf Shop | `manual_review` | `unknown` | `0` | `40` | No board inventory surface confirmed. Keep in manual review. |
| Groove Surf | `manual_review` | `unknown` | `0` | `40` | No board inventory surface confirmed. Keep in manual review. |
| Beach Life Margaret River | `manual_review` | `unknown` | `0` | `37` | No board inventory surface confirmed. Keep in manual review. |
| Big Drop Surf | `manual_review` | `unknown` | `0` | `37` | No board inventory surface confirmed. Keep in manual review. |
| Big Surf | `manual_review` | `unknown` | `0` | `37` | No board inventory surface confirmed. Keep in manual review. |
| Board Store | `manual_review` | `unknown` | `0` | `37` | No board inventory surface confirmed. Keep in manual review. |
| Boardriders Coolangatta | `manual_review` | `unknown` | `0` | `37` | No board inventory surface confirmed. Keep in manual review. |
| Boardriders Torquay | `manual_review` | `unknown` | `0` | `37` | No board inventory surface confirmed. Keep in manual review. |
| Byron Bay Surf Company | `manual_review` | `unknown` | `0` | `37` | No board inventory surface confirmed. Keep in manual review. |
| Byron Bay Surfboard Co | `manual_review` | `unknown` | `0` | `37` | No board inventory surface confirmed. Keep in manual review. |
| Cordingley's Surf | `manual_review` | `woocommerce` | `0` | `37` | No board inventory surface confirmed. Keep in manual review. |
| Corner Surf Shop | `manual_review` | `unknown` | `0` | `37` | No board inventory surface confirmed. Keep in manual review. |

## Top 10 Custom / High-Value Candidates

| Retailer | Status | Platform | Priority score | Notes |
| --- | --- | --- | --- | --- |
| City Beach | `manual_review` | `magento` | `96` | non_au_catalogue_surface |
| Goodtime Surfboards | `ready_custom_high_value` | `magento` | `83` | Large retailer signal, but current path is noisy and protected. Better as the next custom target once the coverage factory lands. |
| Surf Shops Australia | `manual_review` | `unknown` | `55` | Earlier BigCommerce surfboard hints were not reconfirmed by the discovery engine, so this should not be promoted into the AU BigCommerce pack yet. |
| Bells Beach Surf Shop | `manual_review` | `unknown` | `40` | no_board_category_or_product_surface |
| Groove Surf | `manual_review` | `unknown` | `40` | no_board_category_or_product_surface |
| Beach Life Margaret River | `manual_review` | `unknown` | `37` | no_board_category_or_product_surface |
| Big Drop Surf | `manual_review` | `unknown` | `37` | no_board_category_or_product_surface |
| Big Surf | `manual_review` | `unknown` | `37` | no_board_category_or_product_surface |
| Board Store | `manual_review` | `unknown` | `37` | no_board_category_or_product_surface |
| Boardriders Coolangatta | `manual_review` | `unknown` | `37` | no_board_category_or_product_surface |

## Recommendation

- Next pack: `BigCommerce Pack`
  Why: Trigger Bros remains the one clean, discovery-confirmed AU BigCommerce surfboard surface, so it is still the strongest reusable reference path.
- Next individual target: `Trigger Bros Surfboards`
  Why: strongest remaining retailer-distinct AU target with visible live board inventory, pricing, imagery and reusable platform signals.
- Keep `Surf Shops Australia` in manual review until a fresh AU board surface is reconfirmed.
- Hold `Goodtime Surfboards` as the next high-value custom follow-up.
- Keep `Surf Boardroom` inside the WooCommerce pack rather than treating it as a standalone custom scraper.

## Full AU Candidate Table

| Dealer | Website | Running | Duplicate of | Status | Platform | Online boards visible | Approx board count | Supported brand signals | Category URL | Example product URLs | Price visible | Stock visible | Images visible | Pagination | Difficulty | Priority score | Recommended action | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Surfboard Empire | `https://surfboardempire.com.au` | `true` |  | `already_running` | `shopify` | `true` | `4944` | Channel Islands |  |  | `true` | `true` | `true` | `false` | `low` | `99` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| The Board Lab | `https://theboardlab.com.au` | `true` |  | `already_running` | `shopify` | `true` | `1438` |  |  |  | `true` | `true` | `true` | `false` | `low` | `57` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Wicks Surf | `https://wickssurf.com.au` | `true` |  | `already_running` | `shopify` | `true` | `1420` |  |  |  | `true` | `true` | `true` | `false` | `low` | `57` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Natural Necessity | `https://naturalnecessity.com.au` | `true` |  | `already_running` | `shopify` | `true` | `969` | Channel Islands, Christenson |  |  | `true` | `true` | `true` | `false` | `low` | `52` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Beachin Surf | `https://beachinsurf.com.au` | `true` |  | `already_running` | `shopify` | `true` | `909` |  |  |  | `true` | `true` | `true` | `false` | `low` | `51` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Surf Culture Bondi | `https://surfculture.com.au` | `true` |  | `already_running` | `shopify` | `true` | `810` |  |  |  | `true` | `true` | `true` | `false` | `low` | `50` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Melbourne Surfboard Shop | `https://melbournesurfboardshop.com.au` | `true` |  | `already_running` | `shopify` | `true` | `776` |  |  |  | `true` | `true` | `true` | `false` | `low` | `49` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Onboard Store | `https://onboardstore.com.au` | `true` |  | `already_running` | `shopify` | `true` | `603` | Channel Islands |  |  | `true` | `true` | `true` | `false` | `low` | `47` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Strapper Surf Torquay | `https://strapper.com.au` | `true` |  | `already_running` | `woocommerce` | `true` | `561` |  |  |  | `true` | `true` | `true` | `false` | `low` | `47` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Zink Surf | `https://zinksurf.com.au` | `true` |  | `already_running` | `shopify` | `true` | `610` |  |  |  | `true` | `true` | `true` | `false` | `low` | `47` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Sanbah Surf Shop | `https://sanbah.com` | `true` |  | `already_running` | `shopify` | `true` | `494` |  |  |  | `true` | `true` | `true` | `false` | `low` | `46` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Classic Malibu | `https://classicmalibu.com` | `true` |  | `already_running` | `woocommerce` | `true` | `462` |  |  |  | `true` | `true` | `true` | `false` | `low` | `45` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Sideways Surf | `https://sideways.com.au` | `true` |  | `already_running` | `shopify` | `true` | `470` |  |  |  | `true` | `true` | `true` | `false` | `low` | `45` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Aloha Surf Manly | `https://alohasurfmanly.com` | `true` |  | `already_running` | `shopify` | `true` | `350` |  |  |  | `true` | `true` | `true` | `false` | `low` | `44` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Star Surf and Skate | `https://starsurf.com.au` | `true` |  | `already_running` | `shopify` | `true` | `346` |  |  |  | `true` | `true` | `true` | `false` | `low` | `44` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Powerhouse Surf | `https://powerhousesurf.com.au` | `true` |  | `already_running` | `shopify` | `true` | `210` |  |  |  | `true` | `true` | `true` | `false` | `low` | `42` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Surfection Bondi | `https://surfection.com` | `true` |  | `already_running` | `shopify` | `true` | `166` |  |  |  | `true` | `true` | `true` | `false` | `low` | `42` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| The Surfboard Warehouse | `https://thesurfboardwarehouse.com.au` | `true` |  | `already_running` | `shopify` | `true` | `185` |  |  |  | `true` | `true` | `true` | `false` | `low` | `42` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Anglesea Surf Centre | `https://www.angleseasurfcentre.com.au` | `true` |  | `already_running` | `woocommerce` | `true` | `97` |  |  |  | `true` | `true` | `true` | `false` | `low` | `41` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Boards In The Bay | `https://boardsinthebay.com.au` | `true` |  | `already_running` | `shopify` | `true` | `150` |  |  |  | `true` | `true` | `true` | `false` | `low` | `41` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Long Reef Surf Co | `https://longreefsurf.com.au` | `true` |  | `already_running` | `shopify` | `true` | `92` |  |  |  | `true` | `true` | `true` | `false` | `low` | `41` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Noosa Longboards | `https://noosalongboards.com` | `true` |  | `already_running` | `shopify` | `true` | `150` |  |  |  | `true` | `true` | `true` | `false` | `low` | `41` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| NT Surfboards | `https://ntsurfboards.com` | `true` |  | `already_running` | `shopify` | `true` | `123` | Dark Arts |  |  | `true` | `true` | `true` | `false` | `low` | `41` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Akwa Surf | `https://akwasurf.com.au` | `true` |  | `already_running` | `shopify` | `true` | `6` |  |  |  | `true` | `true` | `true` | `false` | `low` | `40` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Beach Beat Alexandra Headland | `https://beachbeat.com.au` | `true` |  | `already_running` | `woocommerce` | `true` | `7` | Channel Islands |  |  | `true` | `true` | `true` | `false` | `low` | `40` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Extreme Boardriders | `https://extremeboardriders.com.au` | `true` |  | `already_running` | `woocommerce` | `true` | `47` |  |  |  | `true` | `true` | `true` | `false` | `low` | `40` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Manly Surfboards | `https://manlysurfboards.com.au` | `true` |  | `already_running` | `woocommerce` | `true` | `47` |  |  |  | `true` | `true` | `true` | `false` | `low` | `40` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Ocean Addicts | `https://oceanaddicts.com.au` | `true` |  | `already_running` | `woocommerce` | `true` | `41` |  |  |  | `true` | `true` | `true` | `false` | `low` | `40` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Surf FX | `https://surffx.com.au` | `true` |  | `already_running` | `shopify` | `true` | `33` |  |  |  | `true` | `true` | `true` | `false` | `low` | `40` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| The Surfboard Studio | `https://www.thesurfboardstudio.com.au` | `true` |  | `already_running` | `shopify` | `true` | `8` |  |  |  | `true` | `true` | `true` | `false` | `low` | `40` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Overboard Surf | `https://overboardsurf.com.au` | `false` |  | `ready_shopify` | `shopify` | `true` | `41` | JS Industries, Channel Islands, Firewire, Chilli, DHD | https://overboardsurf.com.au/collections/boards-7s-surfboards | https://overboardsurf.com.au/collections/surf-hardware-surfboard-covers/day-covers, https://overboardsurf.com.au/collections/surf-hardware-surfboard-covers/soft-covers | `true` | `true` | `true` | `true` | `medium` | `85` | Candidate for reusable AU Shopify onboarding. | https://overboardsurf.com.au/products.json?limit=1 |
| AWSM Surf | `https://awsmsurf.com` | `false` |  | `ready_shopify` | `shopify` | `true` | `29` | Channel Islands, JS Industries, Lost | https://www.awsmsurf.com/collections/second-hand-surfboard | https://www.awsmsurf.com/collections/second-hand-surfboard/products/secondlightsurfboardshapedbyrichardevans68, https://www.awsmsurf.com/cdn/shop/products/9b851f1612b5ebc40d4d14e0e38c7bb61c799d3d_2048x.jpg?v=1547178389 | `true` | `true` | `true` | `true` | `medium` | `70` | Candidate for reusable AU Shopify onboarding. | https://www.awsmsurf.com/products.json?limit=1 |
| Underground Surf | `https://undergroundsurf.com.au` | `false` |  | `ready_shopify` | `shopify` | `true` | `14` | Channel Islands, JS Industries | https://www.undergroundsurf.com.au/collections/surfboards-1 | https://www.undergroundsurf.com.au/collections/surfboards-1, https://www.undergroundsurf.com.au/collections/surfboard-hire | `true` | `true` | `true` | `true` | `medium` | `46` | Candidate for reusable AU Shopify onboarding. | https://www.undergroundsurf.com.au/products.json?limit=1 |
| Surf Dive n Ski | `https://www.sds.com.au` | `false` |  | `ready_shopify` | `shopify` | `true` | `11` | JS Industries | https://www.sds.com.au/collections/boys-boardshorts | https://www.sds.com.au/collections/boys-boardshorts, https://www.sds.com.au/collections/boys-printed-boardshorts | `true` | `true` | `true` | `true` | `medium` | `34` | Candidate for reusable AU Shopify onboarding. | https://www.sds.com.au/products.json?limit=1 |
| Surf Boardroom | `https://surfboardroom.com.au` | `false` |  | `ready_woocommerce` | `woocommerce` | `true` | `200` | Firewire, Channel Islands | https://surfboardroom.com.au/surfboards/ |  | `false` | `true` | `true` | `false` | `medium` | `72` | Keep in the WooCommerce pack. Board surface is real, but parser work is still needed. | Boards are visible and the WooCommerce path is real, but the current extraction path undershoots and needs parser recovery. |
| Trigger Bros Surfboards | `https://triggerbrothers.com.au` | `false` |  | `ready_bigcommerce` | `bigcommerce` | `true` | `80` | supported multi-brand surf retailer | https://triggerbrothers.com.au/store/surf/used-surfboards/ | https://triggerbrothers.com.au/trigger-bros-x-dos-lumberjack-6ft-surfboard/, https://triggerbrothers.com.au/trigger-bros-hot-dog-stubby-9ft-surfboard-red/ | `true` | `true` | `true` | `true` | `medium` | `92` | Implement as the BigCommerce reference target and validate in Azure before adding more AU BigCommerce stores. | Best current AU next target. Live BigCommerce site with visible board inventory and reusable platform path. |
| Goodtime Surfboards | `https://www.goodtime.com.au` | `false` |  | `ready_custom_high_value` | `magento` | `true` | `70` | long-running AU surfboard retailer | https://www.goodtime.com.au |  | `true` | `true` | `true` | `true` | `high` | `83` | Treat as a high-value custom follow-up after the BigCommerce pack, not before it. | Large retailer signal, but current path is noisy and protected. Better as the next custom target once the coverage factory lands. |
| Surfers Choice Surf Shop | `https://surferschoice.com.au` | `false` |  | `ready_custom_high_value` | `custom` | `true` | `13` | Channel Islands, JS Industries, DHD, Haydenshapes | https://www.surferschoice.com.au/jr-surfboards.html | https://www.surferschoice.com.au/skimboards.html, https://www.surferschoice.com.au/boards.html | `true` | `true` | `true` | `false` | `medium` | `37` | Candidate for a targeted high-value custom implementation after pack work. | Detected custom catalogue-like HTML surface |
| Manly Surf Guide Surfboard Outlet | `https://manlysurfguide.com.au` | `false` |  | `ready_custom_high_value` | `magento` | `true` | `15` | JS Industries | http://www.manlysurfguide.com.au/shop/soft-surfboards-sale | https://www.manlysurfguide.com.au/shop/soft-surfboards-sale, https://www.manlysurfguide.com.au/shop/soft-surfboards/6ft-soft-surfboard | `true` | `true` | `true` | `false` | `medium` | `34` | Candidate for a targeted high-value custom implementation after pack work. | Detected magento markers in HTML |
| Island Surfboards | `https://www.islandsurfboards.com.au` | `false` |  | `ready_custom_high_value` | `magento` | `true` | `8` | Channel Islands, JS Industries | https://www.islandsurfboards.com.au/islandperformancecoaching | https://www.islandsurfboards.com.au/surfboards, https://www.islandsurfboards.com.au/surfboards/slop-rocket | `true` | `true` | `true` | `false` | `medium` | `30` | Candidate for a targeted high-value custom implementation after pack work. | Detected magento markers in HTML |
| Empire Ave | `https://empireave.com` | `false` |  | `ready_custom_high_value` | `magento` | `true` | `3` | JS Industries, DHD, Channel Islands | https://empireave.com/goods-guides/buyers-guides/fish-surfboards-a-guide/ | https://empireave.com/tag/carbotune/, https://empireave.com/interviews/talking-grips-softboards-and-dhd-with-modom/ | `true` | `true` | `true` | `true` | `medium` | `28` | Candidate for a targeted high-value custom implementation after pack work. | Detected magento markers in HTML |
| World Surfaris Surf Shop | `https://worldsurfaris.com` | `false` |  | `ready_custom_high_value` | `custom` | `true` | `7` | JS Industries | https://worldsurfaris.com/surfboards-rent-hudhuranfushi/ | https://worldsurfaris.com/surfboards-rent-hudhuranfushi/, https://worldsurfaris.com/region/maldives/ | `true` | `true` | `true` | `false` | `medium` | `22` | Candidate for a targeted high-value custom implementation after pack work. | Detected custom catalogue-like HTML surface |
| Soul Boardstore | `https://www.soulboardstore.com.au` | `false` |  | `ready_custom_high_value` | `custom` | `true` | `1` | JS Industries | https://www.soulboardstore.com.au/index.html | https://www.soulboardstore.com.au/online-shop/contact-us-product-range.html | `true` | `true` | `true` | `false` | `medium` | `16` | Candidate for a targeted high-value custom implementation after pack work. | Detected custom catalogue-like HTML surface |
| Slimes Boardstore | `https://slimes.com.au` | `false` |  | `ready_custom_high_value` | `magento` | `true` | `3` | Channel Islands, JS Industries | https://www.slimes.com.au/surfboards | https://www.slimes.com.au/surfboards, https://www.slimes.com.au/softboards | `true` | `true` | `true` | `false` | `medium` | `13` | Candidate for a targeted high-value custom implementation after pack work. | Detected magento markers in HTML |
| Coopers Surf | `https://cooperssurf.com.au` | `false` |  | `ready_custom_high_value` | `magento` | `true` | `3` | JS Industries | https://cooperssurf.com.au/product/outerknown-journey-fish-5-panel-hat/ | https://cooperssurf.com.au/product/outerknown-journey-fish-5-panel-hat/, https://cooperssurf.com.au/product-tag/js-industries-apparel/ | `true` | `true` | `true` | `false` | `medium` | `12` | Candidate for a targeted high-value custom implementation after pack work. | Detected magento markers in HTML |
| Red Herring Surf | `https://redherringsurf.com.au` | `false` | Board Collective | `duplicate_shell` | `shopify` | `false` | `0` | JS Industries, Pyzel, Firewire | https://redherringsurf.com.au/collections/all | https://boardcollective.com.au/products/boardcollective-egift-card | `false` | `false` | `true` | `false` | `low` | `0` | Exclude from AU onboarding and keep Board Collective as the inventory source. | Board Collective shell. products.json empty, surfboard search returned zero, and the public shell resolves product links to boardcollective.com.au. |
| Saltwater Wine Port Macquarie | `https://saltwaterwine.com.au` | `false` | Board Collective | `duplicate_shell` | `shopify` | `false` | `0` | JS Industries, Pyzel, Firewire, Channel Islands | https://saltwaterwine.com.au/collections/all | https://boardcollective.com.au/products/boardcollective-egift-card | `false` | `false` | `true` | `false` | `low` | `0` | Exclude from AU onboarding and keep Board Collective as the inventory source. | Board Collective shell. products.json empty, surfboard search returned zero, and the public shell resolves product links to boardcollective.com.au. |
| Full Circle Surf | `https://fullcirclesurf.com.au` | `false` |  | `no_online_boards` | `squarespace` | `false` | `0` | JS Industries, Firewire |  |  | `false` | `false` | `false` | `false` | `medium` | `10` | Do not implement until a working surfboard storefront is confirmed. | Known retailer, but the current public storefront is broken and not a usable AU inventory source. |
| JS Industries | `https://jsindustries.com` | `false` |  | `shaper_only` | `shopify` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `low` | `5` | Exclude from retailer inventory and leave to canonical / MFA paths. | https://jsindustries.com/products.json?limit=1 |
| Ocean & Earth Store | `https://oceanandearth.com.au` | `false` |  | `shaper_only` | `shopify` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `low` | `0` | Exclude from retailer inventory and leave to canonical / MFA paths. | https://oceanandearth.com.au/products.json?limit=1 |
| City Beach | `https://www.citybeach.com` | `false` |  | `manual_review` | `magento` | `true` | `80` | Channel Islands, JS Industries | https://www.citybeach.com/us/kids/boardsports/ | https://www.citybeach.com/us/kids/, https://www.citybeach.com/us/kids/boardsports/#A | `true` | `false` | `true` | `false` | `medium` | `96` | Keep in manual review until an AU-local inventory surface is confirmed. | non_au_catalogue_surface |
| Surf Shops Australia | `https://surfshopsaustralia.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` | broad surfboard catalogue |  |  | `false` | `false` | `false` | `false` | `medium` | `55` | Keep in manual review until a clean public AU surfboard surface is reconfirmed. | Earlier BigCommerce surfboard hints were not reconfirmed by the discovery engine, so this should not be promoted into the AU BigCommerce pack yet. |
| Bells Beach Surf Shop | `https://bellsbeachsurfshop.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `40` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Groove Surf | `https://groovesurf.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `40` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Beach Life Margaret River | `https://beachlifemargs.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Big Drop Surf | `https://bigdropsurf.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` | Channel Islands |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Big Surf | `https://bigsurf.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` | Channel Islands |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Board Store | `https://boardstore.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Boardriders Coolangatta | `https://boardriders.co` | `false` |  | `manual_review` | `unknown` | `false` | `0` | Channel Islands |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Boardriders Torquay | `https://boardriders.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Byron Bay Surf Company | `https://byronbaysurfcompany.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Byron Bay Surfboard Co | `https://www.byronbaysurfboardco.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Cordingley's Surf | `https://cordingleyssurf.com.au` | `false` |  | `manual_review` | `woocommerce` | `false` | `0` | Channel Islands |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Corner Surf Shop | `https://cornersurfshop.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` | Channel Islands |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Cronulla Surf Design | `https://cronullasurfdesign.com.au` | `false` |  | `manual_review` | `shopify` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Drift Surf | `https://www.driftsurf.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Dripping Wet Surf Co | `https://drippingwetsurf.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Hollow Surf | `https://hollowsurf.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` | Channel Islands |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Innertube Surf Shop | `https://innertubesurf.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` | Channel Islands |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Pittwater Surf | `https://www.pittwatersurf.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Pittwater Surfboards | `https://pittwatersurfboards.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Second Surf | `https://secondsurf.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Sessions Surf Shop | `https://sessionssurfshop.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Surfboard Agency | `https://surfboardagency.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Yallingup Surf Shop | `https://yallingupsurf.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  | https://yallingupsurf.com.au/collections/surfboards |  | `false` | `false` | `false` | `false` | `medium` | `37` | Board categories found, but product inventory could not be confirmed safely. | board_categories_found_no_products |
| Action Board Sports | `https://actionboardsports.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Apollo Bay Surf Shop | `https://apollobaysurfshop.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Blue Planet Surf | `https://blueplanetsurf.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Board Hub | `https://boardhub.com.au` | `false` |  | `manual_review` | `magento` | `false` | `0` |  | https://boardhub.com.au/surfboards/shortboards |  | `false` | `false` | `false` | `false` | `medium` | `34` | Board categories found, but product inventory could not be confirmed safely. | board_categories_found_no_products |
| Coogee Surf Co | `https://coogeesurfco.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| CPS Surf | `https://cpssurf.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Harbour Surfboards | `https://harboursurfboards.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Le Spot Surf Shop | `https://lespotsurfshop.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Maroubra Surf and Skate | `https://maroubrasurfandskate.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Mid Coast Surf | `https://midcoastsurf.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  | https://midcoastsurf.com.au/collections/surfboards |  | `false` | `false` | `false` | `false` | `medium` | `34` | Board categories found, but product inventory could not be confirmed safely. | board_categories_found_no_products |
| Murray Smith Surf Warehouse | `https://murraysmithsurfwarehouse.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| North Coast Surf | `https://northcoastsurf.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Ocean Grove Surf Co | `https://oceangrovesurfco.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| On A Wave Surf Shop | `https://onawavesurfshop.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Prahran Surfboards | `https://prahransurfboards.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Secret Harbour Surf | `https://secretharboursurf.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Shed Nine | `https://shednine.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Surf Connect | `https://www.surfconnect.com` | `false` |  | `manual_review` | `custom` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Surf Warehouse | `https://surfwarehouse.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Surfection Mosman | `https://www.surfectionmosman.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Yorkes Surf | `https://yorkessurf.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Boardcave | `https://www.boardcave.com.au` | `false` |  | `blocked` | `magento` | `false` | `0` | large Australian surfboard marketplace |  |  | `false` | `false` | `false` | `false` | `high` | `35` | Keep blocked. Revisit only if Boardcave exposes a safe public inventory path. | High-value marketplace signal, but current access is blocked and not safe for AU nightly onboarding. |
| Kirra Surf | `https://kirrasurf.com.au` | `false` |  | `blocked` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `low` | `15` | Keep blocked until the site exposes a safe public inventory surface. | request_blocked |
| Triple Bull Surf and Skate | `https://triplebull.com.au` | `false` |  | `blocked` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `low` | `12` | Keep blocked until the site exposes a safe public inventory surface. | request_blocked |
| Three Stories | `https://www.threestories.com.au` | `false` |  | `blocked` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `low` | `9` | Keep blocked until the site exposes a safe public inventory surface. | request_blocked |
| Beaches Apparel | `https://beachesapparel.com` | `false` |  | `unsupported` | `woocommerce` | `false` | `5` |  |  |  | `false` | `false` | `false` | `false` | `low` | `0` | Exclude from AU hardboard onboarding. | Clothing/apparel store, not suitable for Quivrr hardboard retailer inventory |
| Ocean and Earth | `https://oceanearthstore.com` | `false` |  | `unsupported` | `magento` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `low` | `0` | Exclude from AU hardboard onboarding. | Brand/accessory store, not suitable for Quivrr hardboard retailer inventory |
| Rip Curl Australia | `https://www.ripcurl.com/au` | `false` |  | `unsupported` | `magento` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `low` | `0` | Exclude from AU hardboard onboarding. | Does not sell hardboard surfboard inventory online for Quivrr search |
