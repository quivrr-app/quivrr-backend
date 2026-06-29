SET XACT_ABORT ON;
GO

BEGIN TRANSACTION;
GO

IF OBJECT_ID('dbo.UserQuiver', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.UserQuiver (
        QuiverId UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_UserQuiver PRIMARY KEY DEFAULT NEWID(),
        UserId UNIQUEIDENTIFIER NOT NULL,
        BoardModelId INT NULL,
        BoardSizeId INT NULL,
        Nickname NVARCHAR(128) NULL,
        PurchaseYear INT NULL,
        Status NVARCHAR(64) NULL,
        CurrentBoard BIT NOT NULL CONSTRAINT DF_UserQuiver_CurrentBoard DEFAULT 0,
        Notes NVARCHAR(MAX) NULL,
        IsCustomBoard BIT NOT NULL CONSTRAINT DF_UserQuiver_IsCustomBoard DEFAULT 0,
        CustomBrandName NVARCHAR(128) NULL,
        CustomModelName NVARCHAR(256) NULL,
        CustomDimensions NVARCHAR(128) NULL,
        CustomConstruction NVARCHAR(128) NULL,
        CustomVolumeLitres DECIMAL(5, 2) NULL,
        CustomProductUrl NVARCHAR(512) NULL,
        CustomImageUrl NVARCHAR(512) NULL,
        CreatedUtc DATETIME2(7) NOT NULL CONSTRAINT DF_UserQuiver_CreatedUtc DEFAULT SYSUTCDATETIME(),
        UpdatedUtc DATETIME2(7) NOT NULL CONSTRAINT DF_UserQuiver_UpdatedUtc DEFAULT SYSUTCDATETIME(),
        CONSTRAINT FK_UserQuiver_Users FOREIGN KEY (UserId) REFERENCES dbo.Users (UserId)
    );

    CREATE INDEX IX_UserQuiver_UserId_UpdatedUtc ON dbo.UserQuiver (UserId, UpdatedUtc DESC);
    CREATE INDEX IX_UserQuiver_UserId_CurrentBoard ON dbo.UserQuiver (UserId, CurrentBoard);
END;
GO

COMMIT TRANSACTION;
GO
