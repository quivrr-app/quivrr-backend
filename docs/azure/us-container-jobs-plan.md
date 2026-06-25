# USA Container Jobs Plan

This document now captures the live USA Azure Container Apps Jobs and the command pattern used to create and validate them.

## Current recommendation

- Inventory job: `quivrr-nightly-us-inventory`
- Manufacturer availability job: `quivrr-us-mfr-availability`
- Current scope: USA retailer inventory plus guarded USA manufacturer availability
- Current status: both jobs created, manually executed, and validated successfully on 2026-06-25 UTC

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
- Current sizing recommendation for ~7.9k normalised rows / ~7.8k importable retailer rows:
  `--cpu 2.0 --memory 4Gi`
- Current sizing recommendation for ~4.1k validated US MFA rows across JS Industries, Channel Islands, Pyzel, Firewire, Album, Haydenshapes, DHD, Rusty, and Sharp Eye:
  `--cpu 2.0 --memory 4Gi`
- US MFA fresh-build policy: a throttled or temporarily unavailable brand may degrade to a stale-output fallback, but only fresh brand outputs are applied back into SQL.
- Degraded brands must emit structured warning events and must not have their existing US `ManufacturerInventory` rows deleted during that run.

## Nightly order

Run manufacturer availability before retailer inventory:

1. `quivrr-us-mfr-availability`
2. `quivrr-nightly-us-inventory`

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

Use a manual one-off start against the same image and env pattern for operational validation:

```powershell
az containerapp job start `
  -n quivrr-nightly-us-inventory `
  -g quivrr-production-rg `
  --command python `
  --args scripts/usa/run_us_retailer_inventory_refresh.py dry-run
```

## Live schedules

- `quivrr-us-mfr-availability`: `0 21 * * *`
- `quivrr-nightly-us-inventory`: `30 21 * * *`

## Validation status

- MFA job execution succeeded after the refreshed `quivrr-inventory-job:latest` image was pushed to ACR.
- Inventory job execution succeeded after importer rollback and apply-report serialization was made JSON-safe for `Decimal` and `datetime` values.
- Structured stdout events were confirmed in Log Analytics for both jobs.
- Region safety was confirmed from the inventory apply logs: AU, EU, and ID row counts were unchanged before and after the US inventory run.

## Guardrails

- The runtime must keep `QUIVRR_REGION_CODE=US`; the US runner refuses any other region code.
- Apply mode is guarded and requires `--confirm-apply-us APPLY_US`.
- US MFA apply mode is separately guarded and requires `--confirm-apply-us-mfa APPLY_US_MFA`.
- SQL apply is now enabled only through the guarded runtime commands shown here and still requires explicit confirmation tokens inside the job args.

## Manufacturer availability job command

Use the same shared inventory image and run the validated US MFA pipeline:

```powershell
az containerapp job create `
  --name quivrr-us-mfr-availability `
  --resource-group quivrr-production-rg `
  --environment quivrr-jobs-env `
  --trigger-type Schedule `
  --cron-expression "0 21 * * *" `
  --replica-timeout 14400 `
  --replica-retry-limit 1 `
  --replica-completion-count 1 `
  --parallelism 1 `
  --image quivrracrprod.azurecr.io/quivrr-inventory-job:latest `
  --cpu 2.0 `
  --memory 4Gi `
  --command python `
  --args scripts/manufacturer_availability/run_us_manufacturer_availability_pipeline.py apply --confirm-apply-us-mfa APPLY_US_MFA `
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

## Manufacturer availability manual validation

```powershell
az containerapp job start `
  -n quivrr-us-mfr-availability `
  -g quivrr-production-rg `
  --command python `
  --args scripts/manufacturer_availability/run_us_manufacturer_availability_pipeline.py dry-run
```
