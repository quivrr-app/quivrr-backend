# Global Coverage Report

Updated: `2026-06-29`

## 1. Executive Summary

Quivrr has now moved beyond regional architecture build-out and into global coverage expansion.

- Australia is the Gen 3 reference implementation and remains the strongest retailer region operationally.
- Europe is now a production Gen 3 region with the first Sprint 14 coverage-factory onboarding wave completed and production validated.
- United States is now an active Production Beta Gen 3 region with the first Sprint 14 coverage-factory onboarding wave completed and production validated.
- Indonesia is live and region-scoped, but coverage remains materially thinner than AU, EU, and US.

The operating priority from this point is not retailer count for its own sake. The platform should optimise for supported searchable board yield, retailer quality, safe platform-pack reuse, and production-validated regional coverage growth.

## 2. Regional Coverage Summary

Production-backed retailer and MFA counts below come from live SQL on `2026-06-29`. Refresh times come from the latest successful Azure Container App Job executions.

| Region | Status | Live Retailers | Active Retailer Inventory Rows | MFA Rows | Latest Retailer Refresh (UTC) | Latest MFA Refresh (UTC) | Current Readiness / Notes |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| AU | Production, Gen 3 reference | 36 | 12,287 | 6,706 | 2026-06-28 17:00:53 | 2026-06-28 17:04:04 | Strongest live region. Current live SQL row count is slightly below the earlier 12,291 closeout snapshot. AU expansion is parked; next AU work should be linkage uplift for Trigger Bros and Extreme rather than more retailer onboarding. |
| EU | Production, Gen 3 | 13 | 12,148 | 2,721 | 2026-06-28 13:54:53 | 2026-06-27 20:31:56 | Sprint 14 added Hart Beach. EU coverage is now broader and operationally stable, but newly added retailers still need linkage-quality follow-up after scheduled reruns. |
| US | Production Beta, Gen 3 | 21 | 8,018 | 4,682 | 2026-06-28 13:18:10 | 2026-06-27 21:04:47 | Sprint 14 added Reddog Surf Shop. US runtime is now active, job-backed, and production validated, but should still be treated as Production Beta while link quality continues to improve. |
| ID | Production, coverage-limited | 6 | 2,056 | 180 | 2026-06-27 20:31:21 | 2026-06-27 21:15:34 | Region is live and healthy, but retailer breadth is still limited. Indonesia needs dealer-source discovery before another serious onboarding wave is attempted. |

## 3. Platform Distribution

These counts are a mix of current active target registries and coverage-factory planning counts:

- AU counts are planning counts from the current AU reviewed retailer pool in `scrapers/retailers/retailer_master.json`.
- EU counts are from the current EU retailer target registry.
- US counts are from the current US retailer target registry.
- ID remains a legacy custom-script region with no confirmed platform-pack expansion candidates in this closeout.

| Platform | AU | EU | US | ID | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| Shopify | 31 | 7 | 20 | 0 | AU figure is a reviewed-pool planning count. EU and US figures are current target-registry counts. |
| WooCommerce | 15 | 1 | 1 | 0 | AU count includes parked and manual-review names in the reviewed pool. |
| BigCommerce | 2 | 0 | 1 | 0 | AU includes Trigger Bros plus one non-live reviewed candidate. |
| Magento | 4 | 1 | 1 | 0 | EU Magento currently means `58 Surf`; US Magento currently means `Warm Winds`. |
| PrestaShop | 0 | 2 | 0 | 0 | EU currently uses `Mundo Surf` and `Single Quiver`. |
| Neto / Maropost | 2 | 0 | 0 | 0 | AU only in the current reviewed pool. |
| Custom | 0 | 2 | 1 | 6 | EU custom = Surf Corner + Tablas. US custom = Reddog. ID runtime is six legacy retailer-specific builders. |
| Unknown / Manual Review | 5 | 12 | 2 | 0 | Counts represent unresolved or non-promoted registry entries, not live runtime. |

## 4. Retailer Pipeline By Region

