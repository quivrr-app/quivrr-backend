import json
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


load_dotenv()


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


BRAND_ID = 4


def get_model_id(
    connection,
    model_name
):

    query = text("""
        SELECT TOP 1
            BoardModelId
        FROM dbo.BoardModels
        WHERE BrandId = :brand_id
        AND ModelName = :model_name
    """)

    result = connection.execute(
        query,
        {
            "brand_id": BRAND_ID,
            "model_name": model_name
        }
    ).fetchone()

    return result.BoardModelId if result else None


def board_size_exists(
    connection,
    model_id,
    construction,
    length,
    volume
):

    query = text("""
        SELECT TOP 1
            BoardSizeId
        FROM dbo.BoardSizes
        WHERE BoardModelId = :model_id
        AND Construction = :construction
        AND LengthFeetInches = :length
        AND VolumeLitres = :volume
    """)

    result = connection.execute(
        query,
        {
            "model_id": model_id,
            "construction": construction,
            "length": length,
            "volume": volume
        }
    ).fetchone()

    return result is not None


def insert_board_size(
    connection,
    model_id,
    construction,
    tail_shape,
    fin_setup,
    size
):

    already_exists = board_size_exists(
        connection,
        model_id,
        construction,
        size["length"],
        size["volumeLitres"]
    )

    if already_exists:

        print(
            f"Skipping existing size: "
            f"{size['length']} "
            f"{construction}"
        )

        return

    insert_query = text("""
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
            :volume_litres,
            :construction,
            :fin_setup,
            :tail_shape,
            1,
            GETUTCDATE()
        )
    """)

    connection.execute(
        insert_query,
        {
            "model_id": model_id,
            "length": size["length"],
            "width": size["width"],
            "thickness": size["thickness"],
            "volume_litres": size["volumeLitres"],
            "construction": construction,
            "fin_setup": fin_setup,
            "tail_shape": tail_shape
        }
    )

    print(
        f"Inserted: "
        f"{size['length']} "
        f"{construction}"
    )


def main():

    print("\nLoading JS catalogue...\n")

    with open(
        "./catalogues/js_industries.json",
        "r",
        encoding="utf-8"
    ) as file:

        catalogue = json.load(file)

    with engine.begin() as connection:

        for entry in catalogue:

            model_name = entry["modelName"]

            model_id = get_model_id(
                connection,
                model_name
            )

            if not model_id:

                print(
                    f"Skipping missing model: "
                    f"{model_name}"
                )

                continue

            print(
                f"\nProcessing: "
                f"{model_name} "
                f"({entry['construction']})"
            )

            for size in entry["sizes"]:

                insert_board_size(
                    connection,
                    model_id,
                    entry["construction"],
                    entry["tailShape"],
                    entry["finSetup"],
                    size
                )

    print("\nImport complete.\n")


if __name__ == "__main__":
    main()