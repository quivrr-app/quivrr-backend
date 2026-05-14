import json
import os
import socket
import traceback
from datetime import datetime, timezone

import pyodbc
import requests
from dotenv import load_dotenv


load_dotenv()


TARGETS = [
    "https://coopersboardstore.com.au",
    "https://coopersboardstore.com.au/robots.txt",
    "https://coopersboardstore.com.au/sitemap.xml",
]


def utc_now():
    return datetime.now(timezone.utc)


def build_connection():
    server = os.getenv("SQL_SERVER")
    database = os.getenv("SQL_DATABASE")
    username = os.getenv("SQL_USERNAME")
    password = os.getenv("SQL_PASSWORD")
    driver = os.getenv(
        "SQL_DRIVER",
        "ODBC Driver 18 for SQL Server"
    )

    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )

    return pyodbc.connect(connection_string)


def ensure_table(cursor):
    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT *
            FROM sys.tables
            WHERE name = 'ProbeRuns'
        )
        BEGIN
            CREATE TABLE ProbeRuns (
                ProbeRunId INT IDENTITY(1,1) PRIMARY KEY,
                RetailerName NVARCHAR(255),
                Url NVARCHAR(2000),
                StatusCode INT NULL,
                Success BIT,
                ResponseTimeMs INT NULL,
                ErrorMessage NVARCHAR(MAX) NULL,
                ResponseSnippet NVARCHAR(MAX) NULL,
                Hostname NVARCHAR(255) NULL,
                CreatedAtUtc DATETIME2
            )
        END
        """
    )


def insert_result(
    cursor,
    retailer_name,
    url,
    status_code,
    success,
    response_time_ms,
    error_message,
    response_snippet,
    hostname
):
    cursor.execute(
        """
        INSERT INTO ProbeRuns (
            RetailerName,
            Url,
            StatusCode,
            Success,
            ResponseTimeMs,
            ErrorMessage,
            ResponseSnippet,
            Hostname,
            CreatedAtUtc
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        retailer_name,
        url,
        status_code,
        success,
        response_time_ms,
        error_message,
        response_snippet,
        hostname,
        utc_now()
    )


def run_probe(url):
    start = utc_now()

    try:
        response = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/136.0 Safari/537.36"
                )
            }
        )

        elapsed_ms = int(
            (utc_now() - start).total_seconds() * 1000
        )

        snippet = response.text[:4000]

        return {
            "success": response.ok,
            "status_code": response.status_code,
            "response_time_ms": elapsed_ms,
            "error_message": None,
            "response_snippet": snippet
        }

    except Exception:
        elapsed_ms = int(
            (utc_now() - start).total_seconds() * 1000
        )

        return {
            "success": False,
            "status_code": None,
            "response_time_ms": elapsed_ms,
            "error_message": traceback.format_exc(),
            "response_snippet": None
        }


def main():
    print("=" * 60)
    print("Coopers SQL probe")
    print("=" * 60)

    hostname = socket.gethostname()

    connection = build_connection()
    cursor = connection.cursor()

    ensure_table(cursor)
    connection.commit()

    for url in TARGETS:
        print()
        print(f"Testing: {url}")

        result = run_probe(url)

        print(
            json.dumps(
                result,
                indent=2,
                default=str
            )
        )

        insert_result(
            cursor=cursor,
            retailer_name="Coopers Board Store",
            url=url,
            status_code=result["status_code"],
            success=result["success"],
            response_time_ms=result["response_time_ms"],
            error_message=result["error_message"],
            response_snippet=result["response_snippet"],
            hostname=hostname
        )

        connection.commit()

    cursor.close()
    connection.close()

    print()
    print("Probe complete")


if __name__ == "__main__":
    main()