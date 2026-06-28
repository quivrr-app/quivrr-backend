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

## Sprint 13 Closeout Position

- `Trigger Bros Surfboards` is live in AU on the reusable BigCommerce path and should now be treated as production validation work, not backlog onboarding.
- `Extreme Boardriders` is live in AU on the reusable WooCommerce path and is the final approved AU closeout retailer from Nathan's latest review.
- `AWSM Surf` may keep its existing live second-hand rows, but it is no longer an active AU expansion target.
- `Overboard Surf` remains correctly parked at zero while supported-brand saleable stock is unavailable.
- Australia should be parked after Trigger Bros and Extreme are production-validated unless a materially higher-value AU source appears.

## Retailer Inventory Guardrail

- Allowed: new boards, used boards, second-hand boards, ex-demo boards, clearance boards, and demo stock where a physical board is clearly for sale.
- Rejected: hire boards, rental boards, lessons, repairs, services, trips, storage, and non-board accessories.
- Shared retailer filters should preserve second-hand surfboards while excluding hire and service listings.

## AU Coverage Factory Summary

- AU candidates reviewed: `103`
- Already running: `30`
- Duplicate shells: `2`
- Manual review: `48`
- Manual review before discovery: `42`
- AU candidates re-analysed by discovery engine: `57`
- Recommended next pack: `None`
- Recommended next individual target: `None`
- Australia recommendation: `Park AU after Trigger Bros and Extreme validation unless a materially higher-value source appears.`

### Classification Summary

- `already_running`: `30`
- `parked_live`: `2`
- `parked_manual`: `7`
- `ready_shopify`: `1`
- `ready_custom_high_value`: `5`
- `duplicate_shell`: `2`
- `shaper_only`: `2`
- `manual_review`: `48`
- `blocked`: `3`
- `unsupported`: `3`

### Platform Summary

- `bigcommerce`: `2`
- `blocked`: `1`
- `connection_error`: `25`
- `magento`: `11`
- `shopify`: `32`
- `squarespace`: `1`
- `ssl_error`: `3`
- `ssl_problem_site`: `1`
- `unknown`: `17`
- `woocommerce`: `10`

### Pack Group Summary

- `Custom High Value Pack`: `5`
- `Duplicate Shells`: `2`
- `Exclude`: `8`
- `Manual Review`: `78`
- `Parked`: `9`
- `Shopify Pack`: `1`

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
- `Trigger Bros Surfboards` | `bigcommerce` | active rows `66`
- `Extreme Boardriders` | `woocommerce` | active rows `47`
- `Manly Surfboards` | `woocommerce` | active rows `47`
- `Ocean Addicts` | `woocommerce` | active rows `41`
- `Surf FX` | `shopify` | active rows `33`
- `The Surfboard Studio` | `shopify` | active rows `8`
- `Beach Beat Alexandra Headland` | `woocommerce` | active rows `7`

## Parked / Low Priority

- `AWSM Surf` | `parked_live` | Keep the existing live AU rows, but park further AWSM onboarding work unless a stronger supported-board surface appears.
- `Akwa Surf` | `parked_live` | Leave the existing AU rows in place, but park new Akwa work unless a stronger supported-board surface is verified.
- `Goodtime Surfboards` | `parked_manual` | Park for now. Nathan review found low supported-manufacturer value relative to AU effort.
- `Surf Boardroom` | `parked_manual` | Park for now. No useful automated online board listing was confirmed in Nathan's AU review.
- `Overboard Surf` | `parked_manual` | Park for now. Zero live AU rows is the correct production outcome until supported-brand saleable stock returns.
- `Underground Surf` | `parked_manual` | Park for now. The surface is mostly hire or non-sale inventory and should stay out of AU active work.
- `Full Circle Surf` | `parked_manual` | Park for now. Treat as non-viable until a real online surfboard storefront exists.
- `Surfers Choice Surf Shop` | `parked_manual` | Park for now. Too few useful boards and no strong add-to-cart flow for Quivrr search quality.
- `Soul Boardstore` | `parked_manual` | Park for now. Product signals exist, but no useful supported-board inventory was confirmed.

