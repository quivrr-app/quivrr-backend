# USA Container Jobs Plan

This document captures the reviewed Azure Container Apps Job command plan for a future manual USA rollout. No Azure commands were run.

## Current recommendation

- Candidate inventory job: `quivrr-nightly-us-inventory`
- Current scope: USA retailer inventory only
- Deferred: USA manufacturer availability job
  Reason: do not create a USA MFA nightly job until at least one US MFA brand is implemented and validated

## Shared assumptions

- Resource group: `quivrr-production-rg`
- Container Apps environment: `quivrr-jobs-env`
- Image: `quivrracrprod.azurecr.io/quivrr-inventory-job:latest`
- Region env var: `QUIVRR_REGION_CODE=US`
- SQL env pattern: same as EU and ID
  `SQL_SERVER=quivrr-sql-prod.database.windows.net`
  `SQL_DATABASE=quivrr-db-prod`
  `SQL_USERNAME=<runtime env value>`
  `SQL_PASSWORD=secretref:sql-password`
  `SQL_DRIVER=ODBC Driver 18 for SQL Server`
- Registry secret: `acr-password`
- SQL secret: `sql-password`
- Logging: stdout must remain Log Analytics compatible structured output
- Current sizing recommendation for ~7.9k normalised rows / ~7.8k importable rows:
  `--cpu 2.0 --memory 4Gi`

## Scheduled job command

Use the existing inventory job image and run guarded US apply through the regional runner:

```powershell
az containerapp job create `
  --name quivrr-nightly-us-inventory `
  --resource-group quivrr-production-rg `
  --environment quivrr-jobs-env `
  --trigger-type Schedule `
  --cron-expression "30 21 * * *" `
  --replica-timeout 14400 `
  --replica-retry-limit 1 `
  --replica-completion-count 1 `
  --parallelism 1 `
  --image quivrracrprod.azurecr.io/quivrr-inventory-job:latest `
  --cpu 2.0 `
  --memory 4Gi `
  --command python `
  --args scripts/usa/run_us_retailer_inventory_refresh.py apply --confirm-apply-us APPLY_US `
  --registry-server quivrracrprod.azurecr.io `
  --registry-username <acr-username> `
  --registry-password secretref:acr-password `
  --secrets "sql-password=<sql-password>" "acr-password=<acr-password>" `
  --env-vars `
    SQL_SERVER=quivrr-sql-prod.database.windows.net `
    SQL_DATABASE=quivrr-db-prod `
    SQL_USERNAME=<sql-username> `
    SQL_PASSWORD=secretref:sql-password `
    SQL_DRIVER="ODBC Driver 18 for SQL Server" `
    QUIVRR_REGION_CODE=US
```

## Manual validation command

Before scheduling nightly execution, validate with a manual one-off start against the same image and env pattern:

```powershell
az containerapp job start `
  -n quivrr-nightly-us-inventory `
  -g quivrr-production-rg `
  --command python `
  --args scripts/usa/run_us_retailer_inventory_refresh.py dry-run
```

## Guardrails

- The runtime must keep `QUIVRR_REGION_CODE=US`; the US runner refuses any other region code.
- Apply mode is guarded and requires `--confirm-apply-us APPLY_US`.
- SQL apply remains blocked pending explicit rollout approval and Azure SQL access from the approved runtime.
- No USA MFA job should be created from this plan yet.
