import json
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


load_dotenv()


BRAND_ID = 4

CATALOGUE_PATH = (
    "./scrapers/brands/output/js_master_catalogue.json"
)

CANONICAL_MODELS_PATH = (
    "./scrapers/brands/js_canonical_models.json"
)


def build_connection_string():

    server = os.getenv("SQL_SERVER")
    database = os.getenv("SQL_DATABASE")
    username = os.getenv("SQL_USERNAME")
    password = os.getenv("SQL_PASSWORD")
    driver = os.getenv(
        "SQL_DRIVER",
        "ODBC Driver 18 for SQL Server"
    )

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

    return (
        "mssql+pyodbc:///?odbc_connect="
        + quote_plus(odbc_string)
    )


engine = create_engine(build_connection_string())


def normalise_construction(value):

    if not value:

        return None

    value = value.strip()

    if value.lower() == "carbotune":

        return "CarboTune"

    return value


def find_canonical_model(
    raw_model,
    canonical_models
):

    raw_lower = raw_model.lower()

    matches = []

    for canonical in canonical_models:

        if canonical.lower() in raw_lower:

            matches.append(canonical)

    if not matches:

        return None

    matches.sort(
        key=len,
        reverse=True
    )

    return matches[0]


def main():

    print(
        "\nImporting JS master catalogue into SQL...\n"
    )

    with open(
        CATALOGUE_PATH,
        "r",
        encoding="utf-8"
    ) as file:

        catalogue = json.load(file)

    with open(
        CANONICAL_MODELS_PATH,
        "r",
        encoding="utf-8"
    ) as file:

        canonical_models = json.load(file)

    inserted = 0
    skipped = 0
    cleaned = 0

    model_cache = {}

    with engine.begin() as connection:

        connection.execute(
            text("""
                DELETE bs
                FROM dbo.BoardSizes bs
                INNER JOIN dbo.BoardModels bm
                    ON bs.BoardModelId = bm.BoardModelId
                WHERE bm.BrandId = :brand_id
            """),
            {
                "brand_id": BRAND_ID
            }
        )

        connection.execute(
            text("""
                DELETE FROM dbo.BoardModels
                WHERE BrandId = :brand_id
            """),
            {
                "brand_id": BRAND_ID
            }
        )

        for item in catalogue:

            raw_model = item.get("model")

            if not raw_model:

                skipped += 1
                continue

            model_name = find_canonical_model(
                raw_model,
                canonical_models
            )

            if not model_name:

                skipped += 1
                continue

            if raw_model != model_name:

                cleaned += 1

            if model_name not in model_cache:

                result = connection.execute(
                    text("""
                        INSERT INTO dbo.BoardModels (
                            BrandId,
                            ModelName,
                            OfficialProductUrl,
                            OfficialImageUrl,
                            IsActive,
                            CreatedAtUtc
                        )
                        OUTPUT INSERTED.BoardModelId
                        VALUES (
                            :brand_id,
                            :model_name,
                            :product_url,
                            :image_url,
                            1,
                            GETUTCDATE()
                        )
                    """),
                    {
                        "brand_id": BRAND_ID,
                        "model_name": model_name,
                        "product_url": item.get("product_url"),
                        "image_url": item.get("image_url")
                    }
                ).fetchone()

                model_cache[model_name] = (
                    result.BoardModelId
                )

            model_id = model_cache[model_name]

            length = item.get("length")
            width = item.get("width")
            thickness = item.get("thickness")
            volume = item.get("volume_litres")

            if not length or volume is None:

                skipped += 1
                continue

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
                    )
                """),
                {
                    "model_id": model_id,
                    "length": length,
                    "width": width,
                    "thickness": thickness,
                    "volume": volume,
                    "construction": normalise_construction(
                        item.get("construction")
                    ),
                    "fin_setup": item.get("fin_system"),
                    "tail_shape": item.get("tail_shape")
                }
            )

            inserted += 1

    print(f"Canonical models: {len(model_cache)}")
    print(f"Rows inserted: {inserted}")
    print(f"Models cleaned: {cleaned}")
    print(f"Rows skipped: {skipped}")

    print("\nImport complete.\n")


if __name__ == "__main__":
    main()