## Duplicate Shells

- `Red Herring Surf` -> `Board Collective` | Board Collective shell. products.json empty, surfboard search returned zero, and the public shell resolves product links to boardcollective.com.au.
- `Saltwater Wine Port Macquarie` -> `Board Collective` | Board Collective shell. products.json empty, surfboard search returned zero, and the public shell resolves product links to boardcollective.com.au.

## Top 20 Implementation Candidates

| Retailer | Status | Platform | Approx board count | Priority score | Why now |
| --- | --- | --- | --- | --- | --- |
| City Beach | `manual_review` | `magento` | `80` | `96` | Keep in manual review until an AU-local inventory surface is confirmed. |
| Surf Shops Australia | `manual_review` | `bigcommerce` | `0` | `55` | Keep in manual review until a clean public AU surfboard surface is reconfirmed. |
| Bells Beach Surf Shop | `manual_review` | `unknown` | `0` | `40` | No board inventory surface confirmed. Keep in manual review. |
| Groove Surf | `manual_review` | `unknown` | `0` | `40` | No board inventory surface confirmed. Keep in manual review. |
| Beach Life Margaret River | `manual_review` | `unknown` | `0` | `37` | No board inventory surface confirmed. Keep in manual review. |
| Big Drop Surf | `manual_review` | `unknown` | `0` | `37` | No board inventory surface confirmed. Keep in manual review. |
| Big Surf | `manual_review` | `unknown` | `0` | `37` | No board inventory surface confirmed. Keep in manual review. |
| Boardriders Coolangatta | `manual_review` | `unknown` | `0` | `37` | No board inventory surface confirmed. Keep in manual review. |
| Boardriders Torquay | `manual_review` | `unknown` | `0` | `37` | No board inventory surface confirmed. Keep in manual review. |
| Byron Bay Surf Company | `manual_review` | `unknown` | `0` | `37` | No board inventory surface confirmed. Keep in manual review. |
| Byron Bay Surfboard Co | `manual_review` | `unknown` | `0` | `37` | No board inventory surface confirmed. Keep in manual review. |
| Cordingley's Surf | `manual_review` | `woocommerce` | `0` | `37` | No board inventory surface confirmed. Keep in manual review. |
| Corner Surf Shop | `manual_review` | `connection_error` | `` | `37` | Review inventory surface before any implementation work. |
| Cronulla Surf Design | `manual_review` | `shopify` | `0` | `37` | No board inventory surface confirmed. Keep in manual review. |
| Drift Surf | `manual_review` | `connection_error` | `` | `37` | Review inventory surface before any implementation work. |
| Dripping Wet Surf Co | `manual_review` | `connection_error` | `` | `37` | Review inventory surface before any implementation work. |
| Hollow Surf | `manual_review` | `connection_error` | `` | `37` | Review inventory surface before any implementation work. |
| Innertube Surf Shop | `manual_review` | `connection_error` | `` | `37` | Review inventory surface before any implementation work. |
| Pittwater Surf | `manual_review` | `connection_error` | `` | `37` | Review inventory surface before any implementation work. |
| Pittwater Surfboards | `manual_review` | `connection_error` | `` | `37` | Review inventory surface before any implementation work. |

## Top 10 Custom / High-Value Candidates

