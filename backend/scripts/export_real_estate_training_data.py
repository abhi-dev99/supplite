from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

from supply_chain_brief.housing_signals import build_fallback_heatmap, build_real_estate_heatmap


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Census-backed real estate demand features for model training")
    parser.add_argument("--year", type=int, default=2024, help="Target ACS year")
    parser.add_argument("--compare-year", type=int, default=2023, help="Baseline ACS year")
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of ZCTA points")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("../data/real_estate_training_data.csv"),
        help="Output CSV path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    points, warnings = build_real_estate_heatmap(
        year=args.year,
        compare_year=args.compare_year,
        api_key=os.getenv("CENSUS_API_KEY"),
        limit=max(1, min(args.limit, 500)),
    )
    if not points:
        points = build_fallback_heatmap(year=args.year, limit=max(1, min(args.limit, 500)))

    fieldnames = [
        "id",
        "hub",
        "zcta",
        "state",
        "risk",
        "volume",
        "demand_index",
        "owner_households",
        "renter_households",
        "owner_share_pct",
        "renter_share_pct",
        "owner_yoy_pct",
        "renter_yoy_pct",
        "housing_units_yoy_pct",
        "median_rent_usd",
        "source",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for point in points:
            writer.writerow({key: point.get(key) for key in fieldnames})

    print(f"Exported {len(points)} rows to {output_path}")
    if warnings:
        print("Warnings:")
        for warning in warnings[:10]:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
