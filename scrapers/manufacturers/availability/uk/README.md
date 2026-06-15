# UK Manufacturer Direct Availability

## RegionCode

`RegionCode = UK`

UK means United Kingdom fulfilment. UK must remain separate from EU because tax, duty, fulfilment, shipping rules, currency, and retailer relevance differ.

## Current State

This folder is a scaffold for future UK manufacturer direct availability builders. Do not run this folder as a live pipeline yet.

There are no production UK MFA builders, importers, or Azure jobs enabled from this scaffold.

## Expected Future Pattern

Future UK MFA should follow the existing AU and ID patterns:

- brand-specific builders live under this folder or brand subfolders
- generated output is written under `scrapers/manufacturers/availability/output/`
- importers live under `scripts/manufacturer_availability/`
- orchestration should be explicit, reviewed, and separate from AU, ID, and EU
- rows should use `RegionCode = UK`
- native pricing should use `PriceAmount` and `PriceCurrency`

Target config examples live in:

```text
scrapers/manufacturers/availability/config/uk_manufacturer_availability_targets.example.json
```

The example config is disabled and non-live.
