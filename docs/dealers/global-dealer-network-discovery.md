# Global Dealer Network Discovery

Generated from Sprint 8 dealer discovery on `2026-06-27`.

## Executive Summary

Quivrr now has a repeatable first-pass dealer registry workflow sitting between canonical product truth and regional inventory.

This pass reviewed official dealer or stockist sources for:

- Channel Islands
- JS Industries
- Lost
- Firewire
- Haydenshapes
- Pyzel
- DHD
- Sharp Eye
- Album
- Chilli

The executable discovery script produced `705` deduplicated dealers from reviewed official sources across live and future regions. The strongest structured sources in this pass were:

- `JS Industries` via official Storeify geojson
- `Sharp Eye` via official Storeify geojson
- `Firewire` via official Stockist APIs for AU, US, EU and UK
- `Pyzel AU/NZ` via official Stockist API

The weaker or manual-only sources were:

- `Channel Islands` global dealer page
- `Lost` dealer page from non-US egress
- `Album` with no official locator found in the current review
- `Chilli` dealer pages requiring a dedicated parser
- `Pyzel` global page, which still needs a dedicated extractor beyond AU/NZ

## Current Quivrr Retailer Coverage

Live SQL baseline used for this review:

- `AU`: `33` live retailers, `11,800` active rows
- `EU`: `12` live retailers, `12,040` active rows
- `ID`: `6` live retailers, `2,056` active rows
- `US`: `20` live retailers, `7,812` active rows

Representative live retailers by region:

- `AU`: Surfboard Empire, Beachin Surf, Natural Necessity, Onboard Store, Wicks Surf, Sanbah Surf Shop, Strapper Surf Torquay, Slimes Newcastle
- `EU`: Mundo Surf, Pukas Surf Shop, 58 Surf, Bell Surf, Surf Boss, Board Exchange, Noordzee Boardstore, Surf Corner, Tablas Surf Shop, Pop Up Surf Shop
- `ID`: White Monkey Surf, Onboard Store Indonesia, BGS Bali, Freefall Surf Industries, Boardriders Bali, Drifter Surf
- `US`: Catalyst Surf Shop, Real Watersports, Cleanline Surf, Surf Station, Jack's Surfboards, Hawaiian South Shore, Surfboard Broker, Warm Winds, Infinity Surfboards, Walden Surfboards

No new scrapers or retailer jobs were onboarded in this sprint. This report packages discovery and prioritisation only.

## Manufacturer Source Summary

Reviewed official dealer pages and current extraction status:

