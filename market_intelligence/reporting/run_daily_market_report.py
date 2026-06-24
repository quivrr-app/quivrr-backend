import time

from market_intelligence.db import execute_with_retry
from market_intelligence.retailer_deltas.snapshot_inventory import main as snapshot_main
from market_intelligence.retailer_deltas.snapshot_inventory import COUNT_SQL as SNAPSHOT_COUNT_SQL
from market_intelligence.retailer_deltas.calculate_deltas import main as delta_main
from market_intelligence.retailer_deltas.calculate_deltas import COUNT_EVENTS_SQL, GET_DATES_SQL
from market_intelligence.reporting.email_daily_delta_report import main as email_main
from utils.structured_logging import emit_event, update_job_state


def main():
    started = time.perf_counter()
    print("Starting Quivrr daily market intelligence report pipeline.")
    emit_event("market_intelligence_started", "market_intelligence", status="success")
    try:
        snapshot_main()
        snapshot_rows = execute_with_retry(SNAPSHOT_COUNT_SQL)[0].SnapshotRows
        emit_event("market_snapshot_completed", "market_intelligence", status="success", snapshot_rows=int(snapshot_rows or 0))

        delta_main()
        date_row = execute_with_retry(GET_DATES_SQL)[0]
        counts = execute_with_retry(COUNT_EVENTS_SQL, {"current_snapshot_date": date_row.CurrentSnapshotDate})[0]
        emit_event(
            "market_delta_completed",
            "market_intelligence",
            status="success",
            sold_out_count=int(counts.SoldOutCount or 0),
            new_stock_count=int(counts.NewStockCount or 0),
        )

        email_main()
        emit_event("market_report_sent", "market_intelligence", status="success")
        duration = round(time.perf_counter() - started, 3)
        emit_event(
            "market_intelligence_completed",
            "market_intelligence",
            status="success",
            snapshot_rows=int(snapshot_rows or 0),
            sold_out_count=int(counts.SoldOutCount or 0),
            new_stock_count=int(counts.NewStockCount or 0),
            duration_seconds=duration,
        )
        update_job_state(
            "market_intelligence_daily",
            "market_intelligence",
            "market_intelligence",
            "success",
            snapshot_rows=int(snapshot_rows or 0),
            sold_out_count=int(counts.SoldOutCount or 0),
            new_stock_count=int(counts.NewStockCount or 0),
            duration_seconds=duration,
        )
        print("Daily market intelligence report pipeline complete.")
    except Exception as exc:
        emit_event(
            "market_intelligence_failed",
            "market_intelligence",
            status="failed",
            error_type=type(exc).__name__,
            error_message=str(exc),
            duration_seconds=round(time.perf_counter() - started, 3),
        )
        update_job_state(
            "market_intelligence_daily",
            "market_intelligence",
            "market_intelligence",
            "failed",
            error_type=type(exc).__name__,
            error_message=str(exc),
            duration_seconds=round(time.perf_counter() - started, 3),
        )
        raise


if __name__ == "__main__":
    main()
