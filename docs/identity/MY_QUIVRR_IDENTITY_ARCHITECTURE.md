# My Quivrr Identity Architecture

## Purpose

My Quivrr uses Microsoft Entra External ID as the customer identity provider. Quivrr keeps anonymous search public and adds a separate authenticated API surface for current user identity, optional profile data, consent, events and future personalised recommendations.

## Identity Provider

Microsoft Entra External ID is the only planned identity provider for customer authentication.

Future sign-in methods should be enabled inside Entra External ID, not by building a custom identity provider in Quivrr:

- Email
- Google
- Apple
- Microsoft
- Facebook later

## Public Search Boundary

These endpoints remain public and must not require authentication:

- `GET /api/brands`
- `GET /api/models/{brand_id}`
- `GET /api/constructions/{model_id}`
- `GET /api/sizes/{model_id}/{construction}`
- `GET /api/search`

Authenticated APIs are separate under `/api/me`, `/api/my-quivrr/*` and `/api/events`.

## Backend Components

`auth/entra_external_id.py` owns Entra configuration loading, JWKS retrieval, token validation hooks and current-user helpers.

The API exposes protected Sprint 16.2 endpoints:

- `GET /api/me`
- `GET /api/my-quivrr/profile`
- `PUT /api/my-quivrr/profile`
- `POST /api/logout`

The following endpoints remain placeholders and must not be surfaced as product features until their own sprint:

- `GET /api/my-quivrr/saved-boards`
- `POST /api/my-quivrr/saved-boards`
- `GET /api/my-quivrr/watchlist`
- `POST /api/my-quivrr/watchlist`

The API also exposes `POST /api/events`, which accepts anonymous events when `AnonymousSessionId` or `anonymousSessionId` is supplied.

If Entra configuration is missing, protected endpoints return a clear `503` response and public endpoints continue to run.

## SQL Ownership

Identity tables are created by `sql/identity/001_create_my_quivrr_identity_tables.sql`.

The identity schema is intentionally separate from:

- Retailer inventory
- Manufacturer inventory
- Canonical catalogue
- Search runtime tables
- Scraper outputs

`dbo.Users.EntraObjectId` stores the external identity reference. `dbo.Users.UserId` is the internal Quivrr user key used by profile, consent, event and recommendation tables.

## Privacy And Consent Model

Profile data is optional. Consent is explicit and versioned in `dbo.UserConsents`.

User behaviour events are stored in `dbo.UserEvents` rather than mixed into transactional profile tables. Anonymous events may use `AnonymousSessionId`; authenticated events may attach `UserId`.

## Bodhi Readiness

Recommendation inputs and outputs belong in `dbo.RecommendationHistory`. Bodhi should use this only after the authenticated profile flow is implemented and consent rules are confirmed.

## Frontend Integration Points

`quivrr.app` and `quivrr.surf`:

- Load Entra External ID client configuration from public deployment config, not secrets.
- Send access tokens only to `/api/me` and `/api/my-quivrr/*`.
- Keep public search calls token-free unless there is a specific analytics reason later.
- Use `POST /api/events` with `anonymousSessionId` before sign-in.
- Prompt for marketing, analytics and product notification consent explicitly.

Sprint 16.2 uses browser authorization-code-with-PKCE. Tokens are held in browser session storage so refreshes keep the current session active without committing tokens to long-term storage. Cross-site continuity relies on the Entra browser session when moving between `quivrr.surf` and `quivrr.app`.
