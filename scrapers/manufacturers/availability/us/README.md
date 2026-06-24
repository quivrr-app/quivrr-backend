# US Manufacturer Direct Availability

## RegionCode

`RegionCode = US`

US means United States fulfilment. US must be added beside AU, EU, and ID rather than folded into any existing region.

## Current State

This folder is a scaffold for future USA manufacturer direct availability rollout work. Phase 1 does not enable any production US MFA builders, importers, SQL jobs, or Azure jobs.

Some brand-specific US experiments already exist in-repo, but they are not treated as approved regional pipeline components from this scaffold until they are reviewed brand by brand.

## Expected Future Pattern

Future US MFA should follow the reviewed regional pattern:

- brand-specific builders live under `scrapers/manufacturers/availability/`
- generated output is written under `scrapers/manufacturers/availability/output/`
- importers live under `scripts/manufacturer_availability/`
- orchestration should be explicit, reviewed, and separate from AU, EU, and ID
- rows should use `RegionCode = US`
- native pricing should use `PriceAmount` and `PriceCurrency`

Target config examples live in:

```text
scrapers/manufacturers/availability/config/us_manufacturer_availability_targets.example.json
```

The example config is disabled and non-live.
