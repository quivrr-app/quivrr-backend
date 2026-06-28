import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
DEALER_POLICY = ROOT / "config" / "dealer_source_policy.json"
RETAILER_MASTER = ROOT / "scrapers" / "retailers" / "retailer_master.json"
CLASSIFIED_TARGETS = (
    ROOT / "scrapers" / "retailers" / "retailer_scrape_targets_classified.json"
)
EXPANSION_CANDIDATES = (
    ROOT / "scrapers" / "retailers" / "retailer_expansion_candidates_au.json"
)
PLATFORM_DETECTION = (
    ROOT / "scrapers" / "retailers" / "retailer_platform_detection_report.json"
)
DISCOVERY_REPORT = (
    ROOT / "scripts" / "dealers" / "output" / "au_retailer_discovery_report.json"
)
OUTPUT_DOC = ROOT / "docs" / "dealers" / "australia-retailer-qualification.md"


CLASSIFICATION_ORDER = [
    "already_running",
    "parked_live",
    "parked_manual",
    "ready_shopify",
    "ready_woocommerce",
    "ready_bigcommerce",
    "ready_neto_maropost",
    "ready_opencart",
    "ready_custom_high_value",
    "duplicate_shell",
    "catalogue_only",
    "no_online_boards",
    "shaper_only",
    "distributor_only",
    "closed_or_redirected",
    "manual_review",
    "blocked",
    "unsupported",
]

PLATFORM_PACKS = {
    "parked_live": "Parked",
    "parked_manual": "Parked",
    "ready_shopify": "Shopify Pack",
    "ready_woocommerce": "WooCommerce Pack",
    "ready_bigcommerce": "BigCommerce Pack",
    "ready_neto_maropost": "Neto / Maropost Pack",
    "ready_opencart": "OpenCart Pack",
    "ready_custom_high_value": "Custom High Value Pack",
    "duplicate_shell": "Duplicate Shells",
    "manual_review": "Manual Review",
    "catalogue_only": "Exclude",
    "no_online_boards": "Exclude",
    "shaper_only": "Exclude",
    "distributor_only": "Exclude",
    "closed_or_redirected": "Exclude",
    "blocked": "Exclude",
    "unsupported": "Exclude",
}

