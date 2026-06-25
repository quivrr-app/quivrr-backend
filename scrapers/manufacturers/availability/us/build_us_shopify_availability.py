from __future__ import annotations

import argparse
import html
import json
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scrapers.manufacturers.availability.us import us_mfa_additional_sources

REGION_CODE = "US"
SOURCE = "manufacturer_direct"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; Quivrr-US-MFA/1.1; "
        "+https://quivrr.app/united-states)"
    )
}
ALBUM_PAGE_WORKERS = 8
MAX_FETCH_ATTEMPTS = 5
BASE_REQUEST_DELAY_SECONDS = 0.75
MAX_BACKOFF_SECONDS = 30.0
TARGETS = {
    "js_industries": {
        "brand_name": "JS Industries",
        "base_url": "https://us.jsindustries.com",
        "feed_path": "/products.json",
        "parser": "js",
    },
    "channel_islands": {
        "brand_name": "Channel Islands",
        "base_url": "https://cisurfboards.com",
        "feed_path": "/products.json",
        "parser": "ci",
    },
    "pyzel": {
        "brand_name": "Pyzel",
        "base_url": "https://pyzelsurfboards.com",
        "feed_path": "/products.json",
        "parser": "pyzel",
    },
    "firewire": {
        "brand_name": "Firewire",
        "base_url": "https://firewiresurfboards.com",
        "feed_path": "/products.json",
        "parser": "firewire",
    },
    "album": {
        "brand_name": "Album",
        "base_url": "https://albumsurf.com",
        "feed_path": "/collections/new-boards/products.json",
        "parser": "album",
    },
    "haydenshapes": {
        "brand_name": "Haydenshapes",
        "base_url": "https://haydenshapes.com",
        "feed_path": "/collections/surfboards/products.json",
        "parser": "haydenshapes",
    },
    "dhd": {
        "brand_name": "DHD",
        "base_url": "https://dhdsurf.com",
        "feed_path": "/collections/surfboards/products.json",
        "parser": "dhd",
    },
    "rusty": {
        "brand_name": "Rusty",
        "base_url": "https://rustysurfboards.com",
        "feed_path": "/products.json",
        "parser": "rusty",
    },
    "sharpeye": {
        "brand_name": "Sharp Eye",
        "base_url": "https://sharpeyesurfboards.com",
        "feed_path": "/products.json",
        "parser": "sharpeye",
    },
}
TARGETS.update(us_mfa_additional_sources.EXTRA_TARGETS)
OUTPUT_ROOT = Path("scrapers/manufacturers/availability")
DIAGNOSTICS_OUTPUT = OUTPUT_ROOT / "us" / "output" / "us_mfa_shopify_diagnostics.json"

