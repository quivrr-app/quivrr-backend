from pathlib import Path

files = {}

files["scrapers/brands/common_shopify_catalogue.py"] = r'''
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QuivrrBot/1.0; +https://quivrr.app)",
    "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


SIZE_LINE_RE = re.compile(
    r"(?P<length>[4-9]\s*(?:'|’|ft)\s*\d{1,2}|[4-9]-\d{1,2})"
    r".{0,18}?"
    r"(?P<width>\d{1,2}(?:\s+\d/\d|(?:\.\d+)?|(?:\s*/\s*\d+)?)?)"
    r".{0,18}?"
    r"(?P<thickness>\d(?:\s+\d/\d|(?:\.\d+)?|(?:\s*/\s*\d+)?)?)"
    r".{0,30}?"
    r"(?P<volume>\d{2}(?:\.\d+)?)\s*(?:l|litres|liters)",
    re.IGNORECASE,
)

LENGTH_ONLY_RE = re.compile(r"\b([4-9])\s*(?:'|’|ft|-)\s*(\d{1,2})\b", re.IGNORECASE)
VOLUME_RE = re.compile(r"\b(\d{2}(?:\.\d+)?)\s*(?:l|litres|liters)\b", re.IGNORECASE)

CONSTRUCTION_TERMS = [
    "PU",
    "PE",
    "EPS",
    "Epoxy",
    "Electralite",
    "ElectraLite",
    "FutureFlex",
    "Carbon",
    "Carbon Wrap",
    "Dark Arts",
    "Phantom Phlex",
    "Stringerless",
]

FIN_TERMS = [
    "FCS II",
    "FCS2",
    "FCS",
    "Futures",
    "Future",
    "Twin",
    "Thruster",
    "Quad",
    "5 Fin",
]


def clean(value):
    if value is None:
        return None

    value = str(value)
    value = re.sub(r"\s+", " ", value).strip()

    return value or None


def normalise_length(value):
    value = clean(value)

    if not value:
        return None

    match = LENGTH_ONLY_RE.search(value)

    if not match:
        return value

    return f"{match.group(1)}'{match.group(2)}"


def find_volume(value):
    value = clean(value)

    if not value:
        return None

    match = VOLUME_RE.search(value)

    if not match:
        return None

    try:
        return float(match.group(1))
    except ValueError:
        return None


def find_term(value, terms):
    text = clean(value)

    if not text:
        return None

    lowered = text.lower()

    for term in terms:
        if term.lower() in lowered:
            return term

    return None


def strip_size_noise(title):
    title = clean(title) or ""
    title = SIZE_LINE_RE.sub("", title)
    title = VOLUME_RE.sub("", title)
    title = LENGTH_ONLY_RE.sub("", title)
    title = re.sub(r"\b(FCS II|FCS2|FCS|Futures|Future|Thruster|Quad|Twin|5 Fin)\b", "", title, flags=re.I)
    title = re.sub(r"\b(PU|PE|EPS|Epoxy|Electralite|FutureFlex|Carbon Wrap|Carbon|Dark Arts|Phantom Phlex)\b", "", title, flags=re.I)
    title = re.sub(r"[-|_/]+", " ", title)
    title = re.sub(r"\s+", " ", title).strip()

    return title


def request_json(url):
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    return response.json()


def request_text(url):
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    return response.text


def fetch_shopify_products(base_url):
    products = []

    for page in range(1, 40):
        url = f"{base_url.rstrip('/')}/products.json?limit=250&page={page}"
        data = request_json(url)

        page_products = data.get("products", [])

        if not page_products:
            break

        products.extend(page_products)
        time.sleep(0.4)

    return products


def parse_size_lines(text):
    rows = []

    for match in SIZE_LINE_RE.finditer(text or ""):
        rows.append({
            "length": normalise_length(match.group("length")),
            "width": clean(match.group("width")),
            "thickness": clean(match.group("thickness")),
            "volume_litres": find_volume(match.group("volume")),
        })

    return rows


def html_to_text(html):
    soup = BeautifulSoup(html or "", "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    return soup.get_text(" ", strip=True)


def build_catalogue(brand_name, base_url, output_file):
    print("")
    print(f"Building {brand_name} manufacturer catalogue")
    print(f"Source: {base_url}")
    print("")

    products = fetch_shopify_products(base_url)

    rows = []
    seen = set()

    for product in products:
        title = clean(product.get("title"))
        handle = clean(product.get("handle"))
        body_html = product.get("body_html") or ""
        body_text = html_to_text(body_html)
        product_url = urljoin(base_url.rstrip("/") + "/", f"products/{handle}") if handle else base_url
        image_url = None

        images = product.get("images") or []

        if images:
            image_url = images[0].get("src")

        product_type = clean(product.get("product_type"))
        tags = product.get("tags") or []
        tags_text = " ".join(tags) if isinstance(tags, list) else str(tags)

        product_context = " ".join([
            title or "",
            product_type or "",
            tags_text or "",
            body_text[:5000],
        ])

        variants = product.get("variants") or []

        for variant in variants:
            variant_title = clean(variant.get("title"))
            variant_context = " ".join([
                title or "",
                variant_title or "",
                body_text[:5000],
            ])

            size_rows = parse_size_lines(variant_context)

            if not size_rows:
                volume = find_volume(variant_context)
                length_match = LENGTH_ONLY_RE.search(variant_context)

                if volume and length_match:
                    size_rows = [{
                        "length": normalise_length(length_match.group(0)),
                        "width": None,
                        "thickness": None,
                        "volume_litres": volume,
                    }]

            for size in size_rows:
                model_name = strip_size_noise(title)
                construction = find_term(variant_context, CONSTRUCTION_TERMS) or find_term(product_context, CONSTRUCTION_TERMS)
                fin_setup = find_term(variant_context, FIN_TERMS) or find_term(product_context, FIN_TERMS)

                key = (
                    brand_name,
                    model_name,
                    size.get("length"),
                    size.get("width"),
                    size.get("thickness"),
                    size.get("volume_litres"),
                    construction,
                    fin_setup,
                )

                if key in seen:
                    continue

                seen.add(key)

                rows.append({
                    "brand": brand_name,
                    "model": model_name,
                    "model_family": model_name,
                    "board_category": product_type,
                    "length": size.get("length"),
                    "width": size.get("width"),
                    "thickness": size.get("thickness"),
                    "volume_litres": size.get("volume_litres"),
                    "construction": construction,
                    "fin_system": fin_setup,
                    "tail_shape": None,
                    "official_product_url": product_url,
                    "official_image_url": image_url,
                    "source": base_url,
                    "source_product_id": product.get("id"),
                    "source_variant_id": variant.get("id"),
                    "source_variant_title": variant_title,
                    "scraped_at_utc": datetime.now(timezone.utc).isoformat(),
                    "is_active": True,
                })

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    report_path = output_path.with_name(output_path.stem + "_report.json")
    report_path.write_text(
        json.dumps(
            {
                "brand": brand_name,
                "base_url": base_url,
                "products_seen": len(products),
                "catalogue_rows": len(rows),
                "output_file": str(output_path),
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Products seen: {len(products)}")
    print(f"Catalogue rows: {len(rows)}")
    print(f"Output: {output_path}")
    print(f"Report: {report_path}")
    print("")

    if len(rows) == 0:
        raise RuntimeError(f"No catalogue rows were built for {brand_name}")

    return rows
'''