MANUAL_OVERRIDES: dict[str, dict[str, Any]] = {
    "redherringsurf.com.au": {
        "status": "duplicate_shell",
        "duplicateOf": "Board Collective",
        "onlineBoardInventoryVisible": False,
        "approxBoardProductCount": 0,
        "supportedBrandSignals": ["JS Industries", "Pyzel", "Firewire"],
        "boardCategoryUrl": "https://redherringsurf.com.au/collections/all",
        "productUrlExamples": [
            "https://boardcollective.com.au/products/boardcollective-egift-card"
        ],
        "priceVisible": False,
        "stockVisible": False,
        "imagesVisible": True,
        "paginationPresent": False,
        "scrapeDifficulty": "low",
        "priorityScore": 0,
        "recommendedAction": "Exclude from AU onboarding and keep Board Collective as the inventory source.",
        "notes": "Board Collective shell. products.json empty, surfboard search returned zero, and the public shell resolves product links to boardcollective.com.au.",
    },
    "saltwaterwine.com.au": {
        "status": "duplicate_shell",
        "duplicateOf": "Board Collective",
        "onlineBoardInventoryVisible": False,
        "approxBoardProductCount": 0,
        "supportedBrandSignals": ["JS Industries", "Pyzel", "Firewire", "Channel Islands"],
        "boardCategoryUrl": "https://saltwaterwine.com.au/collections/all",
        "productUrlExamples": [
            "https://boardcollective.com.au/products/boardcollective-egift-card"
        ],
        "priceVisible": False,
        "stockVisible": False,
        "imagesVisible": True,
        "paginationPresent": False,
        "scrapeDifficulty": "low",
        "priorityScore": 0,
        "recommendedAction": "Exclude from AU onboarding and keep Board Collective as the inventory source.",
        "notes": "Board Collective shell. products.json empty, surfboard search returned zero, and the public shell resolves product links to boardcollective.com.au.",
    },
    "triggerbrothers.com.au": {
        "status": "already_running",
        "alreadyRunning": True,
        "onlineBoardInventoryVisible": True,
        "approxBoardProductCount": 66,
        "supportedBrandSignals": ["supported multi-brand surf retailer"],
        "boardCategoryUrl": "https://triggerbrothers.com.au/store/surf/used-surfboards/",
        "productUrlExamples": [
            "https://triggerbrothers.com.au/trigger-bros-x-dos-lumberjack-6ft-surfboard/",
            "https://triggerbrothers.com.au/trigger-bros-hot-dog-stubby-9ft-surfboard-red/",
        ],
        "priceVisible": True,
        "stockVisible": True,
        "imagesVisible": True,
        "paginationPresent": True,
        "scrapeDifficulty": "medium",
        "priorityScore": 92,
        "recommendedAction": "Keep live in AU and treat as a validated BigCommerce production retailer.",
        "notes": "Production-validated AU BigCommerce retailer. Keep healthy, keep linked, and do not treat it as backlog work anymore.",
    },
    "extremeboardriders.com.au": {
        "status": "already_running",
        "alreadyRunning": True,
        "onlineBoardInventoryVisible": True,
        "approxBoardProductCount": 47,
        "supportedBrandSignals": ["supported multi-brand surf retailer"],
        "priceVisible": True,
        "stockVisible": True,
        "imagesVisible": True,
        "paginationPresent": True,
        "scrapeDifficulty": "low",
        "priorityScore": 78,
        "recommendedAction": "Keep live in AU and validate it through the standard WooCommerce nightly path.",
        "notes": "Approved AU closeout retailer. Existing WooCommerce path is already the correct implementation surface.",
    },
    "awsmsurf.com": {
        "status": "parked_live",
        "alreadyRunning": True,
        "onlineBoardInventoryVisible": True,
        "approxBoardProductCount": 2,
        "supportedBrandSignals": ["used and second-hand supported-brand boards"],
        "boardCategoryUrl": "https://www.awsmsurf.com/collections/second-hand-surfboard",
        "priceVisible": True,
        "stockVisible": True,
        "imagesVisible": True,
        "paginationPresent": True,
        "scrapeDifficulty": "medium",
        "priorityScore": 18,
        "recommendedAction": "Keep the existing live AU rows, but park further AWSM onboarding work unless a stronger supported-board surface appears.",
        "notes": "Nathan review: low-value AU source for now. Existing second-hand supported boards may remain live, but this is not an active expansion target.",
    },
    "akwasurf.com.au": {
        "status": "parked_live",
        "alreadyRunning": True,
        "onlineBoardInventoryVisible": True,
        "approxBoardProductCount": 6,
        "priceVisible": True,
        "stockVisible": True,
        "imagesVisible": True,
        "paginationPresent": False,
        "scrapeDifficulty": "low",
        "priorityScore": 14,
        "recommendedAction": "Leave the existing AU rows in place, but park new Akwa work unless a stronger supported-board surface is verified.",
        "notes": "Nathan review: no useful AU online stock signal worth active onboarding investment right now.",
    },
    "surfshopsaustralia.com.au": {
        "status": "manual_review",
        "onlineBoardInventoryVisible": False,
        "approxBoardProductCount": 0,
        "supportedBrandSignals": ["broad surfboard catalogue"],
        "boardCategoryUrl": "",
        "productUrlExamples": [],
        "priceVisible": False,
        "stockVisible": False,
        "imagesVisible": False,
        "paginationPresent": False,
        "scrapeDifficulty": "medium",
        "priorityScore": 55,
        "recommendedAction": "Keep in manual review until a clean public AU surfboard surface is reconfirmed.",
        "notes": "Earlier BigCommerce surfboard hints were not reconfirmed by the discovery engine, so this should not be promoted into the AU BigCommerce pack yet.",
    },
    "goodtime.com.au": {
        "status": "parked_manual",
        "onlineBoardInventoryVisible": True,
        "approxBoardProductCount": 70,
        "supportedBrandSignals": ["long-running AU surfboard retailer"],
        "boardCategoryUrl": "https://www.goodtime.com.au",
        "productUrlExamples": [],
        "priceVisible": True,
        "stockVisible": True,
        "imagesVisible": True,
        "paginationPresent": True,
        "scrapeDifficulty": "high",
        "priorityScore": 8,
        "recommendedAction": "Park for now. Nathan review found low supported-manufacturer value relative to AU effort.",
        "notes": "Manual review closeout: mostly smaller or unsupported local-brand value. Not worth active AU onboarding effort right now.",
    },
    "surfboardroom.com.au": {
        "status": "parked_manual",
        "onlineBoardInventoryVisible": False,
        "approxBoardProductCount": 0,
        "supportedBrandSignals": ["Firewire", "Channel Islands"],
        "boardCategoryUrl": "https://surfboardroom.com.au/surfboards/",
        "productUrlExamples": [],
        "priceVisible": False,
        "stockVisible": False,
        "imagesVisible": True,
        "paginationPresent": False,
        "scrapeDifficulty": "medium",
        "priorityScore": 6,
        "recommendedAction": "Park for now. No useful automated online board listing was confirmed in Nathan's AU review.",
        "notes": "Manual review closeout: no useful online board listing found for Quivrr search despite earlier WooCommerce signals.",
    },
    "fullcirclesurf.com.au": {
        "status": "parked_manual",
        "onlineBoardInventoryVisible": False,
        "approxBoardProductCount": 0,
        "supportedBrandSignals": ["JS Industries", "Firewire"],
        "priceVisible": False,
        "stockVisible": False,
        "imagesVisible": False,
        "paginationPresent": False,
        "scrapeDifficulty": "medium",
        "priorityScore": 4,
        "recommendedAction": "Park for now. Treat as non-viable until a real online surfboard storefront exists.",
        "notes": "Manual review closeout: effectively Facebook or Instagram presence only, not a usable AU live-stock source.",
    },
    "boardcave.com.au": {
        "status": "blocked",
        "onlineBoardInventoryVisible": False,
        "approxBoardProductCount": 0,
        "supportedBrandSignals": ["large Australian surfboard marketplace"],
        "priceVisible": False,
        "stockVisible": False,
        "imagesVisible": False,
        "paginationPresent": False,
        "scrapeDifficulty": "high",
        "priorityScore": 35,
        "recommendedAction": "Keep blocked. Revisit only if Boardcave exposes a safe public inventory path.",
        "notes": "High-value marketplace signal, but current access is blocked and not safe for AU nightly onboarding.",
    },
    "overboardsurf.com.au": {
        "status": "parked_manual",
        "onlineBoardInventoryVisible": False,
        "approxBoardProductCount": 0,
        "supportedBrandSignals": ["JS Industries", "Channel Islands", "Firewire", "Chilli", "DHD"],
        "boardCategoryUrl": "https://overboardsurf.com.au/collections/boards-7s-surfboards",
        "productUrlExamples": [],
        "priceVisible": True,
        "stockVisible": False,
        "imagesVisible": True,
        "paginationPresent": True,
        "scrapeDifficulty": "medium",
        "priorityScore": 5,
        "recommendedAction": "Park for now. Zero live AU rows is the correct production outcome until supported-brand saleable stock returns.",
        "notes": "Manual review closeout: sold out for supported-brand board variants. Do not treat the current zero-row state as an engineering failure.",
    },
    "undergroundsurf.com.au": {
        "status": "parked_manual",
        "onlineBoardInventoryVisible": False,
        "approxBoardProductCount": 0,
        "supportedBrandSignals": ["Channel Islands", "JS Industries"],
        "boardCategoryUrl": "https://www.undergroundsurf.com.au/collections/surfboards-1",
        "productUrlExamples": [
            "https://www.undergroundsurf.com.au/collections/surfboard-hire",
        ],
        "priceVisible": True,
        "stockVisible": False,
        "imagesVisible": True,
        "paginationPresent": True,
        "scrapeDifficulty": "medium",
        "priorityScore": 5,
        "recommendedAction": "Park for now. The surface is mostly hire or non-sale inventory and should stay out of AU active work.",
        "notes": "Manual review closeout: useful online sale inventory was not confirmed. Hire and rental content is a recurring false-positive risk.",
    },
    "surferschoice.com.au": {
        "status": "parked_manual",
        "onlineBoardInventoryVisible": False,
        "approxBoardProductCount": 2,
        "supportedBrandSignals": ["Channel Islands", "JS Industries", "DHD", "Haydenshapes"],
        "boardCategoryUrl": "https://www.surferschoice.com.au/boards.html",
        "productUrlExamples": [],
        "priceVisible": True,
        "stockVisible": False,
        "imagesVisible": True,
        "paginationPresent": False,
        "scrapeDifficulty": "medium",
        "priorityScore": 4,
        "recommendedAction": "Park for now. Too few useful boards and no strong add-to-cart flow for Quivrr search quality.",
        "notes": "Manual review closeout: only a couple of boards and no proper modern retailer flow worth engineering further.",
    },
    "soulboardstore.com.au": {
        "status": "parked_manual",
        "onlineBoardInventoryVisible": False,
        "approxBoardProductCount": 0,
        "supportedBrandSignals": ["JS Industries"],
        "boardCategoryUrl": "https://www.soulboardstore.com.au/index.html",
        "productUrlExamples": [],
        "priceVisible": False,
        "stockVisible": False,
        "imagesVisible": True,
        "paginationPresent": False,
        "scrapeDifficulty": "medium",
        "priorityScore": 3,
        "recommendedAction": "Park for now. Product signals exist, but no useful supported-board inventory was confirmed.",
        "notes": "Manual review closeout: products exist, but not enough useful Quivrr board stock to justify AU engineering work.",
    },
}


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalise_website(url: str) -> str:
    url = clean(url)
    if not url:
        return ""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = parsed.netloc or parsed.path
    host = host.lower().replace("www.", "").strip().rstrip("/")
    return host


