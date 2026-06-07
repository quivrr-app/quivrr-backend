from sqlalchemy import text

from market_intelligence.db import execute_with_retry


DDL = text("""
IF OBJECT_ID('dbo.RetailerInventorySnapshot', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.RetailerInventorySnapshot (
        SnapshotId BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        SnapshotDate DATE NOT NULL,
        InventoryId INT NULL,
        RetailerId INT NULL,
        RetailerName NVARCHAR(255) NULL,
        BrandName NVARCHAR(255) NULL,
        ModelName NVARCHAR(255) NULL,
        RawProductTitle NVARCHAR(500) NULL,
        NormalisedProductTitle NVARCHAR(500) NULL,
        ProductUrl NVARCHAR(1000) NULL,
        ProductImageUrl NVARCHAR(1000) NULL,
        PriceAud DECIMAL(18,2) NULL,
        StockStatus NVARCHAR(100) NULL,
        Construction NVARCHAR(255) NULL,
        FinSetup NVARCHAR(255) NULL,
        LengthFeetInches NVARCHAR(50) NULL,
        Width NVARCHAR(50) NULL,
        Thickness NVARCHAR(50) NULL,
        VolumeLitres DECIMAL(10,2) NULL,
        SnapshotCreatedUtc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );

    CREATE INDEX IX_RetailerInventorySnapshot_Date
        ON dbo.RetailerInventorySnapshot (SnapshotDate);

    CREATE INDEX IX_RetailerInventorySnapshot_Retailer
        ON dbo.RetailerInventorySnapshot (SnapshotDate, RetailerName);

    CREATE INDEX IX_RetailerInventorySnapshot_ProductUrl
        ON dbo.RetailerInventorySnapshot (SnapshotDate, ProductUrl);
END;

IF OBJECT_ID('dbo.RetailerInventoryDelta', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.RetailerInventoryDelta (
        DeltaId BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        EventDate DATE NOT NULL,
        EventType NVARCHAR(50) NOT NULL,
        PreviousSnapshotDate DATE NULL,
        CurrentSnapshotDate DATE NULL,
        InventoryId INT NULL,
        RetailerName NVARCHAR(255) NULL,
        BrandName NVARCHAR(255) NULL,
        ModelName NVARCHAR(255) NULL,
        RawProductTitle NVARCHAR(500) NULL,
        ProductUrl NVARCHAR(1000) NULL,
        PriceAud DECIMAL(18,2) NULL,
        PreviousPriceAud DECIMAL(18,2) NULL,
        CurrentPriceAud DECIMAL(18,2) NULL,
        StockStatus NVARCHAR(100) NULL,
        PreviousStockStatus NVARCHAR(100) NULL,
        CurrentStockStatus NVARCHAR(100) NULL,
        Construction NVARCHAR(255) NULL,
        FinSetup NVARCHAR(255) NULL,
        LengthFeetInches NVARCHAR(50) NULL,
        Width NVARCHAR(50) NULL,
        Thickness NVARCHAR(50) NULL,
        VolumeLitres DECIMAL(10,2) NULL,
        CreatedUtc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );

    CREATE INDEX IX_RetailerInventoryDelta_Date
        ON dbo.RetailerInventoryDelta (EventDate, EventType);

    CREATE INDEX IX_RetailerInventoryDelta_Retailer
        ON dbo.RetailerInventoryDelta (EventDate, RetailerName);

    CREATE INDEX IX_RetailerInventoryDelta_ProductUrl
        ON dbo.RetailerInventoryDelta (ProductUrl);
END;
""")

CHECK = text("""
SELECT TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'dbo'
AND TABLE_NAME IN (
    'RetailerInventorySnapshot',
    'RetailerInventoryDelta'
)
ORDER BY TABLE_NAME;
""")


def main():
    execute_with_retry(DDL)
    rows = execute_with_retry(CHECK)

    print("Market intelligence SQL tables present:")
    for row in rows:
        print(f" - {row.TABLE_NAME}")


if __name__ == "__main__":
    main()
