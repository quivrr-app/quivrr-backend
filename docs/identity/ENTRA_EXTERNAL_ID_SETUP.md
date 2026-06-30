# Entra External ID Setup

## Required Environment Variables

Do not commit real tenant IDs, client IDs or secrets.

Backend placeholders:

- `ENTRA_EXTERNAL_ID_TENANT_ID`
- `ENTRA_EXTERNAL_ID_CLIENT_ID`
- `ENTRA_EXTERNAL_ID_ISSUER`
- `ENTRA_EXTERNAL_ID_JWKS_URL`
- `ENTRA_EXTERNAL_ID_AUDIENCE`

The current backend reads these variables at runtime. Protected endpoints return `503` until all values are present.

## Azure Setup Outline

1. Create or select the Microsoft Entra External ID tenant for Quivrr customers.
2. Register the Quivrr customer-facing application.
3. Enable the required identity providers in Entra External ID.
4. Configure redirect URIs for each deployed frontend surface.
5. Configure logout redirect URIs.
6. Expose or confirm the API audience expected by the backend.
7. Add backend environment variables to Azure App Service configuration.
8. Restart the backend app service only after configuration is complete.

## Provider Readiness Checklist

Do not enable public auth until at least one provider completes a full live flow:

1. Branded My Quivrr provider chooser is live.
2. Provider button is enabled only when its Entra path is configured.
3. Provider returns to the correct Quivrr redirect URI.
4. Frontend exchanges the code successfully with PKCE.
5. `GET /api/me` returns `200`.
6. First login creates `dbo.Users`, `dbo.UserProfiles` and `dbo.UserConsents`.
7. Profile save, reload and logout work.
8. Public search still works while logged out.

## Redirect URI Placeholders

Production placeholders:

- `https://quivrr.app/australia/`
- `https://quivrr.app/europe/`
- `https://quivrr.app/united-states/`
- `https://quivrr.app/indonesia/`
- `https://quivrr.surf/`

Local development placeholders:

- `http://localhost:4280/`
- `http://localhost:5173/`

The current static frontends use same-page callbacks. Entra redirects back to the page that initiated sign-in, the browser exchanges the authorization code with PKCE, then calls `GET /api/me`.

## Frontend Public Configuration

The browser configuration is public SPA metadata and must not include secrets. Configure it before loading `my-quivrr.js`:

```html
<script>
  window.QUIVRR_AUTH_CONFIG = {
    clientId: "PUBLIC-SPA-CLIENT-ID",
    authority: "https://TENANT.ciamlogin.com/TENANT.onmicrosoft.com",
    scopes: ["openid", "profile", "email", "api://QUIVRR-API-APP-ID/access_as_user"],
    apiBaseUrl: "https://quivrr-backend-api.azurewebsites.net",
    postLogoutRedirectUri: "https://quivrr.app/"
  };
</script>
```

If `clientId` or `authority` is missing, the My Quivrr modal remains visible but sign-in reports that Entra frontend configuration is pending.

The frontend readiness config now also supports provider flags:

```html
<script>
  window.QUIVRR_AUTH_CONFIG = {
    enabled: false,
    authority: "",
    clientId: "",
    redirectUri: "",
    postLogoutRedirectUri: "",
    scopes: ["openid", "profile", "email"],
    apiBaseUrl: "https://quivrr-backend-api.azurewebsites.net",
    providers: {
      google: { enabled: false, authorizeUrl: "", message: "Google sign-in is being enabled." },
      apple: { enabled: false, authorizeUrl: "", message: "Apple sign-in is being enabled." },
      email: { enabled: false, authorizeUrl: "", message: "Email sign-in is being enabled." },
      microsoft: { enabled: false, authorizeUrl: "", message: "Microsoft sign-in is being enabled." }
    }
  };
</script>
```

## Entra Portal Areas And Required Setup

These are the concrete portal areas the current Quivrr rollout needs reviewed before public enablement.

### Google

