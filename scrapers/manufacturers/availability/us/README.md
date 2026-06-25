# US Manufacturer Direct Availability

## RegionCode

`RegionCode = US`

US means United States fulfilment. US must be added beside AU, EU, and ID rather than folded into any existing region.

## Current State

This folder is the USA manufacturer direct availability rollout workspace. It is still guarded and non-live: no production US MFA builders, importers, SQL jobs, or Azure jobs are enabled from this path yet.

Some brand-specific US experiments already exist in-repo, but they are not treated as approved regional pipeline components until they are reviewed brand by brand. At the current state:

- `Album` has an in-repo experimental builder, but it still points at `/en-au` inventory and emits AUD pricing, so it remains blocked for `RegionCode = US`.
- The remaining approved brands are tracked through the US rollout plan and stay planning-only until their source, currency, and row shape are validated.

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

The example config is disabled and non-live. The guarded runtime wrapper writes a planning report to:

```text
scripts/manufacturer_availability/output/us_mfa_rollout_plan.json
```
