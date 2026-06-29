# My Quivrr Profile, Quiver And Activity

## Profile Model

Profile fields are optional and live across `dbo.Users` and `dbo.UserProfiles`.

User identity fields:

- `UserId`
- `EntraObjectId`
- `Email`
- `DisplayName`
- `IdentityProvider`
- `HomeRegion`
- `CreatedUtc`
- `LastLoginUtc`

Profile fields:

- `HeightCm`
- `WeightKg`
- `Ability`
- `CurrentVolumeLitres`
- `PreferredVolumeMinLitres`
- `PreferredVolumeMaxLitres`
- `WaveType`
- `WaveSize`
- `SurfFrequency`
- `HomeBreak`
- `HomeCountry`
- `PreferredBrands`

## Quiver Model

`dbo.UserQuiver` stores both official Quivrr boards and custom boards.

Core fields:

- `QuiverId`
- `UserId`
- `BoardModelId`
- `BoardSizeId`
- `Nickname`
- `PurchaseYear`
- `Status`
- `CurrentBoard`
- `Notes`
- `CreatedUtc`
- `UpdatedUtc`

Custom board support:

- `IsCustomBoard`
- `CustomBrandName`
- `CustomModelName`
- `CustomDimensions`
- `CustomConstruction`
- `CustomVolumeLitres`
- `CustomProductUrl`
- `CustomImageUrl`

`Status` is intentionally flexible so users can use:

- `Current board`
- `Favourite board`
- `Travel board`
- `Step-up`
- `Grovel board`
- `Longboard`
- any custom label that fits their quiver

## Saved Boards Model

`dbo.SavedBoards` stores the user shortlist for future review.

Fields used by Sprint 16.3:

- `SavedBoardId`
- `UserId`
- `BoardModelId`
- `BoardSizeId`
- `RegionCode`
- `Notes`
- `CreatedUtc`

Saved boards are returned with joined canonical context where available:

- `BrandName`
- `ModelName`
- `Construction`
- `LengthFeetInches`
- `Width`
- `Thickness`
- `VolumeLitres`

## Recent Activity

Recent activity is read from `dbo.UserEvents` and limited to the latest 20 rows.

Sprint 16.3 writes:

- `ProfileUpdated`
- `BoardSaved`
- `BoardRemoved`
- `QuiverUpdated`
- `BoardViewed`
- `SearchPerformed`

## API Endpoints

Implemented in Sprint 16.3:

- `GET /api/my-quivrr/profile`
- `PUT /api/my-quivrr/profile`
- `GET /api/my-quivrr/quiver`
- `POST /api/my-quivrr/quiver`
- `DELETE /api/my-quivrr/quiver/{id}`
- `GET /api/my-quivrr/saved-boards`
- `POST /api/my-quivrr/saved-boards`
- `DELETE /api/my-quivrr/saved-boards/{id}`
- `POST /api/events`

Response shape notes:

- profile response includes `recentActivity`
- quiver response returns `quiver[]`
- saved boards response returns `savedBoards[]`
- public search remains anonymous

## Frontend Behaviour

- My Quivrr opens from the existing modal shell.
- Authenticated users see profile summary, quiver, saved boards and recent activity.
- Search result cards can write `BoardViewed`, `SearchPerformed`, `BoardSaved` and quiver actions through the backend.
- Anonymous users can still search normally and create anonymous activity rows through `AnonymousSessionId`.
