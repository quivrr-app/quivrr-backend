import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

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

engine = create_engine("mssql+pyodbc:///?odbc_connect=" + quote_plus(odbc_string))

with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT
            b.BrandName,
            COUNT(DISTINCT bm.BoardModelId) AS ModelCount,
            COUNT(bs.BoardSizeId) AS SizeCount,
            SUM(CASE WHEN bm.OfficialImageUrl IS NULL OR bm.OfficialImageUrl = '' THEN 1 ELSE 0 END) AS MissingModelImages
        FROM dbo.Brands b
        INNER JOIN dbo.BoardModels bm
            ON b.BrandId = bm.BrandId
        LEFT JOIN dbo.BoardSizes bs
            ON bm.BoardModelId = bs.BoardModelId
        WHERE b.BrandName IN ('Pyzel', 'DHD')
        GROUP BY b.BrandName
        ORDER BY b.BrandName;
    """)).fetchall()

    for row in rows:
        print(dict(row._mapping))
