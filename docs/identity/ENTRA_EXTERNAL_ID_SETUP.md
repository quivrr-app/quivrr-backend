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

- `https://quivrr.app/auth/callback`
- `https://quivrr.app/australia/auth/callback`
- `https://quivrr.app/europe/auth/callback`
- `https://quivrr.app/united-states/auth/callback`
- `https://quivrr.app/indonesia/auth/callback`
- `https://quivrr.surf/auth/callback`

Local development placeholders:

- `http://localhost:4280/auth/callback`
- `http://localhost:5173/auth/callback`

Final frontend routing should decide the exact callback paths before live OAuth is enabled.

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

`PyJWT` must be available in the runtime before live Entra validation is enabled. Sprint 16.1 keeps OAuth wiring disabled until configuration and deployment steps are reviewed.

## Operational Notes

- Public search must continue to work when Entra config is absent.
- Protected APIs must fail clearly when Entra config is absent.
- Access tokens must not be logged.
- No password storage exists in Quivrr.
- Customer identity must remain in Entra External ID, with Quivrr storing only profile and product interaction data needed for the product experience.
