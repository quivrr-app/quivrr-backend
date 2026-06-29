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
2. Static frontend starts Microsoft Entra External ID authorization-code-with-PKCE flow.
3. Entra handles Email, Google, Microsoft and Apple-ready provider selection according to tenant configuration.
4. Frontend receives the code on the same page and exchanges it for tokens.
5. Frontend calls `GET /api/me` with `Authorization: Bearer <access token>`.
6. Backend validates the JWT and looks up `dbo.Users.EntraObjectId`.
7. Existing users get `LastLoginUtc` and `IdentityProvider` updated.
8. New users are inserted into `dbo.Users`, `dbo.UserProfiles` and `dbo.UserConsents`.
9. Profile fields remain optional and can be saved later through `PUT /api/my-quivrr/profile`.

## Operational Notes

- Public search must continue to work when Entra config is absent.
- Protected APIs must fail clearly when Entra config is absent.
- Access tokens must not be logged.
- Static frontend sessions use browser session storage for the token so refreshes keep the current tab signed in without long-term token storage.
- Cross-site continuity between `quivrr.surf` and `quivrr.app` is provided by the Entra browser session. Each site still obtains its own token through the same configured Entra app flow.
- No password storage exists in Quivrr.
- Customer identity must remain in Entra External ID, with Quivrr storing only profile and product interaction data needed for the product experience.
