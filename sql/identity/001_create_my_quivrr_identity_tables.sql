SET XACT_ABORT ON;
GO

BEGIN TRANSACTION;
GO

IF OBJECT_ID('dbo.Users', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.Users (
        UserId UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_Users PRIMARY KEY DEFAULT NEWID(),
        EntraObjectId NVARCHAR(128) NOT NULL,
        Email NVARCHAR(320) NULL,
        DisplayName NVARCHAR(256) NULL,
        IdentityProvider NVARCHAR(64) NOT NULL CONSTRAINT DF_Users_IdentityProvider DEFAULT 'entra_external_id',
        HomeRegion NVARCHAR(16) NULL,
        CreatedUtc DATETIME2(7) NOT NULL CONSTRAINT DF_Users_CreatedUtc DEFAULT SYSUTCDATETIME(),
        LastLoginUtc DATETIME2(7) NULL,
        IsActive BIT NOT NULL CONSTRAINT DF_Users_IsActive DEFAULT 1
    );

    CREATE UNIQUE INDEX UX_Users_EntraObjectId ON dbo.Users (EntraObjectId);
    CREATE INDEX IX_Users_Email ON dbo.Users (Email);
END;
GO

IF OBJECT_ID('dbo.UserProfiles', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.UserProfiles (
        UserProfileId UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_UserProfiles PRIMARY KEY DEFAULT NEWID(),
        UserId UNIQUEIDENTIFIER NOT NULL,
        HeightCm INT NULL,
        WeightKg INT NULL,
        Ability NVARCHAR(64) NULL,
        CurrentVolumeLitres DECIMAL(5, 2) NULL,
        PreferredVolumeMinLitres DECIMAL(5, 2) NULL,
        PreferredVolumeMaxLitres DECIMAL(5, 2) NULL,
        WaveType NVARCHAR(128) NULL,
        WaveSize NVARCHAR(128) NULL,
        SurfFrequency NVARCHAR(128) NULL,
        PreferredBrands NVARCHAR(MAX) NULL,
        HomeBreak NVARCHAR(256) NULL,
        HomeCountry NVARCHAR(128) NULL,
        UpdatedUtc DATETIME2(7) NOT NULL CONSTRAINT DF_UserProfiles_UpdatedUtc DEFAULT SYSUTCDATETIME(),
        CONSTRAINT FK_UserProfiles_Users FOREIGN KEY (UserId) REFERENCES dbo.Users (UserId)
    );

    CREATE UNIQUE INDEX UX_UserProfiles_UserId ON dbo.UserProfiles (UserId);
END;
GO

IF OBJECT_ID('dbo.UserConsents', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.UserConsents (
        UserConsentId UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_UserConsents PRIMARY KEY DEFAULT NEWID(),
        UserId UNIQUEIDENTIFIER NOT NULL,
        ConsentVersion NVARCHAR(64) NOT NULL,
        MarketingConsent BIT NOT NULL CONSTRAINT DF_UserConsents_MarketingConsent DEFAULT 0,
        AnalyticsConsent BIT NOT NULL CONSTRAINT DF_UserConsents_AnalyticsConsent DEFAULT 0,
        ProductNotificationConsent BIT NOT NULL CONSTRAINT DF_UserConsents_ProductNotificationConsent DEFAULT 0,
        ConsentCapturedUtc DATETIME2(7) NOT NULL CONSTRAINT DF_UserConsents_ConsentCapturedUtc DEFAULT SYSUTCDATETIME(),
        ConsentSource NVARCHAR(128) NULL,
        CONSTRAINT FK_UserConsents_Users FOREIGN KEY (UserId) REFERENCES dbo.Users (UserId)
    );

    CREATE INDEX IX_UserConsents_UserId_CapturedUtc ON dbo.UserConsents (UserId, ConsentCapturedUtc DESC);
END;
GO

IF OBJECT_ID('dbo.UserEvents', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.UserEvents (
        UserEventId BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_UserEvents PRIMARY KEY,
        UserId UNIQUEIDENTIFIER NULL,
        AnonymousSessionId NVARCHAR(128) NULL,
        EventType NVARCHAR(128) NOT NULL,
        RegionCode NVARCHAR(16) NULL,
        BrandName NVARCHAR(128) NULL,
        ModelName NVARCHAR(256) NULL,
        BoardModelId INT NULL,
        BoardSizeId INT NULL,
        RetailerId INT NULL,
        ManufacturerName NVARCHAR(128) NULL,
        EventPayload NVARCHAR(MAX) NULL,
        CreatedUtc DATETIME2(7) NOT NULL CONSTRAINT DF_UserEvents_CreatedUtc DEFAULT SYSUTCDATETIME(),
        CONSTRAINT FK_UserEvents_Users FOREIGN KEY (UserId) REFERENCES dbo.Users (UserId)
    );

    CREATE INDEX IX_UserEvents_UserId_CreatedUtc ON dbo.UserEvents (UserId, CreatedUtc DESC);
    CREATE INDEX IX_UserEvents_AnonymousSessionId_CreatedUtc ON dbo.UserEvents (AnonymousSessionId, CreatedUtc DESC);
    CREATE INDEX IX_UserEvents_EventType_CreatedUtc ON dbo.UserEvents (EventType, CreatedUtc DESC);
END;
GO

IF OBJECT_ID('dbo.SavedBoards', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.SavedBoards (
        SavedBoardId UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_SavedBoards PRIMARY KEY DEFAULT NEWID(),
        UserId UNIQUEIDENTIFIER NOT NULL,
        BoardModelId INT NULL,
        BoardSizeId INT NULL,
        RegionCode NVARCHAR(16) NULL,
        Notes NVARCHAR(MAX) NULL,
        CreatedUtc DATETIME2(7) NOT NULL CONSTRAINT DF_SavedBoards_CreatedUtc DEFAULT SYSUTCDATETIME(),
        CONSTRAINT FK_SavedBoards_Users FOREIGN KEY (UserId) REFERENCES dbo.Users (UserId)
    );

    CREATE INDEX IX_SavedBoards_UserId_CreatedUtc ON dbo.SavedBoards (UserId, CreatedUtc DESC);
END;
GO

IF OBJECT_ID('dbo.UserWatchlists', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.UserWatchlists (
        WatchlistId UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_UserWatchlists PRIMARY KEY DEFAULT NEWID(),
        UserId UNIQUEIDENTIFIER NOT NULL,
        BoardModelId INT NULL,
        BoardSizeId INT NULL,
        RegionCode NVARCHAR(16) NOT NULL,
        ManufacturerAlerts BIT NOT NULL CONSTRAINT DF_UserWatchlists_ManufacturerAlerts DEFAULT 1,
        RetailerAlerts BIT NOT NULL CONSTRAINT DF_UserWatchlists_RetailerAlerts DEFAULT 1,
        PriceAlerts BIT NOT NULL CONSTRAINT DF_UserWatchlists_PriceAlerts DEFAULT 0,
        CreatedUtc DATETIME2(7) NOT NULL CONSTRAINT DF_UserWatchlists_CreatedUtc DEFAULT SYSUTCDATETIME(),
        IsActive BIT NOT NULL CONSTRAINT DF_UserWatchlists_IsActive DEFAULT 1,
        CONSTRAINT FK_UserWatchlists_Users FOREIGN KEY (UserId) REFERENCES dbo.Users (UserId)
    );

    CREATE INDEX IX_UserWatchlists_UserId_Active ON dbo.UserWatchlists (UserId, IsActive);
END;
GO

IF OBJECT_ID('dbo.UserNotificationSettings', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.UserNotificationSettings (
        NotificationSettingsId UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_UserNotificationSettings PRIMARY KEY DEFAULT NEWID(),
        UserId UNIQUEIDENTIFIER NOT NULL,
        EmailEnabled BIT NOT NULL CONSTRAINT DF_UserNotificationSettings_EmailEnabled DEFAULT 1,
        WeeklyDigestEnabled BIT NOT NULL CONSTRAINT DF_UserNotificationSettings_WeeklyDigestEnabled DEFAULT 0,
        NewStockEnabled BIT NOT NULL CONSTRAINT DF_UserNotificationSettings_NewStockEnabled DEFAULT 1,
        PriceChangeEnabled BIT NOT NULL CONSTRAINT DF_UserNotificationSettings_PriceChangeEnabled DEFAULT 0,
        ManufacturerReleaseEnabled BIT NOT NULL CONSTRAINT DF_UserNotificationSettings_ManufacturerReleaseEnabled DEFAULT 0,
        UpdatedUtc DATETIME2(7) NOT NULL CONSTRAINT DF_UserNotificationSettings_UpdatedUtc DEFAULT SYSUTCDATETIME(),
        CONSTRAINT FK_UserNotificationSettings_Users FOREIGN KEY (UserId) REFERENCES dbo.Users (UserId)
    );

    CREATE UNIQUE INDEX UX_UserNotificationSettings_UserId ON dbo.UserNotificationSettings (UserId);
END;
GO

IF OBJECT_ID('dbo.RecommendationHistory', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.RecommendationHistory (
        RecommendationHistoryId UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_RecommendationHistory PRIMARY KEY DEFAULT NEWID(),
        UserId UNIQUEIDENTIFIER NOT NULL,
        RegionCode NVARCHAR(16) NULL,
        ProfileSnapshot NVARCHAR(MAX) NOT NULL,
        RecommendationPayload NVARCHAR(MAX) NOT NULL,
        FollowedSearch BIT NOT NULL CONSTRAINT DF_RecommendationHistory_FollowedSearch DEFAULT 0,
        CreatedUtc DATETIME2(7) NOT NULL CONSTRAINT DF_RecommendationHistory_CreatedUtc DEFAULT SYSUTCDATETIME(),
        CONSTRAINT FK_RecommendationHistory_Users FOREIGN KEY (UserId) REFERENCES dbo.Users (UserId)
    );

    CREATE INDEX IX_RecommendationHistory_UserId_CreatedUtc ON dbo.RecommendationHistory (UserId, CreatedUtc DESC);
END;
GO

COMMIT TRANSACTION;
GO
