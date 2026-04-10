from __future__ import annotations

import csv
import io
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen
from zipfile import ZipFile

CENSUS_API_BASE = "https://api.census.gov/data"
GAZETTEER_URL_TEMPLATE = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/{year}_Gazetteer/{year}_Gaz_zcta_national.zip"
)


@dataclass(frozen=True)
class ZctaSeedPoint:
    zcta: str
    label: str
    state: str
    latitude: float
    longitude: float


# These are representative ZCTAs for major demand centers where WSI has meaningful coverage.
SEED_ZCTA_POINTS: list[ZctaSeedPoint] = [
    ZctaSeedPoint("10001", "New York, Manhattan", "NY", 40.7506, -73.9972),
    ZctaSeedPoint("11201", "Brooklyn Heights", "NY", 40.6943, -73.9928),
    ZctaSeedPoint("90012", "Los Angeles Downtown", "CA", 34.0614, -118.2385),
    ZctaSeedPoint("90210", "Beverly Hills", "CA", 34.0901, -118.4065),
    ZctaSeedPoint("94103", "San Francisco SoMa", "CA", 37.7725, -122.4091),
    ZctaSeedPoint("94301", "Palo Alto", "CA", 37.4443, -122.1598),
    ZctaSeedPoint("92660", "Newport Beach", "CA", 33.6221, -117.8930),
    ZctaSeedPoint("98101", "Seattle Downtown", "WA", 47.6101, -122.3344),
    ZctaSeedPoint("98004", "Bellevue", "WA", 47.6104, -122.2015),
    ZctaSeedPoint("60611", "Chicago Near North Side", "IL", 41.8945, -87.6200),
    ZctaSeedPoint("60614", "Chicago Lincoln Park", "IL", 41.9227, -87.6545),
    ZctaSeedPoint("33139", "Miami Beach", "FL", 25.7826, -80.1341),
    ZctaSeedPoint("33131", "Miami Brickell", "FL", 25.7670, -80.1880),
    ZctaSeedPoint("33480", "Palm Beach", "FL", 26.7056, -80.0364),
    ZctaSeedPoint("30305", "Atlanta Buckhead", "GA", 33.8304, -84.3857),
    ZctaSeedPoint("30309", "Atlanta Midtown", "GA", 33.7925, -84.3886),
    ZctaSeedPoint("78701", "Austin Downtown", "TX", 30.2711, -97.7437),
    ZctaSeedPoint("78746", "West Lake Hills", "TX", 30.2862, -97.8034),
    ZctaSeedPoint("75201", "Dallas Downtown", "TX", 32.7876, -96.7994),
    ZctaSeedPoint("75205", "Highland Park", "TX", 32.8369, -96.7969),
    ZctaSeedPoint("77005", "Houston West U", "TX", 29.7175, -95.4284),
    ZctaSeedPoint("77019", "Houston River Oaks", "TX", 29.7491, -95.3928),
    ZctaSeedPoint("85004", "Phoenix Downtown", "AZ", 33.4517, -112.0685),
    ZctaSeedPoint("85251", "Scottsdale Old Town", "AZ", 33.4942, -111.9260),
    ZctaSeedPoint("80206", "Denver Cherry Creek", "CO", 39.7184, -104.9535),
    ZctaSeedPoint("98109", "Seattle SLU", "WA", 47.6284, -122.3394),
    ZctaSeedPoint("02116", "Boston Back Bay", "MA", 42.3496, -71.0763),
    ZctaSeedPoint("20007", "Washington Georgetown", "DC", 38.9140, -77.0657),
    ZctaSeedPoint("19103", "Philadelphia Center City", "PA", 39.9524, -75.1748),
    ZctaSeedPoint("55416", "Minneapolis St. Louis Park", "MN", 44.9486, -93.3372),
]

SEED_ZCTA_INDEX: dict[str, ZctaSeedPoint] = {point.zcta: point for point in SEED_ZCTA_POINTS}


