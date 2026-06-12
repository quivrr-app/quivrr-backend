IF COL_LENGTH('dbo.Retailers', 'RegionCode') IS NULL
BEGIN
    ALTER TABLE dbo.Retailers ADD RegionCode nvarchar(10) NULL;
END;

IF COL_LENGTH('dbo.RetailerInventory', 'RegionCode') IS NULL
BEGIN
    ALTER TABLE dbo.RetailerInventory ADD RegionCode nvarchar(10) NULL;
END;

IF COL_LENGTH('dbo.RetailerInventory', 'PriceAmount') IS NULL
BEGIN
    ALTER TABLE dbo.RetailerInventory ADD PriceAmount decimal(18,2) NULL;
END;

IF COL_LENGTH('dbo.RetailerInventory', 'PriceCurrency') IS NULL
BEGIN
    ALTER TABLE dbo.RetailerInventory ADD PriceCurrency nvarchar(10) NULL;
END;

UPDATE dbo.Retailers
SET RegionCode = 'AU'
WHERE RegionCode IS NULL
  AND (Country = 'Australia' OR Country IS NULL);

UPDATE dbo.RetailerInventory
SET RegionCode = 'AU',
    PriceAmount = ISNULL(PriceAmount, PriceAud),
    PriceCurrency = ISNULL(PriceCurrency, 'AUD')
WHERE RegionCode IS NULL;
