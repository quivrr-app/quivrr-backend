# United States Retailer Qualification

## Scope

Sprint 14 United States Coverage Factory using the Australia Gen 3 process:

Dealer Registry -> Discovery Engine -> Platform Detection -> Qualification -> Platform Pack -> Azure Validation -> Operations Centre -> Search

Review date: `2026-06-28`

## Current US Runtime

- `RegionCode = US`
- Current validated US runnable retailer set: `23`
- Current validated US active retailer inventory rows: `8,496`
- Current validated US importer output rows in the latest safe pass: `8,401`
- Current validated US importable raw rows in the latest safe pass: `8,291`
- Production-validated onboarding additions so far: `Reddog Surf Shop`, `Cinnamon Rainbows`, `Huntington Surf & Sport`

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
| Surfboard Broker | Shopify | 192 |
| Warm Winds | Magento/html | 172 |
| Island Water Sports | Shopify | 162 |
| Hawaiian South Shore | Shopify | 124 |
| Infinity Surfboards | Shopify | 98 |
| Cinnamon Rainbows | Custom Squarespace used inventory | 57 |
| Walden Surfboards | Shopify | 55 |
| Reddog Surf Shop | Custom Wix + JSON-LD | 39 |
| Robert August Surf Company | Shopify | 39 |
| Moment Surf Co | Shopify | 21 |
| Surf N Sea | Shopify | 20 |
| Dark Arts Surf | Shopify | 12 |
| Kimo's Surf Hut | Shopify | 10 |
| Huntington Surf & Sport | Custom Shopify stocklist JSON | 418 |

## Coverage Factory Classification

### Already Running

- `23` retailers are already runnable in the US regional stack.
- Platform split of current runnable set:
  - `18` Shopify
  - `1` BigCommerce
  - `1` Magento/html
  - `3` custom high-value paths

### Immediate Priority Injection Review

| Retailer | Production state | Platform | Board-only surface | Estimated board inventory | Supported overlap | Price / stock visibility | Dimensions / volume | Pack compatibility | Engineering effort | Priority score | Recommended path |
| --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- | ---: | --- |
| Catalyst Surf Shop | Already live | BigCommerce | `/webstore/surfboards/` plus surfboard brand categories | 2,389 runnable rows in latest safe pass | Strong | Visible | Strong dimensions, volume where available | Existing US BigCommerce pack | Already complete | 95 | Keep live, no further onboarding work needed in this sprint |
| Jack's Surfboards | Already live | Shopify | `/collections/surfboards` and `/collections/surf-shortboards` | 200 runnable rows in latest safe pass | Strong | Visible | Strong dimensions, volume where available | Existing US Shopify pack | Already complete | 88 | Keep live, no further onboarding work needed in this sprint |
| Huntington Surf & Sport | Live after production validation | Custom Shopify stocklist JSON | Public stocklist page backed by `boards.json` | 422 raw stocklist rows, 418 accepted/importable rows | Firewire, Lost, Channel Islands, Sharp Eye, Rusty, Haydenshapes, JS Industries all present | Visible | Lengths are present on 418 importable rows; volume is generally absent | Small US-only custom path using the existing custom runner | Low-to-medium | 91 | Keep live and treat it as the current reference custom stocklist path |

### Ready Shopify Follow-Up

- `Hansen Surfboards`
  Why: reachable Shopify storefront and high-value surfboard brand, but the current exposed feeds still do not yield safe board rows.
- `Encinitas Surfboards`
  Why: board-room path is real and valuable, but still needs a clean surfboard-only extraction surface.

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
  Why promoted: public Squarespace used-board pages expose direct product URLs plus JSON-LD price, availability, image, and exact dimensions. The production-validated import added `57` active US rows with `28` linked models and `13` linked sizes on first live run.

## Sprint 15 Phase 3 Promotion

- `Huntington Surf & Sport`
  Why promoted: the public HSS stocklist page exposes a dedicated `boards.json` asset with current board rows containing shaper, model, length, price, store, and condition fields. Lightweight Shopify feed inspection was misleading, but the stocklist JSON path is stable, board-specific, low-noise, and fits a small US-only custom adapter safely. The validated local pass recovered `418` importable rows from `422` raw stocklist rows, and the live Azure refresh produced `418` active US retailer rows with `228` linked models and `61` linked sizes.

## Sprint 14 Recommendation

- Treat `Reddog Surf Shop` as the first Sprint 14 US onboarding outcome for production validation.
- Keep the US strategy focused on the next highest-value retailer per existing pack instead of widening platform scope.
- Prioritise one more strong Magento promotion before building any new custom stack.
- Keep `Hansen Surfboards` and `Encinitas Surfboards` under active review because they are high-value, but do not force them live until a clean board-only path is proven.

## Updated Recommendation

- Treat `Huntington Surf & Sport` as a completed high-value US promotion and use it as the reference pattern for future stocklist-style custom retailer sources.
- Keep `Hansen Surfboards` and `Encinitas Surfboards` as high-value follow-ups, but continue to avoid force-fitting them into the runner until a board-specific path is proven.
- After HSS, return to the next best Magento promotion candidate rather than widening custom logic further.

## Risks

- The current US runtime is Shopify-heavy; quality stays high only if board-only filtering remains strict.
- Several Magento candidates look promising, but none should be promoted until they prove board pages, pricing, availability, and dimensions cleanly.
- Blocked or opaque candidates should stay out of the runner rather than lowering the retailer quality bar.
