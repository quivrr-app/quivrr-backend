import os
import time
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError


load_dotenv()


def build_connection_string() -> str:
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


engine = create_engine(
    build_connection_string(),
    pool_pre_ping=True,
    pool_recycle=120,
    pool_size=5,
    max_overflow=10,
)


def execute_with_retry(query, params=None, attempts=3):
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            with engine.begin() as connection:
                result = connection.execute(query, params or {})

                if result.returns_rows:
                    return list(result)

                return []

        except OperationalError as exc:
            last_error = exc

            if attempt == attempts:
                raise

            time.sleep(0.4 * attempt)

    raise last_error
