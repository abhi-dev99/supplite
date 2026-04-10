from __future__ import annotations

import csv
import json
import os
import time
from datetime import date, datetime, timezone
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
    primary = (os.getenv("GEMINI_MODEL") or "gemini-1.5-flash").strip()
    fallbacks_raw = (os.getenv("GEMINI_MODEL_FALLBACKS") or "gemini-flash-latest,gemini-2.0-flash").strip()
    fallbacks = [part.strip() for part in fallbacks_raw.split(",") if part.strip()]

    models: list[str] = []
    for model in [primary, *fallbacks]:
        if model and model not in models:
            models.append(model)
    return models or ["gemini-1.5-flash"]


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
                "maxOutputTokens": 4096,
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
                with urlopen(request, timeout=45) as response:  # noqa: S310 - fixed trusted endpoint
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
    with urlopen(request, timeout=50) as response:  # noqa: S310 - local endpoint
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
