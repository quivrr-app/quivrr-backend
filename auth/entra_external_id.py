import os
import time
from functools import lru_cache
from urllib.parse import urlparse

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


@lru_cache(maxsize=1)
def get_jwk_client():
    config = _require_config()

    try:
        import jwt
    except ImportError as exc:
        raise AuthConfigurationError(
            "PyJWT is required before live Entra token validation is enabled."
        ) from exc

    return jwt.PyJWKClient(config["jwks_url"])


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
        jwk_client = get_jwk_client()
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=config["audience"],
            issuer=config["issuer"],
            options={"require": ["exp", "aud", "iss", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise AuthValidationError("Access token validation failed.") from exc
    except Exception as exc:
        raise AuthValidationError("Access token signing key validation failed.") from exc

    return claims


def _claim_email(claims: dict) -> str | None:
    emails = claims.get("emails")
    if isinstance(emails, list) and emails:
        return emails[0]
    return claims.get("email") or claims.get("preferred_username") or claims.get("upn")


def _identity_provider(claims: dict) -> str:
    provider = claims.get("idp") or claims.get("identityProvider") or claims.get("tfp") or claims.get("acr")
    if provider:
        return str(provider)[:64]

    issuer = claims.get("iss")
    if issuer:
        hostname = urlparse(str(issuer)).hostname
        if hostname:
            return hostname[:64]

    return "entra_external_id"


def get_current_user_optional(authorization: str | None = None) -> dict | None:
    token = _bearer_token(authorization)
    if token is None:
        return None

    claims = validate_access_token(token)
    entra_object_id = claims.get("oid") or claims.get("sub")
    if not entra_object_id:
        raise AuthValidationError("Access token does not contain an Entra object identifier.")

    return {
        "entraObjectId": entra_object_id,
        "subject": claims.get("sub"),
        "email": _claim_email(claims),
        "displayName": claims.get("name") or claims.get("given_name"),
        "identityProvider": _identity_provider(claims),
        "claims": claims,
        "validatedAtUnix": int(time.time()),
    }


def require_current_user(authorization: str | None = None) -> dict:
    user = get_current_user_optional(authorization)
    if user is None:
        raise AuthValidationError("Authentication is required.")
    return user
