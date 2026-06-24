# Azure Monitor Alerting

## Critical

- Backend API unavailable
- Board Guide API unavailable
- Azure SQL unavailable
- Azure OpenAI unavailable

## High

- Latest scheduled inventory job failed
- No successful inventory refresh inside freshness window
- No successful MFA refresh inside freshness window
- Weekly catalogue refresh failed
- Region inventory drops unexpectedly
- Region leakage detected

## Medium

- BoardModelId or BoardSizeId link quality drops
- Weak Bodhi coverage increases
- Recommendation generation failures increase

## Noise Control

- Do not alert on an old failed job if a later successful run exists.
- Prefer freshness and latest-state rules over raw historical error counts.
- Only escalate repeated failures when the latest operational state is still unhealthy.
