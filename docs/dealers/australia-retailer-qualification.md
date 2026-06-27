# Australia Retailer Qualification

## Scope

Sprint 10 Phase 1 qualification for the five Australia Priority 1 retailer candidates:

1. Surf Boardroom
2. Trigger Bros Surfboards
3. Red Herring Surf
4. Saltwater Wine
5. Goodtime Surfboards

This pass is review-first only. No scraper has been onboarded from this document.

## Method

Evidence used:

- Current Quivrr retailer governance state in `scrapers/retailers/retailer_master.json`
- Existing platform detection in `scrapers/retailers/retailer_platform_detection_report.json`
- Live public website inspection
- Public `robots.txt` and public product/category endpoints where available

Review date: `2026-06-27`

## Qualification Summary

| Retailer | Website | Platform | Supported brand signal | Approx board catalogue size | Stock visible online | Pricing visible | Variant quality | Images | Pagination | Search capability | Auth | Robots / restrictions | Scrape difficulty | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Surf Boardroom | `https://surfboardroom.com.au` | WooCommerce / WordPress | Medium: visible Channel Islands and Sharp Eye signals; broader supported-brand coverage not clearly enumerated online | `200+ in-store` claimed, but direct product-level online board catalogue is weak | Weak for live board SKUs; surfboards page is mostly editorial plus custom-order flow | Weak for boards; gift cards are priced, board catalogue pricing is not clearly exposed in the public board landing page | Weak; no strong public board variant surface found in the current online flow | Yes | No clear public board pagination observed | Yes, public site search exists | None for browsing | `robots.txt` allows search crawling, blocks AI training and standard admin/cart paths | Medium | Keep in queue, but do not take first. Real surf retailer, weak public board inventory surface. |
| Trigger Bros Surfboards | `https://triggerbrothers.com.au` | BigCommerce | Medium: strong surfboard catalogue, but public board page looks heavily weighted to Trigger house boards, customs and softboards; supported-brand overlap needs deeper model-level validation | High: public boards category shows at least `6+` pages, likely `70-100+` board listings | Yes | Yes | Medium: titles include size and board names; enough structure for parsing but not obviously canonical-ready | Yes | Yes | Yes, but `search.php` is disallowed in `robots.txt` | None for browsing | `robots.txt` disallows account/cart/checkout/search and sets `crawl-delay: 10` for many AI bots | Medium | Strong candidate for later AU uplift, but not the best first retailer if we want supported-brand coverage first. |
| Red Herring Surf | `https://redherringsurf.com.au` | Shopify | High: visible surfboard taxonomy, multi-store surf retail signal, public content references Firewire and other supported-board discussion, plus prior stockist overlap for JS / Pyzel / Firewire | Medium, but public JSON feed is not exposing products. Board taxonomy is visible, exact board count is not currently countable from the simple Shopify feed | Partially. Board categories are public, but `products.json` currently returns an empty array | Category and product pricing are visible in public snippets and public pages | Medium: board categories are clear, but variant extraction likely needs collection HTML or alternate storefront surface | Yes | Not clearly confirmed from the public shell, but the store is category-driven and likely paginated | Yes | None for browsing | Shopify storefront policy allows public HTML, but standard AJAX/catalog shortcuts are limited; `products.json` returns empty | Medium-High | Best first AU implementation candidate. Highest likely supported-brand coverage upside if the public collection path can be recovered safely. |
| Saltwater Wine | `https://saltwaterwine.com.au` | Shopify | High: same surf retail family as Red Herring, strong supported-brand editorial overlap including JS / Pyzel / Firewire / Channel Islands references | Medium, but exact online board count is not currently countable from the public feed | Partially. Board taxonomy is visible, but `products.json` currently returns an empty array | Public pricing is visible on live pages and snippets | Medium: likely recoverable, but current simple feed path is empty and the storefront is apparel-heavy | Yes | Not clearly confirmed from the public shell | Yes | None for browsing | Shopify storefront policy allows public HTML, but standard AJAX/catalog shortcuts are limited; `products.json` returns empty | Medium-High | Second-best AU implementation candidate, especially if it can reuse the same recovery path as Red Herring. |
| Goodtime Surfboards | `https://www.goodtime.com.au` | Legacy OpenCart-style stack currently classified as Magento in Quivrr reports | Low-Medium: public category pages are dominated by Goodtime house boards; supported-brand overlap is not strong from the visible board catalogue | Medium-High: visible dozens of public board products and category pagination controls | Yes | Yes | High for raw parsing: titles include dimensions and litres, but the stack is brittle and old | Yes | Yes | Yes | None for browsing | No useful `robots.txt` found; public pages render with visible template warnings and older storefront patterns | High | Valuable raw board source, but not the first AU Gen 3 retailer. Engineering cost is high and supported-brand coverage looks weaker than Red Herring / Saltwater. |

## Retailer Notes

### Surf Boardroom

- Current Quivrr status: `parser_review`
- Existing governance reason: `Products scraped but surfboard filter did not identify boards`
- Public surfboards page says `With over 200+ boards in-store`
- Current public online experience looks more like:
  - editorial landing page
  - custom order workflow
  - in-store stock signal
  - weak product-level public board inventory