files["scrapers/brands/pyzel/build_pyzel_master_catalogue.py"] = r'''
from scrapers.brands.common_shopify_catalogue import build_catalogue


def main():
    build_catalogue(
        brand_name="Pyzel",
        base_url="https://pyzelsurfboards.com",
        output_file="scrapers/brands/pyzel/output/pyzel_master_catalogue_clean.json",
    )


if __name__ == "__main__":
    main()
'''

files["scrapers/brands/dhd/build_dhd_master_catalogue.py"] = r'''
from scrapers.brands.common_shopify_catalogue import build_catalogue


def main():
    build_catalogue(
        brand_name="DHD",
        base_url="https://dhdsurf.com",
        output_file="scrapers/brands/dhd/output/dhd_master_catalogue_clean.json",
    )


if __name__ == "__main__":
    main()
'''

files["scripts/import_brand_catalogue_common.py"] = r'''
import json
import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text


load_dotenv()


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


@event.listens_for(engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    if executemany:
        cursor.fast_executemany = True


def clean(value):
    if value is None:
        return None

    value = str(value).strip()

    return value or None


def load_catalogue(path):
    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise RuntimeError(f"Catalogue must be a list: {path}")

    return data


def get_or_create_brand(connection, brand_name):
    row = connection.execute(
        text("""
            SELECT BrandId
            FROM dbo.Brands
            WHERE BrandName = :brand_name;
        """),
        {"brand_name": brand_name},
    ).fetchone()

    if row:
        return row.BrandId

    inserted = connection.execute(
        text("""
            INSERT INTO dbo.Brands (
                BrandName,
                IsActive,
                CreatedAtUtc
            )
            OUTPUT INSERTED.BrandId
            VALUES (
                :brand_name,
                1,
                GETUTCDATE()
            );
        """),
        {"brand_name": brand_name},
    ).fetchone()

    return inserted.BrandId


def build_models(catalogue):
    models = {}

    for item in catalogue:
        model_name = clean(item.get("model"))

        if not model_name:
            continue

        if model_name not in models:
            models[model_name] = {
                "model_name": model_name,
                "model_family": clean(item.get("model_family")) or model_name,
                "board_category": clean(item.get("board_category")),
                "official_product_url": clean(item.get("official_product_url")),
                "official_image_url": clean(item.get("official_image_url")),
                "is_active": bool(item.get("is_active", True)),
            }

    return models


def build_size_rows(catalogue, model_cache):
    rows = []

    for item in catalogue:
        model_name = clean(item.get("model"))
        model_id = model_cache.get(model_name)

        if not model_id:
            continue

        length = clean(item.get("length"))
        volume = item.get("volume_litres")

        if not length or volume is None:
            continue

        rows.append({
            "model_id": model_id,
            "length": length,
            "width": clean(item.get("width")),
            "thickness": clean(item.get("thickness")),
            "volume": volume,
            "construction": clean(item.get("construction")),
            "fin_setup": clean(item.get("fin_system")),
            "tail_shape": clean(item.get("tail_shape")),
        })

    return rows


def import_catalogue(brand_name, catalogue_path):
    print("")
    print(f"Importing {brand_name} catalogue into SQL")
    print(f"Input: {catalogue_path}")
    print("")

    catalogue = load_catalogue(catalogue_path)
    models = build_models(catalogue)

    print(f"Catalogue rows loaded: {len(catalogue)}")
    print(f"Models prepared: {len(models)}")

    with engine.begin() as connection:
        brand_id = get_or_create_brand(connection, brand_name)

        print(f"BrandId: {brand_id}")
        print(f"Cleaning existing {brand_name} catalogue")

        connection.execute(
            text("""
                DELETE bs
                FROM dbo.BoardSizes bs
                INNER JOIN dbo.BoardModels bm
                    ON bs.BoardModelId = bm.BoardModelId
                WHERE bm.BrandId = :brand_id;
            """),
            {"brand_id": brand_id},
        )

        connection.execute(
            text("""
                DELETE FROM dbo.BoardModels
                WHERE BrandId = :brand_id;
            """),
            {"brand_id": brand_id},
        )

        model_cache = {}

        for model in models.values():
            result = connection.execute(
                text("""
                    INSERT INTO dbo.BoardModels (
                        BrandId,
                        ModelName,
                        ModelFamily,
                        BoardCategory,
                        OfficialProductUrl,
                        OfficialImageUrl,
                        IsActive,
                        CreatedAtUtc
                    )
                    OUTPUT INSERTED.BoardModelId
                    VALUES (
                        :brand_id,
                        :model_name,
                        :model_family,
                        :board_category,
                        :official_product_url,
                        :official_image_url,
                        :is_active,
                        GETUTCDATE()
                    );
                """),
                {
                    "brand_id": brand_id,
                    "model_name": model["model_name"],
                    "model_family": model["model_family"],
                    "board_category": model["board_category"],
                    "official_product_url": model["official_product_url"],
                    "official_image_url": model["official_image_url"],
                    "is_active": model["is_active"],
                },
            ).fetchone()

            model_cache[model["model_name"]] = result.BoardModelId

        size_rows = build_size_rows(catalogue, model_cache)

        print(f"Batch inserting sizes: {len(size_rows)}")

        if size_rows:
            connection.execute(
                text("""
                    INSERT INTO dbo.BoardSizes (
                        BoardModelId,
                        LengthFeetInches,
                        Width,
                        Thickness,
                        VolumeLitres,
                        Construction,
                        FinSetup,
                        TailShape,
                        IsStockSize,
                        CreatedAtUtc
                    )
                    VALUES (
                        :model_id,
                        :length,
                        :width,
                        :thickness,
                        :volume,
                        :construction,
                        :fin_setup,
                        :tail_shape,
                        1,
                        GETUTCDATE()
                    );
                """),
                size_rows,
            )

    print(f"Models imported: {len(model_cache)}")
    print(f"Rows inserted: {len(size_rows)}")
    print("Import complete")
    print("")
'''

