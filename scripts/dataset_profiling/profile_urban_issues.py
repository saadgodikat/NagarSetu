import sys
from collections import Counter
from pathlib import Path

# Urban Issues Dataset Class Definitions (YOLO format)
URBAN_ISSUES_CLASSES = {
    0: "Damaged Road issues (Road cracks)",
    1: "Pothole Issues",
    2: "Illegal Parking Issues",
    3: "Broken Road Sign Issues",
    4: "Fallen trees",
    5: "Littering/Garbage on Public Places",
    6: "Vandalism Issues (Graffiti)",
    7: "Dead Animal Pollution",
    8: "Damaged concrete structures",
    9: "Damaged Electric wires and poles",
}

# NagarIQ Mapping
URBAN_TO_NAGARIQ = {
    0: "pothole",      # Damaged Road
    1: "pothole",      # Pothole
    2: "other",        # Illegal Parking
    3: "other",        # Broken Sign
    4: "other",        # Fallen trees
    5: "garbage",      # Littering/Garbage
    6: "other",        # Vandalism
    7: "other",        # Dead Animal
    8: "other",        # Concrete structures
    9: "streetlight",  # Electric wires & poles
}

def profile_urban_issues(dataset_dir: Path):
    print(f"=== Profiling Urban Issues Dataset (YOLO): {dataset_dir} ===")
    if not dataset_dir.exists():
        print(f"[!] Directory not found: {dataset_dir}. Extract Urban Issues dataset here.")
        return

    label_files = list(dataset_dir.rglob("*.txt"))
    print(f"Found {len(label_files)} label files.")

    class_counts = Counter()
    nagariq_counts = Counter()

    for lf in label_files:
        if lf.name in ("classes.txt", "data.yaml", "README.txt"):
            continue
        try:
            with open(lf, "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if parts:
                        cls_id = int(parts[0])
                        class_counts[cls_id] += 1
                        nagariq_cat = URBAN_TO_NAGARIQ.get(cls_id, "other")
                        nagariq_counts[nagariq_cat] += 1
        except Exception:
            pass

    print("\nBounding Box Counts per Urban Issues Class:")
    for cls_id, name in URBAN_ISSUES_CLASSES.items():
        print(f"  Class {cls_id} ({name}): {class_counts.get(cls_id, 0)} boxes")

    print("\nMapped NagarIQ Categories (Object Detection Instances):")
    for cat in ["garbage", "pothole", "drainage", "streetlight", "water_leakage", "other"]:
        print(f"  {cat}: {nagariq_counts.get(cat, 0)}")

if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw/urban_issues")
    profile_urban_issues(target)
