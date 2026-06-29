# Europe Retailer Qualification

## Scope

Sprint 14 Europe Coverage Factory using the Australia Gen 3 process:

Dealer Registry -> Discovery Engine -> Platform Detection -> Qualification -> Platform Pack -> Azure Validation -> Operations Centre -> Search

Review date: `2026-06-29`

## Current EU Runtime

- `RegionCode = EU`
- Current validated EU runnable retailer set: `16`
- Current validated EU active retailer inventory rows: `12,407`
- Production-validated onboarding additions so far: `Hart Beach`, `HawaiiSurf`, `SantoLoco`, `Surf Pirates`
- Sprint 14 local validation also fixed the slow but valid `Mundo Surf` category timeout path and aligned the master registry with the active PrestaShop runtime for `Mundo Surf` and `Single Quiver`

### Current Runnable Retailers

| Retailer | Platform | Country | Validated rows |
| --- | --- | --- | ---: |
| Mundo Surf | PrestaShop | Spain | 4,854 |
| Pukas Surf Shop | Shopify | Spain | 2,004 |
| Bell Surf | Shopify | Portugal | 523 |
| 58 Surf | Magento/html | Portugal | 450 |
| Single Quiver | PrestaShop | Spain | 377 |
| Surf Boss | WooCommerce | EU | 338 |
| Surf Corner | Custom Daisuke | Italy | 184 |
| Noordzee Boardstore | Shopify | Netherlands | 136 |
| Board Exchange | Shopify | Portugal | 122 |
| Hart Beach | Shopify | Netherlands | 107 |
| Pop Up Surf Shop | Shopify | Netherlands | 88 |
| SantoLoco | Shopify | Germany | 132 |
| HawaiiSurf | Shopify | France | 47 |
| Surf Pirates | Custom structured thumbnail cards | Germany | 75 |
| Tablas Surf Shop | Custom Magento cards | Spain | 86 |
| GSI Europe | Shopify | EU | 14 |

## Coverage Factory Classification

### Already Running

- `58 Surf`
- `Pukas Surf Shop`
- `Mundo Surf`
- `Bell Surf`
- `Surf Boss`
- `Surf Corner`
- `Single Quiver`
- `Board Exchange`
- `Pop Up Surf Shop`
- `Noordzee Boardstore`
- `GSI Europe`
- `Tablas Surf Shop`
- `Hart Beach`
- `HawaiiSurf`
- `SantoLoco`
- `Surf Pirates`

### Ready Shopify

- `Guincho Wind Factory`
  Why: Shopify collection path already identified; Portugal source with real surfboard orientation.

### Manual Review

- `Warehouse One`
  Why: worthwhile German retailer candidate, but current evidence is still broad boardsports rather than a proven hardboard-only surface.
- `Full & Cas`
  Why: real surf retailer signal, but no validated board feed or stable category path yet.
- `Ericeira Surf & Skate`
  Why: strong retailer brand, but the online surfboard catalogue remains unclear from the current lightweight pass.
- `Blue Tomato`
  Why: very large commerce surface with likely noise risk; valuable only if a clean supported-board slice can be isolated.

### Blocked

- `Surfshop Deutschland`
  Why: Cloudflare-managed challenge. Do not bypass.

### Unsupported Or Low Value For This Pass

- `Deeply`
  Why: current evidence skews clothing / wetsuits / accessories, not hardboard inventory.
- `Glisshop`
  Why: broad action-sports shell without a validated Quivrr surfboard surface.
- `Flysurf`
  Why: needs proof of meaningful hardboard inventory before engineering effort is justified.

## Top Five Remaining EU Onboarding Candidates

These are ranked by likely supported-board uplift, not just implementation ease.

1. `Guincho Wind Factory`
   Why now: Portugal source on a reusable Shopify path with likely low engineering cost.
2. `Warehouse One`
   Why now: high commercial value if a clean surfboard slice can be isolated, but only after review confirms it is not too noisy.
3. `Full & Cas`
   Why now: real surf retailer signal with upside if a stable board-only path can be isolated.
4. `Ericeira Surf & Skate`
   Why now: still requires review, but remains one of the more credible surf-first non-live EU sources.
5. `Blue Tomato`
   Why now: only worth it if a genuinely clean supported-board slice can be isolated from the broader boardsports surface.

## Sprint 14 Recommendation

- Keep the EU runtime centred on the existing proven pack mix: Shopify, PrestaShop, WooCommerce, Magento/html, and small custom paths.
- Treat `Hart Beach` as the first Sprint 14 EU onboarding outcome for production validation.
- Do not spend more time on new EU frameworks until the next highest-value retailer can fit an existing pack.
- `HawaiiSurf` has now completed the same production path successfully and should be treated as a proven EU Shopify onboarding outcome.
- `SantoLoco` has now completed the same production path successfully and should be treated as a proven EU Shopify onboarding outcome.
- `Surf Pirates` has now completed the same production path successfully and should be treated as a proven EU custom onboarding outcome.

## Risks

- `Mundo Surf` is high yield but slow, so timeout budgets must remain explicit.
- The first Azure execution in this slice failed on a transient `Mundo Surf` discovery collapse before a clean retry succeeded. Treat this as an EU runtime fragility signal to monitor rather than a blocker for Surf Pirates itself.
- Several high-value German and French candidates still need proof that they expose real hardboard inventory rather than broad boardsports shells.
- Cloudflare-protected retailers should remain blocked rather than being forced through brittle workarounds.
