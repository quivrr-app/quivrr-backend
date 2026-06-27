from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONFIG_PATH = ROOT / "config" / "dealer_source_policy.json"
OUTPUT_DIR = ROOT / "scripts" / "dealers" / "output"
JSON_OUTPUT_PATH = OUTPUT_DIR / "global_dealer_network_report.json"
MD_OUTPUT_PATH = OUTPUT_DIR / "global_dealer_network_report.md"
SQL_SNAPSHOT_STATUS = {
    "available": False,
    "error": None,
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0 Safari/537.36 QuivrrDealerDiscovery/1.0"
    )
}

HIGH_PRIORITY_REGIONS = {"AU", "US", "EU", "ID"}
FUTURE_REGIONS = {"CA", "UK", "JP", "NZ", "BR", "ZA", "MX", "PR", "HI"}
EU_COUNTRIES = {
    "Portugal",
    "Spain",
    "France",
    "Germany",
    "Netherlands",
    "Ireland",
    "Italy",
    "Belgium",
    "Denmark",
    "Norway",
    "Sweden",
    "Switzerland",
    "Austria",
}


@dataclass
class CurrentRetailer:
    retailer_name: str
    website: str | None
    platform: str | None
    configured: bool
    enabled: bool
    region_code: str
    source_file: str
    notes: str | None = None
    active_rows: int = 0
    last_successful_scrape_utc: str | None = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_policy() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalise_dealer_name(value: Any) -> str:
    text_value = clean_text(value).lower()
    text_value = text_value.replace("&", " and ")
    text_value = text_value.replace("’", "'")
    text_value = re.sub(r"[^a-z0-9]+", " ", text_value)
    text_value = re.sub(r"\b(surfboards|surfboard|surf shop|surfshop|board store|boardstore)\b", " ", text_value)
    return re.sub(r"\s+", " ", text_value).strip()


def canonical_domain(value: Any) -> str | None:
    raw = normalise_website(value)
    if not raw:
        return None
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    hostname = parsed.netloc.lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname or None


def normalise_website(value: Any) -> str | None:
    raw = clean_text(value)
    if not raw:
        return None
    href_match = re.search(r'href="([^"]+)"', raw, re.I)
    if href_match:
        return href_match.group(1).strip()
    if raw.lower().startswith(("http://", "https://")):
        return raw
    return None


def infer_region_code(country: str | None, state_or_province: str | None = None) -> str:
    country_value = clean_text(country)
    state_value = clean_text(state_or_province)
    combined = f"{country_value} {state_value}".lower()

    if "puerto rico" in combined:
        return "PR"
    if "hawaii" in combined or "o'ahu" in combined or "maui" in combined or "kauai" in combined:
        return "HI"

    if country_value in {"Australia"}:
        return "AU"
    if country_value in {"Indonesia"}:
        return "ID"
    if country_value in {"United States", "USA", "United States of America"}:
        return "US"
    if country_value in {"Canada"}:
        return "CA"
    if country_value in {"United Kingdom", "UK", "England", "Scotland", "Wales"}:
        return "UK"
    if country_value in {"Japan"}:
        return "JP"
    if country_value in {"New Zealand"}:
        return "NZ"
    if country_value in {"Brazil"}:
        return "BR"
    if country_value in {"South Africa"}:
        return "ZA"
    if country_value in {"Mexico"}:
        return "MX"
    if country_value in EU_COUNTRIES:
        return "EU"
    return "EU" if "europe" in combined else "OTHER"


def stockist_api_url(tag: str) -> str:
    return f"https://stockist.co/api/v1/{tag}/locations/all"


def fetch_json(url: str) -> Any:
    response = requests.get(url, headers=HEADERS, timeout=45)
    response.raise_for_status()
    return response.json()


def fetch_text(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=45)
    response.raise_for_status()
    return response.text


