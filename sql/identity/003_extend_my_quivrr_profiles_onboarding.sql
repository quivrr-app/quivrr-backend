SET XACT_ABORT ON;
GO

BEGIN TRANSACTION;
GO

IF COL_LENGTH('dbo.UserProfiles', 'CurrentBoard') IS NULL
BEGIN
    ALTER TABLE dbo.UserProfiles
    ADD CurrentBoard NVARCHAR(256) NULL;
END;
GO

IF COL_LENGTH('dbo.UserProfiles', 'SurfingGoal') IS NULL
BEGIN
    ALTER TABLE dbo.UserProfiles
    ADD SurfingGoal NVARCHAR(128) NULL;
END;
GO

COMMIT TRANSACTION;
GO
