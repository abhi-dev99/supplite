from __future__ import annotations

import csv
import json
import os
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .housing_signals import (
    build_fallback_heatmap,
    build_national_real_estate_heatmap,
    build_real_estate_heatmap,
    load_scored_heatmap_from_csv,
)


class BriefSKU(BaseModel):
    sku_id: str = Field(min_length=1, max_length=64)
    product_name: str = Field(min_length=1, max_length=120)
    brand: str = Field(min_length=1, max_length=64)
    category: str = Field(min_length=1, max_length=64)
    current_stock: int = Field(ge=0)
    on_order: int = Field(ge=0)
    lead_time_days: int = Field(ge=1, le=365)
    days_of_supply: float = Field(ge=0)
    risk_level: Literal["STOCKOUT_RISK", "OVERSTOCK_RISK", "WATCH", "OK"]
    forecast_demand_60d: int = Field(ge=0)
    demand_shortfall: int = Field(ge=0)
    primary_signal: str = Field(min_length=1, max_length=64)
    signal_detail: str = Field(min_length=1, max_length=200)
    recommended_action: str = Field(min_length=1, max_length=200)


class BriefContext(BaseModel):
    brief_date: date
    metro: str
    dc_name: str
    week_summary: str
    urgent_skus: list[BriefSKU]
    overstock_skus: list[BriefSKU]
    watch_skus: list[BriefSKU]
    kpis: dict[str, float | int | str] = Field(default_factory=dict)
    signal_drivers: list[dict[str, Any]] = Field(default_factory=list)


class BriefResponse(BaseModel):
    brief_date: date
    generated_at: datetime
    model_version: str
    provider: str
    cache_hit: bool
    brief_text: str
    context: BriefContext


class HealthResponse(BaseModel):
    status: str
    model_version: str
    database_ready: bool
    cache_ready: bool


class RealEstateHeatmapPoint(BaseModel):
    id: str
    hub: str
    zipPrefix: str
    zcta: str
    state: str
    position: list[float]
    risk: Literal["STOCKOUT_RISK", "OVERSTOCK_RISK", "WATCH", "OK"]
    volume: int
    delay: str
    demand_index: float
    owner_households: int
    renter_households: int
    owner_share_pct: float
    renter_share_pct: float
    owner_yoy_pct: float
    renter_yoy_pct: float
    housing_units_yoy_pct: float
    median_rent_usd: float
    source: str


class RealEstateHeatmapResponse(BaseModel):
    generated_at: datetime
    year: int
    compare_year: int
    point_count: int
    mode: Literal["live", "fallback"]
    notes: list[str]
    points: list[RealEstateHeatmapPoint]


class TimelinePoint(BaseModel):
    date: str
    sales_velocity_7d: float
    search_velocity_7d: float
    units_sold: int
    surge_score: float


class TimelineSummary(BaseModel):
    point_count: int
    metro_count: int
    sales_delta: float
    search_delta: float


class TimelineResponse(BaseModel):
    generated_at: datetime
    sku_id: str
    product_name: str
    category: str
    period_days: int
    points: list[TimelinePoint]
    summary: TimelineSummary


class TimelineOption(BaseModel):
    sku_id: str
    product_name: str
    category: str


class TimelineOptionsResponse(BaseModel):
    generated_at: datetime
    period_options: list[int]
    sku_options: list[TimelineOption]


class SimulationOption(BaseModel):
    sku_id: str
    product_name: str
    category: str
    metro: str
    dc: str


class SimulationOptionsResponse(BaseModel):
    generated_at: datetime
    sku_options: list[SimulationOption]


class SimulationPoint(BaseModel):
    date: str
    demand_units: int
    inventory_baseline: int
    inventory_early: int
    fulfilled_baseline: int
    fulfilled_early: int
    lost_baseline: int
    lost_early: int
    cumulative_revenue_baseline: float
    cumulative_revenue_early: float
    cumulative_profit_baseline: float
    cumulative_profit_early: float


class SimulationSummary(BaseModel):
    horizon_days: int
    event_date: str
    baseline_lag_days: int
    earlier_by_days: int
    baseline_lost_units: int
    early_lost_units: int
    units_saved: int
    revenue_uplift_usd: float
    profit_uplift_usd: float
    baseline_service_level_pct: float
    early_service_level_pct: float
    replenishment_units: int
    lead_time_days: int


class SimulationResponse(BaseModel):
    generated_at: datetime
    sku_id: str
    product_name: str
    category: str
    metro: str
    dc: str
    price: float
    margin_rate: float
    points: list[SimulationPoint]
    summary: SimulationSummary


app = FastAPI(title="Supply Chain Brief Backend", version="0.1.0")

# Load local env files for backend runtime configuration without committing secrets.
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_BACKEND_ROOT / ".env", override=False)
load_dotenv(_REPO_ROOT / ".env", override=False)

_LIVE_HEATMAP_CACHE: dict[str, dict[str, object]] = {}
_LIVE_HEATMAP_CACHE_LOCK = Lock()
_WEEKLY_BRIEF_CACHE: dict[str, dict[str, object]] = {}
_WEEKLY_BRIEF_CACHE_LOCK = Lock()

