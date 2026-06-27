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
- Manual review: `45`
- Recommended next pack: `BigCommerce Pack`
- Recommended next individual target: `Trigger Bros Surfboards`

### Classification Summary

- `already_running`: `30`
- `ready_shopify`: `3`
- `ready_woocommerce`: `7`
- `ready_bigcommerce`: `2`
- `ready_neto_maropost`: `1`
- `ready_opencart`: `1`
- `ready_custom_high_value`: `5`
- `duplicate_shell`: `2`
- `no_online_boards`: `1`
- `shaper_only`: `2`
- `manual_review`: `45`
- `blocked`: `1`
- `unsupported`: `3`

### Platform Summary

- `bigcommerce`: `2`
- `blocked`: `1`
- `connection_error`: `31`
- `magento`: `5`
- `neto_maropost`: `1`
- `opencart`: `1`
- `shopify`: `32`
- `squarespace`: `3`
- `ssl_error`: `5`
- `ssl_problem_site`: `2`
- `unknown`: `5`
- `woocommerce`: `15`

### Pack Group Summary

- `BigCommerce Pack`: `2`
- `Custom High Value Pack`: `5`
- `Duplicate Shells`: `2`
- `Exclude`: `7`
- `Manual Review`: `75`
- `Neto / Maropost Pack`: `1`
- `OpenCart Pack`: `1`
- `Shopify Pack`: `3`
- `WooCommerce Pack`: `7`

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
| Trigger Bros Surfboards | `ready_bigcommerce` | `bigcommerce` | `80` | `92` | Implement as the BigCommerce reference target and validate in Azure before adding more AU BigCommerce stores. |
| Goodtime Surfboards | `ready_custom_high_value` | `magento` | `70` | `83` | Treat as a high-value custom follow-up after the BigCommerce pack, not before it. |
| Surf Shops Australia | `ready_bigcommerce` | `bigcommerce` | `60` | `79` | Keep as the second AU BigCommerce pack target once Trigger Bros proves the shared scraper path. |
| Island Surfboards | `ready_custom_high_value` | `squarespace` | `128` | `74` | Candidate for targeted high-value onboarding after pack work. |
| Surf Boardroom | `ready_woocommerce` | `woocommerce` | `200` | `72` | Keep in the WooCommerce pack. Board surface is real, but parser work is still needed. |
| Empire Ave | `ready_custom_high_value` | `magento` | `30` | `68` | Candidate for targeted high-value onboarding after pack work. |
| Manly Surf Guide Surfboard Outlet | `ready_custom_high_value` | `squarespace` | `15` | `68` | Candidate for targeted high-value onboarding after pack work. |
| Cronulla Surf Design | `ready_shopify` | `shopify` | `363` | `67` | Candidate for the reusable AU Shopify pack. |
| Surf Dive n Ski | `ready_shopify` | `shopify` | `` | `67` | Candidate for the reusable AU Shopify pack. |
| City Beach | `ready_custom_high_value` | `magento` | `` | `65` | Candidate for targeted high-value onboarding after pack work. |
| Underground Surf | `ready_shopify` | `shopify` | `163` | `64` | Candidate for the reusable AU Shopify pack. |
| Boardriders Coolangatta | `ready_woocommerce` | `woocommerce` | `` | `63` | Candidate for the reusable AU WooCommerce pack. |
| Cordingley's Surf | `ready_woocommerce` | `woocommerce` | `8` | `63` | Candidate for the reusable AU WooCommerce pack. |
| Yallingup Surf Shop | `ready_woocommerce` | `woocommerce` | `` | `63` | Candidate for the reusable AU WooCommerce pack. |
| Board Hub | `ready_woocommerce` | `woocommerce` | `` | `60` | Candidate for the reusable AU WooCommerce pack. |
| Board Store | `ready_neto_maropost` | `neto_maropost` | `` | `60` | Candidate for the reusable AU Neto / Maropost pack. |
| Mid Coast Surf | `ready_woocommerce` | `woocommerce` | `` | `60` | Candidate for the reusable AU WooCommerce pack. |
| Surf Warehouse | `ready_woocommerce` | `woocommerce` | `` | `60` | Candidate for the reusable AU WooCommerce pack. |
| Slimes Boardstore | `ready_opencart` | `opencart` | `` | `58` | Candidate for a reusable adapter once the pack is proven. |
| AWSM Surf | `manual_review` | `shopify` | `1966` | `40` | Review inventory surface before any implementation work. |