- Portal area: `Microsoft Entra admin center -> External Identities -> All identity providers -> Google`
- Required setup:
  - Google client ID
  - Google client secret
  - the redirect and origin values required by the Google provider setup flow
- Quivrr note:
  - Keep Google disabled in `auth-config.js` until the provider completes a full live sign-in and `/api/me` validation.

### Apple

- Portal area: `Microsoft Entra admin center -> External Identities -> All identity providers -> Apple`
- Required setup:
  - Apple Services ID
  - Apple Team ID
  - Apple Key ID
  - Apple private key
- Quivrr note:
  - Keep Apple disabled until Apple returns cleanly to one of the registered Quivrr redirect URIs and `/api/me` succeeds.

### Email

- Portal areas:
  - `Microsoft Entra admin center -> External Identities -> All identity providers -> Email one-time passcode`
  - the sign-up / sign-in user flow or customer experience that exposes email sign-in to customers
- Required setup:
  - confirm the chosen email sign-in method
  - confirm the selected flow returns a usable code to the Quivrr redirect URI
- Quivrr note:
  - Do not mark Email ready until a real email-based login finishes the full PKCE callback and `/api/me` validation.

### Microsoft Personal Accounts

- Portal area:
  - the Microsoft identity provider configuration inside Entra External ID
  - plus the backing provider/client registration used during the Microsoft account handoff
- Observed live blocker:
  - production testing with `dunn.nathan@hotmail.com` reached `login.live.com` and failed with `invalid_request` because the `redirect_uri` was not registered for that provider/client handoff
- Required fix:
  - align the provider-specific Microsoft handoff with the live Quivrr redirect URIs:
    - `https://quivrr.surf/`
    - `https://quivrr.app/australia/`
    - `https://quivrr.app/europe/`
    - `https://quivrr.app/indonesia/`
    - `https://quivrr.app/united-states/`
- Quivrr note:
  - Microsoft personal accounts remain not production-ready until that provider-specific redirect issue is corrected and re-tested live.

## SQL Migration Order

Run the identity migration after the existing production schema is available:

1. `sql/identity/001_create_my_quivrr_identity_tables.sql`

The migration creates only identity-owned tables and indexes. It does not modify canonical catalogue, retailer inventory, manufacturer inventory, search tables or scraper state.

## Token Validation

The backend validation module is `auth/entra_external_id.py`.

The validation path uses:

- Entra issuer
- API audience
- JWKS URL
- RS256 signing keys

`PyJWT[crypto]` must be available in the runtime. The backend validates issuer, audience, signature, expiry and required claims before creating or updating a Quivrr user record.

## Runtime Flow

1. User clicks My Quivrr.
2. Static frontend shows a Quivrr-branded provider chooser first.
3. Only provider buttons marked ready in `auth-config.js` start a Microsoft Entra External ID authorization-code-with-PKCE flow.
4. Entra handles Email, Google, Microsoft and Apple-ready provider selection according to tenant configuration.
5. Frontend receives the code on the same page and exchanges it for tokens.
6. Frontend calls `GET /api/me` with `Authorization: Bearer <access token>`.
7. Backend validates the JWT and looks up `dbo.Users.EntraObjectId`.
8. Existing users get `LastLoginUtc` and `IdentityProvider` updated.
9. New users are inserted into `dbo.Users`, `dbo.UserProfiles` and `dbo.UserConsents`.
10. Profile fields remain optional and can be saved later through `PUT /api/my-quivrr/profile`.

## Operational Notes

- Public search must continue to work when Entra config is absent.
- Protected APIs must fail clearly when Entra config is absent.
- Access tokens must not be logged.
- Static frontend sessions use browser session storage for the token so refreshes keep the current tab signed in without long-term token storage.
- Cross-site continuity between `quivrr.surf` and `quivrr.app` is provided by the Entra browser session. Each site still obtains its own token through the same configured Entra app flow.
- No password storage exists in Quivrr.
- Customer identity must remain in Entra External ID, with Quivrr storing only profile and product interaction data needed for the product experience.
