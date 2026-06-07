from market_intelligence.retailer_deltas.snapshot_inventory import main as snapshot_main
from market_intelligence.retailer_deltas.calculate_deltas import main as delta_main
from market_intelligence.reporting.email_daily_delta_report import main as email_main


def main():
    print("Starting Quivrr daily market intelligence report pipeline.")
    snapshot_main()
    delta_main()
    email_main()
    print("Daily market intelligence report pipeline complete.")


if __name__ == "__main__":
    main()
