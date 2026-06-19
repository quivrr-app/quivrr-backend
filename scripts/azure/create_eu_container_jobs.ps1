[CmdletBinding()]
param(
    [switch]$Apply,
    [string]$ResourceGroup = "quivrr-production-rg",
    [string]$Environment = "quivrr-jobs-env",
    [string]$Image = "quivrracrprod.azurecr.io/quivrr-inventory-job:latest"
)

$ErrorActionPreference = "Stop"

$jobs = @(
    @{
        Name = "quivrr-nightly-eu-inventory"
        Cron = "30 19 * * *"
        Timeout = "14400"
        Runner = "scripts/europe/run_eu_retailer_inventory_refresh.py"
    },
    @{
        Name = "quivrr-eu-mfr-availability"
        Cron = "30 20 * * *"
        Timeout = "14400"
        Runner = "scripts/manufacturer_availability/run_eu_manufacturer_availability_pipeline.py"
    }
)

function Show-Plan {
    param([hashtable]$Job)
    Write-Host ""
    Write-Host "Job:      $($Job.Name)"
    Write-Host "Schedule: $($Job.Cron) UTC"
    Write-Host "Image:    $Image"
    Write-Host "Command:  python $($Job.Runner) apply"
}

function Assert-AzSuccess {
    param([string]$Operation)
    if ($LASTEXITCODE -ne 0) {
        throw "Azure CLI failed during: $Operation"
    }
}

foreach ($job in $jobs) {
    Show-Plan -Job $job
}

if (-not $Apply) {
    Write-Host ""
    Write-Host "Preview only. No Azure resources were changed."
    Write-Host "After review, set QUIVRR_SQL_USERNAME and QUIVRR_SQL_PASSWORD, then rerun with -Apply."
    exit 0
}

$requiredRuntimeFiles = @(
    "scripts/europe/run_eu_retailer_inventory_refresh.py",
    "scripts/europe/import_eu_retailer_inventory.py",
    "scrapers/retailers/europe/run_eu_retailer_discovery.py",
    "scrapers/retailers/europe/prestashop/discover_eu_prestashop_products.py",
    "scripts/manufacturer_availability/run_eu_manufacturer_availability_pipeline.py",
    "scripts/manufacturer_availability/import_eu_manufacturer_availability.py",
    "scrapers/manufacturers/availability/eu/build_eu_shopify_availability.py"
)
foreach ($path in $requiredRuntimeFiles) {
    if (-not (Test-Path $path)) {
        throw "Required runtime file is missing: $path"
    }
    git ls-files --error-unmatch -- $path 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Required runtime file is not tracked and cannot be present in the deployed image: $path"
    }
    git diff --quiet -- $path
    if ($LASTEXITCODE -ne 0) {
        throw "Required runtime file has uncommitted changes, so local validation does not match the deployed image: $path"
    }
}

if ([string]::IsNullOrWhiteSpace($env:QUIVRR_SQL_USERNAME)) {
    throw "QUIVRR_SQL_USERNAME must be provided through the process environment."
}
if ([string]::IsNullOrWhiteSpace($env:QUIVRR_SQL_PASSWORD)) {
    throw "QUIVRR_SQL_PASSWORD must be provided through the process environment."
}

az account show --only-show-errors --output none
Assert-AzSuccess -Operation "Azure account validation"
az containerapp env show `
    --name $Environment `
    --resource-group $ResourceGroup `
    --only-show-errors `
    --output none
Assert-AzSuccess -Operation "Container Apps environment validation"

$acrName = ($Image -split "\.")[0]
$acrServer = "$acrName.azurecr.io"
$acrUsername = az acr credential show --name $acrName --query username --output tsv
Assert-AzSuccess -Operation "ACR username lookup"
$acrPassword = az acr credential show --name $acrName --query "passwords[0].value" --output tsv
Assert-AzSuccess -Operation "ACR password lookup"
if ([string]::IsNullOrWhiteSpace($acrUsername) -or [string]::IsNullOrWhiteSpace($acrPassword)) {
    throw "Could not obtain ACR credentials for $acrName."
}

$commonEnv = @(
    "SQL_SERVER=quivrr-sql-prod.database.windows.net",
    "SQL_DATABASE=quivrr-db-prod",
    "SQL_USERNAME=$($env:QUIVRR_SQL_USERNAME)",
    "SQL_PASSWORD=secretref:sql-password",
    "SQL_DRIVER=ODBC Driver 18 for SQL Server",
    "QUIVRR_REGION_CODE=EU"
)