def slugify(value: str) -> str:
    return (
        clean(value)
        .lower()
        .replace("&", "and")
        .replace("'", "")
        .replace("’", "")
        .replace("-", "_")
        .replace("/", "_")
        .replace(".", "")
        .replace(" ", "_")
    )


def load_running_index() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_domain: dict[str, dict[str, Any]] = {}
    by_slug: dict[str, dict[str, Any]] = {}
    for row in load_json(RETAILER_MASTER):
        domain = normalise_website(row.get("website"))
        slug = clean(row.get("retailerSlug"))
        if domain:
            by_domain[domain] = row
        if slug:
            by_slug[slug] = row
    return by_domain, by_slug


def load_detection_index() -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    report = load_json(PLATFORM_DETECTION)
    for row in report.get("results", []):
        domain = normalise_website(row.get("website"))
        if domain:
            index[domain] = row
    return index


def load_discovery_index() -> dict[str, dict[str, Any]]:
    if not DISCOVERY_REPORT.exists():
        return {}

    index: dict[str, dict[str, Any]] = {}
    report = load_json(DISCOVERY_REPORT)
    for row in report.get("results", []):
        domain = normalise_website(row.get("website"))
        if domain:
            index[domain] = row
    return index


def source_candidates() -> list[dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}

    for row in load_json(CLASSIFIED_TARGETS):
        if clean(row.get("country")).lower() != "australia":
            continue
        domain = normalise_website(row.get("website"))
        key = domain or slugify(row.get("primary_name") or row.get("website"))
        item = candidates.setdefault(
            key,
            {
                "dealerName": clean(row.get("primary_name")) or clean(row.get("website")),
                "website": clean(row.get("website")),
                "states": set(),
                "source_brands": set(),
                "priority": row.get("priority") or 3,
                "retailer_types": set(),
            },
        )
        item["dealerName"] = item["dealerName"] or clean(row.get("primary_name"))
        item["website"] = item["website"] or clean(row.get("website"))
        item["priority"] = min(item["priority"], row.get("priority") or 3)
        for state in row.get("states", []) or []:
            if clean(state):
                item["states"].add(clean(state))
        for brand in row.get("source_brands", []) or []:
            if clean(brand):
                item["source_brands"].add(clean(brand))
        for retailer_type in row.get("retailer_types", []) or []:
            if clean(retailer_type):
                item["retailer_types"].add(clean(retailer_type))

    for row in load_json(EXPANSION_CANDIDATES):
        if clean(row.get("country")).lower() != "australia":
            continue
        domain = normalise_website(row.get("website"))
        key = domain or slugify(row.get("primary_name") or row.get("website"))
        item = candidates.setdefault(
            key,
            {
                "dealerName": clean(row.get("primary_name")) or clean(row.get("website")),
                "website": clean(row.get("website")),
                "states": set(),
                "source_brands": set(),
                "priority": row.get("priority") or 3,
                "retailer_types": set(),
            },
        )
        item["dealerName"] = item["dealerName"] or clean(row.get("primary_name"))
        item["website"] = item["website"] or clean(row.get("website"))
        item["priority"] = min(item["priority"], row.get("priority") or 3)
        if clean(row.get("state")):
            item["states"].add(clean(row.get("state")))
        if clean(row.get("retailer_type")):
            item["retailer_types"].add(clean(row.get("retailer_type")))

    return list(candidates.values())


