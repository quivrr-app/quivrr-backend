from __future__ import annotations

import os
from datetime import datetime, timezone
from html import escape
from typing import Any

from azure.communication.email import EmailClient

from .health import collect_health_snapshot


SENDER = os.getenv(
    "QUIVRR_REPORT_SENDER",
    "DoNotReply@ff941a60-94ca-4bb4-8d18-d5f377617fe1.azurecomm.net",
)
RECIPIENT = os.getenv("QUIVRR_REPORT_RECIPIENT", "dunn.nathan@hotmail.com")
CONNECTION_STRING = os.getenv("ACS_EMAIL_CONNECTION_STRING")


def _cell(value: Any) -> str:
    return escape(str(value or ""))


def _status_badge(status: str) -> str:
    colours = {
        "Healthy": "#166534",
        "Warning": "#92400e",
        "High": "#991b1b",
        "Critical": "#7f1d1d",
    }
    background = {
        "Healthy": "#dcfce7",
        "Warning": "#fef3c7",
        "High": "#fee2e2",
        "Critical": "#fecaca",
    }
    return (
        f"<span style=\"display:inline-block;padding:4px 10px;border-radius:999px;"
        f"background:{background.get(status, '#e5e7eb')};color:{colours.get(status, '#111827')};"
        f"font-weight:700;\">{_cell(status)}</span>"
    )


def _list_items(items: list[str]) -> str:
    if not items:
        return "<li>No current issues.</li>"
    return "".join(f"<li>{_cell(item)}</li>" for item in items)


def build_daily_report_html(snapshot: dict[str, Any]) -> str:
    regions = snapshot["regionHealth"]
    return f"""<!doctype html>
<html>
  <body style="font-family:Arial,Helvetica,sans-serif;background:#f3f4f6;padding:24px;color:#111827;">
    <div style="max-width:1080px;margin:0 auto;background:#ffffff;border:1px solid #e5e7eb;border-radius:20px;padding:24px;">
      <h1 style="margin:0 0 8px 0;">Quivrr Daily Observability Report</h1>
      <p style="margin:0 0 18px 0;color:#4b5563;">Generated { _cell(snapshot['generatedAtUtc']) }</p>
      <h2>Platform Health</h2>
      <p>{_status_badge(snapshot['platformHealth']['status'])} {_cell(snapshot['platformHealth']['reason'])}</p>
      <h2>Region Health</h2>
      <table style="width:100%;border-collapse:collapse;">
        <thead>
          <tr style="background:#f9fafb;text-align:left;">
            <th style="padding:10px;">Region</th>
            <th style="padding:10px;">Status</th>
            <th style="padding:10px;">Inventory</th>
            <th style="padding:10px;">MFA</th>
            <th style="padding:10px;">Retailer Rows</th>
            <th style="padding:10px;">MFA Rows</th>
          </tr>
        </thead>
        <tbody>
          {"".join(
              f"<tr>"
              f"<td style='padding:10px;border-top:1px solid #e5e7eb;'>{_cell(row['region'])}</td>"
              f"<td style='padding:10px;border-top:1px solid #e5e7eb;'>{_status_badge(row['status'])}</td>"
              f"<td style='padding:10px;border-top:1px solid #e5e7eb;'>{_cell(row['inventoryStatus'])}</td>"
              f"<td style='padding:10px;border-top:1px solid #e5e7eb;'>{_cell(row['mfaStatus'])}</td>"
              f"<td style='padding:10px;border-top:1px solid #e5e7eb;'>{_cell(row['retailerInventoryRows'])}</td>"
              f"<td style='padding:10px;border-top:1px solid #e5e7eb;'>{_cell(row['manufacturerInventoryRows'])}</td>"
              f"</tr>"
              for row in regions
          )}
        </tbody>
      </table>
      <h2>Catalogue Health</h2>
      <p>{_status_badge(snapshot['catalogueHealth']['status'])} {_cell(snapshot['catalogueHealth']['reason'])}</p>
      <p>Models: {_cell(snapshot['catalogueHealth']['modelCount'])} | Sizes: {_cell(snapshot['catalogueHealth']['sizeCount'])}</p>
      <h2>Inventory Health</h2>
      <p>Null RegionCode rows: retailer={_cell(snapshot['inventoryHealth']['nullRegionCounts']['retailerInventoryNullRegionRows'])}, manufacturer={_cell(snapshot['inventoryHealth']['nullRegionCounts']['manufacturerInventoryNullRegionRows'])}</p>
      <p>Retailer leakage rows: {_cell(snapshot['inventoryHealth']['regionLeakage']['retailerRegionLeakageRows'])}</p>
      <h2>MFA Health</h2>
      <p>Manufacturer coverage is region-aware and based on current active manufacturer-direct rows.</p>
      <h2>Bodhi Health</h2>
      <p>{_status_badge(snapshot['bodhiHealth']['status'])} {_cell(snapshot['bodhiHealth']['reason'])}</p>
      <h2>Open Issues</h2>
      <ul>{_list_items(snapshot['openIssues'])}</ul>
      <h2>Recommended Actions</h2>
      <ul>{_list_items(snapshot['recommendedActions'])}</ul>
    </div>
  </body>
</html>"""


