# US Manufacturer Direct Availability

## RegionCode

`RegionCode = US`

US means United States fulfilment. US manufacturer-direct rows must stay isolated from AU, EU, and ID and must only write to `dbo.ManufacturerInventory` with `AvailabilitySource = manufacturer_direct`.

## Current State

USA is Production Beta and now has a guarded, live MFA path.

Current safe US MFA brands:

- `JS Industries`
- `Channel Islands`
- `Pyzel`
- `Firewire`
- `Album`
- `Haydenshapes`
- `DHD`
- `Rusty`
- `Sharp Eye`
- `Christenson`
- `Misfit Shapes`
- `Chilli`
- `Pukas`

Current explicit non-US or degraded exceptions:

- `Lost`
  Direct Manufacturer Stock Not Available. Lost USA should stay out of MFA because the public site acts as a catalogue plus dealer-routing surface rather than a manufacturer-direct stock feed.
- `Chemistry`
  Still blocked in this US path.
- `Simon Anderson`
  Australia only. Do not add to US MFA unless a reliable US or worldwide source is validated later.

## Builder Pattern

The runtime entrypoint is still:

```text
scrapers/manufacturers/availability/us/build_us_shopify_availability.py
```

Despite the name, the builder now acts as the US MFA coordinator for several source types:

- Shopify JSON feeds for the original US brands
- adapted Shopify plus canonical-size enrichment for `Misfit Shapes`
- adapted Shopify title parsing for `Pukas`
- HTML stock page parsing for `Christenson`
- US storefront map plus ShaperBuddy dimension availability for `Chilli`

Additional non-Shopify US brand logic lives in:

```text
scrapers/manufacturers/availability/us/us_mfa_additional_sources.py
```

## Currency and Shipping Notes

US MFA rows keep `RegionCode = US`, but they do not force all prices to `USD`.

- `Christenson` uses US storefront pricing in `USD`
- `Chilli` uses US storefront pricing in `USD` where exposed
- `Misfit Shapes` preserves the source storefront currency
- `Pukas` preserves the source storefront currency

For worldwide or cross-region direct sources, the backend adds response metadata:

- `sourceRegionCode`
- `shippingScope`
- `shippingNote`

The US frontend uses that metadata to show a small manufacturer-card note when direct stock may ship from another region.

## Operational Guardrails

- The US MFA runner refuses any `QUIVRR_REGION_CODE` other than `US`.
- Apply mode requires `--confirm-apply-us-mfa APPLY_US_MFA`.
- Deletes are scoped by `BrandId`, `RegionCode = 'US'`, and `AvailabilitySource = 'manufacturer_direct'`.
- A degraded brand must not fail the whole US job if other brands succeed fresh.
- Stale fallback may be used for diagnostics, but only fresh brand outputs are applied back into SQL.
- The US MFA runner now supervises child build/import commands with explicit progress output and bounded timeouts.
- Each brand prints start and completion progress, and the wrapper emits heartbeat lines while a builder is still running.
- If a builder command overruns its timeout budget, the runner degrades that brand with `source_status = command_timeout` instead of hanging silently.
- The guarded importer path remains the validated SQL write path for USA MFA.
- The full US MFA wrapper has now been revalidated locally in both `dry-run` and guarded `apply` modes. It exits cleanly, preserves AU/EU/ID counts, and records degraded brands explicitly when the runner budget is exhausted.
## Regional Adaptation Assessment

- `Misfit Shapes`
  Candidate for AU, EU, and ID reuse because the current-model source is global. Keep region-specific pricing and shipping notes explicit if reused.
- `Chilli`
  Candidate for AU, EU, and ID reuse because the source stack is global and storefront-region aware. Reuse should preserve regional storefront URLs and currency evidence.
- `Pukas`
  Candidate for EU-first reuse and possible AU/ID review because the source is worldwide, but shipping and native-currency messaging must remain explicit.
- `Christenson`
  Keep US-only in this path unless a reliable AU, EU, or ID stock source is validated.
- `Lost`
  Do not treat Lost as MFA-eligible unless the official US site later exposes genuine manufacturer-direct purchasable stock. Current review evidence supports catalogue and retailer coverage only:
  - model pages such as `/surfboards/california-twin/` and `/surfboards/driver/` show descriptions, dimensions, and dealer-routing links rather than add-to-cart manufacturer inventory
  - the site has dedicated `Dealer Locator` and `Online Dealers` pages that route shoppers to retailers
  - the `Lost Custom Classics` page instructs shoppers to custom order through a nearest Lost dealer
  For now, keep Lost in the canonical catalogue and retailer inventory layers only.