@dataclass(frozen=True)
class ResolvedYears:
    year: int
    compare_year: int


def _safe_int(value: Any) -> int:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return 0.0


def _pct_change(current: float, previous: float) -> float:
    if previous <= 0:
        return 0.0
    return (current - previous) / previous


def _fetch_json(url: str, timeout_seconds: int = 20) -> list[list[str]]:
    with urlopen(url, timeout=timeout_seconds) as response:  # noqa: S310 - fixed trusted endpoints
        return json.loads(response.read().decode("utf-8"))


def _dataset_available(year: int, dataset: str, api_key: str | None) -> bool:
    params = {
        "get": "NAME",
        "for": "zip code tabulation area:10001",
    }
    if api_key:
        params["key"] = api_key

    url = f"{CENSUS_API_BASE}/{year}/{dataset}?{urlencode(params)}"
    try:
        rows = _fetch_json(url)
        return len(rows) >= 2
    except (HTTPError, URLError, ValueError, json.JSONDecodeError, TimeoutError):
        return False


def resolve_acs_year_pair(*, requested_year: int, requested_compare_year: int, api_key: str | None) -> ResolvedYears:
    current_year = requested_year
    while current_year >= 2010:
        if _dataset_available(current_year, "acs/acs5/profile", api_key) and _dataset_available(current_year, "acs/acs5", api_key):
            break
        current_year -= 1

    if current_year < 2010:
        raise ValueError("No ACS year available from 2010 onward")

    compare_year = min(requested_compare_year, current_year - 1)
    while compare_year >= 2009:
        if _dataset_available(compare_year, "acs/acs5/profile", api_key) and _dataset_available(compare_year, "acs/acs5", api_key):
            break
        compare_year -= 1

    if compare_year < 2009:
        compare_year = max(2009, current_year - 1)

    return ResolvedYears(year=current_year, compare_year=compare_year)


def _build_url(year: int, dataset: str, variables: list[str], zcta: str, api_key: str | None) -> str:
    params = {
        "get": ",".join(["NAME", *variables]),
        "for": f"zip code tabulation area:{zcta}",
    }
    if api_key:
        params["key"] = api_key
    return f"{CENSUS_API_BASE}/{year}/{dataset}?{urlencode(params)}"


def _build_all_zcta_url(year: int, dataset: str, variables: list[str], api_key: str | None) -> str:
    params = {
        "get": ",".join(["NAME", *variables]),
        "for": "zip code tabulation area:*",
    }
    if api_key:
        params["key"] = api_key
    return f"{CENSUS_API_BASE}/{year}/{dataset}?{urlencode(params)}"


def _fetch_single_row(year: int, dataset: str, variables: list[str], zcta: str, api_key: str | None) -> dict[str, str]:
    rows = _fetch_json(_build_url(year, dataset, variables, zcta, api_key))
    if len(rows) < 2:
        raise ValueError(f"No rows returned for ZCTA {zcta} in {year}")
    header, values = rows[0], rows[1]
    return {key: value for key, value in zip(header, values, strict=False)}


def _fetch_all_rows(year: int, dataset: str, variables: list[str], api_key: str | None) -> dict[str, dict[str, str]]:
    rows = _fetch_json(_build_all_zcta_url(year, dataset, variables, api_key), timeout_seconds=60)
    if len(rows) < 2:
        return {}

    header = rows[0]
    by_zcta: dict[str, dict[str, str]] = {}
    for row in rows[1:]:
        obj = {key: value for key, value in zip(header, row, strict=False)}
        zcta = (obj.get("zip code tabulation area") or "").strip()
        if zcta:
            by_zcta[zcta] = obj
    return by_zcta


