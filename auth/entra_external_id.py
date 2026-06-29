import os
import time
from functools import lru_cache

import requests


ENTRA_CONFIG_KEYS = {
    "tenant_id": "ENTRA_EXTERNAL_ID_TENANT_ID",
    "client_id": "ENTRA_EXTERNAL_ID_CLIENT_ID",
    "issuer": "ENTRA_EXTERNAL_ID_ISSUER",
    "jwks_url": "ENTRA_EXTERNAL_ID_JWKS_URL",
    "audience": "ENTRA_EXTERNAL_ID_AUDIENCE",
}


class AuthConfigurationError(RuntimeError):
    """Raised when Entra External ID is not configured for protected APIs."""


class AuthValidationError(RuntimeError):
    """Raised when an access token cannot be validated."""


def _config() -> dict[str, str]:
    return {
        key: os.getenv(env_name, "").strip()
        for key, env_name in ENTRA_CONFIG_KEYS.items()
    }


def is_configured() -> bool:
    config = _config()
    return all(config.values())


def missing_config_keys() -> list[str]:
    config = _config()
    return [
        env_name
        for key, env_name in ENTRA_CONFIG_KEYS.items()
        if not config[key]
    ]


def _require_config() -> dict[str, str]:
    config = _config()
    missing = [
        env_name
        for key, env_name in ENTRA_CONFIG_KEYS.items()
        if not config[key]
    ]

    if missing:
        raise AuthConfigurationError(
            "Entra External ID is not configured. Missing: "
            + ", ".join(missing)
        )

    return config


@lru_cache(maxsize=1)
def get_jwks() -> dict:
    config = _require_config()
    response = requests.get(config["jwks_url"], timeout=10)
    response.raise_for_status()
    return response.json()


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None

    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthValidationError("Authorization header must use Bearer token format.")

    return parts[1].strip() or None


def validate_access_token(token: str) -> dict:
    config = _require_config()

    try:
        import jwt
    except ImportError as exc:
        raise AuthValidationError(
            "PyJWT is required before live Entra token validation is enabled."
        ) from exc

    try:
        jwk_client = jwt.PyJWKClient(config["jwks_url"])
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=config["audience"],
            issuer=config["issuer"],
            options={"require": ["exp", "aud", "iss", "sub"]},
        )
    except Exception as exc:
        raise AuthValidationError("Access token validation failed.") from exc

    return claims


def get_current_user_optional(authorization: str | None = None) -> dict | None:
    token = _bearer_token(authorization)
    if token is None:
        return None

    claims = validate_access_token(token)
    return {
        "entraObjectId": claims.get("oid") or claims.get("sub"),
        "subject": claims.get("sub"),
        "email": claims.get("emails", [None])[0] if isinstance(claims.get("emails"), list) else claims.get("email"),
        "displayName": claims.get("name"),
        "identityProvider": claims.get("idp") or claims.get("tfp") or "entra_external_id",
        "claims": claims,
        "validatedAtUnix": int(time.time()),
    }


def require_current_user(authorization: str | None = None) -> dict:
    user = get_current_user_optional(authorization)
    if user is None:
        raise AuthValidationError("Authentication is required.")
    return user
