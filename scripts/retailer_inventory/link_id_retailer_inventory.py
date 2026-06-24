
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from app import execute_with_retry, engine


MODEL_CANDIDATE_SQL = text("""
WITH candidates AS (
    SELECT
        ri.InventoryId,
        b.BrandId,
        b.BrandName,
        bm.BoardModelId,
        bm.ModelName,
        ROW_NUMBER() OVER (
            PARTITION BY ri.InventoryId
            ORDER BY LEN(bm.ModelName) DESC, bm.BoardModelId
        ) AS rn
    FROM dbo.RetailerInventory ri
    JOIN dbo.Brands b
        ON (
               UPPER(ri.RawProductTitle) LIKE '%' + UPPER(b.BrandName) + '%'
            OR (b.BrandName = 'JS Industries' AND (UPPER(ri.RawProductTitle) LIKE 'JS %' OR UPPER(ri.RawProductTitle) LIKE '% JS %'))
            OR (b.BrandName = 'Album' AND (
                   UPPER(ri.RawProductTitle) LIKE '%BOM DIA%'
                OR UPPER(ri.RawProductTitle) LIKE '%SUNSTONE%'
                OR UPPER(ri.RawProductTitle) LIKE '%MOONSTONE%'
                OR UPPER(ri.RawProductTitle) LIKE '%VESPER%'
                OR UPPER(ri.RawProductTitle) LIKE '%PLASMIC%'
            ))
        )
    JOIN dbo.BoardModels bm
        ON bm.BrandId = b.BrandId
       AND bm.IsActive = 1
       AND UPPER(ri.RawProductTitle) LIKE '%' + UPPER(bm.ModelName) + '%'
    WHERE ri.RegionCode = 'ID'
      AND ri.IsActive = 1
      AND ri.BoardModelId IS NULL
)
SELECT InventoryId, BrandId, BrandName, BoardModelId, ModelName
FROM candidates
WHERE rn = 1
ORDER BY InventoryId;
""")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    candidates = [dict(r._mapping) for r in execute_with_retry(MODEL_CANDIDATE_SQL)]

    out_dir = Path("audit_output")
    out_dir.mkdir(exist_ok=True)
    (out_dir / "id_retailer_model_link_report.json").write_text(json.dumps({
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "mode": "apply" if args.apply else "dry_run",
        "modelCandidateRows": len(candidates),
        "sample": candidates[:200],
    }, indent=2, default=str), encoding="utf-8")

    print("ID retailer model link candidates:", len(candidates))

    if not args.apply:
        print("Dry run only. Re-run with --apply to update SQL.")
        return 0

    model_update_sql = text("""
    WITH candidates AS (
        SELECT
            ri.InventoryId,
            b.BrandId,
            bm.BoardModelId,
            ROW_NUMBER() OVER (
                PARTITION BY ri.InventoryId
                ORDER BY LEN(bm.ModelName) DESC, bm.BoardModelId
            ) AS rn
        FROM dbo.RetailerInventory ri
        JOIN dbo.Brands b
            ON (
                   UPPER(ri.RawProductTitle) LIKE '%' + UPPER(b.BrandName) + '%'
                OR (b.BrandName = 'JS Industries' AND (UPPER(ri.RawProductTitle) LIKE 'JS %' OR UPPER(ri.RawProductTitle) LIKE '% JS %'))
                OR (b.BrandName = 'Album' AND (
                       UPPER(ri.RawProductTitle) LIKE '%BOM DIA%'
                    OR UPPER(ri.RawProductTitle) LIKE '%SUNSTONE%'
                    OR UPPER(ri.RawProductTitle) LIKE '%MOONSTONE%'
                    OR UPPER(ri.RawProductTitle) LIKE '%VESPER%'
                    OR UPPER(ri.RawProductTitle) LIKE '%PLASMIC%'
                ))
            )
        JOIN dbo.BoardModels bm
            ON bm.BrandId = b.BrandId
           AND bm.IsActive = 1
           AND UPPER(ri.RawProductTitle) LIKE '%' + UPPER(bm.ModelName) + '%'
        WHERE ri.RegionCode = 'ID'
          AND ri.IsActive = 1
          AND ri.BoardModelId IS NULL
    )
    UPDATE ri
    SET
        ri.BrandId = c.BrandId,
        ri.BoardModelId = c.BoardModelId,
        ri.UpdatedAtUtc = SYSUTCDATETIME()
    FROM dbo.RetailerInventory ri
    JOIN candidates c
        ON c.InventoryId = ri.InventoryId
       AND c.rn = 1;
    """)

    size_update_sql = text("""
    WITH candidates AS (
        SELECT
            ri.InventoryId,
            bs.BoardSizeId,
            ROW_NUMBER() OVER (
                PARTITION BY ri.InventoryId
                ORDER BY
                    CASE WHEN ri.VolumeLitres IS NOT NULL AND bs.VolumeLitres IS NOT NULL
                         THEN ABS(CAST(ri.VolumeLitres AS float) - CAST(bs.VolumeLitres AS float))
                         ELSE 999 END,
                    bs.BoardSizeId
            ) AS rn
        FROM dbo.RetailerInventory ri
        JOIN dbo.BoardSizes bs
            ON bs.BoardModelId = ri.BoardModelId
           AND bs.LengthFeetInches = ri.LengthFeetInches
           AND (
                (
                    ri.VolumeLitres IS NOT NULL
                    AND bs.VolumeLitres IS NOT NULL
                    AND ABS(CAST(ri.VolumeLitres AS float) - CAST(bs.VolumeLitres AS float)) <= 0.75
                )
                OR (
                    ri.Width IS NOT NULL
                    AND ri.Thickness IS NOT NULL
                    AND REPLACE(REPLACE(ri.Width, '"', ''), ' ', '') =
                        REPLACE(REPLACE(bs.Width, '"', ''), ' ', '')
                    AND REPLACE(REPLACE(ri.Thickness, '"', ''), ' ', '') =
                        REPLACE(REPLACE(bs.Thickness, '"', ''), ' ', '')
                )
           )
        WHERE ri.RegionCode = 'ID'
          AND ri.IsActive = 1
          AND ri.BoardModelId IS NOT NULL
          AND ri.BoardSizeId IS NULL
    )
    UPDATE ri
    SET
        ri.BoardSizeId = c.BoardSizeId,
        ri.UpdatedAtUtc = SYSUTCDATETIME()
    FROM dbo.RetailerInventory ri
    JOIN candidates c
        ON c.InventoryId = ri.InventoryId
       AND c.rn = 1;
    """)

    with engine.begin() as connection:
        model_result = connection.execute(model_update_sql)
        size_result = connection.execute(size_update_sql)

    print(f"Applied ID retailer model links. Rows affected: {model_result.rowcount}")
    print(f"Applied ID retailer size links. Rows affected: {size_result.rowcount}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
