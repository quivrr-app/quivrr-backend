from __future__ import annotations

from observability.reports import render_daily_payload, send_report_email
from utils.structured_logging import emit_event


def main() -> None:
    emit_event("observability_report_started", "platform_observability", status="success", report_type="daily")
    payload = render_daily_payload()
    send_report_email(payload["subject"], payload["html"], payload["plainText"])
    emit_event(
        "observability_report_completed",
        "platform_observability",
        status="success",
        report_type="daily",
        open_issue_count=len(payload["snapshot"]["openIssues"]),
    )


if __name__ == "__main__":
    main()
