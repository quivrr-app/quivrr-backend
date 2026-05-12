import json
import os
from urllib.parse import quote_plus, urlparse

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


load_dotenv()

INPUT_FILE = "scrapers/retailers/retailer_profiles_enriched.json"


def build_connection_string():
    server = os.getenv("SQL_SERVER")
    database = os.getenv("SQL_DATABASE")
    username = os.getenv("SQL_USERNAME")
    password = os.getenv("SQL_PASSWORD")
    driver = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server")

    odbc_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )

    return "mssql+pyodbc:///?odbc_connect=" + quote_plus(odbc_string)


engine = create_engine(build_connection_string())


def clean(value):
    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def domain_from_url(url):
    url = clean(url)

    if not url:
        return None

    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return None


def normalise_shopify_width_url(url):
    url = clean(url)

    if not url:
        return None

    return (
        url
        .replace("_{width}x", "_240x")
        .replace("{width}x", "240x")
    )


def logo_looks_wrong(profile, logo_url):
    logo_url = clean(logo_url)

    if not logo_url:
        return True

    retailer_name = clean(profile.get("name")) or ""
    retailer_domain = clean(profile.get("domain")) or domain_from_url(profile.get("website")) or ""

    text = f"{logo_url} {retailer_name} {retailer_domain}".lower()

    bad_terms = [
        "afterpay",
        "paypal",
        "visa",
        "mastercard",
        "amex",
        "zip-pay",
        "zippay",
        "payment",
        "thunderbolt_logo",
    ]

    for term in bad_terms:
        if term in text:
            return True

    return False


def best_logo_url(profile):
    logo_url = normalise_shopify_width_url(profile.get("logo_url"))
    favicon_url = clean(profile.get("favicon_url"))

    if logo_url and not logo_looks_wrong(profile, logo_url):
        return logo_url

    return favicon_url


def main():
    print("")
    print("Importing retailer profile logos into SQL...")
    print("")

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        profiles = json.load(file)

    with engine.begin() as connection:
        rows = connection.execute(
            text("""
                SELECT
                    RetailerId,
                    RetailerName,
                    WebsiteUrl
                FROM dbo.Retailers
            """)
        ).fetchall()

        retailers_by_name = {
            row.RetailerName.strip().lower(): row
            for row in rows
            if row.RetailerName
        }

        retailers_by_domain = {}

        for row in rows:
            domain = domain_from_url(row.WebsiteUrl)

            if domain:
                retailers_by_domain[domain] = row

        updated = 0
        skipped = 0

        for profile in profiles:
            name = clean(profile.get("name"))
            website = clean(profile.get("website"))
            profile_domain = clean(profile.get("domain")) or domain_from_url(website)
            logo_url = best_logo_url(profile)

            if not logo_url:
                skipped += 1
                continue

            retailer = None

            if name and name.lower() in retailers_by_name:
                retailer = retailers_by_name[name.lower()]

            if retailer is None and profile_domain:
                retailer = retailers_by_domain.get(profile_domain)

            if retailer is None:
                skipped += 1
                continue

            connection.execute(
                text("""
                    UPDATE dbo.Retailers
                    SET
                        LogoUrl = :logo_url,
                        UpdatedAtUtc = GETUTCDATE()
                    WHERE RetailerId = :retailer_id
                """),
                {
                    "logo_url": logo_url,
                    "retailer_id": retailer.RetailerId,
                },
            )

            updated += 1

        print(f"Profiles loaded: {len(profiles)}")
        print(f"Retailers in SQL: {len(rows)}")
        print(f"Retailers updated: {updated}")
        print(f"Profiles skipped: {skipped}")

    print("")
    print("Retailer profile logo import complete.")
    print("")


if __name__ == "__main__":
    main()