def _fetch_dp04_tenure(year: int, zcta: str, api_key: str | None) -> dict[str, int]:
    row = _fetch_single_row(
        year=year,
        dataset="acs/acs5/profile",
        variables=["DP04_0001E", "DP04_0046E", "DP04_0047E"],
        zcta=zcta,
        api_key=api_key,
    )
    return {
        "housing_units": _safe_int(row.get("DP04_0001E")),
        "owner_households": _safe_int(row.get("DP04_0046E")),
        "renter_households": _safe_int(row.get("DP04_0047E")),
    }


def _fetch_b25003_tenure(year: int, zcta: str, api_key: str | None) -> dict[str, int]:
    row = _fetch_single_row(
        year=year,
        dataset="acs/acs5",
        variables=["B25003_001E", "B25003_002E", "B25003_003E"],
        zcta=zcta,
        api_key=api_key,
    )
    return {
        "housing_units": _safe_int(row.get("B25003_001E")),
        "owner_households": _safe_int(row.get("B25003_002E")),
        "renter_households": _safe_int(row.get("B25003_003E")),
    }


def _fetch_tenure(year: int, zcta: str, api_key: str | None) -> dict[str, int]:
    try:
        return _fetch_dp04_tenure(year, zcta, api_key)
    except (HTTPError, URLError, ValueError, json.JSONDecodeError):
        return _fetch_b25003_tenure(year, zcta, api_key)


def _fetch_median_rent(year: int, zcta: str, api_key: str | None) -> float:
    try:
        row = _fetch_single_row(
            year=year,
            dataset="acs/acs5",
            variables=["B25064_001E"],
            zcta=zcta,
            api_key=api_key,
        )
        return _safe_float(row.get("B25064_001E"))
    except (HTTPError, URLError, ValueError, json.JSONDecodeError):
        return 0.0


def _fetch_all_tenure(year: int, api_key: str | None) -> dict[str, dict[str, int]]:
    try:
        rows = _fetch_all_rows(
            year,
            "acs/acs5/profile",
            ["DP04_0001E", "DP04_0046E", "DP04_0047E"],
            api_key,
        )
        output: dict[str, dict[str, int]] = {}
        for zcta, row in rows.items():
            output[zcta] = {
                "housing_units": _safe_int(row.get("DP04_0001E")),
                "owner_households": _safe_int(row.get("DP04_0046E")),
                "renter_households": _safe_int(row.get("DP04_0047E")),
            }
        return output
    except (HTTPError, URLError, ValueError, json.JSONDecodeError):
        rows = _fetch_all_rows(
            year,
            "acs/acs5",
            ["B25003_001E", "B25003_002E", "B25003_003E"],
            api_key,
        )
        output = {}
        for zcta, row in rows.items():
            output[zcta] = {
                "housing_units": _safe_int(row.get("B25003_001E")),
                "owner_households": _safe_int(row.get("B25003_002E")),
                "renter_households": _safe_int(row.get("B25003_003E")),
            }
        return output


def _fetch_all_median_rent(year: int, api_key: str | None) -> dict[str, float]:
    rows = _fetch_all_rows(year, "acs/acs5", ["B25064_001E"], api_key)
    return {zcta: _safe_float(row.get("B25064_001E")) for zcta, row in rows.items()}


