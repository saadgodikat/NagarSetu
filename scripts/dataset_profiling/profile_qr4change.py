import sys
from collections import Counter
from pathlib import Path

# Common image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

def profile_qr4change(dataset_dir: Path):
    print(f"=== Profiling QR4Change Image Dataset: {dataset_dir} ===")
    if not dataset_dir.exists():
        print(f"[!] Directory not found: {dataset_dir}. Unzip QR4Change dataset here.")
        return

    class_counts = Counter()
    total_images = 0
    corrupted = 0
    formats = Counter()

    for p in dataset_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
            total_images += 1
            formats[p.suffix.lower()] += 1
            
            # Determine class from folder path
            parent_name = p.parent.name.lower()
            if "pothole" in parent_name:
                if "plain" in parent_name or "non" in parent_name:
                    class_counts["other (plain_road)"] += 1
                else:
                    class_counts["pothole"] += 1
            elif "garbage" in parent_name:
                if "non" in parent_name:
                    class_counts["other (non_garbage)"] += 1
                else:
                    class_counts["garbage"] += 1
            else:
                class_counts["unclassified"] += 1

    print(f"\nTotal Images Found: {total_images}")
    print("\nFormat Distribution:")
    for fmt, cnt in formats.items():
        print(f"  {fmt}: {cnt}")

    print("\nClass Breakdown:")
    for cls, cnt in class_counts.items():
        print(f"  {cls}: {cnt}")

    print("\nNagarIQ Category Mapping:")
    print(f"  garbage: {class_counts.get('garbage', 0)}")
    print(f"  pothole: {class_counts.get('pothole', 0)}")
    print(f"  other: {class_counts.get('other (plain_road)', 0) + class_counts.get('other (non_garbage)', 0)}")
    print(f"  drainage: 0 (Not present)")
    print(f"  streetlight: 0 (Not present)")
    print(f"  water_leakage: 0 (Not present)")

if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw/qr4change")
    profile_qr4change(target)