SUPPORTED_METROS = (
    "Atlanta",
    "Chicago",
    "Dallas",
    "Denver",
    "Houston",
    "Los Angeles",
    "Miami",
    "New York",
    "Phoenix",
    "San Francisco",
    "Seattle",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


def _safe_int(value: str | int | float | None) -> int:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return 0


def _safe_float(value: str | int | float | None) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return 0.0


def _data_root() -> Path:
    root = Path(__file__).resolve().parents[3] / "data"
    new_root = root / "new"
    # Prefer refreshed dataset bundle when present.
    if (new_root / "sku_inventory.csv").exists() and (new_root / "sku_daily_signals.csv").exists():
        return new_root
    return root


def _data_file(file_name: str) -> Path:
    return _data_root() / file_name


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        return [dict(row) for row in reader]


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _to_brief_sku(row: dict[str, str]) -> BriefSKU:
    return BriefSKU(
        sku_id=row.get("sku_id", "UNKNOWN"),
        product_name=row.get("product_name", "Unknown Product"),
        brand=row.get("brand", "Unknown"),
        category=row.get("category", "Unknown"),
        current_stock=_safe_int(row.get("stock_on_hand")),
        on_order=_safe_int(row.get("on_order")),
        lead_time_days=max(1, _safe_int(row.get("lead_time_days"))),
        days_of_supply=max(0.0, _safe_float(row.get("days_of_supply"))),
        risk_level=(row.get("risk_level") or "OK") if (row.get("risk_level") or "OK") in {"STOCKOUT_RISK", "OVERSTOCK_RISK", "WATCH", "OK"} else "OK",
        forecast_demand_60d=_safe_int(row.get("forecast_demand_60d")),
        demand_shortfall=max(0, _safe_int(row.get("demand_shortfall"))),
        primary_signal=row.get("primary_signal", "baseline"),
        signal_detail=row.get("signal_detail", "No signal detail"),
        recommended_action=row.get("recommended_action", "Monitor and adjust ordering"),
    )


def _latest_signal_drivers(metro: str, sku_ids: set[str], limit: int = 14) -> list[dict[str, Any]]:
    rows = _read_csv_rows(_data_file("sku_daily_signals.csv"))
    filtered = [
        row
        for row in rows
        if (row.get("metro") == metro and row.get("sku_id") in sku_ids)
    ]

    latest_by_key: dict[tuple[str, str], dict[str, str]] = {}
    for row in filtered:
        key = (row.get("metro", ""), row.get("sku_id", ""))
        existing = latest_by_key.get(key)
        if existing is None or (row.get("date", "") > existing.get("date", "")):
            latest_by_key[key] = row

    drivers = []
    for row in latest_by_key.values():
        drivers.append(
            {
                "sku_id": row.get("sku_id", ""),
                "date": row.get("date", ""),
                "sales_velocity_7d": round(_safe_float(row.get("sales_velocity_7d")), 2),
                "search_velocity_7d": round(_safe_float(row.get("search_velocity_7d")), 2),
                "permit_velocity_30d": round(_safe_float(row.get("permit_velocity_30d")), 2),
                "holiday_factor": round(_safe_float(row.get("holiday_factor")), 3),
                "scenario_type": row.get("scenario_type", ""),
                "surge_score": round(_safe_float(row.get("surge_score")), 2),
            }
        )

    drivers.sort(key=lambda item: abs(_safe_float(item.get("search_velocity_7d"))) + abs(_safe_float(item.get("sales_velocity_7d"))), reverse=True)
    return drivers[:limit]


def _timeline_period_options() -> list[int]:
    return [14, 30, 60, 90, 180]


def _normalize_period_days(period_days: int) -> int:
    options = _timeline_period_options()
    if period_days in options:
        return period_days
    if period_days < min(options):
        return min(options)
    if period_days > max(options):
        return max(options)
    return min(options, key=lambda option: abs(option - period_days))


def _build_timeline_options() -> list[TimelineOption]:
    inventory_rows = _read_csv_rows(_data_file("sku_inventory.csv"))
    catalog_rows = _read_csv_rows(_data_file("sku_catalog.csv"))

    catalog_by_sku: dict[str, dict[str, str]] = {}
    for row in catalog_rows:
        sku_id = (row.get("sku_id") or "").strip()
        if sku_id:
            catalog_by_sku[sku_id] = row

    options_by_sku: dict[str, TimelineOption] = {}
    for row in inventory_rows:
        sku_id = (row.get("sku_id") or "").strip()
        if not sku_id:
            continue
        catalog = catalog_by_sku.get(sku_id, {})
        product_name = (row.get("product_name") or catalog.get("product_name") or "Unknown Product").strip()
        category = (row.get("category") or catalog.get("category") or "Unknown").strip()
        if sku_id not in options_by_sku:
            options_by_sku[sku_id] = TimelineOption(
                sku_id=sku_id,
                product_name=product_name,
                category=category,
            )

    return sorted(options_by_sku.values(), key=lambda item: item.sku_id)


def _build_signal_timeline(sku_id: str, period_days: int) -> TimelineResponse:
    normalized_sku = sku_id.strip().upper()
    normalized_period = _normalize_period_days(period_days)

    if not normalized_sku:
        raise ValueError("sku_id is required")

    signal_rows = _read_csv_rows(_data_file("sku_daily_signals.csv"))
    filtered_rows = [row for row in signal_rows if (row.get("sku_id") or "").strip().upper() == normalized_sku]
    if not filtered_rows:
        raise ValueError(f"No daily signal rows found for sku_id '{normalized_sku}'")

    dated_rows: list[tuple[date, dict[str, str]]] = []
    for row in filtered_rows:
        parsed_date = _parse_iso_date(row.get("date"))
        if parsed_date is not None:
            dated_rows.append((parsed_date, row))

    if not dated_rows:
        raise ValueError(f"No valid dated signal rows found for sku_id '{normalized_sku}'")

    latest_date = max(item[0] for item in dated_rows)
    cutoff_date = latest_date - timedelta(days=normalized_period - 1)

    daily_aggregate: dict[str, dict[str, Any]] = {}
    metros: set[str] = set()
    for row_date, row in dated_rows:
        if row_date < cutoff_date:
            continue
        day_key = row_date.isoformat()
        bucket = daily_aggregate.setdefault(
            day_key,
            {
                "sales_values": [],
                "search_values": [],
                "units_sold": 0,
                "surge_values": [],
            },
        )
        bucket["sales_values"].append(_safe_float(row.get("sales_velocity_7d")))
        bucket["search_values"].append(_safe_float(row.get("search_velocity_7d")))
        bucket["units_sold"] += _safe_int(row.get("units_sold"))
        bucket["surge_values"].append(_safe_float(row.get("surge_score")))
        metro_name = (row.get("metro") or "").strip()
        if metro_name:
            metros.add(metro_name)

    points: list[TimelinePoint] = []
    for day_key in sorted(daily_aggregate.keys()):
        bucket = daily_aggregate[day_key]
        sales_values = bucket["sales_values"]
        search_values = bucket["search_values"]
        surge_values = bucket["surge_values"]
        points.append(
            TimelinePoint(
                date=day_key,
                sales_velocity_7d=round(sum(sales_values) / max(len(sales_values), 1), 2),
                search_velocity_7d=round(sum(search_values) / max(len(search_values), 1), 2),
                units_sold=int(bucket["units_sold"]),
                surge_score=round(sum(surge_values) / max(len(surge_values), 1), 2),
            )
        )

    sales_delta = 0.0
    search_delta = 0.0
    if len(points) >= 2:
        sales_delta = round(points[-1].sales_velocity_7d - points[0].sales_velocity_7d, 2)
        search_delta = round(points[-1].search_velocity_7d - points[0].search_velocity_7d, 2)

    inventory_rows = _read_csv_rows(_data_file("sku_inventory.csv"))
    sku_inventory_rows = [row for row in inventory_rows if (row.get("sku_id") or "").strip().upper() == normalized_sku]
    product_name = sku_inventory_rows[0].get("product_name", "Unknown Product") if sku_inventory_rows else "Unknown Product"
    category = sku_inventory_rows[0].get("category", "Unknown") if sku_inventory_rows else "Unknown"

    return TimelineResponse(
        generated_at=datetime.now(timezone.utc),
        sku_id=normalized_sku,
        product_name=product_name,
        category=category,
        period_days=normalized_period,
        points=points,
        summary=TimelineSummary(
            point_count=len(points),
            metro_count=len(metros),
            sales_delta=sales_delta,
            search_delta=search_delta,
        ),
    )


def _normalize_horizon_days(horizon_days: int) -> int:
    return max(14, min(int(horizon_days), 120))


def _normalize_margin_rate(margin_rate: float) -> float:
    return max(0.05, min(float(margin_rate), 0.9))


def _normalize_baseline_lag_days(baseline_lag_days: int) -> int:
    return max(1, min(int(baseline_lag_days), 30))


def _normalize_earlier_by_days(earlier_by_days: int, baseline_lag_days: int) -> int:
    normalized = max(1, min(int(earlier_by_days), 30))
    return min(normalized, max(1, baseline_lag_days - 1))


def _build_simulation_options(dc: str = "ALL") -> list[SimulationOption]:
    inventory_rows = _read_csv_rows(_data_file("sku_inventory.csv"))
    selected_dc = (dc or "ALL").strip()

    options: list[SimulationOption] = []
    for row in inventory_rows:
        dc_name = (row.get("dc") or "").strip()
        if selected_dc != "ALL" and dc_name != selected_dc:
            continue
        sku_id = (row.get("sku_id") or "").strip()
        if not sku_id:
            continue
        options.append(
            SimulationOption(
                sku_id=sku_id,
                product_name=(row.get("product_name") or "Unknown Product").strip(),
                category=(row.get("category") or "Unknown").strip(),
                metro=(row.get("metro") or "Unknown").strip(),
                dc=dc_name or "Unknown",
            )
        )

    options.sort(key=lambda item: (item.sku_id, item.metro, item.dc))
    return options


def _resolve_inventory_row(sku_id: str, metro: str | None = None) -> dict[str, str] | None:
    inventory_rows = _read_csv_rows(_data_file("sku_inventory.csv"))
    normalized_sku = sku_id.strip().upper()
    normalized_metro = (metro or "").strip().lower()

    candidates = [
        row
        for row in inventory_rows
        if (row.get("sku_id") or "").strip().upper() == normalized_sku
    ]
    if not candidates:
        return None

    if normalized_metro:
        for row in candidates:
            if (row.get("metro") or "").strip().lower() == normalized_metro:
                return row

    candidates.sort(key=lambda row: _safe_float(row.get("surge_score")), reverse=True)
    return candidates[0]


def _event_index_from_signals(rows: list[tuple[date, dict[str, str]]]) -> int:
    if not rows:
        return 0

    for idx, (_, row) in enumerate(rows):
        if _safe_float(row.get("search_velocity_7d")) >= 15.0 and _safe_float(row.get("sales_velocity_7d")) >= 8.0:
            return idx

    scored = [
        (
            idx,
            _safe_float(row.get("search_velocity_7d")) * 0.6
            + _safe_float(row.get("sales_velocity_7d")) * 0.4
            + max(0.0, _safe_float(row.get("composite_score")) - 55.0) * 0.2,
        )
        for idx, (_, row) in enumerate(rows)
    ]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[0][0] if scored else 0


def _simulate_stock_path(
    *,
    demand_series: list[tuple[date, int]],
    initial_stock: int,
    replenishment_units: int,
    arrival_day_index: int,
    price: float,
    margin_rate: float,
) -> list[dict[str, int | float | str]]:
    stock = max(0, int(initial_stock))
    cumulative_revenue = 0.0
    cumulative_profit = 0.0
    output: list[dict[str, int | float | str]] = []

    for idx, (day, demand_units) in enumerate(demand_series):
        if idx == arrival_day_index:
            stock += max(0, int(replenishment_units))

        demand = max(0, int(demand_units))
        fulfilled = min(stock, demand)
        lost = max(0, demand - fulfilled)
        stock = max(0, stock - fulfilled)

        cumulative_revenue += fulfilled * price
        cumulative_profit += fulfilled * price * margin_rate

        output.append(
            {
                "date": day.isoformat(),
                "demand_units": demand,
                "inventory": stock,
                "fulfilled": fulfilled,
                "lost": lost,
                "cumulative_revenue": round(cumulative_revenue, 2),
                "cumulative_profit": round(cumulative_profit, 2),
            }
        )

    return output


def _build_early_catch_simulation(
    *,
    sku_id: str,
    metro: str | None,
    horizon_days: int,
    baseline_lag_days: int,
    earlier_by_days: int,
    margin_rate: float,
) -> SimulationResponse:
    normalized_sku = (sku_id or "").strip().upper()
    if not normalized_sku:
        raise ValueError("sku_id is required")

    normalized_horizon = _normalize_horizon_days(horizon_days)
    normalized_lag = _normalize_baseline_lag_days(baseline_lag_days)
    normalized_earlier = _normalize_earlier_by_days(earlier_by_days, normalized_lag)
    normalized_margin = _normalize_margin_rate(margin_rate)

    inventory_row = _resolve_inventory_row(normalized_sku, metro=metro)
    if inventory_row is None:
        raise ValueError(f"No inventory row found for sku_id '{normalized_sku}'")

    chosen_metro = (metro or inventory_row.get("metro") or "").strip()
    signal_rows = _read_csv_rows(_data_file("sku_daily_signals.csv"))
    filtered = [
        row
        for row in signal_rows
        if (row.get("sku_id") or "").strip().upper() == normalized_sku
        and (not chosen_metro or (row.get("metro") or "").strip() == chosen_metro)
    ]
    if not filtered and chosen_metro:
        filtered = [
            row
            for row in signal_rows
            if (row.get("sku_id") or "").strip().upper() == normalized_sku
        ]

    dated_rows: list[tuple[date, dict[str, str]]] = []
    for row in filtered:
        parsed = _parse_iso_date(row.get("date"))
        if parsed is not None:
            dated_rows.append((parsed, row))

    if not dated_rows:
        raise ValueError(f"No signal rows found for sku_id '{normalized_sku}'")

    dated_rows.sort(key=lambda item: item[0])
    event_idx = _event_index_from_signals(dated_rows)

    event_idx = min(event_idx, max(0, len(dated_rows) - 1))
    event_date = dated_rows[event_idx][0]

    last_known_date = dated_rows[-1][0]
    last_known_units = max(1, _safe_int(dated_rows[-1][1].get("units_sold")))

    demand_series: list[tuple[date, int]] = []
    for day_offset in range(normalized_horizon):
        row_idx = event_idx + day_offset
        if row_idx < len(dated_rows):
            row_date, row = dated_rows[row_idx]
            demand_series.append((row_date, max(0, _safe_int(row.get("units_sold")))))
        else:
            projected_date = last_known_date + timedelta(days=row_idx - len(dated_rows) + 1)
            demand_series.append((projected_date, last_known_units))

    initial_stock = max(0, _safe_int(inventory_row.get("stock_on_hand")))
    lead_time_days = max(1, _safe_int(inventory_row.get("lead_time_days")))
    avg_daily_sales = max(1.0, _safe_float(inventory_row.get("avg_daily_sales")))
    forecast_demand_60d = max(1, _safe_int(inventory_row.get("forecast_demand_60d")))
    replenishment_units = max(
        int(round(avg_daily_sales * lead_time_days * 0.8)),
        int(round(forecast_demand_60d * 0.35)),
        1,
    )

    late_arrival_idx = normalized_lag + lead_time_days
    early_arrival_idx = max(0, normalized_lag - normalized_earlier) + lead_time_days

    baseline_path = _simulate_stock_path(
        demand_series=demand_series,
        initial_stock=initial_stock,
        replenishment_units=replenishment_units,
        arrival_day_index=late_arrival_idx,
        price=max(0.0, _safe_float(inventory_row.get("price"))),
        margin_rate=normalized_margin,
    )
    early_path = _simulate_stock_path(
        demand_series=demand_series,
        initial_stock=initial_stock,
        replenishment_units=replenishment_units,
        arrival_day_index=early_arrival_idx,
        price=max(0.0, _safe_float(inventory_row.get("price"))),
        margin_rate=normalized_margin,
    )

    points: list[SimulationPoint] = []
    for idx in range(normalized_horizon):
        base = baseline_path[idx]
        early = early_path[idx]
        points.append(
            SimulationPoint(
                date=str(base["date"]),
                demand_units=int(base["demand_units"]),
                inventory_baseline=int(base["inventory"]),
                inventory_early=int(early["inventory"]),
                fulfilled_baseline=int(base["fulfilled"]),
                fulfilled_early=int(early["fulfilled"]),
                lost_baseline=int(base["lost"]),
                lost_early=int(early["lost"]),
                cumulative_revenue_baseline=float(base["cumulative_revenue"]),
                cumulative_revenue_early=float(early["cumulative_revenue"]),
                cumulative_profit_baseline=float(base["cumulative_profit"]),
                cumulative_profit_early=float(early["cumulative_profit"]),
            )
        )

    baseline_lost_units = int(sum(int(point["lost"]) for point in baseline_path))
    early_lost_units = int(sum(int(point["lost"]) for point in early_path))
    total_demand_units = int(sum(max(0, demand) for _, demand in demand_series))
    units_saved = max(0, baseline_lost_units - early_lost_units)
    baseline_revenue = float(baseline_path[-1]["cumulative_revenue"]) if baseline_path else 0.0
    early_revenue = float(early_path[-1]["cumulative_revenue"]) if early_path else 0.0
    baseline_profit = float(baseline_path[-1]["cumulative_profit"]) if baseline_path else 0.0
    early_profit = float(early_path[-1]["cumulative_profit"]) if early_path else 0.0

    summary = SimulationSummary(
        horizon_days=normalized_horizon,
        event_date=event_date.isoformat(),
        baseline_lag_days=normalized_lag,
        earlier_by_days=normalized_earlier,
        baseline_lost_units=baseline_lost_units,
        early_lost_units=early_lost_units,
        units_saved=units_saved,
        revenue_uplift_usd=round(max(0.0, early_revenue - baseline_revenue), 2),
        profit_uplift_usd=round(max(0.0, early_profit - baseline_profit), 2),
        baseline_service_level_pct=round((1.0 - (baseline_lost_units / max(total_demand_units, 1))) * 100.0, 2),
        early_service_level_pct=round((1.0 - (early_lost_units / max(total_demand_units, 1))) * 100.0, 2),
        replenishment_units=replenishment_units,
        lead_time_days=lead_time_days,
    )

    return SimulationResponse(
        generated_at=datetime.now(timezone.utc),
        sku_id=normalized_sku,
        product_name=(inventory_row.get("product_name") or "Unknown Product").strip(),
        category=(inventory_row.get("category") or "Unknown").strip(),
        metro=(inventory_row.get("metro") or chosen_metro or "Unknown").strip(),
        dc=(inventory_row.get("dc") or "Unknown").strip(),
        price=round(max(0.0, _safe_float(inventory_row.get("price"))), 2),
        margin_rate=normalized_margin,
        points=points,
        summary=summary,
    )


def _build_city_context(metro: str) -> BriefContext:
    normalized_metro = metro.strip()
    if normalized_metro not in SUPPORTED_METROS:
        normalized_metro = "Dallas"

    inventory_rows = _read_csv_rows(_data_file("sku_inventory.csv"))
    metro_rows = [row for row in inventory_rows if row.get("metro") == normalized_metro]
    if not metro_rows:
        raise ValueError(f"No SKU inventory rows found for metro '{normalized_metro}'")

    dc_name = metro_rows[0].get("dc", "Unknown DC")

    stockout_rows = [row for row in metro_rows if row.get("risk_level") == "STOCKOUT_RISK"]
    overstock_rows = [row for row in metro_rows if row.get("risk_level") == "OVERSTOCK_RISK"]
    watch_rows = [row for row in metro_rows if row.get("risk_level") == "WATCH"]

    stockout_rows.sort(key=lambda row: (_safe_int(row.get("demand_shortfall")), _safe_float(row.get("surge_score"))), reverse=True)
    overstock_rows.sort(key=lambda row: (_safe_float(row.get("days_of_supply")), _safe_float(row.get("stock_on_hand"))), reverse=True)
    watch_rows.sort(key=lambda row: (_safe_float(row.get("surge_score")), _safe_float(row.get("search_index"))), reverse=True)

    urgent = [_to_brief_sku(row) for row in stockout_rows[:10]]
    overstock = [_to_brief_sku(row) for row in overstock_rows[:10]]
    watch = [_to_brief_sku(row) for row in watch_rows[:10]]

    total_on_hand = sum(_safe_int(row.get("stock_on_hand")) for row in metro_rows)
    total_on_order = sum(_safe_int(row.get("on_order")) for row in metro_rows)
    at_risk_shortfall = sum(_safe_int(row.get("demand_shortfall")) for row in stockout_rows)
    avg_days_of_supply = (
        round(sum(_safe_float(row.get("days_of_supply")) for row in metro_rows) / max(len(metro_rows), 1), 1)
    )
    hot_search_count = sum(1 for row in metro_rows if _safe_float(row.get("surge_score")) >= 12.0)

    sku_ids = {sku.sku_id for sku in urgent + overstock + watch}
    drivers = _latest_signal_drivers(normalized_metro, sku_ids)

    week_summary = (
        f"{normalized_metro} buyer desk ({dc_name}) has {len(urgent)} stockout-risk SKUs, "
        f"{len(overstock)} overstock SKUs, and {len(watch)} watch SKUs. "
        f"Net shortfall exposure is {at_risk_shortfall:,} units with average days-of-supply at {avg_days_of_supply}."
    )

    return BriefContext(
        brief_date=date.today(),
        metro=normalized_metro,
        dc_name=dc_name,
        week_summary=week_summary,
        urgent_skus=urgent,
        overstock_skus=overstock,
        watch_skus=watch,
        kpis={
            "total_skus": len(metro_rows),
            "total_on_hand": total_on_hand,
            "total_on_order": total_on_order,
            "at_risk_shortfall": at_risk_shortfall,
            "avg_days_of_supply": avg_days_of_supply,
            "high_surge_skus": hot_search_count,
        },
        signal_drivers=drivers,
    )


def _compose_structured_brief(context: BriefContext) -> str:
    def _format_line(sku: BriefSKU) -> str:
        return (
            f"- {sku.sku_id} | {sku.product_name} | Risk={sku.risk_level} | "
            f"DOS={sku.days_of_supply:.1f} | Shortfall={sku.demand_shortfall:,} | "
            f"Signal={sku.primary_signal}: {sku.signal_detail} | Action={sku.recommended_action}"
        )

    urgent_block = "\n".join(_format_line(sku) for sku in context.urgent_skus[:8]) or "- None"
    overstock_block = "\n".join(_format_line(sku) for sku in context.overstock_skus[:8]) or "- None"
    watch_block = "\n".join(_format_line(sku) for sku in context.watch_skus[:8]) or "- None"

    return (
        f"WEEKLY BUYER BRIEF | Metro: {context.metro} | DC: {context.dc_name} | Week: {context.brief_date:%Y-%m-%d}\n\n"
        f"Executive Summary\n{context.week_summary}\n\n"
        "Urgent Action (Stockout Risk)\n"
        f"{urgent_block}\n\n"
        "Overstock Action\n"
        f"{overstock_block}\n\n"
        "Watch List\n"
        f"{watch_block}\n"
    )


def _gemini_model_candidates() -> list[str]:
    primary = (os.getenv("GEMINI_MODEL") or "gemini-flash-latest").strip()
    fallbacks_raw = (os.getenv("GEMINI_MODEL_FALLBACKS") or "gemini-2.0-flash,gemini-1.5-flash").strip()
    fallbacks = [part.strip() for part in fallbacks_raw.split(",") if part.strip()]

    models: list[str] = []
    for model in [primary, *fallbacks]:
        if model and model not in models:
            models.append(model)
    return models or ["gemini-flash-latest"]


def _gemini_generate(prompt: str) -> tuple[str, str]:
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY")

    last_error: Exception | None = None
    for model in _gemini_model_candidates():
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 8192,
            },
        }

        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        for attempt in range(3):
            try:
                with urlopen(request, timeout=90) as response:  # noqa: S310 - fixed trusted endpoint
                    data = json.loads(response.read().decode("utf-8"))
                candidates = data.get("candidates") or []
                if not candidates:
                    raise ValueError("Gemini returned no candidates")
                parts = ((candidates[0].get("content") or {}).get("parts") or [])
                text = "\n".join((part.get("text") or "").strip() for part in parts if part.get("text"))
                if not text:
                    raise ValueError("Gemini returned empty text")
                return text.strip(), model
            except HTTPError as error:
                # Retry transient provider issues before trying alternate models/fallback.
                if error.code in {429, 500, 502, 503, 504} and attempt < 2:
                    last_error = error
                    time.sleep(2.0 * (attempt + 1))
                    continue
                last_error = error
                break
            except URLError as error:
                if attempt < 2:
                    last_error = error
                    time.sleep(2.0 * (attempt + 1))
                    continue
                last_error = error
                break
            except (ValueError, json.JSONDecodeError) as error:
                last_error = error
                break

    if last_error is not None:
        raise last_error
    raise ValueError("Gemini failed without a concrete error")


