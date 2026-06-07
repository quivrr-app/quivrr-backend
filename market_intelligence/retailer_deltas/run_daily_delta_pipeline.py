from market_intelligence.retailer_deltas.snapshot_inventory import main as snapshot_main
from market_intelligence.retailer_deltas.calculate_deltas import main as delta_main


def main():
    print("Starting Quivrr market intelligence daily retailer delta pipeline.")
    snapshot_main()
    delta_main()
    print("Daily retailer delta pipeline complete.")


if __name__ == "__main__":
    main()
