from app.models.enums import ComplaintCategory

# Seed IDs from backend/seeds/seed.py
_CATEGORY_DEPARTMENT = {
    ComplaintCategory.garbage: 1,  # Solid Waste Management
    ComplaintCategory.drainage: 2,  # Public Health & Sanitation
    ComplaintCategory.pothole: 3,  # Roads & Infrastructure
    ComplaintCategory.streetlight: 4,
    ComplaintCategory.water_leakage: 5,
    ComplaintCategory.other: 7,  # Public Works
}


def department_id_for_category(category: ComplaintCategory) -> int:
    return _CATEGORY_DEPARTMENT[category]
