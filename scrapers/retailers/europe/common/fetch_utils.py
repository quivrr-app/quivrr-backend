from __future__ import annotations

from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/137.0 Safari/537.36 QuivrrEURetailerDiscovery/1.0"
)

DEFAULT_TIMEOUT_SECONDS = 18
DEFAULT_MAX_BYTES = 2_500_000

CLOUDFLARE_MARKERS = [
    "just a moment",
    "__cf_chl",
    "cf_chl",
    "enable javascript and cookies to continue",
]


@dataclass
class FetchResult:
    status: str
    url: str
    final_url: str
    http_status: int | None
    text: str
    reason: str

    @property
    def ok(self) -> bool:
        return self.status == "ok"


def is_cloudflare_challenge(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in CLOUDFLARE_MARKERS)


def has_cloudflare_headers(headers: object) -> bool:
    if not headers:
        return False

    header_text = "\n".join(
        f"{key}: {value}"
        for key, value in getattr(headers, "items", lambda: [])()
    ).lower()

    return "cloudflare" in header_text or "cf-ray" in header_text or "cf-cache-status" in header_text


def fetch_text(
    url: str,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    retries: int = 1,
) -> FetchResult:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
        },
    )

    attempts = max(1, retries + 1)
    last_reason = ""

    for attempt in range(1, attempts + 1):
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read(max_bytes)
                encoding = response.headers.get_content_charset() or "utf-8"
                text = raw.decode(encoding, errors="replace")
                http_status = getattr(response, "status", None)
                final_url = response.geturl()

                if is_cloudflare_challenge(text) or (
                    http_status in {403, 429, 503} and has_cloudflare_headers(response.headers)
                ):
                    return FetchResult(
                        status="blocked_by_cloudflare",
                        url=url,
                        final_url=final_url,
                        http_status=http_status,
                        text="",
                        reason="Cloudflare challenge markers detected",
                    )

                return FetchResult(
                    status="ok",
                    url=url,
                    final_url=final_url,
                    http_status=http_status,
                    text=text,
                    reason="",
                )
        except HTTPError as error:
            try:
                body = error.read(max_bytes)
                text = body.decode("utf-8", errors="replace")
            except Exception:
                text = ""

            if is_cloudflare_challenge(text) or (
                error.code in {403, 429, 503} and has_cloudflare_headers(error.headers)
            ):
                return FetchResult(
                    status="blocked_by_cloudflare",
                    url=url,
                    final_url=url,
                    http_status=error.code,
                    text="",
                    reason="Cloudflare challenge markers detected",
                )

            return FetchResult(
                status="http_error",
                url=url,
                final_url=url,
                http_status=error.code,
                text=text,
                reason=f"HTTP {error.code}",
            )
        except URLError as error:
            last_reason = f"{type(error.reason).__name__}: {error.reason}"
        except Exception as error:
            last_reason = f"{type(error).__name__}: {error}"

        if attempt >= attempts:
            break

    return FetchResult(
        status="network_error",
        url=url,
        final_url=url,
        http_status=None,
        text="",
        reason=last_reason or "Network error",
    )