| Region | Already Running | New In Sprint 14 | Qualified / Ready | Manual Review | Parked / Blocked | Next Best Candidates |
| --- | --- | --- | --- | --- | --- | --- |
| AU | 36 live retailers in production | None | No new AU onboarding recommended in this sprint | AU long tail remains reviewed but intentionally de-prioritised | AU is parked for coverage expansion; Trigger Bros and Extreme are live and should now be treated as linkage-quality work, not new onboarding | Trigger Bros linkage uplift, Extreme linkage uplift, AWSM governance check, Overboard parked-at-zero review, broader AU linkage uplift only if reopened |
| EU | 13 runnable retailers | Hart Beach | HawaiiSurf, Surf Pirates, Guincho Wind Factory, SantoLoco | Warehouse One, Full & Cas, Ericeira Surf & Skate, Blue Tomato | Surfshop Deutschland blocked; Deeply, Glisshop and Flysurf remain low-value or unsupported for this pass | HawaiiSurf, Surf Pirates, Guincho Wind Factory, SantoLoco, Warehouse One |
| US | 21 runnable retailers | Reddog Surf Shop | Hansen Surfboards, Encinitas Surfboards, Aqua East Surf Shop, Farias Surf Shop, Breakwater Surf Co | Nomad Surf Shop, Quality Surfboards Hawaii, Aloha Board Shop, Miller's Surf and Sport, CB Surf Shop | Ron Jon, Tamba Surf, Hi-Tech Surf Sports, K-Coast, Verde Azul, Hapa, Brave New World remain blocked | Hansen Surfboards, Encinitas Surfboards, Aqua East Surf Shop, Farias Surf Shop, Breakwater Surf Co |
| ID | 6 live retailers | None | None confirmed in Sprint 14 | Fresh dealer-registry and qualification pass required before new onboarding | Coverage-limited; no current pack-ready follow-up source is confirmed | Start with retailer-source discovery rather than implementation |

## 5. Sprint 14 Additions

| Region | Retailer | Platform | Rows Added | Azure Job | Validation | Notes |
| --- | --- | --- | ---: | --- | --- | --- |
| EU | Hart Beach | Shopify | 107 | `quivrr-nightly-eu-inventory` | Succeeded | Live and production validated. |
| US | Reddog Surf Shop | Custom Wix / structured product pages | 39 | `quivrr-nightly-us-inventory` | Succeeded | Live and production validated. |

## 6. Search And Operations Validation

Production validation completed in the Sprint 14 closeout window:

- Backend root returned `online`.
- EU live search returned HTTP `200`.
- US live search returned HTTP `200`.
- `searchVersion` remained stable:
  - `search_timeout_fix_v2_thin_fallback_v1_broader_brand_fallback_exact_gate_sprint6_1_legacy_brand_rows`
- Latest validated search smoke from this closeout:
  - EU `boardSizeId=179264` returned close matches successfully.
  - US `boardSizeId=179264` returned manufacturer-direct inventory successfully.

Operations Centre was **not directly authenticated in this closeout**. A direct unauthenticated request to `/api/ops/dashboard` returned `403 Forbidden`, so top-level Operations Centre card verification should be treated as operational follow-up rather than part of this unauthenticated report.

## 7. Coverage KPI

Quivrr should now optimise for **supported searchable boards added**, not just raw retailer count.

That means:

- a retailer with hundreds of supported, dimensioned, searchable boards is materially more valuable than multiple retailers with tiny or mostly unsupported catalogues
- platform-pack reuse should still matter, but only when it improves supported-board yield safely
- retailer prioritisation should always consider supported brand overlap, clean stock visibility, dimensions, pricing, and stable production automation

Practical rule:

> A retailer with 500 supported manufacturer boards is more valuable than ten retailers with five unsupported boards each.

## 8. Top Five Next Retailers

### Australia

Australia is mostly parked for new onboarding. The next AU work should focus on linkage quality, not retailer expansion.

| Rank | Candidate / Work Item | Current Position | Why |
| --- | --- | --- | --- |
| 1 | Trigger Bros Surfboards | Already live | Next AU value is linkage uplift, not onboarding. |
| 2 | Extreme Boardriders | Already live | Same as Trigger Bros: live scrape health is proven, linkage quality still matters. |
| 3 | AWSM Surf | Parked | Existing rows may remain, but no new AU engineering effort is justified right now. |
| 4 | Overboard Surf | Parked | Correct to remain parked at zero until supported-brand saleable stock returns. |
| 5 | AU linkage uplift | Recommended AU follow-up | If AU reopens, the best next move is improving canonical linkage for active AU rows rather than adding more low-yield retailers. |

Recommended AU position:

- No more AU retailer onboarding unless a genuinely high-value source appears.
- Next AU work should be linkage quality for Trigger Bros and Extreme.

### Europe

Ranked by expected supported-board yield, platform readiness, engineering complexity, and source reliability.

| Rank | Retailer | Platform / Path | Why Next |
| --- | --- | --- | --- |
| 1 | HawaiiSurf | Shopify signal | Best remaining France candidate on an existing low-risk platform pack. |
| 2 | Surf Pirates | Custom high-value | Germany is under-covered and this is the strongest prepared non-Shopify EU candidate. |
| 3 | Guincho Wind Factory | Shopify signal | Portugal source with likely low engineering cost and good board relevance. |
| 4 | SantoLoco | Shopify signal | Adds Germany with existing platform-pack compatibility. |
| 5 | Warehouse One | Manual review | Large upside if a clean surfboard slice can be isolated without introducing noise. |

### United States

Ranked by expected supported-board yield, platform readiness, engineering complexity, and source reliability.

| Rank | Retailer | Platform / Path | Why Next |
| --- | --- | --- | --- |
| 1 | Hansen Surfboards | Shopify follow-up | High-value storefront with strong supported-brand overlap if a clean board surface is recovered. |
| 2 | Encinitas Surfboards | Shopify board-room follow-up | One of the most valuable remaining surfboard-specific storefronts if the board-room path is isolated safely. |
| 3 | Aqua East Surf Shop | Magento follow-up | Strong East Coast retailer brand and best current Magento promotion candidate after Warm Winds. |
| 4 | Farias Surf Shop | Magento follow-up | Real surf-retailer signal with likely stronger supported-board yield than broader boardsports stores. |
| 5 | Breakwater Surf Co | Magento follow-up | Another meaningful Magento candidate that could deepen the reusable US pack. |

### Indonesia

Indonesia does not yet have a credible top-five onboarding queue from the current Sprint 14 evidence base.

| Rank | Candidate / Work Item | Current Position | Why |
| --- | --- | --- | --- |
| 1 | Fresh ID dealer-source discovery | Recommended next step | Current discovery signal is too thin to justify implementation-first work. |
| 2 | White Monkey governance follow-up | Maintenance | Existing live retailer should stay healthy, but this is not a coverage-factory expansion target. |
| 3 | Onboard Store Indonesia quality review | Maintenance | Useful only as a maintenance / linkage-quality check. |
| 4 | BGS Bali quality review | Maintenance | Same as above. |
| 5 | New ID qualification pass | Recommended | Indonesia needs source discovery and qualification before another onboarding sprint. |

## 9. Sprint 15 Recommendation

Sprint 15 should be treated as **Global Coverage Expansion**, not as a single-region sprint.

Guiding principle:

- Each sprint should pick the highest-value retailer globally based on expected supported searchable boards added, not simply work through one region in sequence.

Recommended Sprint 15 priority:

1. Highest-yield US retailer candidate
2. Highest-yield EU retailer candidate
3. Indonesia only if a meaningful online stock source is identified
4. AU only for linkage uplift or a genuinely high-value inventory source

The practical interpretation of that ranking today is:

- US and EU should continue alternating based on the next best supported-board yield
- AU should move into maintenance plus linkage quality
- ID should not consume implementation effort until dealer-source discovery produces real, qualified inventory opportunities

## 10. Risks And Open Items

- Operations Centre authenticated payload health should continue to be monitored.
- US and EU newly added retailers should have linkage quality reviewed after their next scheduled runs.
- AU Trigger Bros and Extreme have scrape health, but still need linkage uplift attention.
- Indonesia remains coverage-limited.
- The retailer partnership page form endpoint still relies on `mailto:` and should eventually move to a backend or ACS-backed path.
- Platform-pack reuse should stay disciplined; new custom paths should only be created when supported-board yield clearly justifies them.

## Source Notes

This report was curated from:

- live SQL counts for `RetailerInventory` and `ManufacturerInventory`
- latest successful Azure Container App Job executions
- `docs/dealers/europe-retailer-qualification.md`
- `docs/dealers/united-states-retailer-qualification.md`
- `docs/dealers/indonesia-retailer-qualification.md`
- `docs/dealers/australia-retailer-qualification.md`
- current regional retailer target registries

Raw generated discovery output was intentionally **not** committed as part of this closeout.