| Retailer | Status | Platform | Priority score | Notes |
| --- | --- | --- | --- | --- |
| City Beach | `manual_review` | `magento` | `96` | non_au_catalogue_surface |
| Surf Shops Australia | `manual_review` | `bigcommerce` | `55` | Earlier BigCommerce surfboard hints were not reconfirmed by the discovery engine, so this should not be promoted into the AU BigCommerce pack yet. |
| Bells Beach Surf Shop | `manual_review` | `unknown` | `40` | no_board_category_or_product_surface |
| Groove Surf | `manual_review` | `unknown` | `40` | no_board_category_or_product_surface |
| Beach Life Margaret River | `manual_review` | `unknown` | `37` | no_board_category_or_product_surface |
| Big Drop Surf | `manual_review` | `unknown` | `37` | no_board_category_or_product_surface |
| Big Surf | `manual_review` | `unknown` | `37` | no_board_category_or_product_surface |
| Boardriders Coolangatta | `manual_review` | `unknown` | `37` | no_board_category_or_product_surface |
| Boardriders Torquay | `manual_review` | `unknown` | `37` | no_board_category_or_product_surface |
| Byron Bay Surf Company | `manual_review` | `unknown` | `37` | no_board_category_or_product_surface |

## Recommendation

- Australia closeout: `Park AU after Trigger Bros and Extreme validation.`
  Why: the remaining reviewed shortlist is now low-value, low-signal, sold out, or operationally noisy for Quivrr's supported-manufacturer search quality.
- Keep `Trigger Bros Surfboards` and `Extreme Boardriders` healthy in production.
- Keep existing `AWSM Surf` rows if they remain valid, but do not invest further now.
- Keep `Overboard Surf` parked at zero until supported-brand saleable stock returns.
- Reopen AU only if a materially higher-value retailer source is discovered.

## Full AU Candidate Table