def extract_storeify_geojson(manufacturer: str, source: dict[str, Any]) -> list[dict[str, Any]]:
    payload = fetch_text(source["feedUrl"])
    json_payload = payload[payload.find("(") + 1:payload.rfind(")")]
    data = json.loads(json_payload)
    dealers: list[dict[str, Any]] = []

    for feature in data.get("features", []):
        properties = feature.get("properties", {})
        coordinates = feature.get("geometry", {}).get("coordinates", [None, None])
        address = clean_text(properties.get("address"))
        country = clean_text(properties.get("country")) or derive_country_from_address(address)
        state = clean_text(properties.get("province")) or derive_state_from_address(address)
        city = clean_text(properties.get("city")) or derive_city_from_address(address)
        dealers.append(
            {
                "dealerName": clean_text(properties.get("name")),
                "manufacturer": manufacturer,
                "country": country,
                "regionCode": infer_region_code(country, state),
                "stateOrProvince": state or None,
                "city": city or None,
                "website": normalise_website(properties.get("web")),
                "phone": clean_text(properties.get("phone")) or None,
                "address": address or None,
                "latitude": coordinates[1] if len(coordinates) > 1 else None,
                "longitude": coordinates[0] if len(coordinates) > 0 else None,
                "sourceUrl": source["sourceUrl"],
                "sourceManufacturer": manufacturer,
                "sourceType": source["sourceType"],
                "officialDealer": True,
                "dealerType": "physical_store",
                "discoveredAtUtc": utc_now_iso(),
                "confidence": "high",
                "notes": source.get("notes"),
            }
        )

    return dealers


def extract_stockist_api(manufacturer: str, source: dict[str, Any]) -> list[dict[str, Any]]:
    locations = fetch_json(stockist_api_url(source["stockistTag"]))
    dealers: list[dict[str, Any]] = []

    for location in locations:
        country = clean_text(location.get("country"))
        state = clean_text(location.get("state"))
        city = clean_text(location.get("city"))
        dealers.append(
            {
                "dealerName": clean_text(location.get("name")),
                "manufacturer": manufacturer,
                "country": country,
                "regionCode": infer_region_code(country, state),
                "stateOrProvince": state or None,
                "city": city or None,
                "website": normalise_website(location.get("website")),
                "phone": clean_text(location.get("phone")) or None,
                "address": clean_text(location.get("address_line_1"))
                or clean_text(location.get("full_address"))
                or None,
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude"),
                "sourceUrl": source["sourceUrl"],
                "sourceManufacturer": manufacturer,
                "sourceType": source["sourceType"],
                "officialDealer": True,
                "dealerType": "physical_store",
                "discoveredAtUtc": utc_now_iso(),
                "confidence": "high",
                "notes": source.get("notes"),
            }
        )

    return dealers


def derive_country_from_address(address: str) -> str:
    lower = address.lower()
    if " australia" in lower or lower.endswith("australia"):
        return "Australia"
    if " portugal" in lower or lower.endswith("portugal"):
        return "Portugal"
    if " spain" in lower or lower.endswith("spain"):
        return "Spain"
    if " france" in lower or lower.endswith("france"):
        return "France"
    if " netherlands" in lower or lower.endswith("netherlands"):
        return "Netherlands"
    if " germany" in lower or lower.endswith("germany"):
        return "Germany"
    if " italy" in lower or lower.endswith("italy"):
        return "Italy"
    if " indonesia" in lower or lower.endswith("indonesia"):
        return "Indonesia"
    if " japan" in lower or lower.endswith("japan"):
        return "Japan"
    if " new zealand" in lower or lower.endswith("new zealand"):
        return "New Zealand"
    if " south africa" in lower or lower.endswith("south africa"):
        return "South Africa"
    if " united kingdom" in lower or lower.endswith("united kingdom"):
        return "United Kingdom"
    if " usa" in lower or " united states" in lower:
        return "United States"
    return ""


def derive_state_from_address(address: str) -> str:
    match = re.search(r",\s*([A-Z]{2,3})\s+\d{3,}", address)
    if match:
        return match.group(1)
    return ""


def derive_city_from_address(address: str) -> str:
    parts = [part.strip() for part in address.split(",") if part.strip()]
    if len(parts) >= 2:
        return parts[-2]
    return ""