- Public WooCommerce Store API is live, but the simple surface returned gift cards rather than a usable live hardboard catalogue

Assessment:

- Strong real-world retailer
- Weak current public board inventory surface
- Not the best first AU Gen 3 implementation target unless a cleaner board product endpoint is found

### Trigger Bros Surfboards

- Current Quivrr status: `endpoint_review`
- Existing governance reason: `No raw products returned from scrape output`
- Public board category is clearly live and paginated
- Public board page shows:
  - explicit board listings
  - public pricing
  - visible images
  - page navigation through at least six pages
- Constraint:
  - public catalogue appears to lean heavily toward Trigger house shapes, customs, used boards and softboard-adjacent inventory
  - supported-brand uplift is less certain than the raw board count suggests

Assessment:

- Good retailer source
- Real online stock
- Likely recoverable through a focused BigCommerce path
- Better as a second-wave AU uplift than as the very first target

### Red Herring Surf

- Current Quivrr status: `endpoint_review`
- Existing governance reason: `No raw products returned from scrape output`
- Public surf taxonomy is strong:
  - shortboards
  - mid lengths
  - longboards
  - softboards
- Multi-store retail signal is strong across Tasmania
- Public Shopify `products.json` returned an empty array in this review
- Store FAQ and fulfilment copy confirm a shared store-based fulfilment model across Red Herring / Saltwater / Stormriders

Assessment:

- High-value AU candidate because:
  - supported-brand overlap is more likely
  - online surfboard merchandising is clearly real
  - solving this path may also unlock Saltwater Wine
- Best first AU implementation candidate

### Saltwater Wine

- Current Quivrr status: `endpoint_review`
- Existing governance reason: `No raw products returned from scrape output`
- Same storefront family and fulfilment network characteristics as Red Herring
- Public editorial content directly references supported-board use cases and models such as:
  - JS
  - Pyzel
  - Firewire
  - Channel Islands
- Public Shopify `products.json` returned an empty array in this review
- Storefront is more apparel-heavy than Red Herring, so surfboard extraction needs stronger filtering

Assessment:

- Strong second target after Red Herring
- Very likely to benefit from the same extraction path once Red Herring is proven

### Goodtime Surfboards

- Current Quivrr status: `endpoint_review`
- Existing governance reason: `No raw products returned from scrape output`
- Public board category pages show:
  - explicit board titles
  - dimensions
  - litre values
  - prices
  - images
  - category pagination / sort controls
- Constraint:
  - stack is older and noisy
  - public pages currently emit theme/template warnings
  - visible inventory is dominated by Goodtime house models

Assessment:

- Strong raw inventory source
- High engineering effort
- Lower supported-brand payoff than Red Herring / Saltwater

## Ranked Onboarding Queue

### Priority 1

| Retailer | Estimated engineering effort | Expected inventory gain | Expected coverage improvement | Platform confidence | Why it belongs here |
| --- | --- | --- | --- | --- | --- |
| Red Herring Surf | Medium-High | Medium | High | High | Best supported-brand upside and likely unlock path for another retailer on the same storefront family |
| Saltwater Wine | Medium-High | Medium | High | High | Shared Shopify family with Red Herring; strong editorial and stockist overlap with supported brands |

### Priority 2

| Retailer | Estimated engineering effort | Expected inventory gain | Expected coverage improvement | Platform confidence | Why it belongs here |
| --- | --- | --- | --- | --- | --- |
| Trigger Bros Surfboards | Medium | High | Medium | High | Live online board catalogue is clearly visible and paginated, but supported-brand alignment is less obvious |
| Goodtime Surfboards | High | Medium-High | Low-Medium | Medium | Public board pages are rich, but stack quality is brittle and supported-brand overlap appears weaker |

### Priority 3

| Retailer | Estimated engineering effort | Expected inventory gain | Expected coverage improvement | Platform confidence | Why it belongs here |
| --- | --- | --- | --- | --- | --- |
| Surf Boardroom | Medium | Low-Medium | Medium | High | Strong retailer, but current public site looks more like store presence and custom ordering than a scrapeable online board catalogue |

## Recommended First Retailer

Recommended first AU retailer for Gen 3 implementation:

1. `Red Herring Surf`

Why:

- strongest blend of:
  - supported-brand relevance
  - clear live surfboard merchandising
  - public non-auth board taxonomy
  - likely reusable recovery path for `Saltwater Wine`

Recommended second retailer:

2. `Saltwater Wine`

Recommended hold order after that:

3. `Trigger Bros Surfboards`
4. `Goodtime Surfboards`
5. `Surf Boardroom`

## Recommendation Before Scraper Work

Before Phase 3 implementation starts:

- confirm whether Red Herring and Saltwater are best recovered from:
  - public collection HTML
  - Shopify storefront alternate JSON surfaces
  - Shopify MCP / UCP if appropriate for internal ingestion
- confirm supported-brand ratio on Trigger Bros before spending BigCommerce engineering time
- treat Surf Boardroom as a live-retailer review success but an online-inventory capture risk until product-level boards are proven public