def build_weekly_report_html(snapshot: dict[str, Any]) -> str:
    regions = snapshot["regionHealth"]
    return f"""<!doctype html>
<html>
  <body style="font-family:Arial,Helvetica,sans-serif;background:#f3f4f6;padding:24px;color:#111827;">
    <div style="max-width:1080px;margin:0 auto;background:#ffffff;border:1px solid #e5e7eb;border-radius:20px;padding:24px;">
      <h1 style="margin:0 0 8px 0;">Quivrr Weekly Platform Report</h1>
      <p style="margin:0 0 18px 0;color:#4b5563;">Generated { _cell(snapshot['generatedAtUtc']) }</p>
      <h2>Executive Summary</h2>
      <p>{_status_badge(snapshot['platformHealth']['status'])} {_cell(snapshot['platformHealth']['reason'])}</p>
      <h2>Catalogue Movement</h2>
      <p>Current active catalogue: {_cell(snapshot['catalogueHealth']['modelCount'])} models and {_cell(snapshot['catalogueHealth']['sizeCount'])} sizes.</p>
      <h2>Region Inventory Trends</h2>
      <ul>{"".join(f"<li>{_cell(row['region'])}: {row['retailerInventoryRows']} retailer rows, {row['manufacturerInventoryRows']} manufacturer rows.</li>" for row in regions)}</ul>
      <h2>MFA Coverage Trends</h2>
      <ul>{"".join(f"<li>{_cell(row['region'])}: brand coverage {_cell(row['brandCoverage'])}, model link rate {_cell(row['manufacturerModelLinkRate'])}.</li>" for row in regions)}</ul>
      <h2>Bodhi Quality Trend</h2>
      <p>{_status_badge(snapshot['bodhiHealth']['status'])} {_cell(snapshot['bodhiHealth']['reason'])}</p>
      <h2>Retailer Coverage Gaps</h2>
      <ul>{"".join(f"<li>{_cell(row['region'])}: retailer coverage {_cell(row['retailerCoverage'])}, model link rate {_cell(row['retailerModelLinkRate'])}, size link rate {_cell(row['retailerSizeLinkRate'])}.</li>" for row in regions)}</ul>
      <h2>Data Quality Issues</h2>
      <ul>{_list_items(snapshot['openIssues'])}</ul>
      <h2>Recommended Actions</h2>
      <ul>{_list_items(snapshot['recommendedActions'])}</ul>
      <h2>Upcoming Risks</h2>
      <ul>
        <li>Watch any region whose freshness window is close to expiry.</li>
        <li>Investigate link quality drops before they reduce recommendation precision.</li>
        <li>Keep Europe as the Gen 3 reference when adding future region monitoring.</li>
      </ul>
    </div>
  </body>
</html>"""


def send_report_email(subject: str, html: str, plain_text: str) -> Any:
    if not CONNECTION_STRING:
        raise RuntimeError("Missing ACS_EMAIL_CONNECTION_STRING")
    client = EmailClient.from_connection_string(CONNECTION_STRING)
    poller = client.begin_send(
        {
            "senderAddress": SENDER,
            "recipients": {"to": [{"address": RECIPIENT}]},
            "content": {
                "subject": subject,
                "plainText": plain_text,
                "html": html,
            },
        }
    )
    return poller.result()


def render_daily_payload() -> dict[str, Any]:
    snapshot = collect_health_snapshot()
    return {
        "snapshot": snapshot,
        "html": build_daily_report_html(snapshot),
        "plainText": "Quivrr daily observability report generated successfully.",
        "subject": f"Quivrr Daily Observability Report - {datetime.now(timezone.utc).date().isoformat()}",
    }


def render_weekly_payload() -> dict[str, Any]:
    snapshot = collect_health_snapshot()
    return {
        "snapshot": snapshot,
        "html": build_weekly_report_html(snapshot),
        "plainText": "Quivrr weekly platform report generated successfully.",
        "subject": f"Quivrr Weekly Platform Report - {datetime.now(timezone.utc).date().isoformat()}",
    }
