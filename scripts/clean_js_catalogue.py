import os
import re
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


TAIL_PATTERNS = [
    "Squash Tail",
    "Round Tail",
    "Swallow Tail",
    "Pin Tail",
    "Round Nose Fish"
]


def clean_model_name(model_name):

    cleaned_name = model_name

    detected_tail = None

    for tail in TAIL_PATTERNS:

        if tail.lower() in cleaned_name.lower():

            detected_tail = tail

            cleaned_name = re.sub(
                tail,
                "",
                cleaned_name,
                flags=re.IGNORECASE
            )

    cleaned_name = re.sub(
        r"\s+",
        " ",
        cleaned_name
    ).strip()

    return cleaned_name, detected_tail


def main():

    print("\nLoading JS Industries models...\n")

    query = text("""
        SELECT
            BoardModelId,
            ModelName
        FROM dbo.BoardModels
        WHERE BrandId = 4
    """)

    update_query = text("""
        UPDATE dbo.BoardModels
        SET ModelName = :model_name
        WHERE BoardModelId = :model_id
    """)

    size_update_query = text("""
        UPDATE dbo.BoardSizes
        SET TailShape = :tail_shape
        WHERE BoardModelId = :model_id
    """)

    with engine.begin() as connection:

        rows = list(
            connection.execute(query)
        )

        for row in rows:

            cleaned_name, tail_shape = clean_model_name(
                row.ModelName
            )

            print(
                f"{row.ModelName}"
                f" -> "
                f"{cleaned_name}"
            )

            connection.execute(
                update_query,
                {
                    "model_name": cleaned_name,
                    "model_id": row.BoardModelId
                }
            )

            if tail_shape:

                connection.execute(
                    size_update_query,
                    {
                        "tail_shape": tail_shape,
                        "model_id": row.BoardModelId
                    }
                )

                print(
                    f"  Tail shape detected: "
                    f"{tail_shape}"
                )

    print("\nCatalogue cleanup complete.\n")


if __name__ == "__main__":
    main()
    