def default_status(
    candidate: dict[str, Any],
    running: dict[str, Any] | None,
    detection: dict[str, Any] | None,
) -> str:
    if running and running.get("enabled"):
        return "already_running"

    retailer_types = {value.lower() for value in candidate.get("retailer_types", set())}
    if "shaper_direct" in retailer_types or "brand_retail" in retailer_types:
        return "shaper_only"
    if "distributor" in retailer_types:
        return "distributor_only"

    governance_reason = clean((running or {}).get("governanceReason")).lower()
    governance_status = clean((running or {}).get("governanceStatus")).lower()
    platform = clean((detection or {}).get("detected_platform") or (running or {}).get("platform")).lower()
    detection_status = clean((detection or {}).get("status")).lower()

    if "domain unavailable" in governance_reason or "domain for sale" in governance_reason:
        return "closed_or_redirected"
    if "no online surfboard inventory" in governance_reason:
        return "no_online_boards"
    if "distributor" in governance_reason:
        return "distributor_only"
    if "shaper" in governance_reason:
        return "shaper_only"
    if (
        "clothing" in governance_reason
        or "accessory" in governance_reason
        or "not suitable" in governance_reason
        or "does not sell hardboard" in governance_reason
        or "not a surfboard retailer" in governance_reason
    ):
        return "unsupported"
    if governance_status == "stock_status_review":
        return "manual_review"
    if detection_status == "blocked":
        return "blocked"
    if platform == "shopify":
        return "ready_shopify"
    if platform == "woocommerce":
        return "ready_woocommerce"
    if platform == "bigcommerce":
        return "ready_bigcommerce"
    if platform == "neto_maropost":
        return "ready_neto_maropost"
    if platform in {"opencart", "ecwid"}:
        return "ready_opencart"
    if platform in {"magento", "squarespace"}:
        return "ready_custom_high_value"
    if detection_status in {"failed", "needs_review"} or governance_status in {"endpoint_review", "parser_review"}:
        return "manual_review"
    return "unsupported"


