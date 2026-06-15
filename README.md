# Quivrr Backend

Python/FastAPI backend for Quivrr catalogue search, manufacturer direct availability, retailer inventory ingestion, regional rollout support, and market intelligence jobs.

Start here:

- [Architecture](ARCHITECTURE.md) explains the platform map, API, Azure resources, regional model, production jobs, pipeline boundaries, market intelligence flow, and Bodhi boundary.
- [Engineering Guide](ENGINEERING_GUIDE.md) covers local setup, environment variables, validation commands, SQL notes, deployment notes, operational runbook items, and generated output hygiene.

Production logic lives in `app.py`, `scripts/`, `scrapers/`, and `market_intelligence/`. Do not run live scrapers, imports, or database migrations unless the task explicitly calls for it.
