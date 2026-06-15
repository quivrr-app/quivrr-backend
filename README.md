# Quivrr Backend

Python/FastAPI backend for Quivrr catalogue search, manufacturer direct availability, retailer inventory ingestion, and market intelligence jobs.

Start here:

- [Architecture](ARCHITECTURE.md) explains the API, SQL dependency, pipelines, deployment boundaries, and core data principles.
- [Engineering Guide](ENGINEERING_GUIDE.md) covers local setup, environment variables, validation commands, deployment notes, and temporary script hygiene.

Production logic lives in `app.py`, `scripts/`, `scrapers/`, and `market_intelligence/`. Temporary investigation scripts should not stay in the repository root.
