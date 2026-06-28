# United States Retailer Qualification

## Scope

Sprint 14 United States Coverage Factory using the Australia Gen 3 process:

Dealer Registry -> Discovery Engine -> Platform Detection -> Qualification -> Platform Pack -> Azure Validation -> Operations Centre -> Search

Review date: `2026-06-28`

## Current US Runtime

- `RegionCode = US`
- Current validated US runnable retailer set: `21`
- Current validated US normalised rows: `7,948`
- Current validated US importable raw rows: `7,838`
- Sprint 14 addition in this slice: `Reddog Surf Shop`

### Current Runnable Retailers

| Retailer | Platform | Validated rows |
| --- | --- | ---: |
| Catalyst Surf Shop | BigCommerce | 2,404 |
| Real Watersports | Shopify | 2,034 |
| Bing Surfboards | Shopify | 958 |
| Cleanline Surf | Shopify | 439 |
| Stewart Surfboards | Shopify | 310 |
| Degree 33 Surfboards | Shopify | 263 |
| Surf Station | Shopify | 223 |
| Bird's Surf Shed | Shopify | 213 |
| Jack's Surfboards | Shopify | 200 |
| Warm Winds | Magento/html | 172 |
| Island Water Sports | Shopify | 162 |
| Surfboard Broker | Shopify | 138 |
| Hawaiian South Shore | Shopify | 116 |
| Infinity Surfboards | Shopify | 109 |
| Walden Surfboards | Shopify | 63 |
| Reddog Surf Shop | Custom Wix + JSON-LD | 39 |
| Robert August Surf Company | Shopify | 39 |
| Moment Surf Co | Shopify | 21 |
| Surf N Sea | Shopify | 20 |
| Kimo's Surf Hut | Shopify | 13 |
| Dark Arts Surf | Shopify | 12 |

## Coverage Factory Classification

### Already Running

- `22` retailers are already runnable in the US regional stack.
- Platform split of current runnable set:
  - `18` Shopify
  - `1` BigCommerce
  - `1` Magento/html
  - `2` custom high-value paths

### Ready Shopify Follow-Up

- `Hansen Surfboards`
  Why: reachable Shopify storefront and high-value surfboard brand, but the current exposed feeds still do not yield safe board rows.
- `Encinitas Surfboards`
  Why: board-room path is real and valuable, but still needs a clean surfboard-only extraction surface.
- `Cinnamon Rainbows`
  Why: known surfboard retailer, but the current lightweight validation did not yet recover a safe importable set.

### Ready Magento

- `Aqua East Surf Shop`
- `Breakwater Surf Co`
- `Lucky Dog Surf Co`
- `Farias Surf Shop`
- `Bayfront Boards`
- `Surf Zone Puerto Rico`

Common reason: Magento storefront markers are present, but the current US regional stack still needs the next reviewed Magento promotion after `Warm Winds`.

### Ready WooCommerce

- `Heritage Surf & Sport`
- `808 Boards`

Common reason: WooCommerce signals exist, but the current public category or Store API paths did not yet produce safe surfboard rows.

### Manual Review / Opaque

- `Nomad Surf Shop`
- `Quality Surfboards Hawaii`
- `Aloha Board Shop`
- `Miller's Surf and Sport`
- `CB Surf Shop`

### Blocked

- `Ron Jon Surf Shop`
- `Tamba Surf`
- `Hi-Tech Surf Sports`
- `K-Coast Surf Shop`
- `Verde Azul Surf Shop`
- `Hapa Surf and Skate`
- `Brave New World`

## Top Five Remaining US Onboarding Candidates

These are ranked by likely supported-board uplift, not by which one is easiest to scrape.

1. `Hansen Surfboards`
   Why now: historically meaningful board-room inventory and strong supported-brand overlap if a clean collection path is found.
2. `Encinitas Surfboards`
   Why now: one of the most valuable remaining surfboard-specific storefronts if the board-room path can be isolated safely.
3. `Aqua East Surf Shop`
   Why now: strong East Coast retailer brand and the best current Magento candidate to follow `Warm Winds`.
4. `Farias Surf Shop`
   Why now: real surf retailer signal plus Magento detection; likely better supported-board yield than generic broad-sports shops.
5. `Breakwater Surf Co`
   Why now: another meaningful Magento retailer candidate that could expand the reusable US pack if the board surface validates.

## Sprint 15 Wave 1 Addition

- `Cinnamon Rainbows`
  Why promoted: public Squarespace used-board pages expose direct product URLs plus JSON-LD price, availability, image, and exact dimensions. That makes it a high-value US custom path with real searchable used-board upside and low ambiguity.

## Sprint 14 Recommendation

- Treat `Reddog Surf Shop` as the first Sprint 14 US onboarding outcome for production validation.
- Keep the US strategy focused on the next highest-value retailer per existing pack instead of widening platform scope.
- Prioritise one more strong Magento promotion before building any new custom stack.
- Keep `Hansen Surfboards` and `Encinitas Surfboards` under active review because they are high-value, but do not force them live until a clean board-only path is proven.

## Risks

- The current US runtime is Shopify-heavy; quality stays high only if board-only filtering remains strict.
- Several Magento candidates look promising, but none should be promoted until they prove board pages, pricing, availability, and dimensions cleanly.
- Blocked or opaque candidates should stay out of the runner rather than lowering the retailer quality bar.
