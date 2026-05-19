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
)

engine = create_engine(
    "mssql+pyodbc:///?odbc_connect=" + quote_plus(odbc_string)
)

with engine.begin() as conn:

    rows = conn.execute(text("""
        SELECT TOP 20
            bm.ModelName,
            bs.Construction,
            bs.LengthFeetInches,
            bs.Width,
            bs.Thickness,
            bs.VolumeLitres
        FROM dbo.BoardModels bm
        INNER JOIN dbo.BoardSizes bs
            ON bm.BoardModelId = bs.BoardModelId
        WHERE bm.BrandId = 24
        ORDER BY bm.ModelName, bs.VolumeLitres
    """)).fetchall()

    print("")
    print("=" * 100)
    print("CHILLI SQL CHECK")
    print("=" * 100)

    for row in rows:
        print(dict(row._mapping))