def default_priority_score(status: str, candidate: dict[str, Any], running: dict[str, Any] | None) -> int:
    if status == "already_running":
        return min(99, 40 + int(running.get("availableInventory") or 0) // 80)
    if status == "parked_live":
        return 18
    if status == "parked_manual":
        return 5

    base = {
        "ready_bigcommerce": 88,
        "ready_shopify": 70,
        "ready_woocommerce": 66,
        "ready_neto_maropost": 63,
        "ready_opencart": 58,
        "ready_custom_high_value": 74,
        "duplicate_shell": 0,
        "manual_review": 40,
        "blocked": 15,
        "catalogue_only": 10,
        "no_online_boards": 8,
        "shaper_only": 5,
        "distributor_only": 5,
        "closed_or_redirected": 0,
        "unsupported": 0,
    }.get(status, 0)
    return max(0, base - (int(candidate.get("priority") or 3) - 1) * 3)


def build_candidate_rows(include_discovery: bool = True) -> list[dict[str, Any]]:
    running_by_domain, _ = load_running_index()
    detection_by_domain = load_detection_index()
    discovery_by_domain = load_discovery_index() if include_discovery else {}
    rows: list[dict[str, Any]] = []

    for candidate in source_candidates():
        domain = normalise_website(candidate.get("website"))
        running = running_by_domain.get(domain)
        detection = detection_by_domain.get(domain)
        discovery = discovery_by_domain.get(domain)
        override = MANUAL_OVERRIDES.get(domain, {})
        status = (
            override.get("status")
            or clean((discovery or {}).get("recommendedStatus"))
            or default_status(candidate, running, detection)
        )
        platform = clean(
            override.get("platform")
            or (discovery or {}).get("detectedPlatform")
            or (detection or {}).get("detected_platform")
            or (running or {}).get("platform")
            or "unknown"
        ).lower()
        if platform == "ecwid":
            platform = "opencart"

        already_running = bool(
            override.get("alreadyRunning")
            if "alreadyRunning" in override
            else (running and running.get("enabled"))
        )
        approx_board_count = override.get("approxBoardProductCount")
        if approx_board_count is None:
            if discovery and discovery.get("approxBoardProductCount") is not None:
                approx_board_count = int(discovery.get("approxBoardProductCount") or 0)
            elif already_running:
                approx_board_count = int(running.get("availableInventory") or 0)
            elif running and (running.get("rawProducts") or 0) > 0:
                approx_board_count = int(running.get("rawProducts") or 0)
            else:
                approx_board_count = None

        row = {
            "dealerName": candidate["dealerName"],
            "website": candidate["website"],
            "alreadyRunning": already_running,
            "duplicateOf": override.get("duplicateOf", ""),
            "status": status,
            "platform": platform or "unknown",
            "onlineBoardInventoryVisible": override.get(
                "onlineBoardInventoryVisible",
                already_running
                or bool((discovery or {}).get("approxBoardProductCount"))
                or (running and (running.get("verifiedSurfboards") or 0) > 0)
                or status.startswith("ready_"),
            ),
            "approxBoardProductCount": approx_board_count,
            "supportedBrandSignals": override.get(
                "supportedBrandSignals",
                (discovery or {}).get("supportedBrandSignals")
                or sorted(candidate.get("source_brands", set())),
            ),
            "boardCategoryUrl": override.get(
                "boardCategoryUrl",
                ((discovery or {}).get("boardCategoryUrls") or [""])[0],
            ),
            "productUrlExamples": override.get(
                "productUrlExamples",
                (discovery or {}).get("productUrlExamples", []),
            ),
            "priceVisible": override.get(
                "priceVisible",
                already_running
                or bool((discovery or {}).get("priceVisible"))
                or status.startswith("ready_"),
            ),
            "stockVisible": override.get(
                "stockVisible",
                already_running
                or bool((discovery or {}).get("stockVisible"))
                or status.startswith("ready_"),
            ),
            "imagesVisible": override.get(
                "imagesVisible",
                already_running
                or bool((discovery or {}).get("imagesVisible"))
                or status.startswith("ready_"),
            ),
            "paginationPresent": override.get(
                "paginationPresent",
                bool((discovery or {}).get("paginationDetected"))
                or status in {"ready_bigcommerce", "ready_shopify", "ready_woocommerce"},
            ),
            "scrapeDifficulty": override.get(
                "scrapeDifficulty",
                "medium" if status.startswith("ready_") or status == "manual_review" else "low",
            ),
            "priorityScore": override.get(
                "priorityScore",
                int((discovery or {}).get("priorityScore") or default_priority_score(status, candidate, running)),
            ),
            "recommendedAction": override.get(
                "recommendedAction",
                clean((discovery or {}).get("recommendedAction"))
                or
                {
                    "already_running": "Keep live and use as AU baseline.",
                    "parked_live": "Keep existing live rows, but park further AU expansion work.",
                    "parked_manual": "Park for now based on AU manual review findings.",
                    "ready_shopify": "Candidate for the reusable AU Shopify pack.",
                    "ready_woocommerce": "Candidate for the reusable AU WooCommerce pack.",
                    "ready_bigcommerce": "Candidate for the reusable AU BigCommerce pack.",
                    "ready_neto_maropost": "Candidate for the reusable AU Neto / Maropost pack.",
                    "ready_opencart": "Candidate for a reusable adapter once the pack is proven.",
                    "ready_custom_high_value": "Candidate for targeted high-value onboarding after pack work.",
                    "duplicate_shell": "Exclude from onboarding to avoid duplicate stock coverage.",
                    "catalogue_only": "Exclude from AU retailer inventory.",
                    "no_online_boards": "Exclude until a real online board inventory surface exists.",
                    "shaper_only": "Exclude from retailer inventory and leave to canonical / MFA paths.",
                    "distributor_only": "Exclude from retailer inventory.",
                    "closed_or_redirected": "Exclude and re-check only if the domain recovers.",
                    "manual_review": "Review inventory surface before any implementation work.",
                    "blocked": "Do not onboard until access can be validated safely.",
                    "unsupported": "Exclude from AU hardboard onboarding.",
                }.get(status, "Manual review"),
            ),
            "notes": override.get(
                "notes",
                clean((discovery or {}).get("manualReviewReason"))
                or clean((discovery or {}).get("notes"))
                or clean((discovery or {}).get("evidence"))
                or
                clean((running or {}).get("governanceReason"))
                or clean((detection or {}).get("evidence"))
                or "Dealer registry candidate.",
            ),
        }
        rows.append(row)

    rows.sort(
        key=lambda row: (
            CLASSIFICATION_ORDER.index(row["status"])
            if row["status"] in CLASSIFICATION_ORDER
            else 999,
            -int(row["priorityScore"]),
            row["dealerName"].lower(),
        )
    )
    return rows


def group_pack(status: str) -> str:
    return PLATFORM_PACKS.get(status, "Manual Review")


def render_markdown(rows: list[dict[str, Any]], base_rows: list[dict[str, Any]] | None = None) -> str:
    summary = Counter(row["status"] for row in rows)
    platform_summary = Counter(row["platform"] for row in rows)
    pack_summary = Counter(group_pack(row["status"]) for row in rows)
    baseline_manual_review = None
    if base_rows is not None:
        baseline_manual_review = sum(1 for row in base_rows if row["status"] == "manual_review")

    already_running = [row for row in rows if row["status"] == "already_running"]
    duplicate_shells = [row for row in rows if row["status"] == "duplicate_shell"]
    manual_review = [row for row in rows if row["status"] == "manual_review"]
    parked_rows = [
        row for row in rows if row["status"] in {"parked_live", "parked_manual"}
    ]
    ready_candidates = [row for row in rows if row["status"].startswith("ready_")]
    top_candidates = sorted(
        [
            row
            for row in ready_candidates + manual_review
            if row["status"] != "already_running"
        ],
        key=lambda row: (-int(row["priorityScore"]), row["dealerName"].lower()),
    )[:20]
    top_custom = sorted(
        [
            row
            for row in rows
            if row["status"] in {"ready_custom_high_value", "manual_review", "blocked"}
        ],
        key=lambda row: (-int(row["priorityScore"]), row["dealerName"].lower()),
    )[:10]

    recommended_pack = "None"
    recommended_target = "None"

    lines = [
        "# Australia Retailer Qualification",
        "",
        "## Scope",
        "",
        "Sprint 10 AU Coverage Factory broad triage for Australian dealer and retailer candidates.",
        "",
        "This report now covers the wider AU retailer pool rather than a five-retailer shortlist.",
        "",
        "## Inputs",
        "",
        "- `config/dealer_source_policy.json`",
        "- `scrapers/retailers/retailer_master.json`",
        "- `scrapers/retailers/retailer_scrape_targets_classified.json`",
        "- `scrapers/retailers/retailer_expansion_candidates_au.json`",
        "- `scrapers/retailers/retailer_platform_detection_report.json`",
        "- `docs/dealers/global-dealer-network-discovery.md`",
        "",
        "Review date: `2026-06-28`",
        "",
        "## Sprint 13 Closeout Position",
        "",
        "- `Trigger Bros Surfboards` is live in AU on the reusable BigCommerce path and should now be treated as production validation work, not backlog onboarding.",
        "- `Extreme Boardriders` is live in AU on the reusable WooCommerce path and is the final approved AU closeout retailer from Nathan's latest review.",
        "- `AWSM Surf` may keep its existing live second-hand rows, but it is no longer an active AU expansion target.",
        "- `Overboard Surf` remains correctly parked at zero while supported-brand saleable stock is unavailable.",
        "- Australia should be parked after Trigger Bros and Extreme are production-validated unless a materially higher-value AU source appears.",
        "",
        "## Retailer Inventory Guardrail",
        "",
        "- Allowed: new boards, used boards, second-hand boards, ex-demo boards, clearance boards, and demo stock where a physical board is clearly for sale.",
        "- Rejected: hire boards, rental boards, lessons, repairs, services, trips, storage, and non-board accessories.",
        "- Shared retailer filters should preserve second-hand surfboards while excluding hire and service listings.",
        "",
        "## AU Coverage Factory Summary",
        "",
        f"- AU candidates reviewed: `{len(rows)}`",
        f"- Already running: `{len(already_running)}`",
        f"- Duplicate shells: `{len(duplicate_shells)}`",
        f"- Manual review: `{len(manual_review)}`",
        f"- Manual review before discovery: `{baseline_manual_review if baseline_manual_review is not None else len(manual_review)}`",
        f"- AU candidates re-analysed by discovery engine: `{sum(1 for row in rows if row['status'] in {'manual_review', 'ready_shopify', 'ready_woocommerce', 'ready_bigcommerce', 'ready_neto_maropost', 'ready_opencart', 'ready_custom_high_value', 'blocked'})}`",
        f"- Recommended next pack: `{recommended_pack}`",
        f"- Recommended next individual target: `{recommended_target}`",
        "- Australia recommendation: `Park AU after Trigger Bros and Extreme validation unless a materially higher-value source appears.`",
        "",
        "### Classification Summary",
        "",
    ]

    for status in CLASSIFICATION_ORDER:
        if status in summary:
            lines.append(f"- `{status}`: `{summary[status]}`")

    lines.extend(
        [
            "",
            "### Platform Summary",
            "",
        ]
    )
    for platform, count in sorted(platform_summary.items()):
        lines.append(f"- `{platform}`: `{count}`")

    lines.extend(
        [
            "",
            "### Pack Group Summary",
            "",
        ]
    )
    for pack, count in sorted(pack_summary.items()):
        lines.append(f"- `{pack}`: `{count}`")

    lines.extend(
        [
            "",
            "## Already Running",
            "",
        ]
    )
    for row in sorted(already_running, key=lambda item: (-int(item["approxBoardProductCount"] or 0), item["dealerName"].lower())):
        lines.append(
            f"- `{row['dealerName']}` | `{row['platform']}` | active rows `{row['approxBoardProductCount'] or 0}`"
        )

    lines.extend(
        [
            "",
            "## Parked / Low Priority",
            "",
        ]
    )
    for row in parked_rows:
        lines.append(
            f"- `{row['dealerName']}` | `{row['status']}` | {row['recommendedAction']}"
        )

    lines.extend(
        [
            "",
            "## Duplicate Shells",
            "",
        ]
    )
    for row in duplicate_shells:
        lines.append(
            f"- `{row['dealerName']}` -> `{row['duplicateOf']}` | {row['notes']}"
        )

    lines.extend(
        [
            "",
            "## Top 20 Implementation Candidates",
            "",
            "| Retailer | Status | Platform | Approx board count | Priority score | Why now |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in top_candidates:
        lines.append(
            f"| {row['dealerName']} | `{row['status']}` | `{row['platform']}` | `{row['approxBoardProductCount'] if row['approxBoardProductCount'] is not None else ''}` | `{row['priorityScore']}` | {row['recommendedAction']} |"
        )

    lines.extend(
        [
            "",
            "## Top 10 Custom / High-Value Candidates",
            "",
            "| Retailer | Status | Platform | Priority score | Notes |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in top_custom:
        lines.append(
            f"| {row['dealerName']} | `{row['status']}` | `{row['platform']}` | `{row['priorityScore']}` | {row['notes']} |"
        )

    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            "- Australia closeout: `Park AU after Trigger Bros and Extreme validation.`",
            "  Why: the remaining reviewed shortlist is now low-value, low-signal, sold out, or operationally noisy for Quivrr's supported-manufacturer search quality.",
            "- Keep `Trigger Bros Surfboards` and `Extreme Boardriders` healthy in production.",
            "- Keep existing `AWSM Surf` rows if they remain valid, but do not invest further now.",
            "- Keep `Overboard Surf` parked at zero until supported-brand saleable stock returns.",
            "- Reopen AU only if a materially higher-value retailer source is discovered.",
            "",
            "## Full AU Candidate Table",
            "",
            "| Dealer | Website | Running | Duplicate of | Status | Platform | Online boards visible | Approx board count | Supported brand signals | Category URL | Example product URLs | Price visible | Stock visible | Images visible | Pagination | Difficulty | Priority score | Recommended action | Notes |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )

    for row in rows:
        brand_signals = ", ".join(row["supportedBrandSignals"]) if row["supportedBrandSignals"] else ""
        product_examples = ", ".join(row["productUrlExamples"][:2]) if row["productUrlExamples"] else ""
        lines.append(
            f"| {row['dealerName']} | `{row['website']}` | `{str(row['alreadyRunning']).lower()}` | {row['duplicateOf'] or ''} | `{row['status']}` | `{row['platform']}` | `{str(bool(row['onlineBoardInventoryVisible'])).lower()}` | `{row['approxBoardProductCount'] if row['approxBoardProductCount'] is not None else ''}` | {brand_signals} | {row['boardCategoryUrl'] or ''} | {product_examples} | `{str(bool(row['priceVisible'])).lower()}` | `{str(bool(row['stockVisible'])).lower()}` | `{str(bool(row['imagesVisible'])).lower()}` | `{str(bool(row['paginationPresent'])).lower()}` | `{row['scrapeDifficulty']}` | `{row['priorityScore']}` | {row['recommendedAction']} | {row['notes']} |"
        )

    return "\n".join(lines) + "\n"


def build_report() -> dict[str, Any]:
    base_rows = build_candidate_rows(include_discovery=False)
    rows = build_candidate_rows(include_discovery=True)
    return {
        "rows": rows,
        "markdown": render_markdown(rows, base_rows=base_rows),
        "recommendedNextPack": "None",
        "recommendedNextTarget": "None",
        "manualReviewBefore": sum(1 for row in base_rows if row["status"] == "manual_review"),
        "manualReviewAfter": sum(1 for row in rows if row["status"] == "manual_review"),
    }


def main() -> None:
    report = build_report()
    OUTPUT_DOC.write_text(report["markdown"], encoding="utf-8")
    print(f"Saved AU coverage report: {OUTPUT_DOC}")
    print(f"Candidates reviewed: {len(report['rows'])}")
    print(f"Manual review before: {report['manualReviewBefore']}")
    print(f"Manual review after: {report['manualReviewAfter']}")
    print(f"Recommended next pack: {report['recommendedNextPack']}")
    print(f"Recommended next target: {report['recommendedNextTarget']}")


if __name__ == "__main__":
    main()
