# EU Manufacturer Direct Availability

## RegionCode

`RegionCode = EU`

EU means mainland European Union fulfilment. The initial market focus is Portugal, Spain, and France, but those should not become primary `RegionCode` values yet.

## Current State

This folder is a scaffold for future EU manufacturer direct availability builders. Do not run this folder as a live pipeline yet.

There are no production EU MFA builders, importers, or Azure jobs enabled from this scaffold.

## Expected Future Pattern

Future EU MFA should follow the existing AU and ID patterns:

- brand-specific builders live under this folder or brand subfolders
- generated output is written under `scrapers/manufacturers/availability/output/`
- importers live under `scripts/manufacturer_availability/`
- orchestration should be explicit, reviewed, and separate from AU and ID
- rows should use `RegionCode = EU`
- native pricing should use `PriceAmount` and `PriceCurrency`

Target config examples live in:

```text
scrapers/manufacturers/availability/config/eu_manufacturer_availability_targets.example.json
```

The example config is disabled and non-live.
