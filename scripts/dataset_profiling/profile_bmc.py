import csv
import sys
from collections import Counter
from pathlib import Path

# NagarIQ Target Categories
NAGARIQ_CATEGORIES = [
    "garbage",
    "pothole",
    "drainage",
    "streetlight",
    "water_leakage",
    "other",
]

# Mapping rules from BMC department/complaint keywords to NagarIQ categories
KEYWORD_MAPPING = {
    "garbage": ["solid waste", "garbage", "waste", "trash", "dump", "debris", "cleanliness"],
    "pothole": ["road", "pothole", "pavement", "resurfacing", "trench"],
    "drainage": ["drain", "sewage", "sewer", "storm water", "overflow", "gutter", "nullah"],
    "streetlight": ["light", "lamp", "pole", "electrical", "lighting"],
    "water_leakage": ["water", "leak", "pipeline", "burst", "water supply", "contamination"],
}

def map_bmc_to_nagariq(dept_name, text):
    blob = f"{dept_name} {text}".lower()
    for cat, keywords in KEYWORD_MAPPING.items():
        if any(kw in blob for kw in keywords):
            return cat
    return "other"

def profile_bmc(file_path: Path):
    print(f"=== Profiling BMC Dataset: {file_path} ===")
    if not file_path.exists():
        print(f"[!] File not found: {file_path}. Place BMC dataset CSV at this path.")
        return

    total_rows = 0
    missing_counts = Counter()
    category_counts = Counter()
    nagariq_counts = Counter()
    examples = []

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        print(f"Columns: {fieldnames}")

        for i, row in enumerate(reader):
            total_rows += 1
            for k, v in row.items():
                if not v or not v.strip():
                    missing_counts[k] += 1
            
            # Detect category column
            dept = row.get("department", row.get("Department", row.get("category", "")))
            desc = row.get("description", row.get("Description", row.get("complaint_text", "")))
            
            category_counts[dept] += 1
            nagariq_cat = map_bmc_to_nagariq(dept, desc)
            nagariq_counts[nagariq_cat] += 1

            if len(examples) < 20 and desc.strip():
                examples.append((dept, nagariq_cat, desc[:100]))

    print(f"\nTotal Rows: {total_rows}")
    print("\nMissing Values:")
    for k, v in missing_counts.items():
        print(f"  {k}: {v} ({v/total_rows*100:.2f}%)")

    print("\nTop 10 Raw Categories/Departments:")
    for cat, cnt in category_counts.most_common(10):
        print(f"  {cat}: {cnt}")

    print("\nMapped NagarIQ Categories:")
    for cat in NAGARIQ_CATEGORIES:
        cnt = nagariq_counts[cat]
        print(f"  {cat}: {cnt} ({cnt/max(1, total_rows)*100:.2f}%)")

    print("\nSample Mapped Complaints:")
    for dept, nag_cat, snippet in examples:
        print(f"  [{dept} -> {nag_cat}] {snippet}")

if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw/mumbai_bmc.csv")
    profile_bmc(target)
