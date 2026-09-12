---
description: PostgreSQL and PostGIS database rules for NagarIQ
globs:
  - "backend/**/*.py"
  - "database/**/*"
alwaysApply: false
---

# NagarIQ PostgreSQL + PostGIS Rules

## Database

NagarIQ uses PostgreSQL.

Use database migrations for schema changes.

Never silently modify the database schema without a migration.

Use:

- foreign keys
- constraints
- indexes
- transactions where appropriate

---

## PostGIS

Use PostGIS for geographic operations.

Do not treat latitude and longitude as the complete geographic model when spatial operations are required.

Store geographic data using appropriate PostGIS geometry/geography types.

---

## Ward Lookup

The core geographic workflow is:

Complaint GPS
→ PostGIS Point
→ Spatial lookup
→ Census/Election Ward
→ Zone

Use actual supplied Solapur geographic data.

Never fabricate:

- ward polygons
- ward boundaries
- ward coordinates

---

## Spatial Queries

Use PostGIS for:

- point-in-polygon queries
- distance calculations
- proximity searches
- ward lookup
- zone lookup
- geographic complaint clustering

---

## Spatial Indexing

Use appropriate spatial indexes for frequently queried geometry columns.

Do not perform large geographic scans unnecessarily.

---

## Complaint Location

A complaint should preserve the submitted location information needed for auditing.

Where appropriate, store:

- latitude
- longitude
- PostGIS geometry
- resolved ward
- resolved zone

The resolved geographic assignment should be reproducible from the submitted coordinates and geographic dataset.

---

## Database Integrity

Do not allow invalid relationships between:

- complaints
- users
- departments
- wards
- zones
- assignments

Use database constraints where appropriate.

---

## Query Safety

Never construct SQL using untrusted string concatenation.

Use:

- SQLAlchemy
- parameterized queries
- safe database APIs

---

## Performance

Add indexes to fields frequently used for:

- complaint status
- priority
- department
- assignment
- timestamps
- ward
- zone

Use spatial indexes for geographic columns.

Do not prematurely optimize without evidence.
