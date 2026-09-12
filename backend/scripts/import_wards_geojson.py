#!/usr/bin/env python3
"""Import official ward polygons. Does not invent geometry.

Expected file: database/geo/wards.geojson
Each feature needs properties.ward_id (1-26) and a Polygon/MultiPolygon.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import SessionLocal
from app.geo.lookup import import_geojson

GEOJSON = Path(__file__).resolve().parents[2] / "database" / "geo" / "wards.geojson"


def main() -> None:
    if not GEOJSON.exists():
        raise SystemExit(
            f"Missing {GEOJSON}. Place official Solapur ward GeoJSON there. "
            "Do not invent polygons. Until then, run seed with DEMO_GEO=true."
        )
    db = SessionLocal()
    try:
        n = import_geojson(db, GEOJSON)
        print(f"Imported geometry for {n} wards")
    finally:
        db.close()


if __name__ == "__main__":
    main()
