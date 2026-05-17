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
            bm.ModelName,
            bs.Construction,
            COUNT(*) AS SizeCount
        FROM dbo.Brands b
        JOIN dbo.BoardModels bm
            ON b.BrandId = bm.BrandId
        JOIN dbo.BoardSizes bs
            ON bm.BoardModelId = bs.BoardModelId
        WHERE b.BrandName = 'Pyzel'
          AND bs.Construction = 'EPS'
        GROUP BY bm.ModelName, bs.Construction
        ORDER BY bm.ModelName;
    """)).fetchall()

    for row in rows:
        print(dict(row._mapping))