def load_current_retailers() -> dict[str, CurrentRetailer]:
    retailers: dict[str, CurrentRetailer] = {}

    def add_entry(name: str, website: str | None, platform: str | None, configured: bool, enabled: bool, region_code: str, source_file: str, notes: str | None = None) -> None:
        key = build_current_retailer_key(name, website)
        retailers[key] = CurrentRetailer(
            retailer_name=name,
            website=website,
            platform=platform,
            configured=configured,
            enabled=enabled,
            region_code=region_code,
            source_file=source_file,
            notes=notes,
        )

    au_master = json.loads((ROOT / "scrapers" / "retailers" / "retailer_master.json").read_text(encoding="utf-8"))
    for row in au_master:
        add_entry(
            name=row["retailerName"],
            website=normalise_website(row.get("website")),
            platform=row.get("platform"),
            configured=True,
            enabled=bool(row.get("enabled")),
            region_code=row.get("regionCode", "AU"),
            source_file="scrapers/retailers/retailer_master.json",
            notes=row.get("governanceReason"),
        )

    for path_str in [
        "scrapers/retailers/usa/us_retailer_targets.json",
        "scrapers/retailers/usa/us_retailer_candidate_backlog.json",
        "scrapers/retailers/europe/eu_retailer_targets.json",
    ]:
        path = ROOT / path_str
        data = json.loads(path.read_text(encoding="utf-8"))
        for row in data:
            add_entry(
                name=row["retailerName"],
                website=normalise_website(row.get("website")),
                platform=row.get("platform") or row.get("detectedPlatform"),
                configured=True,
                enabled=bool(row.get("enabled")) if "enabled" in row else False,
                region_code=row.get("regionCode", "US"),
                source_file=path_str,
                notes=row.get("notes") or row.get("skipReason"),
            )

    indonesia_module_path = ROOT / "scrapers" / "retailers" / "indonesia" / "import_indonesia_retailer_inventory.py"
    module_globals: dict[str, Any] = {"__file__": str(indonesia_module_path)}
    exec(indonesia_module_path.read_text(encoding="utf-8-sig"), module_globals)
    for row in module_globals["RETAILERS"]:
        add_entry(
            name=row["name"],
            website=normalise_website(row.get("website")),
            platform=None,
            configured=True,
            enabled=True,
            region_code="ID",
            source_file="scrapers/retailers/indonesia/import_indonesia_retailer_inventory.py",
        )

    merge_sql_counts(retailers)
    return retailers


def build_current_retailer_key(name: str, website: str | None) -> str:
    domain = canonical_domain(website)
    if domain:
        return f"domain:{domain}"
    return f"name:{normalise_dealer_name(name)}"


def merge_sql_counts(retailers: dict[str, CurrentRetailer]) -> None:
    load_dotenv(ROOT / ".env")
    server = os.getenv("SQL_SERVER")
    database = os.getenv("SQL_DATABASE")
    username = os.getenv("SQL_USERNAME")
    password = os.getenv("SQL_PASSWORD")
    driver = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")
    if not all([server, database, username, password]):
        return

    engine = create_engine(
        (
            f"mssql+pyodbc://{username}:{password}@{server}:1433/{database}"
            f"?driver={driver.replace(' ', '+')}&Encrypt=yes&TrustServerCertificate=no&Connection+Timeout=60"
        )
    )

    query = text(
        """
        SELECT
            ri.RegionCode,
            r.RetailerName,
            r.WebsiteUrl,
            COUNT(*) AS active_rows,
            MAX(ri.UpdatedAtUtc) AS last_updated_utc
        FROM dbo.RetailerInventory ri
        JOIN dbo.Retailers r
            ON r.RetailerId = ri.RetailerId
        WHERE ri.IsActive = 1
          AND ri.RegionCode IN ('AU', 'EU', 'ID', 'US')
        GROUP BY ri.RegionCode, r.RetailerName, r.WebsiteUrl
        """
    )

    try:
        with engine.connect() as connection:
            rows = connection.execute(query).fetchall()
        SQL_SNAPSHOT_STATUS["available"] = True
        SQL_SNAPSHOT_STATUS["error"] = None
    except Exception as exc:  # pragma: no cover - network/login variance
        SQL_SNAPSHOT_STATUS["available"] = False
        SQL_SNAPSHOT_STATUS["error"] = f"{type(exc).__name__}: {exc}"
        return

    for row in rows:
        key = build_current_retailer_key(row.RetailerName, row.WebsiteUrl)
        current = retailers.get(key)
        if current is None:
            current = CurrentRetailer(
                retailer_name=row.RetailerName,
                website=row.WebsiteUrl,
                platform=None,
                configured=False,
                enabled=True,
                region_code=row.RegionCode,
                source_file="live_sql_only",
            )
            retailers[key] = current
        current.active_rows = int(row.active_rows or 0)
        current.last_successful_scrape_utc = (
            row.last_updated_utc.isoformat().replace("+00:00", "Z")
            if getattr(row, "last_updated_utc", None)
            else None
        )