def _ollama_generate(prompt: str) -> str:
    model = (os.getenv("OLLAMA_MODEL") or "llama3.1:8b").strip()
    base_url = (os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").strip().rstrip("/")
    url = f"{base_url}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2},
    }

    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=90) as response:  # noqa: S310 - local endpoint
        data = json.loads(response.read().decode("utf-8"))
    text = (data.get("response") or "").strip()
    if not text:
        raise ValueError("Ollama returned empty text")
    return text


def _llm_prompt(context: BriefContext) -> str:
    kpis = context.kpis
    drivers = context.signal_drivers[:8]

    sku_rows = []
    for bucket_name, skus in (
        ("URGENT", context.urgent_skus),
        ("OVERSTOCK", context.overstock_skus),
        ("WATCH", context.watch_skus),
    ):
        for sku in skus[:10]:
            sku_rows.append(
                {
                    "bucket": bucket_name,
                    "sku_id": sku.sku_id,
                    "product": sku.product_name,
                    "category": sku.category,
                    "stock": sku.current_stock,
                    "on_order": sku.on_order,
                    "dos": round(sku.days_of_supply, 1),
                    "lead_time_days": sku.lead_time_days,
                    "forecast_60d": sku.forecast_demand_60d,
                    "shortfall": sku.demand_shortfall,
                    "signal": sku.primary_signal,
                    "signal_detail": sku.signal_detail,
                    "action": sku.recommended_action,
                }
            )

    return (
        "You are writing an executive-level WEEKLY BUYER DOSSIER for a distribution center buyer. "
        "Do not write a short brief. Write a deep, boardroom-ready operating document that reads like a top-tier retail strategy memo. "
        "Tone: decisive, insightful, commercially sharp, with strong narrative flow and concrete decisions.\n\n"
        "OUTPUT FORMAT RULES:\n"
        "- Output valid GitHub-flavored Markdown only.\n"
        "- Use section headings, subheadings, bullet points, and MANY markdown tables.\n"
        "- Minimum target length: 1,500 words. Preferred 1,800-2,500 words when data allows.\n"
        "- Every recommendation must include rationale, expected impact, risk, and timing.\n"
        "- Complete every section fully and do not end mid-sentence or mid-bullet.\n"
        "- Finish with a clear closing paragraph that wraps up the whole dossier.\n"
        "- Never fabricate SKUs, metrics, trends, or DC names outside supplied data.\n\n"
        "MANDATORY SECTIONS (all required):\n"
        "1) Executive Situation Room: strategic narrative, biggest upside/downside, this-week posture.\n"
        "2) KPI Deep Dive: explain each KPI in operational terms and business consequences.\n"
        "3) Urgent Stockout Prevention Plan: SKU-by-SKU triage with immediate actions and backup plans.\n"
        "4) Overstock Recovery Plan: markdown, cancellation, transfer, and velocity-restoration plays.\n"
        "5) Watchlist Intelligence: what could break next and the earliest warning indicators.\n"
        "6) Signal Diagnostics: translate trend/search/permit/seasonality signals into decisions.\n"
        "7) Two-Horizon Buy Plan: next 2 weeks and next 6 weeks with order posture by SKU bucket.\n"
        "8) Scenario Stress Test: base/upside/downside with trigger thresholds and response actions.\n"
        "9) DC Execution Checklist: concrete owner-ready checklist for Monday morning action.\n"
        "10) Leadership Readout: concise but forceful conclusion with top 5 decisions.\n\n"
        "TABLE REQUIREMENTS:\n"
        "- Include at least 6 markdown tables.\n"
        "- Must include one table each for Urgent, Overstock, Watch, Signals, 2-Week Plan, 6-Week Plan.\n"
        "- Recommended table columns: SKU, Product, Risk, DOS, On Hand, On Order, Forecast 60d, Shortfall, Signal, Action, Priority, Timing.\n\n"
        "QUALITY BAR:\n"
        "- Avoid generic filler. Use concrete interpretation from provided numbers.\n"
        "- Explain trade-offs: service level vs working capital vs margin risk.\n"
        "- Call out contradictions in the data when present and propose mitigation.\n"
        "- Make it feel like a document a senior buyer would actually present upward.\n\n"
        f"Metro: {context.metro}\n"
        f"DC: {context.dc_name}\n"
        f"Week: {context.brief_date.isoformat()}\n"
        f"KPI Snapshot: {json.dumps(kpis)}\n"
        f"Signal Drivers: {json.dumps(drivers)}\n"
        f"SKU Decision Rows: {json.dumps(sku_rows)}\n"
    )


