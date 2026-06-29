# Sprint 16 Environment Variables

This document defines the configuration surface needed to enable My Quivrr identity in production without committing tenant-specific values into source control.

## Backend

Set these values on the backend App Service only. Use production secrets or tenant values in Azure App Settings, never in Git.

| Variable | Required | Purpose |
| --- | --- | --- |
| `ENTRA_EXTERNAL_ID_TENANT_ID` | Yes | Microsoft Entra External ID tenant identifier. |
| `ENTRA_EXTERNAL_ID_CLIENT_ID` | Yes | Application client ID used by the public SPA and backend JWT audience validation. |
| `ENTRA_EXTERNAL_ID_ISSUER` | Yes | Expected JWT issuer URI. |
| `ENTRA_EXTERNAL_ID_JWKS_URL` | Yes | JWKS discovery endpoint used for token signature validation. |
| `ENTRA_EXTERNAL_ID_AUDIENCE` | Yes | Expected API audience claim. |

Example placeholders only:

```text
ENTRA_EXTERNAL_ID_TENANT_ID=00000000-0000-0000-0000-000000000000
ENTRA_EXTERNAL_ID_CLIENT_ID=11111111-1111-1111-1111-111111111111
ENTRA_EXTERNAL_ID_ISSUER=https://exampletenant.ciamlogin.com/exampletenant.onmicrosoft.com/v2.0/
ENTRA_EXTERNAL_ID_JWKS_URL=https://exampletenant.ciamlogin.com/exampletenant.onmicrosoft.com/discovery/v2.0/keys
ENTRA_EXTERNAL_ID_AUDIENCE=api://example-client-id
```

## Frontend

Both `quivrr.app` and `quivrr.surf` should load an environment-owned `auth-config.js` before `my-quivrr.js`.

Required runtime shape:

```js
window.QUIVRR_AUTH_CONFIG = {
  enabled: false,
  authority: "",
  clientId: "",
  redirectUri: "",
  postLogoutRedirectUri: "",
  scopes: ["openid", "profile", "email"],
  apiBaseUrl: "https://quivrr-backend-api.azurewebsites.net",
};
```

Behaviour:

- `enabled: false`
  - My Quivrr remains visible.
  - Search, retailer inventory, manufacturer inventory and Bodhi continue working anonymously.
  - Sign-in opens the modal but shows a safe "being enabled" status instead of throwing runtime errors.
- `enabled: true`
  - The frontend uses the PKCE redirect flow already implemented in `my-quivrr.js`.

Example placeholders only:

```js
window.QUIVRR_AUTH_CONFIG = {
  enabled: true,
  authority: "https://exampletenant.ciamlogin.com/exampletenant.onmicrosoft.com",
  clientId: "11111111-1111-1111-1111-111111111111",
  redirectUri: "https://quivrr.app/australia/",
  postLogoutRedirectUri: "https://quivrr.app/australia/",
  scopes: ["openid", "profile", "email", "api://example-client-id/access_as_user"],
  apiBaseUrl: "https://quivrr-backend-api.azurewebsites.net",
};
```

## Static Web App Injection Pattern

Recommended approach:

1. Keep the checked-in `auth-config.js` file as disabled placeholder config.
2. Replace or overwrite `auth-config.js` during the Static Web App release step for each environment.
3. Do not inline tenant IDs directly into page templates.
4. Keep `redirectUri` and `postLogoutRedirectUri` aligned with the deployed site origin and page path.

## Cross-Site Notes

- `quivrr.app` and `quivrr.surf` each need their own valid redirect URI entries in Entra.
- Both frontends may use the same Entra application only if all redirect URIs are explicitly registered.
- Token/session persistence is browser-local; each site still needs its own frontend config file even when both point to the same tenant and client.
