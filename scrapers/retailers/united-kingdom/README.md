# Quivrr United Kingdom Retailer Ingestion

## RegionCode

`RegionCode = UK`

UK means the United Kingdom fulfilment market. It must stay separate from EU because tax, duty, fulfilment, currency, shipping rules, and retailer relevance differ.

## Current State

This folder is a scaffold for future UK retailer onboarding and scraper development. There are no live UK retailer scraper entrypoints yet.

Do not move AU runtime files into this structure. AU remains the production reference implementation, but UK must be validated separately.

## Future Retailer Scraper Expectations

Future UK retailer scrapers should:

- write `RegionCode = UK`
- preserve native currency in `PriceAmount` and `PriceCurrency`
- use UK-specific retailer relevance and fulfilment rules
- avoid being grouped into EU search or inventory behavior
- emit generated output under an `output/` folder
- provide a small reviewed fixture only if needed for tests
- remain disconnected from production imports until explicitly approved

## Generated Output Hygiene

Generated UK output should not be committed unless intentionally promoted to a reviewed fixture or seed file.

Treat these as generated:

- `output/*.json`
- raw downloaded pages
- probe outputs
- temporary inspection files
- local logs