foreach ($job in $jobs) {
    $matchingJobs = az containerapp job list `
        --resource-group $ResourceGroup `
        --query "[?name=='$($job.Name)'] | length(@)" `
        --output tsv `
        --only-show-errors
    Assert-AzSuccess -Operation "existing job lookup for $($job.Name)"
    $exists = [int]$matchingJobs -gt 0

    if (-not $exists) {
        az containerapp job create `
            --name $job.Name `
            --resource-group $ResourceGroup `
            --environment $Environment `
            --trigger-type Schedule `
            --cron-expression $job.Cron `
            --replica-timeout $job.Timeout `
            --replica-retry-limit 1 `
            --replica-completion-count 1 `
            --parallelism 1 `
            --image $Image `
            --cpu 2.0 `
            --memory 4Gi `
            --command python `
            --args $job.Runner apply `
            --registry-server $acrServer `
            --registry-username $acrUsername `
            --registry-password secretref:acr-password `
            --secrets "sql-password=$($env:QUIVRR_SQL_PASSWORD)" "acr-password=$acrPassword" `
            --env-vars $commonEnv `
            --only-show-errors `
            --output none
        Assert-AzSuccess -Operation "create $($job.Name)"
    }
    else {
        az containerapp job secret set `
            --name $job.Name `
            --resource-group $ResourceGroup `
            --secrets "sql-password=$($env:QUIVRR_SQL_PASSWORD)" "acr-password=$acrPassword" `
            --only-show-errors `
            --output none
        Assert-AzSuccess -Operation "set secrets for $($job.Name)"
        az containerapp job registry set `
            --name $job.Name `
            --resource-group $ResourceGroup `
            --server $acrServer `
            --username $acrUsername `
            --password $acrPassword `
            --only-show-errors `
            --output none
        Assert-AzSuccess -Operation "set registry for $($job.Name)"
        az containerapp job update `
            --name $job.Name `
            --resource-group $ResourceGroup `
            --cron-expression $job.Cron `
            --replica-timeout $job.Timeout `
            --replica-retry-limit 1 `
            --replica-completion-count 1 `
            --parallelism 1 `
            --image $Image `
            --cpu 2.0 `
            --memory 4Gi `
            --command python `
            --args $job.Runner apply `
            --replace-env-vars $commonEnv `
            --only-show-errors `
            --output none
        Assert-AzSuccess -Operation "update $($job.Name)"
    }
}

Write-Host ""
Write-Host "Validation"
foreach ($job in $jobs) {
    az containerapp job show `
        --name $job.Name `
        --resource-group $ResourceGroup `
        --query "{name:name,schedule:properties.configuration.scheduleTriggerConfig.cronExpression,image:properties.template.containers[0].image,command:properties.template.containers[0].command,args:properties.template.containers[0].args}" `
        --output json
    Assert-AzSuccess -Operation "validate $($job.Name)"
}

Write-Host ""
Write-Host "No AU or ID Container Apps Jobs were modified by this script."
Write-Host "Safe manual start after image deployment:"
Write-Host "az containerapp job start -n quivrr-nightly-eu-inventory -g $ResourceGroup"
Write-Host "az containerapp job start -n quivrr-eu-mfr-availability -g $ResourceGroup"
Write-Host "Read-only/dry-run execution with scheduled --apply args overridden:"
Write-Host "az containerapp job start -n quivrr-nightly-eu-inventory -g $ResourceGroup --command python --args scripts/europe/run_eu_retailer_inventory_refresh.py dry-run"
Write-Host "az containerapp job start -n quivrr-eu-mfr-availability -g $ResourceGroup --command python --args scripts/manufacturer_availability/run_eu_manufacturer_availability_pipeline.py dry-run"
Write-Host "Execution status:"
Write-Host "az containerapp job execution list -n <job-name> -g $ResourceGroup -o table"
Write-Host "Log Analytics query:"
Write-Host "ContainerAppConsoleLogs_CL | where _ResourceId has '/jobs/quivrr-nightly-eu-inventory' or _ResourceId has '/jobs/quivrr-eu-mfr-availability' | order by TimeGenerated desc"
