from datetime import date

from sqlalchemy import text

from market_intelligence.db import execute_with_retry


SNAPSHOT_SQL = text("""
DECLARE @SnapshotDate DATE = CAST(SYSUTCDATETIME() AS DATE);

DELETE FROM dbo.RetailerInventorySnapshot
WHERE SnapshotDate = @SnapshotDate;

INSERT INTO dbo.RetailerInventorySnapshot (
    SnapshotDate,
    InventoryId,
    RetailerId,
    RetailerName,
    BrandName,
    ModelName,
    RawProductTitle,
    NormalisedProductTitle,
    ProductUrl,
    ProductImageUrl,
    PriceAud,
    StockStatus,
    Construction,
    FinSetup,
    LengthFeetInches,
    Width,
    Thickness,
    VolumeLitres
)
SELECT
    @SnapshotDate,
    ri.InventoryId,
    ri.RetailerId,
    r.RetailerName,
    b.BrandName,
    bm.ModelName,
    ri.RawProductTitle,
    ri.NormalisedProductTitle,
    ri.ProductUrl,
    ri.ProductImageUrl,
    ri.PriceAud,
    ri.StockStatus,
    ri.Construction,
    ri.FinSetup,
    ri.LengthFeetInches,
    ri.Width,
    ri.Thickness,
    ri.VolumeLitres
FROM dbo.RetailerInventory ri
INNER JOIN dbo.Retailers r
    ON ri.RetailerId = r.RetailerId
LEFT JOIN dbo.Brands b
    ON ri.BrandId = b.BrandId
LEFT JOIN dbo.BoardModels bm
    ON ri.BoardModelId = bm.BoardModelId
WHERE ri.IsActive = 1
AND ri.ProductUrl IS NOT NULL
AND (
    ri.StockStatus IS NULL
    OR LOWER(LTRIM(RTRIM(ri.StockStatus))) IN (
        'in stock',
        'instock',
        'available',
        'true'
    )
);
""")

COUNT_SQL = text("""
SELECT COUNT(*) AS SnapshotRows
FROM dbo.RetailerInventorySnapshot
WHERE SnapshotDate = CAST(SYSUTCDATETIME() AS DATE);
""")


def main():
    execute_with_retry(SNAPSHOT_SQL)
    rows = execute_with_retry(COUNT_SQL)
    count = rows[0].SnapshotRows if rows else 0

    print(f"Retailer snapshot complete for {date.today().isoformat()}")
    print(f"Snapshot rows: {count}")


if __name__ == "__main__":
    main()
