from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "output" / "observability" / "job_state"
SENSITIVE_KEY_PATTERN = re.compile(
    r"(password|secret|token|api[_-]?key|connection[_-]?string|authorization)",
    re.IGNORECASE,
)
DEFAULT_PROTECTED_FIELDS = {
    "message",
    "user_message",
    "prompt",
    "page_context",
    "conversation",
    "request_body",
    "content",
}


def utc_timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _sanitize_value(value: Any, protected_fields: set[str] | None = None) -> Any:
    if isinstance(value, dict):
        return {
            key: _sanitize_field(key, item, protected_fields)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_value(item, protected_fields) for item in value]
    return value


def _sanitize_field(name: str, value: Any, protected_fields: set[str] | None = None) -> Any:
    protected = {field.lower() for field in (protected_fields or set())}
    field_name = str(name or "").lower()
    if field_name in protected or field_name in DEFAULT_PROTECTED_FIELDS:
        return "[REDACTED]"
    if SENSITIVE_KEY_PATTERN.search(field_name):
        return "[REDACTED]"
    return _sanitize_value(value, protected_fields)


def build_event(
    event: str,
    service: str,
    region: str | None = None,
    status: str | None = None,
    protected_fields: set[str] | None = None,
    **fields: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": event,
        "service": service,
        "timestamp_utc": utc_timestamp(),
    }
    if region:
        payload["region"] = region
    if status:
        payload["status"] = status
    for key, value in fields.items():
        if value is None:
            continue
        payload[key] = _sanitize_field(key, value, protected_fields)
    return payload


def emit_event(
    event: str,
    service: str,
    region: str | None = None,
    status: str | None = None,
    protected_fields: set[str] | None = None,
    **fields: Any,
) -> dict[str, Any]:
    payload = build_event(
        event,
        service,
        region=region,
        status=status,
        protected_fields=protected_fields,
        **fields,
    )
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), flush=True)
    return payload


def update_job_state(
    job_name: str,
    job_type: str,
    service: str,
    status: str,
    region: str | None = None,
    **fields: Any,
) -> dict[str, Any]:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = STATE_DIR / f"{job_name}.json"
    existing: dict[str, Any] = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}

    consecutive_failures = 0 if status == "success" else int(existing.get("consecutive_failures") or 0) + 1
    latest_success = utc_timestamp() if status == "success" else existing.get("latest_success_timestamp_utc")
    payload = build_event(
        event=f"{job_type}_job_state_updated",
        service=service,
        region=region,
        status=status,
        **fields,
    )
    payload.update(
        {
            "job_name": job_name,
            "job_type": job_type,
            "consecutive_failures": consecutive_failures,
            "latest_success_timestamp_utc": latest_success,
            "latest_status_timestamp_utc": payload["timestamp_utc"],
        }
    )
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload
