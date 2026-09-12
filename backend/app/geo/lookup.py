from pathlib import Path

from geoalchemy2.elements import WKTElement
from shapely.geometry import mapping, shape
from shapely.geometry.multipolygon import MultiPolygon
from shapely.geometry.polygon import Polygon
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.org import Ward

# Tuljapur Naka from the problem statement (Ward 1 demo GPS).
DEMO_WARD1_LNG = 75.9064
DEMO_WARD1_LAT = 17.6599
DEMO_HALF_DEG = 0.008  # ~800m box, marked demo-only


def demo_ward1_polygon() -> Polygon:
    lng, lat, d = DEMO_WARD1_LNG, DEMO_WARD1_LAT, DEMO_HALF_DEG
    return Polygon(
        [
            (lng - d, lat - d),
            (lng + d, lat - d),
            (lng + d, lat + d),
            (lng - d, lat + d),
            (lng - d, lat - d),
        ]
    )


def as_multipolygon(geom) -> MultiPolygon:
    if isinstance(geom, MultiPolygon):
        return geom
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    raise ValueError("Ward geometry must be Polygon or MultiPolygon")


def apply_geometry(db: Session, ward: Ward, geom) -> None:
    mp = as_multipolygon(geom)
    ward.boundary_geojson = mapping(mp)
    ward.boundary = WKTElement(mp.wkt, srid=4326)
    db.add(ward)


def lookup_ward_id(db: Session, lng: float, lat: float) -> int | None:
    row = db.execute(
        text(
            """
            SELECT id
            FROM wards
            WHERE boundary IS NOT NULL
              AND ST_Within(
                    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326),
                    boundary
                  )
            ORDER BY id
            LIMIT 1
            """
        ),
        {"lng": lng, "lat": lat},
    ).first()
    return int(row[0]) if row else None


def import_geojson(db: Session, path: Path) -> int:
    import json

    data = json.loads(path.read_text())
    features = data["features"] if data.get("type") == "FeatureCollection" else [data]
    updated = 0
    for feature in features:
        props = feature.get("properties") or {}
        ward_id = props.get("ward_id") or props.get("id")
        if ward_id is None:
            continue
        ward = db.get(Ward, int(ward_id))
        if ward is None:
            continue
        apply_geometry(db, ward, shape(feature["geometry"]))
        updated += 1
    db.commit()
    return updated