def _load_zcta_centroids(*, cache_path: Path) -> dict[str, tuple[float, float]]:
    if cache_path.exists():
        output: dict[str, tuple[float, float]] = {}
        with cache_path.open("r", newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                zcta = (row.get("zcta") or "").strip()
                lat = _safe_float(row.get("latitude"))
                lon = _safe_float(row.get("longitude"))
                if zcta and lat != 0.0 and lon != 0.0:
                    output[zcta] = (lat, lon)
        if output:
            return output

    for year in (2025, 2024, 2023, 2022, 2021):
        url = GAZETTEER_URL_TEMPLATE.format(year=year)
        try:
            with urlopen(url, timeout=60) as response:  # noqa: S310 - fixed trusted endpoint
                archive_bytes = response.read()
        except (HTTPError, URLError, TimeoutError):
            continue

        output: dict[str, tuple[float, float]] = {}
        # Parse in memory to avoid external dependency.
        with ZipFile(io.BytesIO(archive_bytes)) as archive:
            member = next((name for name in archive.namelist() if name.lower().endswith(".txt")), None)
            if not member:
                continue
            with archive.open(member) as raw_txt:
                text_stream = io.TextIOWrapper(raw_txt, encoding="utf-8")
                # Recent Gazetteer files use pipe delimiters; older files may use tabs.
                header_line = text_stream.readline()
                delimiter = "|" if "|" in header_line else "\t"
                text_stream.seek(0)
                reader = csv.DictReader(text_stream, delimiter=delimiter)
                for row in reader:
                    zcta = (row.get("GEOID") or "").strip()
                    lat = _safe_float(row.get("INTPTLAT"))
                    lon = _safe_float(row.get("INTPTLONG"))
                    if zcta and lat != 0.0 and lon != 0.0:
                        output[zcta] = (lat, lon)

        if output:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with cache_path.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=["zcta", "latitude", "longitude"])
                writer.writeheader()
                for zcta, (lat, lon) in sorted(output.items()):
                    writer.writerow({"zcta": zcta, "latitude": lat, "longitude": lon})
            return output

    return {}


def _risk_bucket(demand_index: float) -> str:
    if demand_index >= 125:
        return "STOCKOUT_RISK"
    if demand_index <= 92:
        return "OVERSTOCK_RISK"
    if demand_index >= 108:
        return "WATCH"
    return "OK"


def _delay_label(risk: str) -> str:
    if risk == "STOCKOUT_RISK":
        return "1-2 Weeks"
    if risk == "OVERSTOCK_RISK":
        return "10-14 Weeks"
    if risk == "WATCH":
        return "4-8 Weeks"
    return "2-4 Weeks"


