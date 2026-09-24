"""
Runs the delivery simulator against every test_case_*.json file in data/,
saves each report next to it in reports/, and prints a summary table plus
a sanity check that delivered packages == total packages for every case.
"""

import glob
import json
import os

from delivery_system import run

DATA_DIR = "data"
REPORTS_DIR = "reports"


def main() -> None:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    test_files = sorted(
        glob.glob(os.path.join(DATA_DIR, "test_case_*.json")),
        key=lambda p: int("".join(filter(str.isdigit, os.path.basename(p)))),
    )

    print(f"{'Test case':<16}{'Packages':<10}{'Delivered':<11}{'Best agent':<12}{'OK?'}")
    print("-" * 60)

    all_ok = True
    for test_file in test_files:
        name = os.path.splitext(os.path.basename(test_file))[0]
        with open(test_file) as f:
            total_packages = len(json.load(f)["packages"])

        report_path = os.path.join(REPORTS_DIR, f"{name}_report.json")
        report = run(test_file, output_path=report_path)

        delivered = sum(
            v["packages_delivered"] for k, v in report.items()
            if k not in ("best_agent", "_warning")
        )
        ok = delivered == total_packages and "_warning" not in report
        all_ok &= ok

        print(f"{name:<16}{total_packages:<10}{delivered:<11}{str(report['best_agent']):<12}{'OK' if ok else 'MISMATCH'}")

    print("-" * 60)
    print("All test cases delivered every package correctly." if all_ok
          else "Some test cases had mismatches -- see above.")


if __name__ == "__main__":
    main()
