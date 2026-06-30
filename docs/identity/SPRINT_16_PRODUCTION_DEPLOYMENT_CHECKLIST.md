# Sprint 16 Production Deployment Checklist

This checklist prepares Sprint 16.1, 16.2 and 16.3 for a safe production rollout of My Quivrr identity, profile and quiver.

## Scope

- Backend identity foundation
- Microsoft Entra External ID authentication
- My Quivrr profile and quiver
- Anonymous search must remain open throughout rollout

## Deployment Order

1. Review and apply SQL migrations.
2. Deploy backend code and backend App Settings.
3. Validate backend identity endpoints before enabling frontend auth.
4. Deploy frontend config-loader support.
5. Publish environment-specific `auth-config.js` values for `quivrr.app`.
6. Validate `quivrr.app` login flow.
7. Publish environment-specific `auth-config.js` values for `quivrr.surf`.
8. Validate `quivrr.surf` login flow.

## SQL Migration Order

Run in order:

1. `sql/identity/001_create_my_quivrr_identity_tables.sql`
2. `sql/identity/002_create_my_quivrr_quiver.sql`

Migration safety status:

- idempotent table guards are present with `IF OBJECT_ID(...) IS NULL`
- wrapped in transactions
- no destructive `DROP`, `TRUNCATE` or inventory/search mutations
- scope limited to identity-owned tables and their indexes

## Azure Backend App Settings

Set before enabling frontend auth:

- `ENTRA_EXTERNAL_ID_TENANT_ID`
- `ENTRA_EXTERNAL_ID_CLIENT_ID`
- `ENTRA_EXTERNAL_ID_ISSUER`
- `ENTRA_EXTERNAL_ID_JWKS_URL`
- `ENTRA_EXTERNAL_ID_AUDIENCE`

Validation after save:

1. Restart or recycle the backend App Service if required by Azure configuration propagation.
2. Confirm `/api/me` returns a 401-style unauthenticated response without crashing when called anonymously.
3. Confirm authenticated tokens validate successfully in a staging or controlled production test.

## Static Web App Config Injection

Each frontend must load `auth-config.js` before `my-quivrr.js`.

Recommended release pattern:

1. Keep the repository placeholder file disabled.
2. During release, overwrite `auth-config.js` with environment-specific values.
3. Do not commit tenant-specific values.
4. Keep `enabled=false` until backend validation is complete.

## Microsoft Entra External ID Setup

Confirm tenant/app registration supports:

- Email sign-in
- Google identity provider
- Microsoft identity provider
- Apple provider readiness if not yet enabled live

Required redirect URIs should include the live public pages that host My Quivrr:

- `https://quivrr.app/australia/`
- `https://quivrr.app/europe/`
- `https://quivrr.app/indonesia/`
- `https://quivrr.app/united-states/`
- `https://quivrr.surf/`

Also register post-logout redirect URIs for the same public surfaces.

Provider readiness must be validated explicitly:

- Google provider configured and returns to Quivrr correctly.
- Apple provider configured and returns to Quivrr correctly.
- Email sign-in flow configured and returns a usable authorization code.
- Microsoft personal account provider redirect URI issue resolved before public enablement.
- At least one provider completes a full live sign-in plus `/api/me` validation before `enabled=true`.

## Backend Validation

Run and confirm:

1. Anonymous `GET /api/me` returns the expected unauthenticated contract.
2. Authenticated `GET /api/me` creates a user if needed and returns a profile bundle.
3. `GET /api/my-quivrr/profile` works after first login.
4. `PUT /api/my-quivrr/profile` persists optional profile fields.
5. Quiver and saved-board endpoints work for authenticated users only.
6. Search, retailer inventory and manufacturer inventory endpoints remain publicly accessible.

## Production Validation Status

Validation run completed on June 30, 2026 against live production.

Completed successfully:

- Backend Entra External ID configuration is live.
- Anonymous `GET /api/me` now returns `401 Authentication is required.` instead of the pre-configuration `503` contract.
- Invalid and malformed JWTs return fast `401` responses.
- Public endpoints remained healthy during identity configuration validation:
  - `/`
  - `/api/brands`
  - `/api/search?boardSizeId=179264&region=AU`
- Frontend `auth-config.js` remains disabled on both `quivrr.app` and `quivrr.surf`.
- With `enabled=false`, My Quivrr opens safely and shows the branded provider chooser plus provider-specific "sign-in is being enabled" messaging.

Blocked / not yet complete:

- Full first-user sign-in was blocked by mandatory Microsoft Authenticator enrollment in the Entra tenant during live production testing.
- Because first sign-in could not complete, the following production checks remain blocked:
  - automatic creation of `Users`, `UserProfiles`, `UserConsents`
  - authenticated `/api/me`
  - profile onboarding, skip flow, profile update and logout after live token issuance
  - cross-site authenticated continuity between `quivrr.surf` and `quivrr.app`
  - authenticated `UserEvents` verification
- Production testing with a Microsoft personal account reached `login.live.com` and failed with an `invalid_request redirect_uri` mismatch, which confirms the Microsoft provider handoff is not ready for public auth enablement.

Current recommendation:

- Do not set frontend `auth-config.js` to `enabled=true` yet.
- Resolve the tenant-side first-login MFA/onboarding path or provide an approved validation identity that can complete the live Entra flow.
- Re-run the blocked first-user and returning-user checks after tenant policy is confirmed.

## Frontend Validation

With `enabled=false`:

- My Quivrr entry remains visible.
- Clicking it does not crash the page.
- The modal shows the branded provider chooser.
- Continue as guest closes the modal and leaves public search available.
- Disabled providers report which sign-in path is still being enabled.

With `enabled=true`:

1. Sign-in redirects into Entra using PKCE.
2. Callback returns to the expected page.
3. Session persists through refresh.
4. `GET /api/me` succeeds after login.
5. First-login profile completion can be skipped.
6. Profile, saved boards and quiver load successfully.
7. Logout clears the session and returns to the configured post-logout URI.

## Anonymous Search Validation

Before and after identity rollout:

- region pages still load anonymously
- search remains open
- manufacturer availability remains visible
- retailer inventory remains visible
- Bodhi basic mode remains available

## Rollback

If backend auth validation fails:

1. Revert backend deployment to the previous production release.
2. Keep frontend `auth-config.js` set to `enabled=false`.
3. Do not remove identity tables unless an explicit rollback script is designed and approved later.

If frontend sign-in fails:

1. Set frontend `auth-config.js` back to `enabled=false`.
2. Redeploy the static site config only.
3. Leave backend identity code in place; anonymous behaviour remains safe.

## Known Limitations

- Cross-site authentication depends on correct redirect URI registration for both `quivrr.app` and `quivrr.surf`.
- Session persistence is frontend-managed and browser-local; both sites require correct environment config even when they share the same Entra tenant.
- Sprint 16 does not include alerts, notifications, Bodhi Personal or commerce workflows.