JS_TITLE_RE = re.compile(
    r"^(?P<model>.*?)\s+"
    r"(?P<length>[4-9]'\d{1,2})\"?\s*x\s*"
    r"(?P<width>.*?)\s*X\s*"
    r"(?P<thickness>.*?)\s*-\s*"
    r"(?P<volume>\d+(?:\.\d+)?)L,\s*"
    r"(?P<tail>.*?),\s*"
    r"(?P<fin_no>\d+)x\s*(?P<fin_system>.*?)\s*Fin Boxes.*?,\s*"
    r"(?P<construction>[A-Za-z0-9.\- ]+)\s*-\s*ID:(?P<source_id>\d+)",
    re.I,
)
PYZEL_TITLE_RE = re.compile(
    r"^(?P<model>.*?)\s*\|\s*"
    r"(?P<length>[4-9]'\d{1,2})\"?\s*x\s*"
    r"(?P<width>.*?)\s*x\s*"
    r"(?P<thickness>.*?)\s*-\s*"
    r"(?P<volume>\d+(?:\.\d+)?)L\s*\|\s*"
    r"(?P<fin_system>[^|]+?)"
    r"(?:\|\s*(?P<construction>[^|]+?))?"
    r"(?:\||$)",
    re.I,
)
CI_VOLUME_RE = re.compile(r"Volume:\s*(?P<volume>\d+(?:\.\d+)?)L", re.I)
CI_DIMENSION_TOKEN = r"\d+(?:\.\d+)?(?:\s+\d+/\d+)?"
CI_DIMS_RE = re.compile(
    rf"(?P<length>[4-9]'\d{{1,2}})\s*x\s*(?P<width>{CI_DIMENSION_TOKEN})\s*x\s*(?P<thickness>{CI_DIMENSION_TOKEN})",
    re.I,
)
CI_FIN_RE = re.compile(r"\b(FCSII|FCS II|FCS2|Futures|Single|2\+1)\b", re.I)
CI_CONSTRUCTION_RE = re.compile(r"\b(ECT(?:-Carbon)?|EPS|PU|Poly)\b", re.I)
DIMENSION_TOKEN = r"\d+(?:\.\d+)?(?:\s+\d+/\d+)?"
GENERIC_DIMS_RE = re.compile(
    rf"(?P<length>[4-9]\s*'\s*\d{{1,2}})\"?\s*(?:x|\s)\s*"
    rf"(?P<width>{DIMENSION_TOKEN})\"?\s*(?:x|\s)\s*"
    rf"(?P<thickness>{DIMENSION_TOKEN})\"?\s*(?:x|/|-|@)\s*"
    rf"(?P<volume>\d+(?:\.\d+)?)\s*L\b",
    re.I,
)
ALBUM_PAGE_DIMS_RE = re.compile(
    r"(?P<length>[4-9]\s*'\s*\d{1,2})\"?\s*x\s*"
    r"(?P<width>\d+(?:\.\d+)?)\"?\s*x\s*"
    r"(?P<thickness>\d+(?:\.\d+)?)\"?\s*"
    r"\((?P<volume>\d+(?:\.\d+)?)\s*Lit(?:ers)?\)",
    re.I,
)
RUSTY_TITLE_RE = re.compile(
    rf"^(?P<model>.*?)\s+(?P<length>[4-9]'\d{{1,2}})\"\s*x\s*(?P<width>{DIMENSION_TOKEN})\s*x\s*(?P<thickness>{DIMENSION_TOKEN})\s*-\s*(?P<volume>\d+(?:\.\d+)?)L,\s*(?P<tail>[^,]+),\s*(?P<fin_count>\d+)x\s*(?P<fin_system>[^,]+?)\s*Fin Boxes\s*,\s*(?P<construction>[^-]+?)\s*-\s*ID:\s*(?P<source_id>\d+)",
    re.I,
)
SHARPEYE_TITLE_RE = re.compile(
    rf"^(?P<model>.*?)\s+(?P<length>[4-9]'\d{{1,2}})\"\s*x\s*(?P<width>{DIMENSION_TOKEN})\s*x\s*(?P<thickness>{DIMENSION_TOKEN})\s*-\s*(?P<volume>\d+(?:\.\d+)?)L,\s*(?P<tail>[^,]+),\s*(?P<fin_count>\d+)x\s*(?P<fin_system>[^,]+?)\s*Fin Boxes\s*,\s*(?P<construction>[^-]+?)\s*-\s*ID:\s*(?P<source_id>\d+)",
    re.I,
)
HAYDEN_LABEL_RE = re.compile(
    r"<b>\s*(?P<label>[^:]+):\s*</b>\s*(?P<value>[^<]+)",
    re.I,
)
DHD_SIZE_ONLY_RE = re.compile(
    rf"(?P<length>[4-9]\s*'\s*\d{{1,2}})\s*x\s*(?P<width>{DIMENSION_TOKEN})\s*x\s*(?P<thickness>{DIMENSION_TOKEN})\s*(?:-|/)\s*(?P<volume>\d+(?:\.\d+)?)L\b",
    re.I,
)


class SourceBuildError(RuntimeError):
    """Raised when a source cannot be built fresh."""