## Top 10 Custom / High-Value Candidates

| Retailer | Status | Platform | Priority score | Notes |
| --- | --- | --- | --- | --- |
| Goodtime Surfboards | `ready_custom_high_value` | `magento` | `83` | Large retailer signal, but current path is noisy and protected. Better as the next custom target once the coverage factory lands. |
| Island Surfboards | `ready_custom_high_value` | `squarespace` | `74` | Products scraped but surfboard filter did not identify boards |
| Empire Ave | `ready_custom_high_value` | `magento` | `68` | Products scraped but surfboard filter did not identify boards |
| Manly Surf Guide Surfboard Outlet | `ready_custom_high_value` | `squarespace` | `68` | Products scraped but surfboard filter did not identify boards |
| City Beach | `ready_custom_high_value` | `magento` | `65` | Detected Magento markers |
| AWSM Surf | `manual_review` | `shopify` | `40` | Surfboards identified but no available inventory |
| Bells Beach Surf Shop | `manual_review` | `unknown` | `40` | Homepage returned 502 |
| Groove Surf | `manual_review` | `connection_error` | `40` | HTTPSConnectionPool(host='groovesurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='groovesurf.com.au', port=443): Failed to resolve 'groovesurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Kirra Surf | `manual_review` | `ssl_problem_site` | `40` | SSL verification failed but site loaded with verify=False |
| Beach Life Margaret River | `manual_review` | `connection_error` | `37` | HTTPSConnectionPool(host='beachlifemargs.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='beachlifemargs.com.au', port=443): Failed to resolve 'beachlifemargs.com.au' ([Errno 11001] getaddrinfo failed)")) |

## Recommendation

- Next pack: `BigCommerce Pack`
  Why: Trigger Bros and Surf Shops Australia both expose real BigCommerce surfboard surfaces, so one reusable AU BigCommerce uplift should beat more low-value Shopify guessing.
- Next individual target: `Trigger Bros Surfboards`
  Why: strongest remaining retailer-distinct AU target with visible live board inventory, pricing, imagery and reusable platform signals.
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
| Cronulla Surf Design | `https://cronullasurfdesign.com.au` | `false` |  | `ready_shopify` | `shopify` | `true` | `363` |  |  |  | `true` | `true` | `true` | `true` | `medium` | `67` | Candidate for the reusable AU Shopify pack. | Products scraped but surfboard filter did not identify boards |
| Surf Dive n Ski | `https://www.sds.com.au` | `false` |  | `ready_shopify` | `shopify` | `true` | `` |  |  |  | `true` | `true` | `true` | `true` | `medium` | `67` | Candidate for the reusable AU Shopify pack. | https://www.sds.com.au/products.json?limit=1 |
| Underground Surf | `https://undergroundsurf.com.au` | `false` |  | `ready_shopify` | `shopify` | `true` | `163` |  |  |  | `true` | `true` | `true` | `true` | `medium` | `64` | Candidate for the reusable AU Shopify pack. | Products scraped but surfboard filter did not identify boards |
| Surf Boardroom | `https://surfboardroom.com.au` | `false` |  | `ready_woocommerce` | `woocommerce` | `true` | `200` | Firewire, Channel Islands | https://surfboardroom.com.au/surfboards/ |  | `false` | `true` | `true` | `false` | `medium` | `72` | Keep in the WooCommerce pack. Board surface is real, but parser work is still needed. | Boards are visible and the WooCommerce path is real, but the current extraction path undershoots and needs parser recovery. |
| Boardriders Coolangatta | `https://boardriders.co` | `false` |  | `ready_woocommerce` | `woocommerce` | `true` | `` | Channel Islands |  |  | `true` | `true` | `true` | `true` | `medium` | `63` | Candidate for the reusable AU WooCommerce pack. | No raw products returned from scrape output |
| Cordingley's Surf | `https://cordingleyssurf.com.au` | `false` |  | `ready_woocommerce` | `woocommerce` | `true` | `8` | Channel Islands |  |  | `true` | `true` | `true` | `true` | `medium` | `63` | Candidate for the reusable AU WooCommerce pack. | Products scraped but surfboard filter did not identify boards |
| Yallingup Surf Shop | `https://yallingupsurf.com.au` | `false` |  | `ready_woocommerce` | `woocommerce` | `true` | `` |  |  |  | `true` | `true` | `true` | `true` | `medium` | `63` | Candidate for the reusable AU WooCommerce pack. | No raw products returned from scrape output |
| Board Hub | `https://boardhub.com.au` | `false` |  | `ready_woocommerce` | `woocommerce` | `true` | `` |  |  |  | `true` | `true` | `true` | `true` | `medium` | `60` | Candidate for the reusable AU WooCommerce pack. | No raw products returned from scrape output |
| Mid Coast Surf | `https://midcoastsurf.com.au` | `false` |  | `ready_woocommerce` | `woocommerce` | `true` | `` |  |  |  | `true` | `true` | `true` | `true` | `medium` | `60` | Candidate for the reusable AU WooCommerce pack. | No raw products returned from scrape output |
| Surf Warehouse | `https://surfwarehouse.com.au` | `false` |  | `ready_woocommerce` | `woocommerce` | `true` | `` |  |  |  | `true` | `true` | `true` | `true` | `medium` | `60` | Candidate for the reusable AU WooCommerce pack. | No raw products returned from scrape output |
| Trigger Bros Surfboards | `https://triggerbrothers.com.au` | `false` |  | `ready_bigcommerce` | `bigcommerce` | `true` | `80` | supported multi-brand surf retailer | https://triggerbrothers.com.au/store/surf/used-surfboards/ | https://triggerbrothers.com.au/trigger-bros-x-dos-lumberjack-6ft-surfboard/, https://triggerbrothers.com.au/trigger-bros-hot-dog-stubby-9ft-surfboard-red/ | `true` | `true` | `true` | `true` | `medium` | `92` | Implement as the BigCommerce reference target and validate in Azure before adding more AU BigCommerce stores. | Best current AU next target. Live BigCommerce site with visible board inventory and reusable platform path. |
| Surf Shops Australia | `https://surfshopsaustralia.com.au` | `false` |  | `ready_bigcommerce` | `bigcommerce` | `true` | `60` | broad surfboard catalogue | https://surfshopsaustralia.com.au/surfboards/ | https://surfshopsaustralia.com.au/surfboards/, https://surfshopsaustralia.com.au/surfboards/shortboards/ | `true` | `true` | `true` | `true` | `medium` | `79` | Keep as the second AU BigCommerce pack target once Trigger Bros proves the shared scraper path. | BigCommerce surfboard taxonomy is public and broad, making it the strongest shared AU BigCommerce follow-on target. |
| Board Store | `https://boardstore.com.au` | `false` |  | `ready_neto_maropost` | `neto_maropost` | `true` | `` |  |  |  | `true` | `true` | `true` | `false` | `medium` | `60` | Candidate for the reusable AU Neto / Maropost pack. | No raw products returned from scrape output |
| Slimes Boardstore | `https://slimes.com.au` | `false` |  | `ready_opencart` | `opencart` | `true` | `` | Channel Islands, Christenson |  |  | `true` | `true` | `true` | `false` | `medium` | `58` | Candidate for a reusable adapter once the pack is proven. | Detected Ecwid markers |
| Goodtime Surfboards | `https://www.goodtime.com.au` | `false` |  | `ready_custom_high_value` | `magento` | `true` | `70` | long-running AU surfboard retailer | https://www.goodtime.com.au |  | `true` | `true` | `true` | `true` | `high` | `83` | Treat as a high-value custom follow-up after the BigCommerce pack, not before it. | Large retailer signal, but current path is noisy and protected. Better as the next custom target once the coverage factory lands. |
| Island Surfboards | `https://www.islandsurfboards.com.au` | `false` |  | `ready_custom_high_value` | `squarespace` | `true` | `128` |  |  |  | `true` | `true` | `true` | `false` | `medium` | `74` | Candidate for targeted high-value onboarding after pack work. | Products scraped but surfboard filter did not identify boards |
| Empire Ave | `https://empireave.com` | `false` |  | `ready_custom_high_value` | `magento` | `true` | `30` |  |  |  | `true` | `true` | `true` | `false` | `medium` | `68` | Candidate for targeted high-value onboarding after pack work. | Products scraped but surfboard filter did not identify boards |
| Manly Surf Guide Surfboard Outlet | `https://manlysurfguide.com.au` | `false` |  | `ready_custom_high_value` | `squarespace` | `true` | `15` |  |  |  | `true` | `true` | `true` | `false` | `medium` | `68` | Candidate for targeted high-value onboarding after pack work. | Products scraped but surfboard filter did not identify boards |
| City Beach | `https://www.citybeach.com` | `false` |  | `ready_custom_high_value` | `magento` | `true` | `` |  |  |  | `true` | `true` | `true` | `false` | `medium` | `65` | Candidate for targeted high-value onboarding after pack work. | Detected Magento markers |
| Red Herring Surf | `https://redherringsurf.com.au` | `false` | Board Collective | `duplicate_shell` | `shopify` | `false` | `0` | JS Industries, Pyzel, Firewire | https://redherringsurf.com.au/collections/all | https://boardcollective.com.au/products/boardcollective-egift-card | `false` | `false` | `true` | `false` | `low` | `0` | Exclude from AU onboarding and keep Board Collective as the inventory source. | Board Collective shell. products.json empty, surfboard search returned zero, and the public shell resolves product links to boardcollective.com.au. |
| Saltwater Wine Port Macquarie | `https://saltwaterwine.com.au` | `false` | Board Collective | `duplicate_shell` | `shopify` | `false` | `0` | JS Industries, Pyzel, Firewire, Channel Islands | https://saltwaterwine.com.au/collections/all | https://boardcollective.com.au/products/boardcollective-egift-card | `false` | `false` | `true` | `false` | `low` | `0` | Exclude from AU onboarding and keep Board Collective as the inventory source. | Board Collective shell. products.json empty, surfboard search returned zero, and the public shell resolves product links to boardcollective.com.au. |
| Full Circle Surf | `https://fullcirclesurf.com.au` | `false` |  | `no_online_boards` | `squarespace` | `false` | `0` | JS Industries, Firewire |  |  | `false` | `false` | `false` | `false` | `medium` | `10` | Do not implement until a working surfboard storefront is confirmed. | Known retailer, but the current public storefront is broken and not a usable AU inventory source. |
| JS Industries | `https://jsindustries.com` | `false` |  | `shaper_only` | `shopify` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `low` | `5` | Exclude from retailer inventory and leave to canonical / MFA paths. | https://jsindustries.com/products.json?limit=1 |
| Ocean & Earth Store | `https://oceanandearth.com.au` | `false` |  | `shaper_only` | `shopify` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `low` | `0` | Exclude from retailer inventory and leave to canonical / MFA paths. | https://oceanandearth.com.au/products.json?limit=1 |
| AWSM Surf | `https://awsmsurf.com` | `false` |  | `manual_review` | `shopify` | `true` | `1966` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `40` | Review inventory surface before any implementation work. | Surfboards identified but no available inventory |
| Bells Beach Surf Shop | `https://bellsbeachsurfshop.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `40` | Review inventory surface before any implementation work. | Homepage returned 502 |
| Groove Surf | `https://groovesurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `40` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='groovesurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='groovesurf.com.au', port=443): Failed to resolve 'groovesurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Kirra Surf | `https://kirrasurf.com.au` | `false` |  | `manual_review` | `ssl_problem_site` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `40` | Review inventory surface before any implementation work. | SSL verification failed but site loaded with verify=False |
| Beach Life Margaret River | `https://beachlifemargs.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='beachlifemargs.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='beachlifemargs.com.au', port=443): Failed to resolve 'beachlifemargs.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Big Drop Surf | `https://bigdropsurf.com.au` | `false` |  | `manual_review` | `ssl_error` | `false` | `` | Channel Islands |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='bigdropsurf.com.au', port=443): Max retries exceeded with url: / (Caused by SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1028)'))) |
| Big Surf | `https://bigsurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` | Channel Islands |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='bigsurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='bigsurf.com.au', port=443): Failed to resolve 'bigsurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Boardriders Torquay | `https://boardriders.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='boardriders.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='boardriders.com.au', port=443): Failed to resolve 'boardriders.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Byron Bay Surf Company | `https://byronbaysurfcompany.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='byronbaysurfcompany.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='byronbaysurfcompany.com.au', port=443): Failed to resolve 'byronbaysurfcompany.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Byron Bay Surfboard Co | `https://www.byronbaysurfboardco.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='www.byronbaysurfboardco.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='www.byronbaysurfboardco.com.au', port=443): Failed to resolve 'www.byronbaysurfboardco.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Coopers Surf | `https://cooperssurf.com.au` | `false` |  | `manual_review` | `ssl_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='cooperssurf.com.au', port=443): Max retries exceeded with url: / (Caused by SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1028)'))) |
| Corner Surf Shop | `https://cornersurfshop.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` | Channel Islands |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='cornersurfshop.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='cornersurfshop.com.au', port=443): Failed to resolve 'cornersurfshop.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Drift Surf | `https://www.driftsurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='www.driftsurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='www.driftsurf.com.au', port=443): Failed to resolve 'www.driftsurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Dripping Wet Surf Co | `https://drippingwetsurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='drippingwetsurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='drippingwetsurf.com.au', port=443): Failed to resolve 'drippingwetsurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Hollow Surf | `https://hollowsurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` | Channel Islands |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='hollowsurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='hollowsurf.com.au', port=443): Failed to resolve 'hollowsurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Innertube Surf Shop | `https://innertubesurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` | Channel Islands |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='innertubesurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='innertubesurf.com.au', port=443): Failed to resolve 'innertubesurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Overboard Surf | `https://overboardsurf.com.au` | `false` |  | `manual_review` | `shopify` | `true` | `1300` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | Surfboards identified but no available inventory |
| Pittwater Surf | `https://www.pittwatersurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='www.pittwatersurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='www.pittwatersurf.com.au', port=443): Failed to resolve 'www.pittwatersurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Pittwater Surfboards | `https://pittwatersurfboards.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='pittwatersurfboards.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='pittwatersurfboards.com.au', port=443): Failed to resolve 'pittwatersurfboards.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Second Surf | `https://secondsurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='secondsurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='secondsurf.com.au', port=443): Failed to resolve 'secondsurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Sessions Surf Shop | `https://sessionssurfshop.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='sessionssurfshop.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='sessionssurfshop.com.au', port=443): Failed to resolve 'sessionssurfshop.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Surfboard Agency | `https://surfboardagency.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='surfboardagency.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='surfboardagency.com.au', port=443): Failed to resolve 'surfboardagency.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Triple Bull Surf and Skate | `https://triplebull.com.au` | `false` |  | `manual_review` | `ssl_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `37` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='triplebull.com.au', port=443): Max retries exceeded with url: / (Caused by SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1028)'))) |
| Action Board Sports | `https://actionboardsports.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='actionboardsports.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='actionboardsports.com.au', port=443): Failed to resolve 'actionboardsports.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Apollo Bay Surf Shop | `https://apollobaysurfshop.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='apollobaysurfshop.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='apollobaysurfshop.com.au', port=443): Failed to resolve 'apollobaysurfshop.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Blue Planet Surf | `https://blueplanetsurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='blueplanetsurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='blueplanetsurf.com.au', port=443): Failed to resolve 'blueplanetsurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Coogee Surf Co | `https://coogeesurfco.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='coogeesurfco.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='coogeesurfco.com.au', port=443): Failed to resolve 'coogeesurfco.com.au' ([Errno 11001] getaddrinfo failed)")) |
| CPS Surf | `https://cpssurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='cpssurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='cpssurf.com.au', port=443): Failed to resolve 'cpssurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Harbour Surfboards | `https://harboursurfboards.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='harboursurfboards.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='harboursurfboards.com.au', port=443): Failed to resolve 'harboursurfboards.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Le Spot Surf Shop | `https://lespotsurfshop.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='lespotsurfshop.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='lespotsurfshop.com.au', port=443): Failed to resolve 'lespotsurfshop.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Maroubra Surf and Skate | `https://maroubrasurfandskate.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='maroubrasurfandskate.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='maroubrasurfandskate.com.au', port=443): Failed to resolve 'maroubrasurfandskate.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Murray Smith Surf Warehouse | `https://murraysmithsurfwarehouse.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='murraysmithsurfwarehouse.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='murraysmithsurfwarehouse.com.au', port=443): Failed to resolve 'murraysmithsurfwarehouse.com.au' ([Errno 11001] getaddrinfo failed)")) |
| North Coast Surf | `https://northcoastsurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='northcoastsurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='northcoastsurf.com.au', port=443): Failed to resolve 'northcoastsurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Ocean Grove Surf Co | `https://oceangrovesurfco.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='oceangrovesurfco.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='oceangrovesurfco.com.au', port=443): Failed to resolve 'oceangrovesurfco.com.au' ([Errno 11001] getaddrinfo failed)")) |
| On A Wave Surf Shop | `https://onawavesurfshop.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='onawavesurfshop.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='onawavesurfshop.com.au', port=443): Failed to resolve 'onawavesurfshop.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Prahran Surfboards | `https://prahransurfboards.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='prahransurfboards.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='prahransurfboards.com.au', port=443): Failed to resolve 'prahransurfboards.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Secret Harbour Surf | `https://secretharboursurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='secretharboursurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='secretharboursurf.com.au', port=443): Failed to resolve 'secretharboursurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Shed Nine | `https://shednine.com.au` | `false` |  | `manual_review` | `ssl_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='shednine.com.au', port=443): Max retries exceeded with url: / (Caused by SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1028)'))) |
| Soul Boardstore | `https://www.soulboardstore.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | Homepage returned 200 |
| Surf Connect | `https://www.surfconnect.com` | `false` |  | `manual_review` | `unknown` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | Homepage returned 200 |
| Surfection Mosman | `https://www.surfectionmosman.com.au` | `false` |  | `manual_review` | `ssl_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='www.surfectionmosman.com.au', port=443): Max retries exceeded with url: / (Caused by SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1028)'))) |
| Surfers Choice Surf Shop | `https://surferschoice.com.au` | `false` |  | `manual_review` | `unknown` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | Homepage returned 200 |
| Three Stories | `https://www.threestories.com.au` | `false` |  | `manual_review` | `ssl_problem_site` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | SSL verification failed but site loaded with verify=False |
| World Surfaris Surf Shop | `https://worldsurfaris.com` | `false` |  | `manual_review` | `unknown` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | Homepage returned 200 |
| Yorkes Surf | `https://yorkessurf.com.au` | `false` |  | `manual_review` | `connection_error` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `medium` | `34` | Review inventory surface before any implementation work. | HTTPSConnectionPool(host='yorkessurf.com.au', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='yorkessurf.com.au', port=443): Failed to resolve 'yorkessurf.com.au' ([Errno 11001] getaddrinfo failed)")) |
| Boardcave | `https://www.boardcave.com.au` | `false` |  | `blocked` | `blocked` | `false` | `0` | large Australian surfboard marketplace |  |  | `false` | `false` | `false` | `false` | `high` | `35` | Keep blocked. Revisit only if Boardcave exposes a safe public inventory path. | High-value marketplace signal, but current access is blocked and not safe for AU nightly onboarding. |
| Beaches Apparel | `https://beachesapparel.com` | `false` |  | `unsupported` | `woocommerce` | `false` | `5` |  |  |  | `false` | `false` | `false` | `false` | `low` | `0` | Exclude from AU hardboard onboarding. | Clothing/apparel store, not suitable for Quivrr hardboard retailer inventory |
| Ocean and Earth | `https://oceanearthstore.com` | `false` |  | `unsupported` | `magento` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `low` | `0` | Exclude from AU hardboard onboarding. | Brand/accessory store, not suitable for Quivrr hardboard retailer inventory |
| Rip Curl Australia | `https://www.ripcurl.com/au` | `false` |  | `unsupported` | `magento` | `false` | `` |  |  |  | `false` | `false` | `false` | `false` | `low` | `0` | Exclude from AU hardboard onboarding. | Does not sell hardboard surfboard inventory online for Quivrr search |
