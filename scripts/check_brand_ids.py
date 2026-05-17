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

with engine.connect() as connection:
    rows = connection.execute(
        text("""
            SELECT
                BrandId,
                BrandName
            FROM dbo.Brands
            ORDER BY BrandName
        """)
    )

    for row in rows:
        print(f"{row.BrandId} | {row.BrandName}")
