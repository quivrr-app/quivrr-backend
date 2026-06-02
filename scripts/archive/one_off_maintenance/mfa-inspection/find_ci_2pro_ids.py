import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

conn_str = (
    f"DRIVER={{{os.getenv('SQL_DRIVER', 'ODBC Driver 18 for SQL Server')}}};"
    f"SERVER={os.getenv('SQL_SERVER')};"
    f"DATABASE={os.getenv('SQL_DATABASE')};"
    f"UID={os.getenv('SQL_USERNAME')};"
    f"PWD={os.getenv('SQL_PASSWORD')};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
)

with pyodbc.connect(conn_str, timeout=30) as conn:
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            bs.BoardSizeId,
            b.BrandName,
            bm.ModelName,
            bs.Construction,
            bs.LengthFeetInches,
            bs.Width,
            bs.Thickness,
            bs.VolumeLitres
        FROM dbo.BoardSizes bs
        JOIN dbo.BoardModels bm ON bs.BoardModelId = bm.BoardModelId
        JOIN dbo.Brands b ON bm.BrandId = b.BrandId
        WHERE b.BrandName = 'Channel Islands'
          AND bm.ModelName = 'ci-2-pro'
          AND bs.LengthFeetInches = '5''11'
          AND bs.Width = '18 7/8'
          AND bs.Thickness = '2 3/8'
        ORDER BY bs.Construction
    """)

    for row in cursor.fetchall():
        print({
            "BoardSizeId": row.BoardSizeId,
            "BrandName": row.BrandName,
            "ModelName": row.ModelName,
            "Construction": row.Construction,
            "Length": row.LengthFeetInches,
            "Width": row.Width,
            "Thickness": row.Thickness,
            "VolumeLitres": float(row.VolumeLitres) if row.VolumeLitres is not None else None,
        })