files["scripts/import_pyzel_catalogue.py"] = r'''
from scripts.import_brand_catalogue_common import import_catalogue


def main():
    import_catalogue(
        brand_name="Pyzel",
        catalogue_path="scrapers/brands/pyzel/output/pyzel_master_catalogue_clean.json",
    )


if __name__ == "__main__":
    main()
'''

files["scripts/import_dhd_catalogue.py"] = r'''
from scripts.import_brand_catalogue_common import import_catalogue


def main():
    import_catalogue(
        brand_name="DHD",
        catalogue_path="scrapers/brands/dhd/output/dhd_master_catalogue_clean.json",
    )


if __name__ == "__main__":
    main()
'''

files["scripts/run_pyzel_pipeline.py"] = r'''
import subprocess
import sys


STEPS = [
    ["python", "scrapers/brands/pyzel/build_pyzel_master_catalogue.py"],
    ["python", "scripts/import_pyzel_catalogue.py"],
]


def run_step(command):
    print("")
    print("=" * 80)
    print("Running:", " ".join(command))
    print("=" * 80)
    print("")

    result = subprocess.run(command)

    if result.returncode != 0:
        raise RuntimeError(f"Step failed: {' '.join(command)}")


def main():
    for step in STEPS:
        run_step(step)

    print("")
    print("Pyzel catalogue pipeline complete")
    print("")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("")
        print(f"Pyzel catalogue pipeline failed: {exc}")
        print("")
        sys.exit(1)
'''