def build_real_estate_heatmap(
    *,
    year: int,
    compare_year: int,
    api_key: str | None,
    limit: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    points: list[dict[str, Any]] = []
    warnings: list[str] = []

    for seed in SEED_ZCTA_POINTS:
        try:
            current = _fetch_tenure(year, seed.zcta, api_key)
            previous = _fetch_tenure(compare_year, seed.zcta, api_key)
            median_rent = _fetch_median_rent(year, seed.zcta, api_key)
        except (HTTPError, URLError, ValueError, json.JSONDecodeError) as exc:
            warnings.append(f"{seed.zcta}: {type(exc).__name__}")
            continue

        occupied_households = max(
            current["owner_households"] + current["renter_households"],
            current["housing_units"],
            1,
        )
        renter_share = current["renter_households"] / occupied_households
        owner_share = current["owner_households"] / occupied_households

        renter_yoy = _pct_change(current["renter_households"], previous["renter_households"])
        owner_yoy = _pct_change(current["owner_households"], previous["owner_households"])
        units_yoy = _pct_change(current["housing_units"], previous["housing_units"])

        # Weighted demand pressure index for home + rental move-ins and turnover.
        demand_index = (
            100.0
            + renter_yoy * 55.0
            + owner_yoy * 35.0
            + units_yoy * 20.0
            + renter_share * 14.0
            + min(median_rent / 2500.0, 1.0) * 6.0
        )

        risk = _risk_bucket(demand_index)
        volume = int(max(40.0, occupied_households * (demand_index / 100.0) / 42.0))

        points.append(
            {
                "id": f"{seed.zcta}-{year}",
                "hub": seed.label,
                "zipPrefix": seed.zcta,
                "zcta": seed.zcta,
                "state": seed.state,
                "position": [seed.longitude, seed.latitude],
                "risk": risk,
                "volume": volume,
                "delay": _delay_label(risk),
                "demand_index": round(demand_index, 2),
                "owner_households": current["owner_households"],
                "renter_households": current["renter_households"],
                "owner_share_pct": round(owner_share * 100.0, 2),
                "renter_share_pct": round(renter_share * 100.0, 2),
                "owner_yoy_pct": round(owner_yoy * 100.0, 2),
                "renter_yoy_pct": round(renter_yoy * 100.0, 2),
                "housing_units_yoy_pct": round(units_yoy * 100.0, 2),
                "median_rent_usd": round(median_rent, 2),
                "source": "ACS DP04 + ACS5",
            }
        )

    points.sort(key=lambda item: item["demand_index"], reverse=True)
    if limit > 0:
        points = points[:limit]
    return points, warnings


def build_national_real_estate_heatmap(
    *,
    year: int,
    compare_year: int,
    api_key: str | None,
    limit: int,
    centroid_cache_path: Path,
) -> tuple[list[dict[str, Any]], list[str], ResolvedYears]:
    resolved = resolve_acs_year_pair(
        requested_year=year,
        requested_compare_year=compare_year,
        api_key=api_key,
    )

    warnings: list[str] = []
    centroids = _load_zcta_centroids(cache_path=centroid_cache_path)
    if not centroids:
        warnings.append("Could not load national ZCTA centroid file; no geographic output available")
        return [], warnings, resolved

    current_tenure = _fetch_all_tenure(resolved.year, api_key)
    previous_tenure = _fetch_all_tenure(resolved.compare_year, api_key)
    current_rent = _fetch_all_median_rent(resolved.year, api_key)

    common_zctas = set(current_tenure).intersection(previous_tenure).intersection(centroids)
    points: list[dict[str, Any]] = []
    for zcta in common_zctas:
        current = current_tenure[zcta]
        previous = previous_tenure[zcta]
        median_rent = current_rent.get(zcta, 0.0)

        occupied_households = max(
            current["owner_households"] + current["renter_households"],
            current["housing_units"],
            1,
        )
        renter_share = current["renter_households"] / occupied_households
        owner_share = current["owner_households"] / occupied_households

        renter_yoy = _pct_change(current["renter_households"], previous["renter_households"])
        owner_yoy = _pct_change(current["owner_households"], previous["owner_households"])
        units_yoy = _pct_change(current["housing_units"], previous["housing_units"])

        demand_index = (
            100.0
            + renter_yoy * 55.0
            + owner_yoy * 35.0
            + units_yoy * 20.0
            + renter_share * 14.0
            + min(median_rent / 2500.0, 1.0) * 6.0
        )
        risk = _risk_bucket(demand_index)
        volume = int(max(40.0, occupied_households * (demand_index / 100.0) / 42.0))
        lat, lon = centroids[zcta]

        points.append(
            {
                "id": f"{zcta}-{resolved.year}",
                "hub": f"ZCTA {zcta}",
                "zipPrefix": zcta,
                "zcta": zcta,
                "state": "US",
                "position": [lon, lat],
                "risk": risk,
                "volume": volume,
                "delay": _delay_label(risk),
                "demand_index": round(demand_index, 2),
                "owner_households": current["owner_households"],
                "renter_households": current["renter_households"],
                "owner_share_pct": round(owner_share * 100.0, 2),
                "renter_share_pct": round(renter_share * 100.0, 2),
                "owner_yoy_pct": round(owner_yoy * 100.0, 2),
                "renter_yoy_pct": round(renter_yoy * 100.0, 2),
                "housing_units_yoy_pct": round(units_yoy * 100.0, 2),
                "median_rent_usd": round(median_rent, 2),
                "source": "ACS DP04 + ACS5 (national)",
            }
        )

    points.sort(key=lambda item: item["demand_index"], reverse=True)
    if limit > 0:
        points = points[:limit]
    return points, warnings, resolved


def build_fallback_heatmap(*, year: int, limit: int) -> list[dict[str, Any]]:
    fallback_points: list[dict[str, Any]] = []

    for index, seed in enumerate(SEED_ZCTA_POINTS):
        if limit > 0 and len(fallback_points) >= limit:
            break

        phase = (index + 1) * 0.45
        demand_index = 100.0 + math.sin(phase) * 18.0 + math.cos(phase * 0.4) * 9.0
        risk = _risk_bucket(demand_index)

        fallback_points.append(
            {
                "id": f"{seed.zcta}-{year}-fallback",
                "hub": seed.label,
                "zipPrefix": seed.zcta,
                "zcta": seed.zcta,
                "state": seed.state,
                "position": [seed.longitude, seed.latitude],
                "risk": risk,
                "volume": int(140 + abs(math.sin(phase)) * 760),
                "delay": _delay_label(risk),
                "demand_index": round(demand_index, 2),
                "owner_households": 0,
                "renter_households": 0,
                "owner_share_pct": 0.0,
                "renter_share_pct": 0.0,
                "owner_yoy_pct": 0.0,
                "renter_yoy_pct": 0.0,
                "housing_units_yoy_pct": 0.0,
                "median_rent_usd": 0.0,
                "source": "deterministic-fallback",
            }
        )

    return fallback_points


def load_scored_heatmap_from_csv(*, csv_path: Path, limit: int) -> tuple[list[dict[str, Any]], list[str]]:
    points: list[dict[str, Any]] = []
    warnings: list[str] = []

    if not csv_path.exists():
        return [], [f"Missing scored CSV at {csv_path}"]

    with csv_path.open("r", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            zcta = (row.get("zcta") or "").strip()
            if not zcta:
                warnings.append("Skipped row with missing zcta")
                continue

            seed = SEED_ZCTA_INDEX.get(zcta)
            lat = _safe_float(row.get("latitude") or row.get("lat"))
            lon = _safe_float(row.get("longitude") or row.get("lng") or row.get("lon"))

            if lat == 0.0 or lon == 0.0:
                if seed is None:
                    warnings.append(f"No coordinates for zcta {zcta}")
                    continue
                lat = seed.latitude
                lon = seed.longitude

            owner_households = _safe_int(row.get("owner_households"))
            renter_households = _safe_int(row.get("renter_households"))
            total_households = max(owner_households + renter_households, 1)

            owner_share_pct = (owner_households / total_households) * 100.0
            renter_share_pct = (renter_households / total_households) * 100.0
            predicted_pressure = _safe_float(row.get("predicted_pressure"))
            risk = (row.get("predicted_risk") or "").strip() or _risk_bucket(predicted_pressure)
            volume = int(max(40.0, total_households * max(predicted_pressure, 1.0) / 45.0))

            points.append(
                {
                    "id": row.get("id") or f"{zcta}-scored",
                    "hub": row.get("hub") or (seed.label if seed else f"ZCTA {zcta}"),
                    "zipPrefix": zcta,
                    "zcta": zcta,
                    "state": row.get("state") or (seed.state if seed else "US"),
                    "position": [lon, lat],
                    "risk": risk,
                    "volume": volume,
                    "delay": _delay_label(risk),
                    "demand_index": round(predicted_pressure, 2),
                    "owner_households": owner_households,
                    "renter_households": renter_households,
                    "owner_share_pct": round(owner_share_pct, 2),
                    "renter_share_pct": round(renter_share_pct, 2),
                    "owner_yoy_pct": _safe_float(row.get("owner_yoy_pct")),
                    "renter_yoy_pct": _safe_float(row.get("renter_yoy_pct")),
                    "housing_units_yoy_pct": _safe_float(row.get("housing_units_yoy_pct")),
                    "median_rent_usd": _safe_float(row.get("median_rent_usd")),
                    "source": "model-scored-csv",
                }
            )

    points.sort(key=lambda item: item["demand_index"], reverse=True)
    if limit > 0:
        points = points[:limit]
    return points, warnings
