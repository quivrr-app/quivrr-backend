# ADR: Platform Observability Framework

## Status

Accepted

## Context

Quivrr had Azure Log Analytics and operational Azure services already in place, but runtime monitoring still relied too heavily on manual checks. The platform needed low-cost observability that respected regional isolation and did not require new infrastructure.

## Decision

Adopt:

- stdout JSON structured logs for scheduled jobs and APIs
- SQL-backed freshness and coverage health calculations
- ACS email for daily and weekly platform summaries
- Azure Monitor Workbook and alert-rule guidance based on the shared event taxonomy

## Consequences

Positive:

- No new platform services required
- Region-aware monitoring is explicit
- Australia is now the Gen 3 reference implementation for rollout and dashboard expectations
- Alert noise is reduced by latest-state and freshness logic

Trade-offs:

- Local state files are a lightweight helper, not a system of record
- Some quality metrics are inferred from current SQL state instead of full historical telemetry

## Follow-up

- Consider querying Log Analytics directly in a later sprint when credentials and cost controls are formalized.
- Extend the same taxonomy to future region rollouts without changing event shape.
