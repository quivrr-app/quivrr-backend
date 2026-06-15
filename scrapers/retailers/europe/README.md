# Quivrr Europe Retailer Ingestion

## RegionCode

`RegionCode = EU`

EU means the mainland European Union fulfilment market. It represents fulfilment and search relevance, not only geography.

Initial market focus:

- Portugal
- Spain
- France

The United Kingdom is excluded. UK fulfilment must use `RegionCode = UK` and must not be grouped into EU.

## Current State

This folder is a scaffold for future EU retailer onboarding and scraper development. There are no live EU retailer scraper entrypoints yet.

Do not move AU runtime files into this structure. AU remains the production reference implementation, but EU must be validated separately for retailer relevance, shipping, tax, duty, currency, and data quality.

## Future Retailer Scraper Expectations

Future EU retailer scrapers should:

- write `RegionCode = EU`
- preserve native currency in `PriceAmount` and `PriceCurrency`
- capture country or submarket metadata such as Portugal, Spain, or France without creating primary `PT`, `ES`, or `FR` RegionCode values
- avoid assuming AU title, price, or shipping conventions
- emit generated output under an `output/` folder
- provide a small reviewed fixture only if needed for tests
- remain disconnected from production imports until explicitly approved

## Generated Output Hygiene

Generated EU output should not be committed unless intentionally promoted to a reviewed fixture or seed file.

Treat these as generated:

- `output/*.json`
- raw downloaded pages
- probe outputs
- temporary inspection files
- local logs
