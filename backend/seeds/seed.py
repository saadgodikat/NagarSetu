"""Seed Solapur zones, 26 election wards, departments, and synthetic demo users.

Ward 1 name/population come from PS2. Remaining ward titles are official SMC
election-ward (prabhag) names. Populations other than Ward 1 are left null.
Polygons are NOT invented: only DEMO_GEO attaches a marked demo box for Ward 1.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.config import settings
from app.db import SessionLocal
from app.geo.lookup import apply_geometry, demo_ward1_polygon, import_geojson
from app.models.enums import UserRole
from app.models.org import Department, Ward, Zone
from app.models.ops import SlaPolicy
from app.models.enums import ComplaintStatus
from app.models.user import User

DEMO_PASSWORD = "Demo@1234"

ZONES = [
    (1, "Zone 1", "Shelgi / Kasbe Solapur including Wards 1–3. Demo GPS: Tuljapur Naka."),
    (2, "Zone 2", "Mangalwar Peth / Kegaon / Kasba including Wards 4, 5, 7."),
    (3, "Zone 3", "Central market / Kasba overlap including Wards 6, 15, 22, 23."),
    (4, "Zone 4", "MIDC / industrial north including Wards 10–12."),
    (5, "Zone 5", "Market Yard / headquarters overlap including Wards 8, 9, 13."),
    (6, "Zone 6", "Begam Peth / Sadar Bazar including Wards 14, 16, 17."),
    (7, "Zone 7", "Western residential belts including Wards 18–21."),
    (8, "Zone 8", "Jule Solapur / airport / Kumthe including Wards 24–26."),
]

# Primary zone assignment uses non-overlapping 2025 zone-committee mapping.
WARDS: list[tuple[int, str, int, int | None, int | None, int | None]] = [
    (1, "Kasbe Solapur-1 Shelgi (Gaonthan)", 1, 37955, 10319, 1271),  # PS2
    (2, "Dahitane, Dayanand College, Satpute Wasti, Joshi Galli, Kamakshi Nagar, Mitra Nagar, Shelgi-2", 1, None, None, None),
    (3, "Shahir Wasti, Ghongade Wasti, Jodbhavi Peth", 1, None, None, None),
    (4, "Bagale Wasti, Yalleshwar Wadi, West/East Mangalwar Peth", 2, None, None, None),
    (5, "Kegaon, Shivaji Nagar, Bale", 2, None, None, None),
    (6, "Basweshwar Nagar, Degaon, Aamrai, Damani Nagar", 3, None, None, None),
    (7, "Nirale Wasti, Uma Nagari, North/South Kasba", 2, None, None, None),
    (8, "North/South Kasba, Shukrawar Peth, Ganesh Peth, Sakhar Peth", 5, None, None, None),
    (9, "Market Yard, Kuchan High School", 5, None, None, None),
    (10, "Sagar Chowk, Mahalaxmi Chowk, Rangraj Nagar, Pogul Mala", 4, None, None, None),
    (11, "Sambhaji High School, Samadhan Nagar, Mallikarjun Nagar", 4, None, None, None),
    (12, "Sunil Nagar, M.I.D.C", 4, None, None, None),
    (13, "Police Head Quarter, Walchand College Parisar", 5, None, None, None),
    (14, "Begam Peth, North Sadar Bazar", 6, None, None, None),
    (15, "Siddheshwar Mandir, Solapur Mahanagarpalika, Killa Parisar", 3, None, None, None),
    (16, "Modi, Shaskiya Vishram Gruha, Police Aayuktalaya", 6, None, None, None),
    (17, "Kongad Kumbhar Wasti, Shastri Nagar", 6, None, None, None),
    (18, "Shaskiya Krida Sankul, Aakashwani Kendra", 7, None, None, None),
    (19, "Nilam Nagar, Shramjivi Nagar", 7, None, None, None),
    (20, "Parasi Vihir, Swagat Nagar", 7, None, None, None),
    (21, "Mohite Nagar, Sahara Nagar, Gurunanak Nagar", 7, None, None, None),
    (22, "Ramwadi, Limayewadi, Revansiddheshwar Mandir", 3, None, None, None),
    (23, "Salgar Wasti, Nirmiti Vihar, Rajaswa Nagar, Soregaon, Pratap Nagar", 3, None, None, None),
    (24, "Sambhaji Talav, D-Mart, ITI, Jule Solapur", 8, None, None, None),
    (25, "Vimantal, Hatture Wasti, Siddheshwar Sakhar Karkhana", 8, None, None, None),
    (26, "Kalyan Nagar, S.R.P. Camp, Kumthe Gavthan", 8, None, None, None),
]

DEPARTMENTS = [
    (1, "Solid Waste Management", "Garbage collection, waste disposal, cleanliness"),
    (2, "Public Health & Sanitation", "Drainage, water leakage, public health hazards"),
    (3, "Roads & Infrastructure", "Potholes, road obstructions, street maintenance"),
    (4, "Street Lighting", "Damaged streetlights, electrical issues"),
    (5, "Water Supply", "Water leakage, supply issues, pipeline maintenance"),
    (6, "Urban Planning", "Property-related complaints, construction violations, zoning"),
    (7, "Public Works", "General infrastructure, building maintenance"),
]


def seed_catalog(db: Session) -> None:
    for zone_id, name, desc in ZONES:
        if db.get(Zone, zone_id) is None:
            db.add(Zone(id=zone_id, zone_name=name, jurisdiction_description=desc))
    db.flush()
    for dept_id, name, desc in DEPARTMENTS:
        if db.get(Department, dept_id) is None:
            db.add(Department(id=dept_id, name=name, description=desc))
    db.flush()
    for ward_id, name, zone_id, pop, sc, st in WARDS:
        existing = db.get(Ward, ward_id)
        if existing is None:
            db.add(
                Ward(
                    id=ward_id,
                    ward_name=name,
                    zone_id=zone_id,
                    population=pop,
                    sc_population=sc,
                    st_population=st,
                )
            )
    db.commit()


def seed_users(db: Session) -> None:
    demo_users = [
        ("Amit Citizen", "amit@demo.solapur", "9000000001", UserRole.citizen, None, None),
        ("Ramesh Worker", "ramesh@demo.solapur", "9000000002", UserRole.field_worker, 1, 1),
        ("Priya Officer", "officer.swm@demo.solapur", "9000000003", UserRole.officer, 1, 1),
        ("Sanjay Head", "head.swm@demo.solapur", "9000000004", UserRole.department_head, 1, None),
        ("Municipal Admin", "admin@demo.solapur", "9000000005", UserRole.admin, None, None),
    ]
    for name, email, phone, role, dept, zone in demo_users:
        if db.scalar(select(User).where(User.email == email)):
            continue
        db.add(
            User(
                name=name,
                email=email,
                phone=phone,
                password_hash=hash_password(DEMO_PASSWORD),
                role=role,
                department_id=dept,
                zone_id=zone,
            )
        )
    db.commit()


def seed_sla_policies(db: Session) -> None:
    defaults = {
        ComplaintStatus.submitted: (120, 240),
        ComplaintStatus.under_review: (240, 480),
        ComplaintStatus.in_progress: (480, 1440),
        ComplaintStatus.resolution_submitted: (2880, 4320),
    }
    for department_id, _, _ in DEPARTMENTS:
        for status, (reminder, escalation) in defaults.items():
            existing = db.scalar(
                select(SlaPolicy).where(
                    SlaPolicy.department_id == department_id,
                    SlaPolicy.status == status.value,
                )
            )
            if existing is None:
                db.add(
                    SlaPolicy(
                        department_id=department_id,
                        status=status.value,
                        reminder_after_minutes=reminder,
                        escalate_after_minutes=escalation,
                        enabled=True,
                    )
                )
    db.commit()


def seed_geo(db: Session) -> None:
    geojson = Path(__file__).resolve().parents[2] / "database" / "geo" / "wards.geojson"
    if geojson.exists():
        import_geojson(db, geojson)
        return
    if settings.demo_geo:
        ward = db.get(Ward, 1)
        if ward and ward.boundary is None:
            apply_geometry(db, ward, demo_ward1_polygon())
            db.commit()


def main() -> None:
    db = SessionLocal()
    try:
        seed_catalog(db)
        seed_users(db)
        seed_sla_policies(db)
        seed_geo(db)
        print("Seed complete. Demo password for all synthetic users: Demo@1234")
    finally:
        db.close()


if __name__ == "__main__":
    main()
