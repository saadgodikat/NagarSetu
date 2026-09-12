import csv
import sys
from collections import Counter
from pathlib import Path

NAGARIQ_CATEGORIES = [
    "garbage",
    "pothole",
    "drainage",
    "streetlight",
    "water_leakage",
    "other",
]

KEYWORD_MAPPING = {
    "garbage": ["garbage", "waste", "trash", "dump"],
    "pothole": ["pothole", "road", "footpath"],
    "drainage": ["drain", "sewer", "overflow"],
    "streetlight": ["light", "lamp", "electric"],
    "water_leakage": ["water", "leak", "pipeline"],
}

def map_text_to_nagariq(text):
    blob = text.lower()
    for cat, keywords in KEYWORD_MAPPING.items():
        if any(kw in blob for kw in keywords):
            return cat
    return "other"

def profile_bengaluru(file_path: Path):
    print(f"=== Profiling Bengaluru Dataset: {file_path} ===")
    if not file_path.exists():
        print(f"[!] File not found: {file_path}. Place Bengaluru CSV at this path.")
        return

    total_rows = 0
    nagariq_counts = Counter()

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        print(f"Columns: {reader.fieldnames}")
        for row in reader:
            total_rows += 1
            text = row.get("complaint", row.get("text", row.get("description", "")))
            nagariq_cat = map_text_to_nagariq(text)
            nagariq_counts[nagariq_cat] += 1

    print(f"Total Rows: {total_rows}")
    print("Category Breakdown:")
    for cat in NAGARIQ_CATEGORIES:
        print(f"  {cat}: {nagariq_counts[cat]}")

if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw/bengaluru.csv")
    profile_bengaluru(target)
