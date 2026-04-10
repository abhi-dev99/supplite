from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

from supply_chain_brief.housing_signals import (
    build_fallback_heatmap,
    build_national_real_estate_heatmap,
    build_real_estate_heatmap,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Census-backed real estate demand features for model training")
    parser.add_argument("--year", type=int, default=2025, help="Target ACS year (auto-falls back if unavailable)")
    parser.add_argument("--compare-year", type=int, default=2024, help="Baseline ACS year (auto-falls back if unavailable)")
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of ZCTA points, 0 means no cap")
    parser.add_argument(
        "--scope",
        choices=["seed", "national"],
        default="national",
        help="Use seed for curated demo ZCTAs or national for all ZCTAs",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("../data/real_estate_training_data_full.csv"),
        help="Output CSV path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    api_key = os.getenv("CENSUS_API_KEY")
    requested_limit = 0 if args.limit <= 0 else max(1, min(args.limit, 45000))

    if args.scope == "national":
        centroid_cache_path = output_path.parent / "zcta_centroids.csv"
        points, warnings, resolved = build_national_real_estate_heatmap(
            year=args.year,
            compare_year=args.compare_year,
            api_key=api_key,
            limit=requested_limit,
            centroid_cache_path=centroid_cache_path,
        )
        used_year = resolved.year
        used_compare_year = resolved.compare_year
    else:
        points, warnings = build_real_estate_heatmap(
            year=args.year,
            compare_year=args.compare_year,
            api_key=api_key,
            limit=requested_limit if requested_limit > 0 else 500,
        )
        used_year = args.year
        used_compare_year = args.compare_year

    if not points:
        fallback_limit = requested_limit if requested_limit > 0 else 500
        points = build_fallback_heatmap(year=used_year, limit=fallback_limit)

    fieldnames = [
        "id",
        "hub",
        "zcta",
        "state",
        "latitude",
        "longitude",
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
            position = point.get("position") or [None, None]
            row = {key: point.get(key) for key in fieldnames}
            row["latitude"] = position[1]
            row["longitude"] = position[0]
            writer.writerow(row)

    print(f"Exported {len(points)} rows to {output_path}")
    print(f"Scope: {args.scope}")
    print(f"Years used: {used_year} vs {used_compare_year}")
    if warnings:
        print("Warnings:")
        for warning in warnings[:10]:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
