$ErrorActionPreference = "Stop"

$resourceGroup = "quivrr-production-rg"
$jobName = "quivrr-weekly-brand-catalogues"

Write-Host ""
Write-Host "============================================================"
Write-Host "AZURE JOB SUMMARY"
Write-Host "============================================================"

az containerapp job show `
  --name $jobName `
  --resource-group $resourceGroup `
  --query "{name:name, resourceGroup:resourceGroup, location:location, provisioningState:properties.provisioningState, triggerType:properties.configuration.triggerType, cronExpression:properties.configuration.scheduleTriggerConfig.cronExpression, image:properties.template.containers[0].image, command:properties.template.containers[0].command, args:properties.template.containers[0].args}" `
  --output json

Write-Host ""
Write-Host "============================================================"
Write-Host "AZURE JOB ENVIRONMENT VARIABLE NAMES"
Write-Host "============================================================"

az containerapp job show `
  --name $jobName `
  --resource-group $resourceGroup `
  --query "properties.template.containers[0].env[].name" `
  --output table

Write-Host ""
Write-Host "============================================================"
Write-Host "RECENT AZURE EXECUTIONS"
Write-Host "============================================================"

az containerapp job execution list `
  --name $jobName `
  --resource-group $resourceGroup `
  --query "sort_by([].{name:name,status:properties.status,start:properties.startTime,end:properties.endTime}, &start)[-10:]" `
  --output table

python .\inspect_local_weekly_runner.py

Write-Host ""
Write-Host "============================================================"
Write-Host "LOCAL GIT COMMIT"
Write-Host "============================================================"

git log -1 --oneline

Write-Host ""
Write-Host "============================================================"
Write-Host "LOCAL GIT STATUS"
Write-Host "============================================================"

git status --short