| Dealer | Website | Running | Duplicate of | Status | Platform | Online boards visible | Approx board count | Supported brand signals | Category URL | Example product URLs | Price visible | Stock visible | Images visible | Pagination | Difficulty | Priority score | Recommended action | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Surfboard Empire | `https://surfboardempire.com.au` | `true` |  | `already_running` | `shopify` | `true` | `4944` | Channel Islands |  |  | `true` | `true` | `true` | `false` | `low` | `99` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Trigger Bros Surfboards | `https://triggerbrothers.com.au` | `true` |  | `already_running` | `bigcommerce` | `true` | `66` | supported multi-brand surf retailer | https://triggerbrothers.com.au/store/surf/used-surfboards/ | https://triggerbrothers.com.au/trigger-bros-x-dos-lumberjack-6ft-surfboard/, https://triggerbrothers.com.au/trigger-bros-hot-dog-stubby-9ft-surfboard-red/ | `true` | `true` | `true` | `true` | `medium` | `92` | Keep live in AU and treat as a validated BigCommerce production retailer. | Production-validated AU BigCommerce retailer. Keep healthy, keep linked, and do not treat it as backlog work anymore. |
| Extreme Boardriders | `https://extremeboardriders.com.au` | `true` |  | `already_running` | `woocommerce` | `true` | `47` | supported multi-brand surf retailer |  |  | `true` | `true` | `true` | `true` | `low` | `78` | Keep live in AU and validate it through the standard WooCommerce nightly path. | Approved AU closeout retailer. Existing WooCommerce path is already the correct implementation surface. |
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
| Beach Beat Alexandra Headland | `https://beachbeat.com.au` | `true` |  | `already_running` | `woocommerce` | `true` | `7` | Channel Islands |  |  | `true` | `true` | `true` | `false` | `low` | `40` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Manly Surfboards | `https://manlysurfboards.com.au` | `true` |  | `already_running` | `woocommerce` | `true` | `47` |  |  |  | `true` | `true` | `true` | `false` | `low` | `40` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Ocean Addicts | `https://oceanaddicts.com.au` | `true` |  | `already_running` | `woocommerce` | `true` | `41` |  |  |  | `true` | `true` | `true` | `false` | `low` | `40` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| Surf FX | `https://surffx.com.au` | `true` |  | `already_running` | `shopify` | `true` | `33` |  |  |  | `true` | `true` | `true` | `false` | `low` | `40` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| The Surfboard Studio | `https://www.thesurfboardstudio.com.au` | `true` |  | `already_running` | `shopify` | `true` | `8` |  |  |  | `true` | `true` | `true` | `false` | `low` | `40` | Keep live and use as AU baseline. | Producing available surfboard inventory |
| AWSM Surf | `https://awsmsurf.com` | `true` |  | `parked_live` | `shopify` | `true` | `2` | used and second-hand supported-brand boards | https://www.awsmsurf.com/collections/second-hand-surfboard | https://www.awsmsurf.com/collections/second-hand-surfboard/products/secondlightsurfboardshapedbyrichardevans68, https://www.awsmsurf.com/cdn/shop/products/9b851f1612b5ebc40d4d14e0e38c7bb61c799d3d_2048x.jpg?v=1547178389 | `true` | `true` | `true` | `true` | `medium` | `18` | Keep the existing live AU rows, but park further AWSM onboarding work unless a stronger supported-board surface appears. | Nathan review: low-value AU source for now. Existing second-hand supported boards may remain live, but this is not an active expansion target. |
| Akwa Surf | `https://akwasurf.com.au` | `true` |  | `parked_live` | `shopify` | `true` | `6` |  |  |  | `true` | `true` | `true` | `false` | `low` | `14` | Leave the existing AU rows in place, but park new Akwa work unless a stronger supported-board surface is verified. | Nathan review: no useful AU online stock signal worth active onboarding investment right now. |
| Goodtime Surfboards | `https://www.goodtime.com.au` | `false` |  | `parked_manual` | `magento` | `true` | `70` | long-running AU surfboard retailer | https://www.goodtime.com.au |  | `true` | `true` | `true` | `true` | `high` | `8` | Park for now. Nathan review found low supported-manufacturer value relative to AU effort. | Manual review closeout: mostly smaller or unsupported local-brand value. Not worth active AU onboarding effort right now. |
| Surf Boardroom | `https://surfboardroom.com.au` | `false` |  | `parked_manual` | `woocommerce` | `false` | `0` | Firewire, Channel Islands | https://surfboardroom.com.au/surfboards/ |  | `false` | `false` | `true` | `false` | `medium` | `6` | Park for now. No useful automated online board listing was confirmed in Nathan's AU review. | Manual review closeout: no useful online board listing found for Quivrr search despite earlier WooCommerce signals. |
| Overboard Surf | `https://overboardsurf.com.au` | `false` |  | `parked_manual` | `shopify` | `false` | `0` | JS Industries, Channel Islands, Firewire, Chilli, DHD | https://overboardsurf.com.au/collections/boards-7s-surfboards |  | `true` | `false` | `true` | `true` | `medium` | `5` | Park for now. Zero live AU rows is the correct production outcome until supported-brand saleable stock returns. | Manual review closeout: sold out for supported-brand board variants. Do not treat the current zero-row state as an engineering failure. |
| Underground Surf | `https://undergroundsurf.com.au` | `false` |  | `parked_manual` | `shopify` | `false` | `0` | Channel Islands, JS Industries | https://www.undergroundsurf.com.au/collections/surfboards-1 | https://www.undergroundsurf.com.au/collections/surfboard-hire | `true` | `false` | `true` | `true` | `medium` | `5` | Park for now. The surface is mostly hire or non-sale inventory and should stay out of AU active work. | Manual review closeout: useful online sale inventory was not confirmed. Hire and rental content is a recurring false-positive risk. |
| Full Circle Surf | `https://fullcirclesurf.com.au` | `false` |  | `parked_manual` | `squarespace` | `false` | `0` | JS Industries, Firewire |  |  | `false` | `false` | `false` | `false` | `medium` | `4` | Park for now. Treat as non-viable until a real online surfboard storefront exists. | Manual review closeout: effectively Facebook or Instagram presence only, not a usable AU live-stock source. |
| Surfers Choice Surf Shop | `https://surferschoice.com.au` | `false` |  | `parked_manual` | `unknown` | `false` | `2` | Channel Islands, JS Industries, DHD, Haydenshapes | https://www.surferschoice.com.au/boards.html |  | `true` | `false` | `true` | `false` | `medium` | `4` | Park for now. Too few useful boards and no strong add-to-cart flow for Quivrr search quality. | Manual review closeout: only a couple of boards and no proper modern retailer flow worth engineering further. |
| Soul Boardstore | `https://www.soulboardstore.com.au` | `false` |  | `parked_manual` | `unknown` | `false` | `0` | JS Industries | https://www.soulboardstore.com.au/index.html |  | `false` | `false` | `true` | `false` | `medium` | `3` | Park for now. Product signals exist, but no useful supported-board inventory was confirmed. | Manual review closeout: products exist, but not enough useful Quivrr board stock to justify AU engineering work. |
| Surf Dive n Ski | `https://www.sds.com.au` | `false` |  | `ready_shopify` | `shopify` | `true` | `11` | JS Industries | https://www.sds.com.au/collections/boys-boardshorts | https://www.sds.com.au/collections/boys-boardshorts, https://www.sds.com.au/collections/boys-printed-boardshorts | `true` | `true` | `true` | `true` | `medium` | `34` | Candidate for reusable AU Shopify onboarding. | https://www.sds.com.au/products.json?limit=1 |
| Manly Surf Guide Surfboard Outlet | `https://manlysurfguide.com.au` | `false` |  | `ready_custom_high_value` | `magento` | `true` | `15` | JS Industries | http://www.manlysurfguide.com.au/shop/soft-surfboards-sale | https://www.manlysurfguide.com.au/shop/soft-surfboards-sale, https://www.manlysurfguide.com.au/shop/soft-surfboards/6ft-soft-surfboard | `true` | `true` | `true` | `false` | `medium` | `34` | Candidate for a targeted high-value custom implementation after pack work. | Detected magento markers in HTML |
| Island Surfboards | `https://www.islandsurfboards.com.au` | `false` |  | `ready_custom_high_value` | `magento` | `true` | `8` | Channel Islands, JS Industries | https://www.islandsurfboards.com.au/islandperformancecoaching | https://www.islandsurfboards.com.au/surfboards, https://www.islandsurfboards.com.au/surfboards/slop-rocket | `true` | `true` | `true` | `false` | `medium` | `30` | Candidate for a targeted high-value custom implementation after pack work. | Detected magento markers in HTML |
| Empire Ave | `https://empireave.com` | `false` |  | `ready_custom_high_value` | `magento` | `true` | `3` | JS Industries, DHD, Channel Islands | https://empireave.com/goods-guides/buyers-guides/fish-surfboards-a-guide/ | https://empireave.com/tag/carbotune/, https://empireave.com/interviews/talking-grips-softboards-and-dhd-with-modom/ | `true` | `true` | `true` | `true` | `medium` | `28` | Candidate for a targeted high-value custom implementation after pack work. | Detected magento markers in HTML |
| Slimes Boardstore | `https://slimes.com.au` | `false` |  | `ready_custom_high_value` | `magento` | `true` | `3` | Channel Islands, JS Industries | https://www.slimes.com.au/surfboards | https://www.slimes.com.au/surfboards, https://www.slimes.com.au/softboards | `true` | `true` | `true` | `false` | `medium` | `13` | Candidate for a targeted high-value custom implementation after pack work. | Detected magento markers in HTML |
| Coopers Surf | `https://cooperssurf.com.au` | `false` |  | `ready_custom_high_value` | `magento` | `true` | `3` | JS Industries | https://cooperssurf.com.au/product/outerknown-journey-fish-5-panel-hat/ | https://cooperssurf.com.au/product/outerknown-journey-fish-5-panel-hat/, https://cooperssurf.com.au/product-tag/js-industries-apparel/ | `true` | `true` | `true` | `false` | `medium` | `12` | Candidate for a targeted high-value custom implementation after pack work. | Detected magento markers in HTML |
| Red Herring Surf | `https://redherringsurf.com.au` | `false` | Board Collective | `duplicate_shell` | `shopify` | `false` | `0` | JS Industries, Pyzel, Firewire | https://redherringsurf.com.au/collections/all | https://boardcollective.com.au/products/boardcollective-egift-card | `false` | `false` | `true` | `false` | `low` | `0` | Exclude from AU onboarding and keep Board Collective as the inventory source. | Board Collective shell. products.json empty, surfboard search returned zero, and the public shell resolves product links to boardcollective.com.au. |
| Saltwater Wine Port Macquarie | `https://saltwaterwine.com.au` | `false` | Board Collective | `duplicate_shell` | `shopify` | `false` | `0` | JS Industries, Pyzel, Firewire, Channel Islands | https://saltwaterwine.com.au/collections/all | https://boardcollective.com.au/products/boardcollective-egift-card | `false` | `false` | `true` | `false` | `low` | `0` | Exclude from AU onboarding and keep Board Collective as the inventory source. | Board Collective shell. products.json empty, surfboard search returned zero, and the public shell resolves product links to boardcollective.com.au. |
| JS Industries | `https://jsindustries.com` | `false` |  | `shaper_only` | `shopify` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `low` | `5` | Exclude from retailer inventory and leave to canonical / MFA paths. | https://jsindustries.com/products.json?limit=1 |
| Ocean & Earth Store | `https://oceanandearth.com.au` | `false` |  | `shaper_only` | `shopify` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `low` | `0` | Exclude from retailer inventory and leave to canonical / MFA paths. | https://oceanandearth.com.au/products.json?limit=1 |
| City Beach | `https://www.citybeach.com` | `false` |  | `manual_review` | `magento` | `true` | `80` | Channel Islands, JS Industries | https://www.citybeach.com/us/kids/boardsports/ | https://www.citybeach.com/us/kids/, https://www.citybeach.com/us/kids/boardsports/#A | `true` | `false` | `true` | `false` | `medium` | `96` | Keep in manual review until an AU-local inventory surface is confirmed. | non_au_catalogue_surface |
| Surf Shops Australia | `https://surfshopsaustralia.com.au` | `false` |  | `manual_review` | `bigcommerce` | `false` | `0` | broad surfboard catalogue |  |  | `false` | `false` | `false` | `false` | `medium` | `55` | Keep in manual review until a clean public AU surfboard surface is reconfirmed. | Earlier BigCommerce surfboard hints were not reconfirmed by the discovery engine, so this should not be promoted into the AU BigCommerce pack yet. |
| Bells Beach Surf Shop | `https://bellsbeachsurfshop.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `40` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Groove Surf | `https://groovesurf.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `40` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Beach Life Margaret River | `https://beachlifemargs.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Big Drop Surf | `https://bigdropsurf.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` | Channel Islands |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Big Surf | `https://bigsurf.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` | Channel Islands |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Boardriders Coolangatta | `https://boardriders.co` | `false` |  | `manual_review` | `unknown` | `false` | `0` | Channel Islands |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Boardriders Torquay | `https://boardriders.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Byron Bay Surf Company | `https://byronbaysurfcompany.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Byron Bay Surfboard Co | `https://www.byronbaysurfboardco.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Cordingley's Surf | `https://cordingleyssurf.com.au` | `false` |  | `manual_review` | `woocommerce` | `false` | `0` | Channel Islands |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Corner Surf Shop | `https://cornersurfshop.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` | Channel Islands |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='cornersurfshop.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='cornersurfshop.com.au', port=443): Failed to resolve 'cornersurfshop.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Cronulla Surf Design | `https://cronullasurfdesign.com.au` | `false` |  | `manual_review` | `shopify` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | No board inventory surface confirmed. Keep in manual review. | no_board_category_or_product_surface |
| Drift Surf | `https://www.driftsurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='www.driftsurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='www.driftsurf.com.au', port=443): Failed to resolve 'www.driftsurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Dripping Wet Surf Co | `https://drippingwetsurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='drippingwetsurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='drippingwetsurf.com.au', port=443): Failed to resolve 'drippingwetsurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Hollow Surf | `https://hollowsurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` | Channel Islands |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='hollowsurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='hollowsurf.com.au', port=443): Failed to resolve 'hollowsurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Innertube Surf Shop | `https://innertubesurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` | Channel Islands |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='innertubesurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='innertubesurf.com.au', port=443): Failed to resolve 'innertubesurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Pittwater Surf | `https://www.pittwatersurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='www.pittwatersurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='www.pittwatersurf.com.au', port=443): Failed to resolve 'www.pittwatersurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Pittwater Surfboards | `https://pittwatersurfboards.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='pittwatersurfboards.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='pittwatersurfboards.com.au', port=443): Failed to resolve 'pittwatersurfboards.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Second Surf | `https://secondsurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='secondsurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='secondsurf.com.au', port=443): Failed to resolve 'secondsurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Sessions Surf Shop | `https://sessionssurfshop.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='sessionssurfshop.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='sessionssurfshop.com.au', port=443): Failed to resolve 'sessionssurfshop.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Surfboard Agency | `https://surfboardagency.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='surfboardagency.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='surfboardagency.com.au', port=443): Failed to resolve 'surfboardagency.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Triple Bull Surf and Skate | `https://triplebull.com.au` | `false` |  | `manual_review` | `ssl_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='triplebull.com.au', port=443): Max retries exceeded with url: / (Caused by SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1028)'))) |
| Yallingup Surf Shop | `https://yallingupsurf.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  | https://yallingupsurf.com.au/collections/surfboards |  | `false` | `false` | `false` | `false` | `medium` | `37` | Board categories found, but product inventory could not be confirmed safely. | board_categories_found_no_products |
| Action Board Sports | `https://actionboardsports.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='actionboardsports.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='actionboardsports.com.au', port=443): Failed to resolve 'actionboardsports.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Apollo Bay Surf Shop | `https://apollobaysurfshop.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='apollobaysurfshop.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='apollobaysurfshop.com.au', port=443): Failed to resolve 'apollobaysurfshop.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Blue Planet Surf | `https://blueplanetsurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='blueplanetsurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='blueplanetsurf.com.au', port=443): Failed to resolve 'blueplanetsurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Board Hub | `https://boardhub.com.au` | `false` |  | `manual_review` | `magento` | `false` | `0` |  | https://boardhub.com.au/surfboards/shortboards |  | `false` | `false` | `false` | `false` | `medium` | `34` | Board categories found, but product inventory could not be confirmed safely. | board_categories_found_no_products |
| Coogee Surf Co | `https://coogeesurfco.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='coogeesurfco.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='coogeesurfco.com.au', port=443): Failed to resolve 'coogeesurfco.com.au' ([Errno 11001] getaddrinfo failed)")) |
| CPS Surf | `https://cpssurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='cpssurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='cpssurf.com.au', port=443): Failed to resolve 'cpssurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Harbour Surfboards | `https://harboursurfboards.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='harboursurfboards.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='harboursurfboards.com.au', port=443): Failed to resolve 'harboursurfboards.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Le Spot Surf Shop | `https://lespotsurfshop.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='lespotsurfshop.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='lespotsurfshop.com.au', port=443): Failed to resolve 'lespotsurfshop.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Maroubra Surf and Skate | `https://maroubrasurfandskate.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='maroubrasurfandskate.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='maroubrasurfandskate.com.au', port=443): Failed to resolve 'maroubrasurfandskate.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Mid Coast Surf | `https://midcoastsurf.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  | https://midcoastsurf.com.au/collections/surfboards |  | `false` | `false` | `false` | `false` | `medium` | `34` | Board categories found, but product inventory could not be confirmed safely. | board_categories_found_no_products |
| Murray Smith Surf Warehouse | `https://murraysmithsurfwarehouse.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='murraysmithsurfwarehouse.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='murraysmithsurfwarehouse.com.au', port=443): Failed to resolve 'murraysmithsurfwarehouse.com.au' ([Errno 11001] getaddrinfo failed)")) |
| North Coast Surf | `https://northcoastsurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='northcoastsurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='northcoastsurf.com.au', port=443): Failed to resolve 'northcoastsurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Ocean Grove Surf Co | `https://oceangrovesurfco.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='oceangrovesurfco.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='oceangrovesurfco.com.au', port=443): Failed to resolve 'oceangrovesurfco.com.au' ([Errno 11001] getaddrinfo failed)")) |
| On A Wave Surf Shop | `https://onawavesurfshop.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='onawavesurfshop.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='onawavesurfshop.com.au', port=443): Failed to resolve 'onawavesurfshop.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Prahran Surfboards | `https://prahransurfboards.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='prahransurfboards.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='prahransurfboards.com.au', port=443): Failed to resolve 'prahransurfboards.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Secret Harbour Surf | `https://secretharboursurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='secretharboursurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='secretharboursurf.com.au', port=443): Failed to resolve 'secretharboursurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Shed Nine | `https://shednine.com.au` | `false` |  | `manual_review` | `ssl_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='shednine.com.au', port=443): Max retries exceeded with url: / (Caused by SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1028)'))) |
| Surf Connect | `https://www.surfconnect.com` | `false` |  | `manual_review` | `unknown` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | Homepage returned 200 |
| Surf Warehouse | `https://surfwarehouse.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `0` |  | https://surfwarehouse.com.au/collections/surfboards |  | `false` | `false` | `false` | `false` | `medium` | `34` | Board categories found, but product inventory could not be confirmed safely. | board_categories_found_no_products |
| Surfection Mosman | `https://www.surfectionmosman.com.au` | `false` |  | `manual_review` | `ssl_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='www.surfectionmosman.com.au', port=443): Max retries exceeded with url: / (Caused by SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1028)'))) |
| Three Stories | `https://www.threestories.com.au` | `false` |  | `manual_review` | `ssl_problem_site` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | SSL verification failed but site loaded with verify=False |
| World Surfaris Surf Shop | `https://worldsurfaris.com` | `false` |  | `manual_review` | `unknown` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | Homepage returned 200 |
| Yorkes Surf | `https://yorkessurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='yorkessurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='yorkessurf.com.au', port=443): Failed to resolve 'yorkessurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Boardcave | `https://www.boardcave.com.au` | `false` |  | `blocked` | `blocked` | `false` | `0` | large Australian surfboard marketplace |  |  | `false` | `false` | `false` | `false` | `high` | `35` | Keep blocked. Revisit only if Boardcave exposes a safe public inventory path. | High-value marketplace signal, but current access is blocked and not safe for AU nightly onboarding. |
| Kirra Surf | `https://kirrasurf.com.au` | `false` |  | `blocked` | `unknown` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `low` | `15` | Keep blocked until the site exposes a safe public inventory surface. | request_blocked |
| Board Store | `https://boardstore.com.au` | `false` |  | `blocked` | `magento` | `false` | `0` |  |  |  | `false` | `false` | `false` | `false` | `low` | `12` | Keep blocked until the site exposes a safe public inventory surface. | homepage_http_403 |
| Beaches Apparel | `https://beachesapparel.com` | `false` |  | `unsupported` | `woocommerce` | `false` | `5` |  |  |  | `false` | `false` | `false` | `false` | `low` | `0` | Exclude from AU hardboard onboarding. | Clothing/apparel store, not suitable for Quivrr hardboard retailer inventory |
| Ocean and Earth | `https://oceanearthstore.com` | `false` |  | `unsupported` | `magento` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `low` | `0` | Exclude from AU hardboard onboarding. | Brand/accessory store, not suitable for Quivrr hardboard retailer inventory |
| Rip Curl Australia | `https://www.ripcurl.com/au` | `false` |  | `unsupported` | `magento` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `low` | `0` | Exclude from AU hardboard onboarding. | Does not sell hardboard surfboard inventory online for Quivrr search |
