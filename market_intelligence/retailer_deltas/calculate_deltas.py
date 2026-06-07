from sqlalchemy import text

from market_intelligence.db import execute_with_retry


GET_DATES_SQL = text("""
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
    ) AS PreviousSnapshotDate;
""")

DELETE_CURRENT_SQL = text("""
DELETE FROM dbo.RetailerInventoryDelta
WHERE EventDate = :current_snapshot_date;
""")

INSERT_SOLD_OUT_SQL = text("""
INSERT INTO dbo.RetailerInventoryDelta (
    EventDate,
    EventType,
    PreviousSnapshotDate,
    CurrentSnapshotDate,
    InventoryId,
    RetailerName,
    BrandName,
    ModelName,
    RawProductTitle,
    ProductUrl,
    PriceAud,
    PreviousPriceAud,
    CurrentPriceAud,
    StockStatus,
    PreviousStockStatus,
    CurrentStockStatus,
    Construction,
    FinSetup,
    LengthFeetInches,
    Width,
    Thickness,
    VolumeLitres
)
SELECT
    :current_snapshot_date,
    'SOLD_OUT',
    :previous_snapshot_date,
    :current_snapshot_date,
    prev.InventoryId,
    prev.RetailerName,
    prev.BrandName,
    prev.ModelName,
    prev.RawProductTitle,
    prev.ProductUrl,
    prev.PriceAud,
    prev.PriceAud,
    NULL,
    prev.StockStatus,
    prev.StockStatus,
    NULL,
    prev.Construction,
    prev.FinSetup,
    prev.LengthFeetInches,
    prev.Width,
    prev.Thickness,
    prev.VolumeLitres
FROM dbo.RetailerInventorySnapshot prev
LEFT JOIN dbo.RetailerInventorySnapshot cur
    ON cur.SnapshotDate = :current_snapshot_date
    AND cur.ProductUrl = prev.ProductUrl
    AND ISNULL(cur.LengthFeetInches, '') = ISNULL(prev.LengthFeetInches, '')
    AND ISNULL(cur.Width, '') = ISNULL(prev.Width, '')
    AND ISNULL(cur.Thickness, '') = ISNULL(prev.Thickness, '')
    AND ISNULL(CAST(cur.VolumeLitres AS decimal(10,2)), -1) = ISNULL(CAST(prev.VolumeLitres AS decimal(10,2)), -1)
    AND ISNULL(cur.Construction, '') = ISNULL(prev.Construction, '')
    AND ISNULL(cur.LengthFeetInches, '') = ISNULL(prev.LengthFeetInches, '')
    AND ISNULL(cur.Width, '') = ISNULL(prev.Width, '')
    AND ISNULL(cur.Thickness, '') = ISNULL(prev.Thickness, '')
    AND ISNULL(CAST(cur.VolumeLitres AS decimal(10,2)), -1) = ISNULL(CAST(prev.VolumeLitres AS decimal(10,2)), -1)
    AND ISNULL(cur.Construction, '') = ISNULL(prev.Construction, '')
WHERE prev.SnapshotDate = :previous_snapshot_date
AND cur.SnapshotId IS NULL;
""")

INSERT_NEW_STOCK_SQL = text("""
INSERT INTO dbo.RetailerInventoryDelta (
    EventDate,
    EventType,
    PreviousSnapshotDate,
    CurrentSnapshotDate,
    InventoryId,
    RetailerName,
    BrandName,
    ModelName,
    RawProductTitle,
    ProductUrl,
    PriceAud,
    PreviousPriceAud,
    CurrentPriceAud,
    StockStatus,
    PreviousStockStatus,
    CurrentStockStatus,
    Construction,
    FinSetup,
    LengthFeetInches,
    Width,
    Thickness,
    VolumeLitres
)
SELECT
    :current_snapshot_date,
    'NEW_STOCK',
    :previous_snapshot_date,
    :current_snapshot_date,
    cur.InventoryId,
    cur.RetailerName,
    cur.BrandName,
    cur.ModelName,
    cur.RawProductTitle,
    cur.ProductUrl,
    cur.PriceAud,
    NULL,
    cur.PriceAud,
    cur.StockStatus,
    NULL,
    cur.StockStatus,
    cur.Construction,
    cur.FinSetup,
    cur.LengthFeetInches,
    cur.Width,
    cur.Thickness,
    cur.VolumeLitres
FROM dbo.RetailerInventorySnapshot cur
LEFT JOIN dbo.RetailerInventorySnapshot prev
    ON prev.SnapshotDate = :previous_snapshot_date
    AND prev.ProductUrl = cur.ProductUrl
WHERE cur.SnapshotDate = :current_snapshot_date
AND prev.SnapshotId IS NULL;
""")

COUNT_EVENTS_SQL = text("""
SELECT
    SUM(CASE WHEN EventType = 'SOLD_OUT' THEN 1 ELSE 0 END) AS SoldOutCount,
    SUM(CASE WHEN EventType = 'NEW_STOCK' THEN 1 ELSE 0 END) AS NewStockCount
FROM dbo.RetailerInventoryDelta
WHERE EventDate = :current_snapshot_date;
""")


def main():
    date_rows = execute_with_retry(GET_DATES_SQL)
    date_row = date_rows[0] if date_rows else None

    print("Retailer delta calculation complete.")

    if not date_row or not date_row.CurrentSnapshotDate:
        print("No current snapshot date found.")
        return

    current_snapshot_date = date_row.CurrentSnapshotDate
    previous_snapshot_date = date_row.PreviousSnapshotDate

    execute_with_retry(
        DELETE_CURRENT_SQL,
        {"current_snapshot_date": current_snapshot_date},
    )

    if previous_snapshot_date:
        params = {
            "current_snapshot_date": current_snapshot_date,
            "previous_snapshot_date": previous_snapshot_date,
        }

        execute_with_retry(INSERT_SOLD_OUT_SQL, params)
        execute_with_retry(INSERT_NEW_STOCK_SQL, params)

    count_rows = execute_with_retry(
        COUNT_EVENTS_SQL,
        {"current_snapshot_date": current_snapshot_date},
    )
    count_row = count_rows[0] if count_rows else None

    sold_out_count = count_row.SoldOutCount if count_row else 0
    new_stock_count = count_row.NewStockCount if count_row else 0

    print(f"Current snapshot date: {current_snapshot_date}")
    print(f"Previous snapshot date: {previous_snapshot_date}")
    print(f"Sold out events: {sold_out_count or 0}")
    print(f"New stock events: {new_stock_count or 0}")


if __name__ == "__main__":
    main()
