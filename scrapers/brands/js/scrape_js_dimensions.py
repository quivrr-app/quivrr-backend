import asyncio
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from playwright.async_api import async_playwright
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")


def build_connection_string() -> str:
    odbc_string = (
        f"DRIVER={{{os.getenv('SQL_DRIVER')}}};"
        f"SERVER={os.getenv('SQL_SERVER')};"
        f"DATABASE={os.getenv('SQL_DATABASE')};"
        f"UID={os.getenv('SQL_USERNAME')};"
        f"PWD={os.getenv('SQL_PASSWORD')};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )

    return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_string)}"


def normalise_inches(value: str) -> str:
    return (
        value.replace("’", "'")
        .replace("”", '"')
        .replace("“", '"')
        .strip()
    )


def extract_dimensions_from_lines(text: str) -> list[dict]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    results = []

    for index, line in enumerate(lines):
        if not re.fullmatch(r"\d{1,2}'\d{1,2}\"", normalise_inches(line)):
            continue

        if index + 3 >= len(lines):
            continue

        length = normalise_inches(lines[index])
        width = normalise_inches(lines[index + 1])
        thickness = normalise_inches(lines[index + 2])
        volume_text = lines[index + 3].replace(" ", "")

        volume_match = re.fullmatch(r"(\d{1,3}(?:\.\d{1,2})?)L", volume_text, re.IGNORECASE)

        if not volume_match:
            continue

        results.append({
            "length": length,
            "width": normalise_inches(width),
            "thickness": normalise_inches(thickness),
            "volume_litres": float(volume_match.group(1)),
        })

    return results


def get_js_models(connection) -> list[dict]:
    rows = connection.execute(text("""
        SELECT
            bm.BoardModelId,
            bm.ModelName,
            bm.BoardCategory,
            bm.OfficialProductUrl
        FROM dbo.BoardModels bm
        INNER JOIN dbo.Brands b
            ON bm.BrandId = b.BrandId
        WHERE b.BrandName = 'JS Industries'
          AND bm.IsActive = 1
          AND bm.OfficialProductUrl IS NOT NULL
        ORDER BY bm.ModelName;
    """)).mappings().all()

    return [dict(row) for row in rows]


def upsert_board_size(connection, size: dict) -> None:
    query = text("""
        IF EXISTS (
            SELECT 1
            FROM dbo.BoardSizes
            WHERE BoardModelId = :board_model_id
              AND LengthFeetInches = :length
              AND ISNULL(Width, '') = ISNULL(:width, '')
              AND ISNULL(Thickness, '') = ISNULL(:thickness, '')
              AND ISNULL(VolumeLitres, 0) = ISNULL(:volume_litres, 0)
        )
        BEGIN
            UPDATE dbo.BoardSizes
            SET
                Width = :width,
                Thickness = :thickness,
                VolumeLitres = :volume_litres,
                IsStockSize = 1,
                UpdatedAtUtc = SYSUTCDATETIME()
            WHERE BoardModelId = :board_model_id
              AND LengthFeetInches = :length
              AND ISNULL(Width, '') = ISNULL(:width, '')
              AND ISNULL(Thickness, '') = ISNULL(:thickness, '')
              AND ISNULL(VolumeLitres, 0) = ISNULL(:volume_litres, 0)
        END
        ELSE
        BEGIN
            INSERT INTO dbo.BoardSizes (
                BoardModelId,
                LengthFeetInches,
                Width,
                Thickness,
                VolumeLitres,
                IsStockSize
            )
            VALUES (
                :board_model_id,
                :length,
                :width,
                :thickness,
                :volume_litres,
                1
            )
        END
    """)

    connection.execute(query, size)


async def scrape_model_dimensions(page, model: dict) -> list[dict]:
    print(f"Scraping {model['ModelName']}")

    await page.goto(model["OfficialProductUrl"], wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(8000)

    await page.mouse.wheel(0, 2500)
    await page.wait_for_timeout(3000)

    body_text = await page.locator("body").inner_text()
    dimensions = extract_dimensions_from_lines(body_text)

    cleaned = []
    seen = set()

    for dimension in dimensions:
        key = (
            dimension["length"],
            dimension["width"],
            dimension["thickness"],
            dimension["volume_litres"],
        )

        if key in seen:
            continue

        seen.add(key)

        cleaned.append({
            "board_model_id": model["BoardModelId"],
            "length": dimension["length"],
            "width": dimension["width"],
            "thickness": dimension["thickness"],
            "volume_litres": dimension["volume_litres"],
        })

    print(f"  Found {len(cleaned)} dimensions")
    return cleaned


async def main_async():
    engine = create_engine(build_connection_string())
    total_sizes = 0

    with engine.begin() as connection:
        models = get_js_models(connection)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1600, "height": 1400})

            for model in models:
                try:
                    sizes = await scrape_model_dimensions(page, model)

                    for size in sizes:
                        upsert_board_size(connection, size)

                    total_sizes += len(sizes)

                except Exception as error:
                    print(f"Failed {model['ModelName']}: {error}")

            await browser.close()

    print(f"Saved {total_sizes} dimension rows into dbo.BoardSizes")


if __name__ == "__main__":
    asyncio.run(main_async())