- `Channel Islands`
  Source: [global dealers](https://cisurfboards.com/pages/dealers), [AU dealers](https://shop-au.cisurfboards.com/pages/dealers-1)
  Status: AU reviewed and seeded. Global page still manual.
- `JS Industries`
  Source: [stockists](https://jsindustries.com/pages/stockists)
  Status: executable via Storeify geojson.
- `Lost`
  Source: [dealers](https://lostsurfboards.net/dealers/), [online dealers](https://lostsurfboards.net/online-dealers/)
  Status: global locator still geo-sensitive. Online dealer overlap preserved as manual seed.
- `Firewire`
  Source: [AU](https://aus.firewiresurfboards.com/pages/store-locator), [US](https://www.firewiresurfboards.com/pages/store-locator), [EU](https://eu.firewiresurfboards.com/pages/store-locator), [UK](https://uk.firewiresurfboards.com/pages/prestige-store-locator)
  Status: executable via Stockist APIs.
- `Haydenshapes`
  Source: [retail partners](https://www.haydenshapes.com/pages/retail-partners)
  Status: manually seeded from reviewed official partner page.
- `Pyzel`
  Source: [AU/NZ locator](https://pyzelsurf.com.au/pages/store-locator), [global locator](https://pyzelsurfboards.com/pages/store-locator)
  Status: AU/NZ executable via Stockist API. Global page still partial/manual.
- `DHD`
  Source: [USA retailers](https://dhdsurf.com/pages/usa)
  Status: manually seeded from reviewed official page.
- `Sharp Eye`
  Source: [stockists](https://sharpeyesurfboards.com/pages/stockists)
  Status: executable via Storeify geojson.
- `Album`
  Source: [brand site](https://albumsurf.com)
  Status: reviewed. No official dealer locator surfaced in this pass.
- `Chilli`
  Source: [dealers](https://www.chillisurfboards.com/dealers.php?direct=1&region=usa), [contacts](https://www.chillisurfboards.com/contacts.php?direct=1&region=usa)
  Status: dealer pages reviewed but not yet executable. Europe showroom/distributor seed preserved.

## Dealer Network By Region

Dealers discovered by planned region in this pass:

- `AU`: `139`
- `US`: `222`
- `EU`: `174`
- `ID`: `1`
- `CA`: `11`
- `UK`: `18`
- `JP`: `2`
- `NZ`: `15`
- `BR`: `3`
- `ZA`: `6`
- `MX`: `2`
- `PR`: `8`
- `HI`: `12`

## AU Candidates

Australia is already strong. Sprint 8 should not prioritise large AU onboarding. The worthwhile follow-up items are parser or governance reviews rather than broad new discovery:

- Full Circle Surf
- Red Herring Surf
- Surfection Mosman alignment review

## Australia Gen 3 Expansion Review

Sprint 9 shifts the AU workstream from broad discovery into reviewed retailer expansion. The dealer registry remains the source of truth, but retailer onboarding should only advance after site review, online stock confirmation, supported-brand confirmation, and platform assessment.

Current AU comparison point:

- Live SQL baseline: `33` active retailers, `11,800` active retailer inventory rows
- Current AU retailer config: `34` production targets, `8` parser-review targets, `12` endpoint-review targets, `3` business-disabled targets
- Current AU posture: Quivrr already has strong Tier 1 coverage, but the next uplift should come from known-but-disabled hardboard retailers before any broader stockist long tail

### Existing Coverage Review

AU retailer review outcomes split into six practical groups:

- `Already running`: Surf FX, The Board Lab, Beach Beat Alexandra Headland, Surfection Mosman and the broader current AU production set
- `Known but disabled`: Full Circle Surf, Red Herring Surf, Goodtime Surfboards, Saltwater Wine Port Macquarie, Trigger Bros Surfboards
- `Parser review`: Surf Boardroom
- `Rebranded / merged`: Zak Surfboards now resolves to Melbourne Surfboard Shop, which is already running in Quivrr
- `Manual review long tail`: Firewire / Pyzel / JS stockist entries with weak or missing website data
- `Out of scope for AU retailer inventory`: distributor-only, school-only, shaper-only, or accessory-only businesses

### Priority Retailer Review Matrix

Reviewed Sprint 9 AU priority names:

| Retailer | Website | Current coverage | Still operating | Sells surfboards | Online inventory visible | Supported brand signal | Likely platform | Scrape difficulty | Priority | Status | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Full Circle Surf | `fullcirclesurf.com.au` | Known but disabled | Yes, but primary site currently broken | Yes in brand stockist signals | No reliable live ecommerce view | JS Industries, Firewire stockist overlap | Squarespace (historic) | Medium | P2 | No online stock | Current site returned 404 in review; do not queue scraper work until a working surfboard storefront is confirmed |
| Red Herring Surf | `redherringsurf.com.au` | Known but disabled | Yes | Yes | Weak direct surfboard visibility | JS Industries, Pyzel stockist overlap | Shopify | Medium | P2 | Needs parser | Live store is active but the visible surf catalogue is mixed and current scrape path returns no usable board rows |
| Surf FX | `surffx.com.au` | Already running | Yes | Yes | Yes | Current AU production retailer | Shopify | Low | Live | Ready | Already producing surfboard inventory in production |
| Gold Coast Longboards | `goldcoastlongboards.com.au` | Missing from AU retailer queue | Yes | No hardboard focus | Yes, but for skate / surf-skate only | No supported hardboard signal | Shopify | Low | P3 | Unsupported | Not a hardboard surfboard retailer target for Quivrr AU inventory |
| Mornington Peninsula Surf | `morningtonpeninsulasurfschool.com.au` | Missing from AU retailer queue | Yes | School / lessons first | Not as a retailer inventory feed | No supported hardboard signal | Custom / brochure site | Medium | P3 | No online stock | Surf school with lessons and bookings, not a usable live retailer inventory source |
| The Surfboard Agency | `surfboardagency.com` | Missing from AU retailer queue | Yes | Yes, as a distributor | Not consumer retailer inventory | Aloha, McCoy, Rip Curl softboards and distribution portfolio | Shopify | Medium | P3 | Catalogue only | Distributor / logistics partner, not a direct AU retailer inventory target |
| The Surfboard Collective | No stable current retail site surfaced | Missing from AU retailer queue | Unclear | Historically yes | No current verified store | No current supported-brand retailer signal | Unknown | High | P3 | Closed | Current public signal points to the physical store having closed; do not queue onboarding |
| The Surfboard Room / Surf Boardroom | `surfboardroom.com.au` | Parser review | Yes | Yes | Yes | Firewire and Channel Islands stockist signal | WooCommerce | Medium | P1 | Needs parser | Boards are visible live, but the current extraction path scraped too little and failed board identification |
| Urban Surf / URBNSURF | `urbnsurf.com` ecosystem | Missing from AU retailer queue | Yes | On-site shop secondary | No verified hardboard ecommerce path | No supported hardboard retailer signal | Custom | High | P3 | Unsupported | Wave-park / venue business, not a confirmed hardboard retailer feed |
| Ocean Rhythm | No stable retail storefront surfaced | Missing from AU retailer queue | Yes as a shaping business | Custom / shaper | No structured retailer stock | House-brand / custom signal only | Custom | High | P3 | Catalogue only | Custom shaping signal, not a scalable AU retailer inventory source |
| Trigger Bros Surfboards | `triggerbrothers.com.au` | Known but disabled | Yes | Yes | Yes | Supported multi-brand surf retailer | BigCommerce | Medium | P1 | Needs parser | Clear live ecommerce presence, but current endpoint review returned zero products and needs platform-specific recovery |
| The Board Lab | `theboardlab.com.au` | Already running | Yes | Yes | Yes | Current AU production retailer | Shopify | Low | Live | Ready | Already producing strong surfboard inventory in production |
| Beach Beat | `beachbeat.com.au` | Already running | Yes | Yes | Yes | Current AU production retailer | WooCommerce | Low | Live | Ready | Already producing available hardboard rows in production |
| Goodtime Surfboards | `goodtime.com.au` | Known but disabled | Yes | Yes | Yes | Long-running AU surfboard retailer | Magento | High | P1 | Needs parser | Surfboard stock is visible, but the site is currently protected and existing scrape output returns no usable rows |
| Core Surf Australia / Core Surfboards | Social / local business only | Missing from AU retailer queue | Yes as a shaper | Yes | No verified ecommerce inventory | House-brand shaping signal | Custom | High | P3 | Catalogue only | Local shaping / custom-board signal, not a current retailer inventory feed |
| Saltwater Wine | `saltwaterwine.com.au` | Known but disabled | Yes | Yes | Weak direct surfboard visibility | JS Industries, Firewire, Pyzel stockist overlap | Shopify | Medium | P1 | Needs parser | Official stockist overlap is strong, but the public store presentation is apparel-heavy and current scrape output returned no usable board rows |
| PSC Surfboards | Social / shaping signal only | Missing from AU retailer queue | Yes as a shaper | Yes | No verified ecommerce inventory | House-brand shaping signal | Custom | High | P3 | Catalogue only | Manufacturer / shaping signal, not a retailer inventory target |
| Zak Surfboards | `zaksurfboards.com` | Rebranded / already covered | Yes | Yes | Historical site only | Zak / Melbourne Surfboard Shop | WooCommerce legacy -> Shopify current via Melbourne Surfboard Shop | Low | Covered | Rebranded | Site now redirects users to Melbourne Surfboard Shop, which is already covered by Quivrr AU inventory |

### Broader AU Dealer Registry Findings

Beyond the named Sprint 9 shortlist, the AU registry still contains a useful second wave of candidates. The best near-term manual-review names are:

- Akwa Surf
- Big Surf Australia
- Extreme Boardriders
- Overboard Surf
- Powerhouse Surf Company
- Three Stories
- Vidlers
- Willocks Surf
- Zink Surf

These all have supported-brand stockist signals, but the source data that produced the dealer registry did not carry enough stable website or ecommerce detail to move them straight into implementation. They should remain `Manual review` until each storefront is checked for:

- live hardboard inventory
- recoverable board dimensions
- stable collection or product endpoints
- clean retailer identity without multi-location duplication

### Recommended AU Onboarding Order

Priority 1 should stay focused on retailers that already have clear board inventory and sit on known ecommerce stacks:

1. Surf Boardroom
2. Trigger Bros Surfboards
3. Goodtime Surfboards
4. Saltwater Wine Port Macquarie
5. Red Herring Surf

Priority 2 should cover known retailers where the trading signal is real but the storefront signal is still incomplete:

1. Full Circle Surf
2. Akwa Surf
3. Extreme Boardriders
4. Overboard Surf
5. Willocks Surf

Priority 3 should remain out of implementation until Quivrr finishes the reviewed retailer backlog:

1. The Surfboard Agency
2. Gold Coast Longboards
3. Mornington Peninsula Surf
4. Urban Surf
5. Ocean Rhythm
6. PSC Surfboards
7. Core Surf Australia

Recommended AU rule before moving to US expansion:

- finish recovery of the known disabled AU hardboard retailers first
- keep distributor, school, shaper, and apparel businesses out of the AU retailer queue
- only promote long-tail stockist records after website and live-stock checks confirm a real retailer inventory source

## US Candidates

These appear on official manufacturer dealer sources and also align with Quivrr's existing backlog or disabled retailer list:

- Aqua East Surf Shop
- Reddog Surf Shop
- Nomad Surf Shop
- B.C. Surf & Sport
- Breakwater Surf Co
- Long Beach Surf Shop
- Farias Surf Shop
- Tamba Surf
- Hapa Surf and Skate
- Hi-Tech Surf Sports

## EU Candidates

The official-source signal is strongest from Firewire, JS and Sharp Eye, but Quivrr's best near-term Europe onboarding list still comes from the existing configured-but-disabled EU registry:

- Hart Beach
- HawaiiSurf
- Surf Pirates
- Warehouse One
- SantoLoco
- Ericeira Surf & Skate
- Blue Tomato

## ID Candidates

Indonesia discovery remained intentionally narrow in this pass. The official source review surfaced only one structured dealer record for the currently configured scope:

- White Monkey Surf governance follow-up

## Future Regions

Most credible future-region retailer signals surfaced from official Firewire and JS locator data:

- `UK`: Boardshop.co.uk, Down The Line Surf Co, Abersoch Watersports
- `CA`: Live to Surf, Kannon Beach Surf Shop
- `JP`: DLIGHT by the sea
- `NZ`: Freeride Surf & Skate, Underground Skate / Surf / Fashion

## Top Onboarding Candidates

Recommended next retailer onboarding order from this discovery pass:

### AU

1. Full Circle Surf
2. Red Herring Surf
3. Surfection Mosman alignment review

### US

1. Aqua East Surf Shop
2. Reddog Surf Shop
3. Nomad Surf Shop
4. B.C. Surf & Sport
5. Breakwater Surf Co
6. Farias Surf Shop

### EU

1. Hart Beach
2. HawaiiSurf
3. Surf Pirates
4. Warehouse One
5. SantoLoco
6. Ericeira Surf & Skate

## Already Running

Best confirmed overlaps between official dealer discovery and Quivrr live retailers:

- `AU`: Onboard Store, Sanbah Surf Shop, Surfboard Empire, Aloha Surf Manly Style, Slimes Newcastle, Surfection Mosman
- `US`: Surf Station, Jack's Surfboards, Real Watersports, Catalyst Surf Shop, Island Water Sports, Surfboard Broker, Hawaiian South Shore, Warm Winds
- `EU`: 58 Surf, Pukas Surf Shop, Board Exchange

This confirms the dealer layer is useful immediately for:

- identifying retailers Quivrr already covers
- finding official overlap for disabled or configured retailers
- identifying future-region dealers before scraper work begins

## Manual Review

Important reviewed-but-not-yet-executable sources from this pass:

- `Lost` global dealer locator still needs a US egress or a locally verified manual review flow.
- `Album` did not expose an official dealer locator in the current source review.
- `Chilli` dealer pages are region-aware but need a small dedicated parser before they become executable.
- `Channel Islands` global dealer page still needs a dedicated extractor. AU coverage is already seeded safely.
- `Pyzel` global dealer page still needs dedicated extraction beyond the AU/NZ Stockist feed.

## Blocked/Source Gaps

Current source blockers that prevented safe automation in Sprint 8:

- `Lost` global dealer page remains geo-sensitive from non-US egress.
- `Album` has no official dealer locator surfaced in this review.
- `Chilli` needs a dedicated parser before it can move from reviewed to executable.
- `Channel Islands` global dealer page is still manual.
- `Pyzel` global locator remains partial outside AU/NZ.

## Discovery Counts By Manufacturer

Dealer counts by manufacturer from reviewed sources:

- `Firewire`: `464`
- `Sharp Eye`: `99`
- `JS Industries`: `66`
- `Pyzel`: `59`
- `Haydenshapes`: `32`
- `Channel Islands`: `6`
- `Lost`: `5`
- `DHD`: `4`
- `Chilli`: `1`

## Recommendation For Implementation Order

1. Use the new dealer registry to promote the best official-overlap US backlog retailers first.
2. Use the same registry to drive the next EU onboarding shortlist.
3. Keep AU limited to targeted parser/governance reviews, not broad expansion.
4. Add small source-specific extractors next for:
   Chilli
   Channel Islands global
   Pyzel global
   Lost from US egress
5. Only after those are stable should Quivrr consider dealer-registry integration in `/api/ops/dashboard`.

## Artefacts

Source and generated artefacts for this sprint:

- `config/dealer_source_policy.json`
- `scripts/dealers/discover_global_dealer_network.py`
- `scripts/dealers/output/global_dealer_network_report.json`
- `scripts/dealers/output/global_dealer_network_report.md`

Raw generated output should remain review artefacts and should not be treated as curated documentation.
