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

Review date: `2026-06-28`

## Qualification Summary

| Retailer | Website | Platform | Supported brand signal | Approx board catalogue size | Stock visible online | Pricing visible | Variant quality | Images | Pagination | Search capability | Auth | Robots / restrictions | Scrape difficulty | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Surf Boardroom | `https://surfboardroom.com.au` | WooCommerce / WordPress | Medium: visible Channel Islands and Sharp Eye signals; broader supported-brand coverage not clearly enumerated online | `200+ in-store` claimed, but direct product-level online board catalogue is weak | Weak for live board SKUs; surfboards page is mostly editorial plus custom-order flow | Weak for boards; gift cards are priced, board catalogue pricing is not clearly exposed in the public board landing page | Weak; no strong public board variant surface found in the current online flow | Yes | No clear public board pagination observed | Yes, public site search exists | None for browsing | `robots.txt` allows search crawling, blocks AI training and standard admin/cart paths | Medium | Keep in queue, but do not take first. Real surf retailer, weak public board inventory surface. |
| Trigger Bros Surfboards | `https://triggerbrothers.com.au` | BigCommerce | Medium: strong surfboard catalogue, but public board page looks heavily weighted to Trigger house boards, customs and softboards; supported-brand overlap needs deeper model-level validation | High: public boards category shows at least `6+` pages, likely `70-100+` board listings | Yes | Yes | Medium: titles include size and board names; enough structure for parsing but not obviously canonical-ready | Yes | Yes | Yes, but `search.php` is disallowed in `robots.txt` | None for browsing | `robots.txt` disallows account/cart/checkout/search and sets `crawl-delay: 10` for many AI bots | Medium | Strong candidate for later AU uplift, but not the best first retailer if we want supported-brand coverage first. |
| Red Herring Surf | `https://redherringsurf.com.au` | Shopify storefront shell | High stockist/editorial overlap, but no retailer-distinct online surfboard inventory surface | Not countable from the Red Herring domain. Public shell links through to Board Collective inventory rather than exposing Red Herring-owned products | No retailer-distinct board stock surface found. `products.json` is empty and surfboard search returns `0` results | Board Collective pricing is visible through linked shell content, but not as a Red Herring-owned product feed | Low for distinct retailer extraction. Public shell does not expose a separate variant catalogue | Yes, via Board Collective-linked assets | No retailer-distinct pagination confirmed | Search exists, but surfboard searches return no products on the Red Herring domain | None for browsing | Public HTML repeatedly references `boardcollective.com.au`; only direct product link found resolves to Board Collective gift card | Low for implementation, high for duplication risk | Defer. Treat as a Board Collective storefront shell, not an independent AU retailer inventory source. |
| Saltwater Wine | `https://saltwaterwine.com.au` | Shopify storefront shell | High stockist/editorial overlap, but no retailer-distinct online surfboard inventory surface | Not countable from the Saltwater domain. Public shell links through to Board Collective inventory rather than exposing Saltwater-owned products | No retailer-distinct board stock surface found. `products.json` is empty and surfboard search returns `0` results | Board Collective pricing is visible through linked shell content, but not as a Saltwater-owned product feed | Low for distinct retailer extraction. Public shell does not expose a separate variant catalogue | Yes, via Board Collective-linked assets | No retailer-distinct pagination confirmed | Search exists, but surfboard searches return no products on the Saltwater domain | None for browsing | Public HTML repeatedly references `boardcollective.com.au`; only direct product link found resolves to Board Collective gift card | Low for implementation, high for duplication risk | Defer. Treat as a Board Collective storefront shell, not an independent AU retailer inventory source. |
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
- Public shell references `boardcollective.com.au` extensively across the page source
- Public Shopify `products.json` returned an empty array in this review
- Public surfboard search returned `0` results
- Public `/collections/all` produced only one direct product link, and it resolved to:
  - `https://boardcollective.com.au/products/boardcollective-egift-card`
- Public surf taxonomy is present in shell navigation, but surf collection pages and product JSON do not expose Red Herring-owned board stock
- This makes the site useful as a stockist / editorial shell, but not as a retailer-distinct Quivrr inventory source

Assessment:

- Do not onboard as an independent retailer
- Current site duplicates Board Collective merchandising and does not expose Red Herring-specific purchasable board inventory
- Correct handling is to keep Board Collective as the inventory source and defer Red Herring unless a retailer-distinct stock feed appears later

### Saltwater Wine

- Current Quivrr status: `endpoint_review`
- Existing governance reason: `No raw products returned from scrape output`
- Public shell references `boardcollective.com.au` extensively across the page source
- Public Shopify `products.json` returned an empty array in this review
- Public surfboard search returned `0` results
- Public `/collections/all` produced only one direct product link, and it resolved to:
  - `https://boardcollective.com.au/products/boardcollective-egift-card`
- Storefront remains apparel/editorial heavy and does not expose Saltwater-owned surfboard inventory independently of Board Collective

Assessment:

- Do not onboard as an independent retailer
- Current site duplicates Board Collective merchandising and does not expose Saltwater-specific purchasable board inventory
- Correct handling is to keep Board Collective as the inventory source and defer Saltwater unless a retailer-distinct stock feed appears later

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
| Trigger Bros Surfboards | Medium | High | Medium | High | Best remaining retailer-distinct ecommerce target with visible live board catalogue, pricing and pagination |
| Goodtime Surfboards | High | Medium-High | Low-Medium | Medium | Valuable raw board source, but higher engineering effort because the stack is older and noisier |

### Priority 2

| Retailer | Estimated engineering effort | Expected inventory gain | Expected coverage improvement | Platform confidence | Why it belongs here |
| --- | --- | --- | --- | --- | --- |
| Surf Boardroom | Medium | Low-Medium | Medium | High | Strong retailer, but current public site looks more like store presence and custom ordering than a scrapeable online board catalogue |

### Priority 3

| Retailer | Estimated engineering effort | Expected inventory gain | Expected coverage improvement | Platform confidence | Why it belongs here |
| --- | --- | --- | --- | --- | --- |
| Red Herring Surf | Low | None as distinct source | None while shell remains shared | High | Shared-shell merchandising duplicates Board Collective rather than exposing independent retailer inventory |
| Saltwater Wine | Low | None as distinct source | None while shell remains shared | High | Shared-shell merchandising duplicates Board Collective rather than exposing independent retailer inventory |

## Recommended First Retailer

Recommended first AU retailer for Gen 3 implementation:

1. `Trigger Bros Surfboards`

Why:

- strongest remaining blend of:
  - retailer-distinct stock
  - visible live board merchandising
  - public pricing and pagination
  - lower duplication risk than the Board Collective shell retailers

Recommended second retailer:

2. `Goodtime Surfboards`

Recommended hold order after that:

3. `Surf Boardroom`
4. `Red Herring Surf`
5. `Saltwater Wine`

## Recommendation Before Scraper Work

Before Phase 3 implementation starts:

- keep Red Herring and Saltwater out of active scraper onboarding unless they expose retailer-distinct board inventory instead of Board Collective shell content
- confirm supported-brand ratio on Trigger Bros before spending BigCommerce engineering time
- treat Surf Boardroom as a live-retailer review success but an online-inventory capture risk until product-level boards are proven public
