# Solapur ward polygons

Place official election-ward GeoJSON here as `wards.geojson`.

Each feature must include:

- `properties.ward_id`: integer 1–26
- `geometry`: Polygon or MultiPolygon, WGS84 (EPSG:4326)

Do not invent boundaries. Until this file exists, seed with `DEMO_GEO=true` attaches a **demo-only** box around Tuljapur Naka (17.6599, 75.9064) to Ward 1.