def enrich_manual_dealers(manufacturer: str, source: dict[str, Any], manual_dealers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    discovered_at = utc_now_iso()
    dealers: list[dict[str, Any]] = []
    for dealer in manual_dealers:
        dealers.append(
            {
                "dealerName": dealer["dealerName"],
                "manufacturer": manufacturer,
                "country": dealer.get("country"),
                "regionCode": dealer.get("regionCode") or infer_region_code(dealer.get("country"), dealer.get("stateOrProvince")),
                "stateOrProvince": dealer.get("stateOrProvince"),
                "city": dealer.get("city"),
                "website": normalise_website(dealer.get("website")),
                "phone": dealer.get("phone"),
                "address": dealer.get("address"),
                "latitude": dealer.get("latitude"),
                "longitude": dealer.get("longitude"),
                "sourceUrl": dealer.get("sourceUrl") or source["sourceUrl"],
                "sourceManufacturer": manufacturer,
                "sourceType": dealer.get("sourceType") or source["sourceType"],
                "officialDealer": dealer.get("officialDealer", True),
                "dealerType": dealer.get("dealerType", "unknown"),
                "discoveredAtUtc": discovered_at,
                "confidence": dealer.get("confidence", "medium"),
                "notes": dealer.get("notes") or source.get("notes"),
            }
        )
    return dealers


def discover_from_policy(policy: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    discovered: list[dict[str, Any]] = []
    source_reviews: list[dict[str, Any]] = []

    for manufacturer_entry in policy["manufacturers"]:
        manufacturer = manufacturer_entry["manufacturer"]
        for source in manufacturer_entry.get("sources", []):
            review = {
                "manufacturer": manufacturer,
                "sourceUrl": source["sourceUrl"],
                "sourceType": source["sourceType"],
                "extractor": source["extractor"],
                "azureValidated": bool(source.get("azureValidated")),
                "status": "reviewed",
                "notes": source.get("notes"),
            }

            try:
                if source["extractor"] == "storeify_geojson":
                    discovered.extend(extract_storeify_geojson(manufacturer, source))
                elif source["extractor"] == "stockist_api":
                    discovered.extend(extract_stockist_api(manufacturer, source))
                elif source["extractor"] == "manual_seed":
                    discovered.extend(
                        enrich_manual_dealers(
                            manufacturer,
                            source,
                            manufacturer_entry.get("manualDealers", []),
                        )
                    )
                elif source["extractor"] == "manual_review":
                    review["status"] = "manual_review"
                else:
                    review["status"] = "unsupported_extractor"
            except Exception as exc:  # pragma: no cover - defensive for live HTTP variance
                review["status"] = "error"
                review["notes"] = f"{source.get('notes', '')} Error: {type(exc).__name__}: {exc}".strip()

            source_reviews.append(review)

    return discovered, source_reviews


def merge_discovered_dealers(discovered: list[dict[str, Any]], current_retailers: dict[str, CurrentRetailer]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}

    for dealer in discovered:
        key = dealer_merge_key(dealer)
        current_match = find_current_retailer_match(dealer["dealerName"], dealer.get("website"), current_retailers)
        website = normalise_website(dealer.get("website")) or (current_match.website if current_match else None)
        if key not in merged:
            merged[key] = {
                "dealerName": dealer["dealerName"],
                "normalisedDealerName": normalise_dealer_name(dealer["dealerName"]),
                "manufacturers": [],
                "country": dealer.get("country"),
                "regionCode": dealer.get("regionCode"),
                "stateOrProvince": dealer.get("stateOrProvince"),
                "city": dealer.get("city"),
                "website": website,
                "phone": dealer.get("phone"),
                "address": dealer.get("address"),
                "latitude": dealer.get("latitude"),
                "longitude": dealer.get("longitude"),
                "sourceUrls": [],
                "sourceManufacturers": [],
                "sourceTypes": [],
                "officialDealer": True,
                "dealerType": dealer.get("dealerType") or "unknown",
                "discoveredAtUtc": dealer.get("discoveredAtUtc"),
                "confidence": dealer.get("confidence") or "medium",
                "notes": [],
            }

        entry = merged[key]
        entry["manufacturers"].append(dealer["manufacturer"])
        entry["sourceManufacturers"].append(dealer["sourceManufacturer"])
        entry["sourceTypes"].append(dealer["sourceType"])
        entry["sourceUrls"].append(dealer["sourceUrl"])
        if dealer.get("notes"):
            entry["notes"].append(dealer["notes"])
        if website and not entry.get("website"):
            entry["website"] = website
        if current_match and current_match.website and not entry.get("website"):
            entry["website"] = current_match.website

    for entry in merged.values():
        entry["manufacturers"] = sorted(set(entry["manufacturers"]))
        entry["sourceManufacturers"] = sorted(set(entry["sourceManufacturers"]))
        entry["sourceTypes"] = sorted(set(entry["sourceTypes"]))
        entry["sourceUrls"] = sorted(set(entry["sourceUrls"]))
        entry["notes"] = [note for note in sorted(set(entry["notes"])) if note]
        entry["status"] = classify_status(entry, current_retailers)
        entry["priorityScore"] = score_dealer(entry)

    return sorted(
        merged.values(),
        key=lambda item: (
            item["regionCode"],
            -item["priorityScore"],
            item["dealerName"],
        ),
    )


def dealer_merge_key(dealer: dict[str, Any]) -> str:
    domain = canonical_domain(dealer.get("website"))
    if domain:
        return f"domain:{domain}"
    return "|".join(
        [
            normalise_dealer_name(dealer["dealerName"]),
            clean_text(dealer.get("city")).lower(),
            clean_text(dealer.get("country")).lower(),
        ]
    )


def classify_status(entry: dict[str, Any], current_retailers: dict[str, CurrentRetailer]) -> str:
    current = find_current_retailer_match(entry["dealerName"], entry.get("website"), current_retailers)
    if current and current.notes:
        notes = current.notes.lower()
        if any(
            phrase in notes
            for phrase in [
                "apparel",
                "not suitable",
                "does not sell hardboard",
                "accessory store",
                "clothing",
            ]
        ):
            return "Blocked"
    if current is None:
        if not entry.get("website"):
            return "Manual review"
        return "Candidate"
    if current.active_rows > 0:
        return "Already running"
    if current.configured and current.enabled:
        return "Configured but inactive"
    if current.configured and not current.enabled:
        return "Known but disabled"
    return "Manual review"


def find_current_retailer_match(
    dealer_name: str,
    website: str | None,
    current_retailers: dict[str, CurrentRetailer],
) -> CurrentRetailer | None:
    domain_key = build_current_retailer_key(dealer_name, website)
    current = current_retailers.get(domain_key)
    if current:
        return current
    name_key = f"name:{normalise_dealer_name(dealer_name)}"
    return current_retailers.get(name_key)


def score_dealer(entry: dict[str, Any]) -> int:
    if entry["status"] == "Blocked":
        return 1
    if entry["status"] == "Already running":
        return 5
    if entry["status"] == "Known but disabled":
        return 4 if entry["regionCode"] in HIGH_PRIORITY_REGIONS else 3
    if entry["status"] == "Configured but inactive":
        return 4

    score = 1
    if entry["regionCode"] in HIGH_PRIORITY_REGIONS:
        score += 2
    elif entry["regionCode"] in FUTURE_REGIONS:
        score += 1
    if len(entry["manufacturers"]) >= 2:
        score += 1
    if entry.get("website"):
        score += 1
    if entry.get("dealerType") == "distributor":
        score -= 1
    return max(1, min(5, score))


def build_summary(dealers: list[dict[str, Any]], current_retailers: dict[str, CurrentRetailer], source_reviews: list[dict[str, Any]]) -> dict[str, Any]:
    region_summary: dict[str, dict[str, Any]] = {}
    manufacturer_summary: dict[str, dict[str, Any]] = {}
    already_running_by_region: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for region in ["AU", "US", "EU", "ID", "CA", "UK", "JP", "NZ", "BR", "ZA", "MX", "PR", "HI"]:
        region_dealers = [dealer for dealer in dealers if dealer["regionCode"] == region]
        region_summary[region] = {
            "totalDiscovered": len(region_dealers),
            "alreadyRunning": sum(1 for dealer in region_dealers if dealer["status"] == "Already running"),
            "candidateDealers": sum(1 for dealer in region_dealers if dealer["status"] == "Candidate"),
            "highPriorityCandidates": sum(
                1
                for dealer in region_dealers
                if dealer["status"] in {"Candidate", "Known but disabled", "Configured but inactive"}
                and dealer["priorityScore"] >= 4
            ),
            "manualReview": sum(1 for dealer in region_dealers if dealer["status"] == "Manual review"),
            "topBrandsRepresented": Counter(
                brand for dealer in region_dealers for brand in dealer["manufacturers"]
            ).most_common(5),
        }

    for dealer in dealers:
        for manufacturer in dealer["manufacturers"]:
            manufacturer_summary.setdefault(
                manufacturer,
                {
                    "dealerCount": 0,
                    "regions": Counter(),
                },
            )
            manufacturer_summary[manufacturer]["dealerCount"] += 1
            manufacturer_summary[manufacturer]["regions"][dealer["regionCode"]] += 1
        if dealer["status"] == "Already running":
            already_running_by_region[dealer["regionCode"]].append(dealer)

    current_by_region: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for retailer in current_retailers.values():
        current_by_region[retailer.region_code].append(
            {
                "retailerName": retailer.retailer_name,
                "website": retailer.website,
                "platform": retailer.platform,
                "status": (
                    "Already running"
                    if retailer.active_rows > 0
                    else ("Known but disabled" if retailer.configured and not retailer.enabled else "Configured but inactive")
                ),
                "activeStockCount": retailer.active_rows,
                "lastSuccessfulScrapeUtc": retailer.last_successful_scrape_utc,
                "sourceFile": retailer.source_file,
            }
        )

    for region, items in current_by_region.items():
        items.sort(key=lambda item: (-item["activeStockCount"], item["retailerName"]))

    top_candidates_by_region: dict[str, list[dict[str, Any]]] = {}
    for region in region_summary.keys():
        region_candidates = [
            dealer
            for dealer in dealers
            if dealer["regionCode"] == region
            and dealer["status"] in {"Candidate", "Known but disabled", "Configured but inactive"}
        ]
        top_candidates_by_region[region] = sorted(
            region_candidates,
            key=lambda item: (-item["priorityScore"], -len(item["manufacturers"]), item["dealerName"]),
        )[:10]

    return {
        "generatedAtUtc": utc_now_iso(),
        "regions": region_summary,
        "manufacturers": {
            key: {
                "dealerCount": value["dealerCount"],
                "regions": dict(value["regions"]),
            }
            for key, value in sorted(manufacturer_summary.items())
        },
        "alreadyRunningByRegion": current_by_region,
        "topCandidatesByRegion": top_candidates_by_region,
        "manualReview": [dealer for dealer in dealers if dealer["status"] == "Manual review"],
        "blockedOrNoWebsite": [dealer for dealer in dealers if dealer["status"] == "Blocked" or not dealer.get("website")],
        "sourceReviews": source_reviews,
    }


def render_markdown(summary: dict[str, Any], dealers: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("# Global Dealer Network Discovery")
    lines.append("")
    lines.append(f"Generated at: `{summary['generatedAtUtc']}`")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(
        f"- Dealers discovered from reviewed official sources: `{len(dealers)}`"
    )
    lines.append(
        f"- Manufacturers reviewed: `{len(summary['manufacturers'])}`"
    )
    lines.append(
        f"- Regions with discovered dealers in this pass: `{sum(1 for value in summary['regions'].values() if value['totalDiscovered'] > 0)}`"
    )
    lines.append("")
    lines.append("## Current Quivrr Retailer Coverage")
    lines.append("")
    for region in ["AU", "US", "EU", "ID"]:
        items = summary["alreadyRunningByRegion"].get(region, [])
        active = sum(1 for item in items if item["activeStockCount"] > 0)
        rows = sum(item["activeStockCount"] for item in items)
        lines.append(f"- `{region}`: `{active}` live retailers, `{rows}` active rows")
    lines.append("")
    lines.append("## Dealer Network By Region")
    lines.append("")
    for region, value in summary["regions"].items():
        if value["totalDiscovered"] == 0:
            continue
        lines.append(f"### {region}")
        lines.append("")
        lines.append(f"- Total discovered: `{value['totalDiscovered']}`")
        lines.append(f"- Already running: `{value['alreadyRunning']}`")
        lines.append(f"- Candidate dealers: `{value['candidateDealers']}`")
        lines.append(f"- High priority candidates: `{value['highPriorityCandidates']}`")
        lines.append(f"- Manual review: `{value['manualReview']}`")
        if value["topBrandsRepresented"]:
            top_brands = ", ".join(f"{brand} ({count})" for brand, count in value["topBrandsRepresented"])
            lines.append(f"- Top brands represented: {top_brands}")
        lines.append("")
    lines.append("## Top Onboarding Candidates")
    lines.append("")
    for region in ["AU", "US", "EU", "ID", "CA", "UK", "JP", "NZ", "BR", "ZA", "MX", "PR", "HI"]:
        candidates = summary["topCandidatesByRegion"].get(region, [])
        if not candidates:
            continue
        lines.append(f"### {region}")
        lines.append("")
        for dealer in candidates:
            website = dealer["website"] or "manual review"
            brands = ", ".join(dealer["manufacturers"])
            lines.append(
                f"- **{dealer['dealerName']}** — score `{dealer['priorityScore']}` — `{dealer['status']}` — {website} — {brands}"
            )
        lines.append("")
    lines.append("## Manufacturer Source Summary")
    lines.append("")
    for review in summary["sourceReviews"]:
        lines.append(
            f"- **{review['manufacturer']}** — `{review['extractor']}` — `{review['status']}` — {review['sourceUrl']}"
        )
    lines.append("")
    lines.append("## Manual Review Required")
    lines.append("")
    for dealer in summary["manualReview"][:25]:
        lines.append(
            f"- **{dealer['dealerName']}** — `{dealer['regionCode']}` — {dealer['notes'][0] if dealer['notes'] else 'No website or source requires manual review.'}"
        )
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> None:
    policy = load_policy()
    current_retailers = load_current_retailers()
    discovered_raw, source_reviews = discover_from_policy(policy)
    discovered = merge_discovered_dealers(discovered_raw, current_retailers)
    summary = build_summary(discovered, current_retailers, source_reviews)
    report = {
        "generatedAtUtc": summary["generatedAtUtc"],
        "service": "dealer_network_discovery",
        "policyPath": str(CONFIG_PATH.relative_to(ROOT)).replace("\\", "/"),
        "sqlSnapshotStatus": SQL_SNAPSHOT_STATUS,
        "discoveredDealers": discovered,
        "summary": summary,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    MD_OUTPUT_PATH.write_text(render_markdown(summary, discovered), encoding="utf-8")

    print(json.dumps(
        {
            "event": "dealer_network_report_generated",
            "service": "dealer_network_discovery",
            "generated_at_utc": summary["generatedAtUtc"],
            "dealer_count": len(discovered),
            "manufacturer_count": len(summary["manufacturers"]),
            "regions_with_dealers": [
                region for region, data in summary["regions"].items() if data["totalDiscovered"] > 0
            ],
            "json_output": str(JSON_OUTPUT_PATH),
            "markdown_output": str(MD_OUTPUT_PATH),
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
