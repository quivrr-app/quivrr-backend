import os
from datetime import datetime, timezone
from html import escape

from azure.communication.email import EmailClient
from sqlalchemy import text

from market_intelligence.db import execute_with_retry


SENDER = os.getenv(
    "QUIVRR_REPORT_SENDER",
    "DoNotReply@ff941a60-94ca-4bb4-8d18-d5f377617fe1.azurecomm.net",
)
RECIPIENT = os.getenv("QUIVRR_REPORT_RECIPIENT", "dunn.nathan@hotmail.com")
CONNECTION_STRING = os.getenv("ACS_EMAIL_CONNECTION_STRING")

SUMMARY_SQL = text("""
SELECT
    (
        SELECT MAX(SnapshotDate)
        FROM dbo.RetailerInventorySnapshot
    ) AS CurrentSnapshotDate,
    (
        SELECT MAX(SnapshotDate)
        FROM dbo.RetailerInventorySnapshot
        WHERE SnapshotDate < (
            SELECT MAX(SnapshotDate)
            FROM dbo.RetailerInventorySnapshot
        )
    ) AS PreviousSnapshotDate,
    (
        SELECT COUNT(*)
        FROM dbo.RetailerInventorySnapshot
        WHERE SnapshotDate = (
            SELECT MAX(SnapshotDate)
            FROM dbo.RetailerInventorySnapshot
        )
    ) AS CurrentSnapshotRows,
    (
        SELECT COUNT(*)
        FROM dbo.RetailerInventoryDelta
        WHERE EventDate = (
            SELECT MAX(SnapshotDate)
            FROM dbo.RetailerInventorySnapshot
        )
        AND EventType = 'SOLD_OUT'
    ) AS SoldOutCount,
    (
        SELECT COUNT(*)
        FROM dbo.RetailerInventoryDelta
        WHERE EventDate = (
            SELECT MAX(SnapshotDate)
            FROM dbo.RetailerInventorySnapshot
        )
        AND EventType = 'NEW_STOCK'
    ) AS NewStockCount;
""")

TOP_EVENTS_SQL = text("""
SELECT TOP 25
    EventType,
    RetailerName,
    BrandName,
    ModelName,
    RawProductTitle,
    LengthFeetInches,
    VolumeLitres,
    PriceAud
FROM dbo.RetailerInventoryDelta
WHERE EventDate = (
    SELECT MAX(SnapshotDate)
    FROM dbo.RetailerInventorySnapshot
)
ORDER BY DeltaId DESC;
""")

RETAILER_SUMMARY_SQL = text("""
SELECT TOP 12
    RetailerName,
    SUM(CASE WHEN EventType = 'SOLD_OUT' THEN 1 ELSE 0 END) AS SoldOutCount,
    SUM(CASE WHEN EventType = 'NEW_STOCK' THEN 1 ELSE 0 END) AS NewStockCount
FROM dbo.RetailerInventoryDelta
WHERE EventDate = (
    SELECT MAX(SnapshotDate)
    FROM dbo.RetailerInventorySnapshot
)
GROUP BY RetailerName
ORDER BY
    SUM(CASE WHEN EventType = 'SOLD_OUT' THEN 1 ELSE 0 END) DESC,
    SUM(CASE WHEN EventType = 'NEW_STOCK' THEN 1 ELSE 0 END) DESC,
    RetailerName;
""")

BRAND_SUMMARY_SQL = text("""
SELECT TOP 12
    BrandName,
    SUM(CASE WHEN EventType = 'SOLD_OUT' THEN 1 ELSE 0 END) AS SoldOutCount,
    SUM(CASE WHEN EventType = 'NEW_STOCK' THEN 1 ELSE 0 END) AS NewStockCount
FROM dbo.RetailerInventoryDelta
WHERE EventDate = (
    SELECT MAX(SnapshotDate)
    FROM dbo.RetailerInventorySnapshot
)
GROUP BY BrandName
ORDER BY
    SUM(CASE WHEN EventType = 'SOLD_OUT' THEN 1 ELSE 0 END) DESC,
    SUM(CASE WHEN EventType = 'NEW_STOCK' THEN 1 ELSE 0 END) DESC,
    BrandName;
""")


def cell(value):
    if value is None:
        return ""
    return escape(str(value))


def money(value):
    if value is None:
        return ""
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return cell(value)


def small_summary_rows(rows, name_field):
    if not rows:
        return """
        <tr>
          <td colspan="3" style="padding:13px;border-top:1px solid #e5e7eb;color:#6b7280;">
            No movement recorded yet.
          </td>
        </tr>
        """

    output = []
    for row in rows:
        name = getattr(row, name_field)
        output.append(f"""
        <tr>
          <td style="padding:11px;border-top:1px solid #e5e7eb;">{cell(name) or "Unknown"}</td>
          <td style="padding:11px;border-top:1px solid #e5e7eb;text-align:center;">{row.SoldOutCount or 0}</td>
          <td style="padding:11px;border-top:1px solid #e5e7eb;text-align:center;">{row.NewStockCount or 0}</td>
        </tr>
        """)
    return "\n".join(output)


def movement_rows(events):
    if not events:
        return """
        <tr>
          <td colspan="8" style="padding:16px;border-top:1px solid #e5e7eb;color:#6b7280;">
            No retailer stock movements were detected for this snapshot yet.
          </td>
        </tr>
        """

    output = []
    for event in events:
        output.append(f"""
        <tr>
          <td style="padding:10px;border-top:1px solid #e5e7eb;">{cell(event.EventType)}</td>
          <td style="padding:10px;border-top:1px solid #e5e7eb;">{cell(event.RetailerName)}</td>
          <td style="padding:10px;border-top:1px solid #e5e7eb;">{cell(event.BrandName)}</td>
          <td style="padding:10px;border-top:1px solid #e5e7eb;">{cell(event.ModelName)}</td>
          <td style="padding:10px;border-top:1px solid #e5e7eb;">{cell(event.RawProductTitle)}</td>
          <td style="padding:10px;border-top:1px solid #e5e7eb;text-align:center;">{cell(event.LengthFeetInches)}</td>
          <td style="padding:10px;border-top:1px solid #e5e7eb;text-align:center;">{cell(event.VolumeLitres)}</td>
          <td style="padding:10px;border-top:1px solid #e5e7eb;text-align:right;">{money(event.PriceAud)}</td>
        </tr>
        """)
    return "\n".join(output)


