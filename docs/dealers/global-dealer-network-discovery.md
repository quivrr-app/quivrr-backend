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
