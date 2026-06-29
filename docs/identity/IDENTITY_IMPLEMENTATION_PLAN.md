# Identity Implementation Plan

## Sprint 16.1 Scope

Sprint 16.1 establishes the identity foundation only:

- Backend Entra External ID configuration placeholders.
- JWT validation module.
- Protected My Quivrr endpoint stubs.
- Anonymous event intake placeholder.
- SQL migration scripts for user-owned data.
- Documentation for Azure setup, consent and frontend integration.

Live OAuth was not enabled in Sprint 16.1.

## Sprint 16.2 Scope

1. Add `PyJWT[crypto]` to the backend runtime.
2. Configure Entra External ID in Azure App Service settings.
3. Apply `sql/identity/001_create_my_quivrr_identity_tables.sql` after review.
4. Implement user upsert on successful token validation.
5. Implement profile read/write persistence.
6. Add frontend sign-in shell wiring for `quivrr.app`.
7. Add frontend sign-in shell wiring for `quivrr.surf`.
8. Keep public search anonymous.

Sprint 16.2 deliberately does not implement saved boards, watchlists, alerts or notifications.

## Frontend Integration Sequence

`quivrr.app` should integrate first because it owns regional search and saved board workflows.

Recommended order:

1. Add frontend config placeholders for Entra authority, client ID, scopes and redirect URI.
2. Add sign-in and sign-out actions to the existing My Quivrr shell.
3. Call `GET /api/me` after sign-in.
4. Add profile form read/write using `/api/my-quivrr/profile`.
5. Keep saved boards, watchlists and alerts out of scope until the next product sprint.
6. Send anonymous `POST /api/events` before sign-in when analytics is approved.
7. Attach authenticated event context after sign-in when analytics is approved.

`quivrr.surf` uses the same My Quivrr sign-in client as `quivrr.app`. The shared Entra browser session provides cross-site continuity; each static site still obtains its own token before calling the API.

## Consent Model

Consent should be explicit and versioned.

Recommended initial consent version:

- `my-quivrr-consent-v1`

Consent categories:

- Marketing consent
- Analytics consent
- Product notification consent

Product notification consent should be required before stock alerts, price alerts or release notifications are sent.

## Analytics Event Model

Initial event types:

- `search_viewed`
- `board_saved`
- `watchlist_created`
- `retailer_clicked`
- `manufacturer_clicked`
- `bodhi_recommendation_viewed`
- `bodhi_recommendation_followed`

Events should store structured JSON in `EventPayload` and avoid secrets or raw access tokens.

## Open Decisions

- Final frontend redirect URI shape.
- Whether saved boards should allow model-only saves, size-only saves, or both.
- Whether watchlists should require a region.
- Email delivery provider for notification flows.
- Retention policy for anonymous events.

## Non-Goals

- No custom password store.
- No custom identity provider.
- No changes to retailer inventory.
- No changes to manufacturer inventory.
- No changes to canonical catalogue.
- No changes to public search behaviour.