def build_html(summary, events, retailer_summary, brand_summary):
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#f3f3f4;font-family:Arial,Helvetica,sans-serif;color:#1f2933;">
    <div style="max-width:940px;margin:0 auto;padding:26px;">
      <div style="background:#102421;color:#ffffff;border-radius:18px;padding:28px;border:1px solid #245f58;">
        <div style="font-size:42px;font-weight:800;letter-spacing:-2px;line-height:1;">quivrr</div>
        <div style="font-size:13px;letter-spacing:4px;color:#9fd8cf;margin-top:8px;text-transform:uppercase;">
          Market Intelligence
        </div>
        <div style="font-size:18px;color:#ffffff;margin-top:10px;">
          Daily Retailer Movement Report
        </div>
      </div>

      <div style="background:#ffffff;border-radius:18px;margin-top:18px;padding:24px;border:1px solid #e5e7eb;">
        <h2 style="margin:0 0 8px 0;color:#2f7f75;">Retailer Inventory Delta Summary</h2>
        <p style="margin:0 0 20px 0;color:#4b5563;line-height:1.45;">
          This report compares the latest retailer inventory snapshot against the previous snapshot and highlights likely stock movement.
        </p>

        <table style="width:100%;border-collapse:collapse;font-size:14px;">
          <tr>
            <td style="padding:12px;background:#f8fafc;border-top-left-radius:10px;">Current snapshot</td>
            <td style="padding:12px;">{cell(summary.CurrentSnapshotDate)}</td>
          </tr>
          <tr>
            <td style="padding:12px;background:#f8fafc;">Previous snapshot</td>
            <td style="padding:12px;">{cell(summary.PreviousSnapshotDate)}</td>
          </tr>
          <tr>
            <td style="padding:12px;background:#f8fafc;border-bottom-left-radius:10px;">Current retailer boards captured</td>
            <td style="padding:12px;">{cell(summary.CurrentSnapshotRows)}</td>
          </tr>
        </table>

        <table style="width:100%;border-collapse:separate;border-spacing:0 12px;margin-top:18px;">
          <tr>
            <td style="width:50%;padding:18px;background:#fff7f7;border:1px solid #fecaca;border-radius:16px;">
              <div style="font-size:13px;color:#7f1d1d;text-transform:uppercase;letter-spacing:1px;">Boards no longer available</div>
              <div style="font-size:38px;font-weight:800;color:#991b1b;margin-top:8px;">{summary.SoldOutCount or 0}</div>
            </td>
            <td style="width:14px;"></td>
            <td style="width:50%;padding:18px;background:#f0fdf8;border:1px solid #bbf7d0;border-radius:16px;">
              <div style="font-size:13px;color:#14532d;text-transform:uppercase;letter-spacing:1px;">New stock detected</div>
              <div style="font-size:38px;font-weight:800;color:#15803d;margin-top:8px;">{summary.NewStockCount or 0}</div>
            </td>
          </tr>
        </table>
      </div>

      <table style="width:100%;border-collapse:separate;border-spacing:0;margin-top:18px;">
        <tr>
          <td style="width:50%;vertical-align:top;background:#ffffff;border:1px solid #e5e7eb;border-radius:18px;padding:20px;">
            <h3 style="margin:0 0 12px 0;color:#2f7f75;">Retailer Movement</h3>
            <table style="width:100%;border-collapse:collapse;font-size:13px;">
              <thead>
                <tr style="text-align:left;background:#f8fafc;">
                  <th style="padding:10px;">Retailer</th>
                  <th style="padding:10px;text-align:center;">No longer available</th>
                  <th style="padding:10px;text-align:center;">New stock</th>
                </tr>
              </thead>
              <tbody>
                {small_summary_rows(retailer_summary, "RetailerName")}
              </tbody>
            </table>
          </td>
          <td style="width:18px;"></td>
          <td style="width:50%;vertical-align:top;background:#ffffff;border:1px solid #e5e7eb;border-radius:18px;padding:20px;">
            <h3 style="margin:0 0 12px 0;color:#2f7f75;">Brand Movement</h3>
            <table style="width:100%;border-collapse:collapse;font-size:13px;">
              <thead>
                <tr style="text-align:left;background:#f8fafc;">
                  <th style="padding:10px;">Brand</th>
                  <th style="padding:10px;text-align:center;">No longer available</th>
                  <th style="padding:10px;text-align:center;">New stock</th>
                </tr>
              </thead>
              <tbody>
                {small_summary_rows(brand_summary, "BrandName")}
              </tbody>
            </table>
          </td>
        </tr>
      </table>

      <div style="background:#ffffff;border-radius:18px;margin-top:18px;padding:24px;border:1px solid #e5e7eb;">
        <h3 style="margin:0 0 14px 0;color:#2f7f75;">Latest Movement Events</h3>
        <table style="width:100%;border-collapse:collapse;font-size:12px;">
          <thead>
            <tr style="text-align:left;background:#f8fafc;">
              <th style="padding:10px;">Type</th>
              <th style="padding:10px;">Retailer</th>
              <th style="padding:10px;">Brand</th>
              <th style="padding:10px;">Model</th>
              <th style="padding:10px;">Title</th>
              <th style="padding:10px;text-align:center;">Length</th>
              <th style="padding:10px;text-align:center;">Litres</th>
              <th style="padding:10px;text-align:right;">Price</th>
            </tr>
          </thead>
          <tbody>
            {movement_rows(events)}
          </tbody>
        </table>
      </div>

      <p style="font-size:12px;color:#6b7280;margin-top:18px;line-height:1.4;">
        Generated by Quivrr Market Intelligence at {generated}. Boards no longer available may represent sold items, retailer removals or source availability changes.
      </p>
    </div>
  </body>
</html>
"""


def main():
    if not CONNECTION_STRING:
        raise SystemExit("Missing ACS_EMAIL_CONNECTION_STRING")

    summary_rows = execute_with_retry(SUMMARY_SQL)
    if not summary_rows:
        raise SystemExit("No retailer snapshot summary found.")

    summary = summary_rows[0]
    events = execute_with_retry(TOP_EVENTS_SQL)
    retailer_summary = execute_with_retry(RETAILER_SUMMARY_SQL)
    brand_summary = execute_with_retry(BRAND_SUMMARY_SQL)

    subject_date = cell(summary.CurrentSnapshotDate) or "latest"
    html = build_html(summary, events, retailer_summary, brand_summary)

    message = {
        "senderAddress": SENDER,
        "recipients": {"to": [{"address": RECIPIENT}]},
        "content": {
            "subject": f"Quivrr Daily Retailer Movement Report - {subject_date}",
            "plainText": (
                f"Quivrr Daily Retailer Movement Report\n\n"
                f"Current snapshot: {cell(summary.CurrentSnapshotDate)}\n"
                f"Previous snapshot: {cell(summary.PreviousSnapshotDate)}\n"
                f"Rows captured: {cell(summary.CurrentSnapshotRows)}\n"
                f"Boards no longer available: {summary.SoldOutCount or 0}\n"
                f"New stock detected: {summary.NewStockCount or 0}\n"
            ),
            "html": html,
        },
    }

    client = EmailClient.from_connection_string(CONNECTION_STRING)
    poller = client.begin_send(message)
    result = poller.result()

    print("Daily retailer movement email result:")
    print(result)


if __name__ == "__main__":
    main()
