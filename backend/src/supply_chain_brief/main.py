from __future__ import annotations

import os
from datetime import date, datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Literal

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
    week_summary: str
    urgent_skus: list[BriefSKU]
    overstock_skus: list[BriefSKU]
    watch_skus: list[BriefSKU]


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


app = FastAPI(title="Supply Chain Brief Backend", version="0.1.0")

_LIVE_HEATMAP_CACHE: dict[str, dict[str, object]] = {}
_LIVE_HEATMAP_CACHE_LOCK = Lock()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


def _build_response() -> BriefResponse:
    brief_date = date.today()
    context = BriefContext(
        brief_date=brief_date,
        week_summary="Signals indicate one urgent stockout risk, one overstock risk, and one housing-permit watch item.",
        urgent_skus=[
            BriefSKU(
                sku_id="PB-BLANKET-42",
                product_name="Throw Blanket, Cognac",
                brand="Pottery Barn",
                category="Bedding",
                current_stock=6200,
                on_order=0,
                lead_time_days=70,
                days_of_supply=34.2,
                risk_level="STOCKOUT_RISK",
                forecast_demand_60d=18400,
                demand_shortfall=12200,
                primary_signal="google_trends",
                signal_detail="Search volume up 840% in 7 days.",
                recommended_action="Expedite supplementary order now.",
            )
        ],
        overstock_skus=[
            BriefSKU(
                sku_id="PB-PILLOW-71",
                product_name="Decorative Pillow, Sage",
                brand="Pottery Barn",
                category="Decor",
                current_stock=4200,
                on_order=800,
                lead_time_days=56,
                days_of_supply=89.0,
                risk_level="OVERSTOCK_RISK",
                forecast_demand_60d=920,
                demand_shortfall=0,
                primary_signal="google_trends",
                signal_detail="Search declining 23% over 8 weeks.",
                recommended_action="Pause replenishment and evaluate markdown.",
            )
        ],
        watch_skus=[
            BriefSKU(
                sku_id="PB-BED-FRAME-33",
                product_name="King Bedroom Set",
                brand="Pottery Barn",
                category="Furniture",
                current_stock=860,
                on_order=240,
                lead_time_days=68,
                days_of_supply=54.4,
                risk_level="WATCH",
                forecast_demand_60d=1320,
                demand_shortfall=220,
                primary_signal="housing_permit",
                signal_detail="Phoenix permits up 34% MoM.",
                recommended_action="Pre-position inventory to Arizona DC.",
            )
        ],
    )
    brief_text = (
        f"WEEKLY DEMAND INTELLIGENCE BRIEF — Week of {brief_date:%Y-%m-%d}\n\n"
        "URGENT ACTION\n"
        "1. PB-BLANKET-42: demand acceleration indicates a likely shortfall. Expedite supplementary order.\n\n"
        "OVERSTOCK WARNING\n"
        "1. PB-PILLOW-71: trend decay detected. Pause replenishment and evaluate markdown trigger.\n\n"
        "WATCH LIST\n"
        "1. PB-BED-FRAME-33: housing permits suggest demand lift in 60-90 days.\n"
    )
    return BriefResponse(
        brief_date=brief_date,
        generated_at=datetime.now(timezone.utc),
        model_version="brief-v1",
        provider="deterministic",
        cache_hit=False,
        brief_text=brief_text,
        context=context,
    )


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
def weekly_brief() -> BriefResponse:
    return _build_response()


@app.post("/api/briefs/weekly", response_model=BriefResponse)
def weekly_brief_post() -> BriefResponse:
    return _build_response()


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