def _generate_brief_text(context: BriefContext, generate_brief: bool) -> tuple[str, str]:
    if not generate_brief:
        return _compose_structured_brief(context), "deterministic-preview"

    prompt = _llm_prompt(context)
    try:
        text, model = _gemini_generate(prompt)
        return text, f"gemini ({model})"
    except (ValueError, HTTPError, URLError, TimeoutError, json.JSONDecodeError) as gemini_error:
        if isinstance(gemini_error, HTTPError):
            gemini_reason = f"gemini-http-{gemini_error.code}"
        else:
            gemini_reason = f"gemini-{type(gemini_error).__name__.lower()}"
        try:
            return _ollama_generate(prompt), f"ollama-fallback ({gemini_reason})"
        except (ValueError, HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            return _compose_structured_brief(context), f"deterministic-fallback ({gemini_reason})"


def _build_response(metro: str, force_refresh: bool, generate_brief: bool) -> BriefResponse:
    context = _build_city_context(metro)
    cache_key = f"weekly:{context.metro}:{context.brief_date.isoformat()}"

    if generate_brief and not force_refresh:
        with _WEEKLY_BRIEF_CACHE_LOCK:
            cached = _WEEKLY_BRIEF_CACHE.get(cache_key)
        if cached:
            cached_payload = cached.get("payload")
            if isinstance(cached_payload, BriefResponse):
                hit = cached_payload.model_copy(deep=True)
                hit.cache_hit = True
                return hit

    brief_text, provider = _generate_brief_text(context, generate_brief=generate_brief)
    response = BriefResponse(
        brief_date=context.brief_date,
        generated_at=datetime.now(timezone.utc),
        model_version="brief-v2-city",
        provider=provider,
        cache_hit=False,
        brief_text=brief_text,
        context=context,
    )

    if generate_brief and provider.startswith("gemini"):
        with _WEEKLY_BRIEF_CACHE_LOCK:
            _WEEKLY_BRIEF_CACHE[cache_key] = {
                "cached_at": datetime.now(timezone.utc),
                "payload": response.model_copy(deep=True),
            }

    return response


def _compute_real_estate_heatmap(
    *,
    year: int | None,
    compare_year: int | None,
    limit: int,
    scope: Literal["seed", "national"],
) -> RealEstateHeatmapResponse:
    target_year = year or (date.today().year - 2)
    baseline_year = compare_year or (target_year - 1)
    requested_limit = max(1, min(limit, 45000))

    api_key = os.getenv("CENSUS_API_KEY")
    resolved_year = target_year
    resolved_compare_year = baseline_year

    if scope == "national":
        workspace_root = Path(__file__).resolve().parents[3]
        centroid_cache_path = workspace_root / "data" / "zcta_centroids.csv"
        points, warnings, resolved = build_national_real_estate_heatmap(
            year=target_year,
            compare_year=baseline_year,
            api_key=api_key,
            limit=requested_limit,
            centroid_cache_path=centroid_cache_path,
        )
        resolved_year = resolved.year
        resolved_compare_year = resolved.compare_year
    else:
        points, warnings = build_real_estate_heatmap(
            year=target_year,
            compare_year=baseline_year,
            api_key=api_key,
            limit=requested_limit,
        )

    mode: Literal["live", "fallback"] = "live"
    notes = [
        "Primary source: Census ACS DP04 tenure fields with ACS5 enrichments.",
        "Geography: ZIP Code Tabulation Areas (ZCTAs), not USPS ZIP delivery routes.",
    ]
    if scope == "national":
        notes.append("National scope uses all available ZCTAs with Gazetteer centroids.")
    if resolved_year != target_year or resolved_compare_year != baseline_year:
        notes.append(
            f"Requested years {target_year}/{baseline_year} were adjusted to available ACS years {resolved_year}/{resolved_compare_year}."
        )

    if not points:
        points = build_fallback_heatmap(year=target_year, limit=requested_limit)
        mode = "fallback"
        notes.append("Live Census fetch unavailable; deterministic fallback has been served.")

    if warnings:
        notes.append(f"Partial fetch warnings: {', '.join(warnings[:6])}")

    return RealEstateHeatmapResponse(
        generated_at=datetime.now(timezone.utc),
        year=resolved_year,
        compare_year=resolved_compare_year,
        point_count=len(points),
        mode=mode,
        notes=notes,
        points=[RealEstateHeatmapPoint(**point) for point in points],
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", model_version="brief-v1", database_ready=True, cache_ready=True)


@app.get("/api/briefs/weekly", response_model=BriefResponse)
def weekly_brief(
    metro: str = "Dallas",
    force_refresh: bool = False,
    generate_brief: bool = False,
) -> BriefResponse:
    return _build_response(metro=metro, force_refresh=force_refresh, generate_brief=generate_brief)


@app.post("/api/briefs/weekly", response_model=BriefResponse)
def weekly_brief_post(
    metro: str = "Dallas",
    force_refresh: bool = False,
    generate_brief: bool = False,
) -> BriefResponse:
    return _build_response(metro=metro, force_refresh=force_refresh, generate_brief=generate_brief)


@app.get("/api/signals/real-estate-heatmap", response_model=RealEstateHeatmapResponse)
def real_estate_heatmap(
    year: int | None = None,
    compare_year: int | None = None,
    limit: int = 500,
    scope: Literal["seed", "national"] = "seed",
) -> RealEstateHeatmapResponse:
    return _compute_real_estate_heatmap(
        year=year,
        compare_year=compare_year,
        limit=limit,
        scope=scope,
    )


@app.get("/api/signals/real-estate-heatmap/live", response_model=RealEstateHeatmapResponse)
def real_estate_heatmap_live(
    year: int | None = None,
    compare_year: int | None = None,
    limit: int = 5000,
    scope: Literal["seed", "national"] = "national",
    cache_ttl_minutes: int = 60,
    force_refresh: bool = False,
) -> RealEstateHeatmapResponse:
    # ACS updates on a scheduled release cadence; this endpoint keeps polling live data
    # while shielding clients from expensive full fetches on every request.
    ttl_seconds = max(0, min(cache_ttl_minutes, 1440)) * 60
    cache_key = f"{scope}:{year}:{compare_year}:{limit}"
    now = datetime.now(timezone.utc)

    if not force_refresh and ttl_seconds > 0:
        with _LIVE_HEATMAP_CACHE_LOCK:
            cached = _LIVE_HEATMAP_CACHE.get(cache_key)
        if cached:
            cached_at = cached.get("cached_at")
            payload = cached.get("payload")
            if isinstance(cached_at, datetime) and isinstance(payload, RealEstateHeatmapResponse):
                age_seconds = max(0, int((now - cached_at).total_seconds()))
                if age_seconds <= ttl_seconds:
                    result = payload.model_copy(deep=True)
                    result.notes.append(f"Live cache hit ({age_seconds}s old).")
                    return result

    result = _compute_real_estate_heatmap(
        year=year,
        compare_year=compare_year,
        limit=limit,
        scope=scope,
    )
    result.notes.append("Live Census refresh executed.")

    with _LIVE_HEATMAP_CACHE_LOCK:
        _LIVE_HEATMAP_CACHE[cache_key] = {
            "cached_at": now,
            "payload": result.model_copy(deep=True),
        }

    return result


@app.get("/api/signals/scored-real-estate-heatmap", response_model=RealEstateHeatmapResponse)
def scored_real_estate_heatmap(limit: int = 2000) -> RealEstateHeatmapResponse:
    requested_limit = max(1, min(limit, 45000))
    workspace_root = Path(__file__).resolve().parents[3]
    full_csv_path = workspace_root / "data" / "scored_real_estate_demand_full.csv"
    csv_path = full_csv_path if full_csv_path.exists() else workspace_root / "data" / "scored_real_estate_demand.csv"

    points, warnings = load_scored_heatmap_from_csv(csv_path=csv_path, limit=requested_limit)
    mode: Literal["live", "fallback"] = "live"
    notes = [
        "Primary source: scored model output from scored_real_estate_demand.csv.",
        "Geography: ZIP Code Tabulation Areas (ZCTAs), using latitude/longitude from the scored CSV when available.",
    ]

    if not points:
        points = build_fallback_heatmap(year=date.today().year, limit=requested_limit)
        mode = "fallback"
        notes.append("Scored CSV unavailable; deterministic fallback has been served.")

    if warnings:
        notes.append(f"CSV parse warnings: {', '.join(warnings[:6])}")

    return RealEstateHeatmapResponse(
        generated_at=datetime.now(timezone.utc),
        year=date.today().year,
        compare_year=date.today().year - 1,
        point_count=len(points),
        mode=mode,
        notes=notes,
        points=[RealEstateHeatmapPoint(**point) for point in points],
    )


@app.get("/api/signals/timeline/options", response_model=TimelineOptionsResponse)
def signal_timeline_options() -> TimelineOptionsResponse:
    return TimelineOptionsResponse(
        generated_at=datetime.now(timezone.utc),
        period_options=_timeline_period_options(),
        sku_options=_build_timeline_options(),
    )


@app.get("/api/signals/timeline", response_model=TimelineResponse)
def signal_timeline(
    sku_id: str,
    period_days: int = 30,
) -> TimelineResponse:
    return _build_signal_timeline(sku_id=sku_id, period_days=period_days)


@app.get("/api/simulations/options", response_model=SimulationOptionsResponse)
def simulation_options(dc: str = "ALL") -> SimulationOptionsResponse:
    return SimulationOptionsResponse(
        generated_at=datetime.now(timezone.utc),
        sku_options=_build_simulation_options(dc=dc),
    )


@app.get("/api/simulations/early-catch", response_model=SimulationResponse)
def simulation_early_catch(
    sku_id: str,
    metro: str | None = None,
    horizon_days: int = 60,
    baseline_lag_days: int = 10,
    earlier_by_days: int = 5,
    margin_rate: float = 0.42,
) -> SimulationResponse:
    return _build_early_catch_simulation(
        sku_id=sku_id,
        metro=metro,
        horizon_days=horizon_days,
        baseline_lag_days=baseline_lag_days,
        earlier_by_days=earlier_by_days,
        margin_rate=margin_rate,
    )
