import sys
from pathlib import Path

from profile_bmc import profile_bmc
from profile_qr4change import profile_qr4change
from profile_urban_issues import profile_urban_issues
from profile_bengaluru import profile_bengaluru

def main():
    base_dir = Path("data/raw")
    print("=== NagarIQ Comprehensive Local Dataset Profiler ===")
    print(f"Checking directory: {base_dir.resolve()}\n")

    profile_bmc(base_dir / "mumbai_bmc.csv")
    print("-" * 50)
    profile_qr4change(base_dir / "qr4change")
    print("-" * 50)
    profile_urban_issues(base_dir / "urban_issues")
    print("-" * 50)
    profile_bengaluru(base_dir / "bengaluru.csv")
    print("=" * 50)

if __name__ == "__main__":
    main()