files["scripts/run_dhd_pipeline.py"] = r'''
import subprocess
import sys


STEPS = [
    ["python", "scrapers/brands/dhd/build_dhd_master_catalogue.py"],
    ["python", "scripts/import_dhd_catalogue.py"],
]


def run_step(command):
    print("")
    print("=" * 80)
    print("Running:", " ".join(command))
    print("=" * 80)
    print("")

    result = subprocess.run(command)

    if result.returncode != 0:
        raise RuntimeError(f"Step failed: {' '.join(command)}")


def main():
    for step in STEPS:
        run_step(step)

    print("")
    print("DHD catalogue pipeline complete")
    print("")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("")
        print(f"DHD catalogue pipeline failed: {exc}")
        print("")
        sys.exit(1)
'''

files["scripts/run_all_brand_catalogues.py"] = r'''
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


STEPS = [
    {
        "name": "JS Industries",
        "command": ["python", "scripts/run_js_pipeline.py"],
        "required": True,
    },
    {
        "name": "Channel Islands",
        "command": ["python", "scripts/run_ci_pipeline.py"],
        "required": True,
    },
    {
        "name": "Pyzel",
        "command": ["python", "scripts/run_pyzel_pipeline.py"],
        "required": True,
    },
    {
        "name": "DHD",
        "command": ["python", "scripts/run_dhd_pipeline.py"],
        "required": True,
    },
]


REPORT_PATH = Path("scrapers/brands/output/weekly_brand_catalogue_report.json")


def run_step(step):
    command_path = Path(step["command"][1])

    if not command_path.exists():
        message = f"Missing pipeline file: {command_path}"

        if step["required"]:
            raise RuntimeError(message)

        return {
            "brand": step["name"],
            "status": "skipped",
            "message": message,
        }

    print("")
    print("=" * 80)
    print(f"Running brand pipeline: {step['name']}")
    print("=" * 80)
    print(" ".join(step["command"]))
    print("")

    started = datetime.now(timezone.utc)
    result = subprocess.run(step["command"])
    ended = datetime.now(timezone.utc)

    status = "succeeded" if result.returncode == 0 else "failed"

    row = {
        "brand": step["name"],
        "command": " ".join(step["command"]),
        "status": status,
        "return_code": result.returncode,
        "started_at_utc": started.isoformat(),
        "ended_at_utc": ended.isoformat(),
    }

    if result.returncode != 0 and step["required"]:
        raise RuntimeError(f"{step['name']} pipeline failed")

    return row


def main():
    results = []
    failed = False

    for step in STEPS:
        try:
            results.append(run_step(step))
        except Exception as exc:
            failed = True
            results.append({
                "brand": step["name"],
                "status": "failed",
                "message": str(exc),
                "ended_at_utc": datetime.now(timezone.utc).isoformat(),
            })
            break

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        __import__("json").dumps(
            {
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "status": "failed" if failed else "succeeded",
                "results": results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("")
    print(f"Weekly brand catalogue report: {REPORT_PATH}")
    print("")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
'''

for path, content in files.items():
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"Wrote {file_path}")

print("")
print("Pyzel and DHD files created.")