class SourceThrottleError(SourceBuildError):
    """Raised when a source is temporarily throttled."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean(value: object) -> str:
    value = html.unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("’", "'").replace("‘", "'")
    value = value.replace("“", '"').replace("”", '"')
    value = value.replace("×", "x")
    return re.sub(r"\s+", " ", value).strip()


def normalise_length(value: object) -> str | None:
    text = clean(value).replace('"', "")
    match = re.search(r"([4-9])\s*'\s*(\d{1,2})", text)
    if not match:
        return None
    return f"{match.group(1)}'{int(match.group(2))}"


def normalise_dimension_text(value: object) -> str | None:
    text = clean(value).replace('"', "")
    return text or None


def normalise_fin_system(value: object) -> str | None:
    text = clean(value).lower()
    if "fcs ii" in text or "fcsii" in text or "fcs2" in text or "fcs 2" in text:
        return "FCS II"
    if "future" in text:
        return "Futures"
    if "single" in text:
        return "Single"
    if "2+1" in text:
        return "2+1"
    return clean(value) or None


def normalise_construction(value: object) -> str | None:
    text = clean(value).lower()
    if "hyfi 3" in text:
        return "HYFI 3.0"
    if "hyfi 2" in text:
        return "HYFI 2.0"
    if "hyfi" in text:
        return "HYFI"
    if "spine" in text:
        return "Spine-Tek"
    if "ect" in text:
        return "ECT-Carbon"
    if "helium" in text:
        return "Helium"
    if "futureflex" in text or "future flex" in text:
        return "FutureFlex"
    if "c1 lite" in text or "c1-lite" in text or "c1 carbon" in text:
        return "C1 Lite"
    if "eps" in text:
        return "EPS"
    if "pu" in text or "poly" in text:
        return "PU"
    return clean(value) or None


def extract_ci_fin_setup(*values: object) -> str | None:
    text = " ".join(clean(value) for value in values if clean(value))
    match = CI_FIN_RE.search(text)
    if not match:
        return None
    return normalise_fin_system(match.group(1))


def extract_ci_construction(*values: object) -> str | None:
    text = " ".join(clean(value) for value in values if clean(value))
    match = CI_CONSTRUCTION_RE.search(text)
    if not match:
        return "PU"
    return normalise_construction(match.group(1)) or "PU"


def is_valid_volume(value: object) -> bool:
    if value in (None, ""):
        return True
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return 10.0 <= number <= 90.0


def paced_delay(multiplier: float = 1.0) -> None:
    time.sleep(BASE_REQUEST_DELAY_SECONDS * multiplier + random.uniform(0.0, 0.35))


def request_with_retry(
    url: str,
    *,
    session: requests.Session | None = None,
    timeout: tuple[int, int] = (10, 60),
) -> requests.Response:
    requester = session.get if session else requests.get
    response = None
    for attempt in range(1, MAX_FETCH_ATTEMPTS + 1):
        paced_delay()
        try:
            response = requester(url, headers=None if session else HEADERS, timeout=timeout)
        except requests.RequestException as exc:
            if attempt == MAX_FETCH_ATTEMPTS:
                raise SourceBuildError(f"Request failed for {url}: {type(exc).__name__}") from exc
            paced_delay(multiplier=min(2 ** attempt, 8))
            continue
        if response.status_code == 200:
            return response
        if response.status_code in {429, 500, 502, 503, 504}:
            retry_after = response.headers.get("Retry-After")
            try:
                delay = float(retry_after) if retry_after else min(2 ** attempt, MAX_BACKOFF_SECONDS)
            except ValueError:
                delay = min(2 ** attempt, MAX_BACKOFF_SECONDS)
            delay += random.uniform(0.0, 1.0)
            if attempt == MAX_FETCH_ATTEMPTS:
                if response.status_code == 429:
                    raise SourceThrottleError(
                        f"HTTP 429 from {url} after {MAX_FETCH_ATTEMPTS} attempts"
                    )
                raise SourceBuildError(
                    f"HTTP {response.status_code} from {url} after {MAX_FETCH_ATTEMPTS} attempts"
                )
            time.sleep(delay)
            continue
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise SourceBuildError(f"HTTP {response.status_code} from {url}") from exc
    raise SourceBuildError(f"Request failed for {url}")


def load_existing_output(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = json.loads(path.read_text(encoding="utf-8"))
    valid_rows = []
    for row in rows:
        if row.get("regionCode") != REGION_CODE:
            continue
        if row.get("availabilitySource") != SOURCE:
            continue
        if row.get("priceAmount") is not None and row.get("priceCurrency") != "USD":
            continue
        valid_rows.append(row)
    return valid_rows


def fetch_products(base_url: str, feed_path: str) -> list[dict]:
    session = requests.Session()
    session.headers.update(HEADERS)
    products: list[dict] = []
    for page in range(1, 40):
        url = f"{base_url.rstrip('/')}{feed_path}?limit=250&page={page}"
        response = request_with_retry(url, session=session)
        if response.status_code != 200:
            if page == 1:
                response.raise_for_status()
            break
        batch = response.json().get("products", [])
        if not batch:
            break
        products.extend(batch)
        if len(batch) < 250:
            break
    return products


def product_url(base_url: str, handle: str, variant_id: object | None) -> str:
    suffix = f"?variant={variant_id}" if variant_id else ""
    return f"{base_url.rstrip('/')}/products/{handle}{suffix}"


def product_image(product: dict, variant: dict | None = None) -> str | None:
    featured = (variant or {}).get("featured_image") or {}
    if isinstance(featured, dict) and clean(featured.get("src")):
        return clean(featured.get("src"))
    images = product.get("images") or []
    for image in images:
        if isinstance(image, dict) and clean(image.get("src")):
            return clean(image.get("src"))
    image = product.get("image")
    if isinstance(image, dict):
        return clean(image.get("src")) or None
    return None


def parse_dimensions(text: object) -> tuple[str | None, str | None, str | None, float | None]:
    value = clean(text)
    match = GENERIC_DIMS_RE.search(value)
    if not match:
        match = DHD_SIZE_ONLY_RE.search(value)
    if not match:
        return None, None, None, None
    return (
        normalise_length(match.group("length")),
        normalise_dimension_text(match.group("width")),
        normalise_dimension_text(match.group("thickness")),
        float(match.group("volume")),
    )


def build_row(
    *,
    brand_name: str,
    model_name: str,
    raw_title: str,
    base_url: str,
    product: dict,
    variant: dict,
    checked_at: str,
    length: str | None,
    width: str | None,
    thickness: str | None,
    volume: float | None,
    construction: str | None,
    fin_setup: str | None,
    tail_shape: str | None = None,
) -> dict:
    price = float(variant.get("price")) if variant.get("price") not in (None, "") else None
    available = bool(variant.get("available"))
    return {
        "brandName": brand_name,
        "modelName": clean(model_name),
        "rawProductTitle": clean(raw_title),
        "sourceUrl": product_url(base_url, clean(product.get("handle")), variant.get("id")),
        "productUrl": product_url(base_url, clean(product.get("handle")), variant.get("id")),
        "productImageUrl": product_image(product, variant),
        "priceAmount": round(price, 2) if price is not None else None,
        "priceCurrency": "USD",
        "stockStatus": "available" if available else "sold_out",
        "isAvailable": available,
        "availabilitySource": SOURCE,
        "regionCode": REGION_CODE,
        "lengthFeetInches": length,
        "width": width,
        "thickness": thickness,
        "volumeLitres": volume,
        "construction": construction,
        "finSetup": fin_setup,
        "tailShape": tail_shape,
        "sourceProductId": str(product.get("id") or ""),
        "sourceVariantId": str(variant.get("id") or ""),
        "sourceVariantTitle": clean(variant.get("title")),
        "lastCheckedUtc": checked_at,
    }


def parse_js_product(product: dict, checked_at: str, base_url: str) -> list[dict]:
    title = clean(product.get("title"))
    variant = (product.get("variants") or [{}])[0]
    match = JS_TITLE_RE.search(title)
    if not match:
        return []
    if clean(product.get("product_type")).lower() == "custom board":
        return []
    if "surfboard" not in clean(product.get("tags")).lower():
        return []
    return [
        build_row(
            brand_name="JS Industries",
            model_name=clean(match.group("model")),
            raw_title=title,
            base_url=base_url,
            product=product,
            variant=variant,
            checked_at=checked_at,
            length=clean(match.group("length")),
            width=clean(match.group("width")),
            thickness=clean(match.group("thickness")),
            volume=float(match.group("volume")),
            construction=normalise_construction(match.group("construction")),
            fin_setup=normalise_fin_system(match.group("fin_system")),
            tail_shape=clean(match.group("tail")),
        )
    ]


def parse_pyzel_product(product: dict, checked_at: str, base_url: str) -> list[dict]:
    title = clean(product.get("title"))
    match = PYZEL_TITLE_RE.search(title)
    if not match:
        return []
    if "surfboard" not in clean(product.get("tags")).lower():
        return []
    variant = (product.get("variants") or [{}])[0]
    return [
        build_row(
            brand_name="Pyzel",
            model_name=clean(match.group("model")),
            raw_title=title,
            base_url=base_url,
            product=product,
            variant=variant,
            checked_at=checked_at,
            length=clean(match.group("length")),
            width=clean(match.group("width")),
            thickness=clean(match.group("thickness")),
            volume=float(match.group("volume")),
            construction=normalise_construction(match.group("construction")),
            fin_setup=normalise_fin_system(match.group("fin_system")),
        )
    ]


def parse_ci_product(product: dict, checked_at: str, base_url: str) -> list[dict]:
    if clean(product.get("vendor")) != "Channel Islands Surfboards":
        return []
    if clean(product.get("product_type")).lower() != "surfboards":
        return []
    title = clean(product.get("title"))
    variant = (product.get("variants") or [{}])[0]
    body = clean(product.get("body_html"))
    dim_match = CI_DIMS_RE.search(body)
    volume_match = CI_VOLUME_RE.search(body)
    if not dim_match or not volume_match:
        return []
    model_name = re.sub(r"^[4-9]'\d{1,2}\s+", "", title)
    model_name = re.sub(r"\s+-\s+FCS\s*II.*$", "", model_name, flags=re.I)
    model_name = re.sub(r"\s+-\s+Futures.*$", "", model_name, flags=re.I)
    return [
        build_row(
            brand_name="Channel Islands",
            model_name=clean(model_name),
            raw_title=title,
            base_url=base_url,
            product=product,
            variant=variant,
            checked_at=checked_at,
            length=clean(dim_match.group("length")),
            width=clean(dim_match.group("width")),
            thickness=clean(dim_match.group("thickness")),
            volume=float(volume_match.group("volume")),
            construction=extract_ci_construction(title, body),
            fin_setup=extract_ci_fin_setup(title, body),
        )
    ]


def parse_firewire_product(product: dict, checked_at: str, base_url: str) -> list[dict]:
    if clean(product.get("product_type")).lower() != "surfboards":
        return []
    rows = []
    title = clean(product.get("title"))
    body = clean(product.get("body_html"))
    for variant in product.get("variants") or []:
        dims_text = clean(variant.get("option3") or variant.get("title"))
        length, width, thickness, volume = parse_dimensions(dims_text)
        if not length or volume is None:
            continue
        rows.append(
            build_row(
                brand_name="Firewire",
                model_name=title,
                raw_title=title,
                base_url=base_url,
                product=product,
                variant=variant,
                checked_at=checked_at,
                length=length,
                width=width,
                thickness=thickness,
                volume=volume,
                construction=normalise_construction(variant.get("option2") or body),
                fin_setup=normalise_fin_system(variant.get("title") or body),
                tail_shape="Diamond" if "diamond tail" in body.lower() else None,
            )
        )
    return rows


def extract_album_dimensions(url: str) -> tuple[str | None, str | None, str | None, float | None]:
    response = request_with_retry(url)
    match = ALBUM_PAGE_DIMS_RE.search(response.text)
    if not match:
        return None, None, None, None
    return (
        normalise_length(match.group("length")),
        normalise_dimension_text(match.group("width")),
        normalise_dimension_text(match.group("thickness")),
        float(match.group("volume")),
    )


def parse_album_product(product: dict, checked_at: str, base_url: str, dimensions: tuple[str | None, str | None, str | None, float | None] | None = None) -> list[dict]:
    title = clean(product.get("title"))
    if clean(product.get("product_type")).lower() != "surfboard":
        return []
    if "used" in title.lower():
        return []
    variant = (product.get("variants") or [{}])[0]
    length, width, thickness, volume = dimensions or (None, None, None, None)
    if not length or volume is None:
        return []
    model = re.sub(r"^[4-9]'\d{1,2}\"?\s*", "", title)
    model = re.sub(r"\([^)]*\)", "", model)
    model = clean(model)
    body = clean(product.get("body_html"))
    construction = None
    if "exo flex" in title.lower() or "exo flex" in body.lower():
        construction = "Exo Flex"
    return [
        build_row(
            brand_name="Album",
            model_name=model or clean(variant.get("title")) or title,
            raw_title=title,
            base_url=base_url,
            product=product,
            variant=variant,
            checked_at=checked_at,
            length=length,
            width=width,
            thickness=thickness,
            volume=volume,
            construction=construction,
            fin_setup=None,
        )
    ]


def parse_album_products(products: list[dict], checked_at: str, base_url: str) -> list[dict]:
    dimensions_by_handle: dict[str, tuple[str | None, str | None, str | None, float | None]] = {}
    urls_by_handle: dict[str, str] = {}
    for product in products:
        title = clean(product.get("title"))
        if clean(product.get("product_type")).lower() != "surfboard" or "used" in title.lower():
            continue
        variant = (product.get("variants") or [{}])[0]
        handle = clean(product.get("handle"))
        if not handle:
            continue
        urls_by_handle[handle] = product_url(base_url, handle, variant.get("id"))

    with ThreadPoolExecutor(max_workers=ALBUM_PAGE_WORKERS) as executor:
        futures = {
            executor.submit(extract_album_dimensions, url): handle
            for handle, url in urls_by_handle.items()
        }
        for future in as_completed(futures):
            handle = futures[future]
            try:
                dimensions_by_handle[handle] = future.result()
            except requests.RequestException:
                dimensions_by_handle[handle] = (None, None, None, None)

    rows: list[dict] = []
    for product in products:
        handle = clean(product.get("handle"))
        rows.extend(
            parse_album_product(
                product,
                checked_at,
                base_url,
                dimensions_by_handle.get(handle),
            )
        )
    return rows


def parse_haydenshapes_product(product: dict, checked_at: str, base_url: str) -> list[dict]:
    body = str(product.get("body_html") or "")
    rows = []
    title = clean(product.get("title"))
    product_type = clean(product.get("product_type"))
    for variant in product.get("variants") or []:
        dims_text = clean(variant.get("option2") or variant.get("title"))
        length, width, thickness, volume = parse_dimensions(dims_text)
        if not length or volume is None:
            continue
        fin_system = normalise_fin_system(variant.get("option1"))
        construction = normalise_construction(product_type)
        rows.append(
            build_row(
                brand_name="Haydenshapes",
                model_name=title.replace(" FutureFlex", "").replace(" PU Performance", "").replace(" Carbonyx", ""),
                raw_title=title,
                base_url=base_url,
                product=product,
                variant=variant,
                checked_at=checked_at,
                length=length,
                width=width,
                thickness=thickness,
                volume=volume,
                construction=construction,
                fin_setup=fin_system,
            )
        )
    if rows:
        return rows
    labels = {clean(m.group("label")).lower(): clean(m.group("value")) for m in HAYDEN_LABEL_RE.finditer(body)}
    variant = (product.get("variants") or [{}])[0]
    length = normalise_length(labels.get("length"))
    width = normalise_dimension_text(labels.get("width"))
    thickness = normalise_dimension_text(labels.get("thickness"))
    volume = float(labels["volume"]) if labels.get("volume") else None
    if not length or volume is None:
        return []
    return [
        build_row(
            brand_name="Haydenshapes",
            model_name=labels.get("model") or title,
            raw_title=title,
            base_url=base_url,
            product=product,
            variant=variant,
            checked_at=checked_at,
            length=length,
            width=width,
            thickness=thickness,
            volume=volume,
            construction=normalise_construction(labels.get("technology") or product_type),
            fin_setup=normalise_fin_system(labels.get("fin style")),
        )
    ]


def parse_dhd_product(product: dict, checked_at: str, base_url: str) -> list[dict]:
    title = clean(product.get("title"))
    body = clean(product.get("body_html"))
    if "pre-loved" in body.lower() or "ex-team" in body.lower():
        return []
    rows = []
    for variant in product.get("variants") or []:
        dims_text = clean(variant.get("option1") or variant.get("title"))
        length, width, thickness, volume = parse_dimensions(dims_text)
        if not length or volume is None:
            continue
        rows.append(
            build_row(
                brand_name="DHD",
                model_name=title,
                raw_title=title,
                base_url=base_url,
                product=product,
                variant=variant,
                checked_at=checked_at,
                length=length,
                width=width,
                thickness=thickness,
                volume=volume,
                construction=normalise_construction(title),
                fin_setup=normalise_fin_system(variant.get("option2")),
            )
        )
    return rows


def parse_rusty_product(product: dict, checked_at: str, base_url: str) -> list[dict]:
    title = clean(product.get("title"))
    tags = clean(product.get("tags")).lower()
    if "surfboard" not in tags and "new surfboard" not in tags:
        return []
    match = RUSTY_TITLE_RE.search(title)
    if not match:
        return []
    variant = (product.get("variants") or [{}])[0]
    return [
        build_row(
            brand_name="Rusty",
            model_name=clean(match.group("model")),
            raw_title=title,
            base_url=base_url,
            product=product,
            variant=variant,
            checked_at=checked_at,
            length=clean(match.group("length")),
            width=clean(match.group("width")),
            thickness=clean(match.group("thickness")),
            volume=float(match.group("volume")),
            construction=normalise_construction(match.group("construction")),
            fin_setup=normalise_fin_system(match.group("fin_system")),
            tail_shape=clean(match.group("tail")),
        )
    ]


def parse_sharpeye_product(product: dict, checked_at: str, base_url: str) -> list[dict]:
    title = clean(product.get("title"))
    if clean(product.get("vendor")) != "Sharp Eye":
        return []
    if "used surfboards" in clean(product.get("product_type")).lower():
        return []
    tags = clean(product.get("tags")).lower()
    if "new surfboard" not in tags:
        return []
    match = SHARPEYE_TITLE_RE.search(title)
    if not match:
        return []
    variant = (product.get("variants") or [{}])[0]
    return [
        build_row(
            brand_name="Sharp Eye",
            model_name=clean(match.group("model")),
            raw_title=title,
            base_url=base_url,
            product=product,
            variant=variant,
            checked_at=checked_at,
            length=clean(match.group("length")),
            width=clean(match.group("width")),
            thickness=clean(match.group("thickness")),
            volume=float(match.group("volume")),
            construction=normalise_construction(match.group("construction")),
            fin_setup=normalise_fin_system(match.group("fin_system")),
            tail_shape=clean(match.group("tail")),
        )
    ]


def parse_product(slug: str, product: dict, checked_at: str, base_url: str) -> list[dict]:
    parser = TARGETS[slug]["parser"]
    if parser == "js":
        return parse_js_product(product, checked_at, base_url)
    if parser == "pyzel":
        return parse_pyzel_product(product, checked_at, base_url)
    if parser == "ci":
        return parse_ci_product(product, checked_at, base_url)
    if parser == "firewire":
        return parse_firewire_product(product, checked_at, base_url)
    if parser == "album":
        return parse_album_product(product, checked_at, base_url)
    if parser == "haydenshapes":
        return parse_haydenshapes_product(product, checked_at, base_url)
    if parser == "dhd":
        return parse_dhd_product(product, checked_at, base_url)
    if parser == "rusty":
        return parse_rusty_product(product, checked_at, base_url)
    if parser == "sharpeye":
        return parse_sharpeye_product(product, checked_at, base_url)
    return []


def dedupe_rows(rows: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for row in rows:
        key = (
            row.get("brandName"),
            row.get("modelName"),
            row.get("lengthFeetInches"),
            row.get("width"),
            row.get("thickness"),
            row.get("volumeLitres"),
            row.get("construction"),
            row.get("productUrl"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def output_path_for_slug(slug: str) -> Path:
    return OUTPUT_ROOT / slug / "output" / f"{slug}_us_manufacturer_inventory.json"


def build_fresh(slug: str) -> dict:
    if slug in us_mfa_additional_sources.EXTRA_TARGETS:
        return us_mfa_additional_sources.build_fresh(slug, request_with_retry)
    target = TARGETS[slug]
    base_url = target["base_url"]
    checked_at = utc_now()
    products = fetch_products(base_url, target["feed_path"])
    rows: list[dict]
    if slug == "album":
        rows = parse_album_products(products, checked_at, base_url)
    else:
        rows = []
        for product in products:
            rows.extend(parse_product(slug, product, checked_at, base_url))
    rows = [row for row in rows if row.get("isAvailable") and is_valid_volume(row.get("volumeLitres"))]
    rows = dedupe_rows(rows)
    if not rows:
        raise SourceBuildError(f"No valid US MFA rows were built for {target['brand_name']}")
    output_path = output_path_for_slug(slug)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "slug": slug,
        "brand": target["brand_name"],
        "source_url": f"{base_url}{target['feed_path']}",
        "source_status": "fresh",
        "fresh_build_success": True,
        "used_stale_fallback": False,
        "error_type": None,
        "error_message_summary": None,
        "discovered_products": len(products),
        "normalised_rows": len(rows),
        "available_rows": len(rows),
        "rows_with_dimensions": sum(1 for row in rows if row.get("lengthFeetInches")),
        "rows_emitted": len(rows),
        "output": str(output_path),
        "regionCode": REGION_CODE,
        "priceCurrency": "USD",
    }


def build(slug: str) -> dict:
    if slug in us_mfa_additional_sources.EXTRA_TARGETS:
        return us_mfa_additional_sources.build(slug, request_with_retry)
    output_path = output_path_for_slug(slug)
    try:
        return build_fresh(slug)
    except Exception as exc:
        stale_rows = load_existing_output(output_path)
        if stale_rows:
            return {
                "slug": slug,
                "brand": TARGETS[slug]["brand_name"],
                "source_url": f"{TARGETS[slug]['base_url']}{TARGETS[slug]['feed_path']}",
                "source_status": "stale_fallback",
                "fresh_build_success": False,
                "used_stale_fallback": True,
                "error_type": type(exc).__name__,
                "error_message_summary": str(exc),
                "discovered_products": None,
                "normalised_rows": len(stale_rows),
                "available_rows": sum(1 for row in stale_rows if row.get("isAvailable")),
                "rows_with_dimensions": sum(1 for row in stale_rows if row.get("lengthFeetInches")),
                "rows_emitted": len(stale_rows),
                "output": str(output_path),
                "regionCode": REGION_CODE,
                "priceCurrency": "USD",
            }
        return {
            "slug": slug,
            "brand": TARGETS[slug]["brand_name"],
            "source_url": f"{TARGETS[slug]['base_url']}{TARGETS[slug]['feed_path']}",
            "source_status": "failed",
            "fresh_build_success": False,
            "used_stale_fallback": False,
            "error_type": type(exc).__name__,
            "error_message_summary": str(exc),
            "discovered_products": None,
            "normalised_rows": 0,
            "available_rows": 0,
            "rows_with_dimensions": 0,
            "rows_emitted": 0,
            "output": str(output_path),
            "regionCode": REGION_CODE,
            "priceCurrency": "USD",
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brand", choices=[*TARGETS, "all"], default="all")
    args = parser.parse_args()
    slugs = list(TARGETS) if args.brand == "all" else [args.brand]
    diagnostics = [build(slug) for slug in slugs]
    DIAGNOSTICS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DIAGNOSTICS_OUTPUT.write_text(json.dumps(diagnostics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(diagnostics, indent=2))


if __name__ == "__main__":
    main()
