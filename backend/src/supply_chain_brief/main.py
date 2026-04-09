from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


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


app = FastAPI(title="Supply Chain Brief Backend", version="0.1.0")

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


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", model_version="brief-v1", database_ready=True, cache_ready=True)


@app.get("/api/briefs/weekly", response_model=BriefResponse)
def weekly_brief() -> BriefResponse:
    return _build_response()


@app.post("/api/briefs/weekly", response_model=BriefResponse)
def weekly_brief_post() -> BriefResponse:
    return _build_response()
