# Quivrr Operations Runbook

## Daily Operator Checks

1. Review the daily observability email.
2. Confirm region health for `AU`, `EU`, and `ID`.
3. Check any freshness warnings against the latest Log Analytics events.
4. Confirm there are no null-region or region-leakage issues.
5. Review Bodhi and OpenAI health before escalating recommendation issues.

## Local Commands

Daily observability report:

```powershell
python scripts/run_daily_observability_report.py
```

Weekly platform report:

```powershell
python scripts/run_weekly_platform_report.py
```

Retailer inventory refresh examples:

```powershell
python scripts/run_nightly_inventory_refresh.py
python scripts/europe/run_eu_retailer_inventory_refresh.py apply
python scrapers/retailers/indonesia/import_indonesia_retailer_inventory.py
```

MFA refresh examples:

```powershell
python scripts/manufacturer_availability/run_au_manufacturer_availability_pipeline.py
python scripts/manufacturer_availability/run_eu_manufacturer_availability_pipeline.py apply
python scripts/manufacturer_availability/run_id_manufacturer_availability_pipeline.py
```

## Troubleshooting

- Inventory stale in one region:
  Check the latest `inventory_refresh_*` events and region freshness metrics.
- MFA stale in one region:
  Check `mfa_refresh_*` and `mfa_brand_*` events and confirm the latest successful manufacturer rows.
- Weekly catalogue failure:
  Review `catalogue_brand_failed` and rerun only after confirming the failing brand pipeline.
- Bodhi recommendation failures:
  Check `bodhi_recommendation_failed` and `bodhi_openai_failure` events.
- Region leakage:
  Investigate `RegionCode` mismatches before any next refresh is allowed to proceed.
