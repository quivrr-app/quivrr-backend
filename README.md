# Quivrr Backend

Python/FastAPI backend for Quivrr catalogue search, manufacturer direct availability, retailer inventory ingestion, regional rollout support, and market intelligence jobs.

Start here:

- [Architecture](ARCHITECTURE.md) explains the platform map, API, Azure resources, regional model, production jobs, pipeline boundaries, market intelligence flow, and Bodhi boundary.
- [Engineering Guide](ENGINEERING_GUIDE.md) covers local setup, environment variables, validation commands, SQL notes, deployment notes, operational runbook items, and generated output hygiene.
- [Regional Rollout](REGIONAL_ROLLOUT.md) defines mandatory RegionCode rules, active AU/EU/ID behavior, UK planning, validation steps, and activation guardrails.
- [Observability](docs/observability.md) defines the shared logging taxonomy, health model, and reporting scope.
- [Operations](docs/operations.md) captures the runbook for daily/weekly monitoring and local validation.
- [Alerting](docs/alerting.md) documents Azure Monitor rule intent and noise controls.

Production logic lives in `app.py`, `scripts/`, `scrapers/`, and `market_intelligence/`. Do not run live scrapers, imports, or database migrations unless the task explicitly calls for it.
