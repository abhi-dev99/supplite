#!/usr/bin/env python3
"""
Synthetic Data Generator v2 — Multi-Signal Demand Intelligence System
=====================================================================
Generates daily demand signals for 30 SKUs across 11 US metro markets.

Output:
    data/sku_daily_signals.csv   (30 × 11 × 365 = 120,450 rows)
    data/sku_inventory.csv       (30 × 11 = 330 rows — per-metro snapshot)
    data/sku_catalog.csv         (30 rows — product metadata)
    data/metro_profiles.csv      (11 rows — metro income/DC data)
    data/metro_dc_stores.csv     (store → metro → DC mapping)
    data/demand_intelligence.db  (SQLite with all tables)

Scoring weights:
    Sales velocity     40%   (actual demand, most trusted signal)
    Income + RE        25%   (high-income real estate = premium buyer)
    Holiday proximity  20%   (seasonal gift-giving prediction)
    Search velocity    15%   (social/trend signal, intentionally low)

Run:  python backend/scripts/generate_synthetic_data.py
"""
from __future__ import annotations

import csv
import math
import os
import random
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — SETUP
# ═══════════════════════════════════════════════════════════════════════════════
SEED = 42
random.seed(SEED)

WORKSPACE = Path(__file__).resolve().parents[2]
DATA_DIR = WORKSPACE / "data"
DATA_DIR.mkdir(exist_ok=True)

NUM_DAYS = 365
END_DATE = date(2026, 4, 10)       # "today" in hackathon
START_DATE = END_DATE - timedelta(days=NUM_DAYS - 1)  # 2025-04-11
DATES = [START_DATE + timedelta(days=i) for i in range(NUM_DAYS)]

INCOME_PREMIUM_THRESHOLD = 120_000  # USD — WSI premium customer threshold

# Scoring weights
W_SALES   = 0.40
W_INCOME_RE = 0.25
W_HOLIDAY = 0.20
W_SEARCH  = 0.15

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — METRO PROFILES (Census B19013 + DC mapping)
# ═══════════════════════════════════════════════════════════════════════════════
@dataclass
class MetroProfile:
    name: str
    median_income: int
    income_factor: float          # min(1.0, income / 120k)
    dc_name: str
    dc_lat: float
    dc_lon: float
    base_permits_monthly: int     # baseline monthly housing permits
    income_tier: str

METRO_PROFILES: dict[str, MetroProfile] = {}

_METRO_RAW = [
    # (name, median_income, dc_name, dc_lat, dc_lon, base_permits_monthly)
    ("San Francisco", 125_105, "Tracy DC",             37.7385, -121.4201, 250),
    ("Seattle",       109_389, "Tracy DC",             37.7385, -121.4201, 400),
    ("Denver",        106_878, "Denver Hub",           39.7392, -104.9848, 600),
    ("New York",      100_022, "South Brunswick DC",   40.3818, -74.5317,  300),
    ("Los Angeles",    95_821, "City of Industry DC",  34.0182, -117.9593, 500),
    ("Dallas",         91_207, "Dallas DC",            32.7762, -96.7968, 1100),
    ("Chicago",        89_918, "Olive Branch DC",      34.9617, -89.8295,  350),
    ("Atlanta",        89_691, "Braselton DC",         34.1092, -83.7626,  900),
    ("Phoenix",        89_610, "Litchfield Park DC",   33.4933, -112.3581, 1200),
    ("Houston",        64_813, "Dallas DC",            32.7762, -96.7968, 1000),
    ("Miami",          62_462, "Pompano Beach Hub",    26.2378, -80.1247,  500),
]

for name, inc, dc, dlat, dlon, bp in _METRO_RAW:
    factor = min(1.0, inc / INCOME_PREMIUM_THRESHOLD)
    tier = "Premium" if inc >= 120_000 else "High" if inc >= 100_000 else "Mid" if inc >= 85_000 else "Lower"
    METRO_PROFILES[name] = MetroProfile(name, inc, round(factor, 3), dc, dlat, dlon, bp, tier)

METROS = list(METRO_PROFILES.keys())  # 11 metros

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — SKU CATALOG (30 SKUs)
# ═══════════════════════════════════════════════════════════════════════════════
@dataclass
class SKU:
    sku_id: str
    product_name: str
    brand: str
    category: str
    price: float
    lead_time_days: int
    base_daily_sales: float   # national baseline units/day (before city adjustment)
    base_search: float        # Google Trends baseline (0-100)
    scenario_type: str        # A-J or R
    scenario_label: str

# fmt: off
ALL_SKUS: list[SKU] = [
    # ─── Pottery Barn (12) ───────────────────────────────────────────────
    SKU("PB-BLANKET-42", "Throw Blanket, Cognac",      "Pottery Barn", "Bedding",   89,  70, 18, 11, "A", "viral_spike"),
    SKU("PB-PILLOW-71",  "Decorative Pillow, Sage",    "Pottery Barn", "Decor",     65,  56, 21, 35, "B", "silent_overstock"),
    SKU("PB-BED-33",     "Bedroom Set, King",          "Pottery Barn", "Furniture", 1899,68,  5, 12, "C", "housing_leading"),
    SKU("PB-SOFA-88",    "Sectional Sofa, Ivory",      "Pottery Barn", "Furniture", 3499,84,  3, 14, "F", "multi_signal"),
    SKU("PB-DUVET-12",   "Linen Duvet Cover",          "Pottery Barn", "Bedding",   249, 49, 14, 20, "R", "random"),
    SKU("PB-DINING-14",  "Farmhouse Dining Table",     "Pottery Barn", "Furniture", 1699,70,  4, 10, "R", "random"),
    SKU("PB-MIRROR-16",  "Arched Wall Mirror",         "Pottery Barn", "Decor",     399, 42, 8,  15, "R", "random"),
    SKU("PB-CANDLE-18",  "Hearth Candle Set",          "Pottery Barn", "Decor",     79,  28, 25, 18, "R", "random"),
    SKU("PB-LAMP-20",    "Tripod Floor Lamp",          "Pottery Barn", "Lighting",  349, 56, 7,  12, "R", "random"),
    SKU("PB-BOOK-22",    "Modular Bookcase",           "Pottery Barn", "Furniture", 899, 63, 5,  9,  "R", "random"),
    SKU("PB-PATIO-24",   "Teak Patio Set",             "Pottery Barn", "Outdoor",   2499,84, 2,  8,  "R", "random"),
    SKU("PB-QUILT-26",   "Handstitched Quilt",         "Pottery Barn", "Bedding",   199, 42, 12, 16, "R", "random"),
    # ─── West Elm (8) ────────────────────────────────────────────────────
    SKU("WE-LAMP-19",    "Table Lamp, Brass",          "West Elm",     "Lighting",  179, 42, 10, 18, "D", "steady_ok"),
    SKU("WE-RUG-15",     "Area Rug, Geometric",        "West Elm",     "Decor",     299, 42, 8,  25, "G", "post_peak_overstock"),
    SKU("WE-SOFA-28",    "Mid-Century Sofa",           "West Elm",     "Furniture", 1799,70, 4,  14, "R", "random"),
    SKU("WE-DESK-30",    "Standing Desk, Walnut",      "West Elm",     "Furniture", 699, 49, 6,  12, "R", "random"),
    SKU("WE-ART-32",     "Gallery Art Print",          "West Elm",     "Decor",     149, 28, 15, 20, "R", "random"),
    SKU("WE-PENDANT-34", "Sculptural Pendant",         "West Elm",     "Lighting",  249, 42, 7,  10, "R", "random"),
    SKU("WE-BENCH-36",   "Entryway Storage Bench",     "West Elm",     "Furniture", 599, 49, 5,  11, "R", "random"),
    SKU("WE-THROW-38",   "Velvet Throw Pillow",        "West Elm",     "Decor",     45,  21, 30, 22, "R", "random"),
    # ─── Williams Sonoma (5) ─────────────────────────────────────────────
    SKU("WS-MIXER-05",   "Stand Mixer, Red",           "Williams Sonoma","Kitchen", 449, 49, 6,  22, "E", "seasonal_surge"),
    SKU("WS-KNIFE-40",   "Chef Knife Set",             "Williams Sonoma","Kitchen", 349, 35, 8,  14, "R", "random"),
    SKU("WS-COPPER-42",  "Copper Cookware Set",        "Williams Sonoma","Kitchen", 899, 56, 3,  9,  "R", "random"),
    SKU("WS-DUTCH-44",   "Dutch Oven, Cast Iron",      "Williams Sonoma","Kitchen", 299, 42, 10, 16, "R", "random"),
    SKU("WS-WINE-46",    "Crystal Wine Glass Set",     "Williams Sonoma","Entertaining",129,28,12,18, "R", "random"),
    # ─── Pottery Barn Kids (2) ───────────────────────────────────────────
    SKU("PBK-BUNK-22",   "Bunk Bed, White",            "Pottery Barn Kids","Furniture",1299,56,4,16,"H","sudden_collapse"),
    SKU("PBK-CRIB-48",   "Convertible Crib, Natural",  "Pottery Barn Kids","Furniture",799,49,5,12, "R", "random"),
    # ─── Rejuvenation (2) ────────────────────────────────────────────────
    SKU("RJ-PENDANT-11", "Industrial Pendant, Black",  "Rejuvenation", "Lighting",  329, 42, 3,  8,  "I", "slow_burn"),
    SKU("RJ-VANITY-50",  "Bathroom Vanity Light",      "Rejuvenation", "Lighting",  219, 35, 5,  10, "R", "random"),
    # ─── Mark & Graham (1) ───────────────────────────────────────────────
    SKU("MG-TOTE-07",    "Monogram Tote, Navy",        "Mark & Graham","Accessories",129,35, 5,  10, "J", "flash_pan"),
]
# fmt: on

SKU_MAP = {s.sku_id: s for s in ALL_SKUS}

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — HOLIDAY CALENDAR
# ═══════════════════════════════════════════════════════════════════════════════
def _build_holiday_factors() -> dict[date, float]:
    """Build a date → holiday_factor (0.0 – 1.0) map for the full 365-day range."""
    factors: dict[date, float] = {d: 0.02 for d in DATES}  # base = 0.02

    # Key US holidays with their peak factors and ramp-up windows
    holidays = [
        # (date, peak_factor, ramp_days_before, ramp_days_after)
        (date(2025, 5, 11),  0.60, 14, 0),   # Mother's Day 2025
        (date(2025, 5, 26),  0.40, 7, 0),    # Memorial Day 2025
        (date(2025, 6, 15),  0.55, 14, 0),   # Father's Day 2025
        (date(2025, 7, 4),   0.40, 7, 2),    # Independence Day 2025
        (date(2025, 9, 1),   0.35, 5, 0),    # Labor Day 2025
        (date(2025, 10, 31), 0.45, 14, 0),   # Halloween 2025
        (date(2025, 11, 27), 1.00, 21, 0),   # Thanksgiving 2025 (peak!)
        (date(2025, 11, 28), 1.00, 0, 0),    # Black Friday 2025
        (date(2025, 12, 1),  0.90, 0, 0),    # Cyber Monday 2025
        (date(2025, 12, 25), 0.95, 30, 0),   # Christmas 2025
        (date(2025, 12, 31), 0.50, 3, 0),    # New Year's Eve 2025
        (date(2026, 1, 1),   0.30, 0, 0),    # New Year's Day 2026
        (date(2026, 2, 14),  0.55, 14, 0),   # Valentine's Day 2026
        (date(2026, 2, 16),  0.30, 5, 0),    # Presidents Day 2026
        (date(2026, 4, 5),   0.40, 10, 0),   # Easter 2026
    ]

    for hdate, peak, ramp_before, ramp_after in holidays:
        for d in DATES:
            delta = (hdate - d).days
            if 0 <= delta <= ramp_before:
                # Ramp up: factor increases as we approach the holiday
                progress = 1.0 - (delta / max(ramp_before, 1))
                val = peak * (0.3 + 0.7 * progress)  # starts at 30% of peak
                factors[d] = max(factors[d], val)
            elif -ramp_after <= delta < 0:
                # Brief tail after holiday
                tail = 1.0 - (abs(delta) / max(ramp_after, 1))
                factors[d] = max(factors[d], peak * 0.3 * tail)

    # Special: Thanksgiving-Christmas sustained peak (Nov 15 – Dec 25)
    for d in DATES:
        if date(2025, 11, 15) <= d <= date(2025, 12, 25):
            # Sustained high: ramps from 0.6 to 1.0 around Thanksgiving, stays 0.8+ through Christmas
            day_in_season = (d - date(2025, 11, 15)).days
            total_days = 40  # Nov 15 to Dec 25
            # Peak around day 12-13 (Thanksgiving), stays high
            base_season = 0.65 + 0.35 * math.sin(math.pi * min(day_in_season, 20) / 20)
            factors[d] = max(factors[d], base_season)

    return factors

HOLIDAY_FACTORS = _build_holiday_factors()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def _income_sales_multiplier(metro: str, price: float) -> float:
    """Scale sales based on metro income and product price tier."""
    income = METRO_PROFILES[metro].median_income
    if price >= 1000:
        return max(0.4, min(1.6, income / 95000))
    elif price >= 300:
        return max(0.6, min(1.4, income / 95000))
    else:
        return max(0.8, min(1.2, income / 95000))

def _seasonal_outdoor_factor(d: date) -> float:
    """Outdoor furniture sells more in spring/summer."""
    month = d.month
    if month in (5, 6, 7, 8):
        return 1.5
    elif month in (4, 9):
        return 1.2
    elif month in (3, 10):
        return 1.0
    else:
        return 0.6

def _smooth_rise(day: int, start: int, tau: float = 10.0, max_val: float = 1.0) -> float:
    """Sigmoid-ish rise starting at 'start' day with time constant 'tau'."""
    if day < start:
        return 0.0
    return max_val * (1.0 - math.exp(-(day - start) / tau))

def _smooth_decay(day: int, start: int, tau: float = 15.0, start_val: float = 1.0) -> float:
    """Exponential decay starting at 'start' day."""
    if day < start:
        return start_val
    return start_val * math.exp(-(day - start) / tau)

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — SCENARIO SIGNAL GENERATORS
# ═══════════════════════════════════════════════════════════════════════════════
# Each returns (sales_multiplier, search_value, permits_override_or_None)
# for a given (day_index, metro).

def _scenario_A(day: int, metro: str, sku: SKU) -> tuple[float, float, float | None]:
    """Viral Spike: search explodes around day 309, sales follow 14 days later."""
    spike_day = 309  # ~8 weeks before end
    search_base = sku.base_search
    # Search spike is NATIONAL
    if day < spike_day:
        search = search_base + random.uniform(-2, 2)
        sales_m = 1.0
    else:
        ds = day - spike_day
        search = search_base + 83 * (1 - math.exp(-ds / 6))
        # Sales lag by 14 days, ramp slower
        if ds > 14:
            sales_m = 1.0 + 4.5 * (1 - math.exp(-(ds - 14) / 8))
        else:
            sales_m = 1.0 + 0.3 * (ds / 14)
    search += random.uniform(-1.5, 1.5)
    return sales_m, _clamp(search, 0, 100), None

def _scenario_B(day: int, metro: str, sku: SKU) -> tuple[float, float, float | None]:
    """Silent Overstock: trend peaked around day 180, fading since."""
    peak_day = 180
    search_base = sku.base_search
    if day < 120:
        # Rising phase
        progress = day / 120
        search = 15 + progress * 35 + random.uniform(-2, 2)
        sales_m = 0.5 + progress * 0.7
    elif day < peak_day:
        # Peak zone
        p = (day - 120) / (peak_day - 120)
        search = 50 + 22 * math.sin(p * math.pi) + random.uniform(-2, 2)
        sales_m = 1.2 + 0.3 * math.sin(p * math.pi)
    else:
        # Decline
        ds = day - peak_day
        search = max(8, 65 * math.exp(-ds / 80) + random.uniform(-2, 2))
        sales_m = max(0.2, 1.3 * math.exp(-ds / 90))
    return sales_m, _clamp(search, 0, 100), None

def _scenario_C(day: int, metro: str, sku: SKU) -> tuple[float, float, float | None]:
    """Housing Leading Indicator: permits climb in Phoenix, search stays flat."""
    search = sku.base_search + random.uniform(-2, 2)
    sales_m = 1.0
    # Permit spike is METRO-SPECIFIC (Phoenix only)
    permits_override = None
    if metro == "Phoenix" and day >= 270:
        ds = day - 270
        base = METRO_PROFILES["Phoenix"].base_permits_monthly
        permits_override = base + ds * 5.5 + random.uniform(-8, 8)
    return sales_m, _clamp(search, 0, 100), permits_override

def _scenario_D(day: int, metro: str, sku: SKU) -> tuple[float, float, float | None]:
    """Steady OK: everything normal everywhere."""
    search = sku.base_search + random.uniform(-3, 3)
    return 1.0, _clamp(search, 0, 100), None

def _scenario_E(day: int, metro: str, sku: SKU) -> tuple[float, float, float | None]:
    """Seasonal Holiday Surge: massive spike Thanksgiving-Christmas, cliff after."""
    d = DATES[day]
    hf = HOLIDAY_FACTORS[d]
    search = sku.base_search
    sales_m = 1.0

    # During the peak holiday season
    if date(2025, 11, 10) <= d <= date(2025, 12, 25):
        search = 22 + 58 * hf + random.uniform(-3, 3)
        sales_m = 1.0 + 2.8 * hf
    elif date(2025, 12, 26) <= d <= date(2026, 1, 7):
        # Post-holiday cliff
        ds = (d - date(2025, 12, 26)).days
        search = max(8, 30 * math.exp(-ds / 4) + random.uniform(-2, 2))
        sales_m = max(0.25, 0.8 * math.exp(-ds / 3))
    else:
        search += random.uniform(-3, 3)

    return sales_m, _clamp(search, 0, 100), None

def _scenario_F(day: int, metro: str, sku: SKU) -> tuple[float, float, float | None]:
    """Multi-Signal: search AND permits both rising (strongest in Phoenix)."""
    search = sku.base_search + random.uniform(-2, 2)
    sales_m = 1.0
    permits_override = None

    if day >= 260:
        ds = day - 260
        # Search rises nationally
        search = sku.base_search + ds * 0.6 + random.uniform(-2, 2)
        sales_m = 1.0 + ds * 0.015
        # Permits rise in Phoenix and Denver
        if metro in ("Phoenix", "Denver"):
            base = METRO_PROFILES[metro].base_permits_monthly
            permits_override = base + ds * 6 + random.uniform(-5, 5)
    return sales_m, _clamp(search, 0, 100), permits_override

def _scenario_G(day: int, metro: str, sku: SKU) -> tuple[float, float, float | None]:
    """Post-Peak Overstock: trend peaked 4+ months ago, still declining."""
    peak_day = 140
    if day < 100:
        progress = day / 100
        search = 15 + progress * 35 + random.uniform(-2, 2)
        sales_m = 0.5 + progress * 0.6
    elif day < peak_day:
        p = (day - 100) / (peak_day - 100)
        search = 50 + 35 * math.sin(p * math.pi) + random.uniform(-2, 2)
        sales_m = 1.1 + 0.7 * math.sin(p * math.pi)
    else:
        ds = day - peak_day
        search = max(5, 75 * math.exp(-ds / 70) + random.uniform(-2, 2))
        sales_m = max(0.15, 1.6 * math.exp(-ds / 80))
    return sales_m, _clamp(search, 0, 100), None

def _scenario_H(day: int, metro: str, sku: SKU) -> tuple[float, float, float | None]:
    """Sudden Collapse: sales healthy then abruptly drop (recall/competitor)."""
    collapse_day = 300
    search = sku.base_search + random.uniform(-2, 2)
    sales_m = 1.0
    if day >= collapse_day:
        ds = day - collapse_day
        # Search spikes briefly (people searching for alternatives/news)
        search = max(4, 50 * math.exp(-ds / 5) + random.uniform(-2, 2))
        sales_m = max(0.08, 0.9 * math.exp(-ds / 8))
    return sales_m, _clamp(search, 0, 100), None

def _scenario_I(day: int, metro: str, sku: SKU) -> tuple[float, float, float | None]:
    """Slow Burn: gradual upward trend over entire year."""
    growth = 1.0 + (day / NUM_DAYS) * 1.2  # doubles over the year
    search = min(80, sku.base_search * (growth ** 0.5) + random.uniform(-1, 1))
    sales_m = min(3.0, growth ** 0.6)
    return sales_m, _clamp(search, 0, 100), None

def _scenario_J(day: int, metro: str, sku: SKU) -> tuple[float, float, float | None]:
    """Flash in the Pan: spike that dies within 10 days."""
    flash_start = 310
    flash_peak = 315
    flash_end = 325
    search = sku.base_search + random.uniform(-2, 2)
    sales_m = 1.0
    if flash_start <= day < flash_peak:
        p = (day - flash_start) / (flash_peak - flash_start)
        search = sku.base_search + 60 * p + random.uniform(-2, 2)
        sales_m = 1.0 + 1.2 * p
    elif flash_peak <= day < flash_end:
        p = (day - flash_peak) / (flash_end - flash_peak)
        search = sku.base_search + 60 * (1 - p) + random.uniform(-2, 2)
        sales_m = 1.0 + 1.2 * (1 - p)
    return sales_m, _clamp(search, 0, 100), None

SCENARIO_FUNCS = {
    "A": _scenario_A, "B": _scenario_B, "C": _scenario_C, "D": _scenario_D,
    "E": _scenario_E, "F": _scenario_F, "G": _scenario_G, "H": _scenario_H,
    "I": _scenario_I, "J": _scenario_J,
}

# Random pattern types for R-type SKUs
_RANDOM_PATTERNS = ["steady", "gentle_up", "gentle_down", "mid_bump", "noisy_flat", "late_uptick"]
_SKU_RANDOM_PATTERN: dict[str, str] = {}
for s in ALL_SKUS:
    if s.scenario_type == "R":
        _SKU_RANDOM_PATTERN[s.sku_id] = random.choice(_RANDOM_PATTERNS)

def _scenario_R(day: int, metro: str, sku: SKU) -> tuple[float, float, float | None]:
    """Random patterns for filler SKUs."""
    pattern = _SKU_RANDOM_PATTERN[sku.sku_id]
    search = sku.base_search
    sales_m = 1.0
    t = day / NUM_DAYS  # 0 → 1

    if pattern == "steady":
        search += random.uniform(-3, 3)
    elif pattern == "gentle_up":
        trend = 1.0 + t * 0.5
        search = sku.base_search * trend * 0.8 + random.uniform(-2, 2)
        sales_m = trend * 0.9
    elif pattern == "gentle_down":
        trend = max(0.4, 1.0 - t * 0.4)
        search = sku.base_search * trend + random.uniform(-2, 2)
        sales_m = trend
    elif pattern == "mid_bump":
        bump_center = 180
        dist = abs(day - bump_center)
        bump = max(0, 1.0 - dist / 50) * 1.5
        search = sku.base_search * (1 + bump) + random.uniform(-2, 2)
        sales_m = 1.0 + bump * 0.5
    elif pattern == "noisy_flat":
        search += random.uniform(-6, 6)
        sales_m = random.uniform(0.7, 1.3)
    elif pattern == "late_uptick":
        if day > 310:
            uptick = (day - 310) * 0.02
            search = sku.base_search * (1 + uptick) + random.uniform(-2, 2)
            sales_m = 1.0 + uptick * 0.8
        else:
            search += random.uniform(-2, 2)

    return sales_m, _clamp(search, 0, 100), None

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — MAIN SIGNAL GENERATION
# ═══════════════════════════════════════════════════════════════════════════════
def generate_raw_signals() -> list[dict]:
    """Generate 120,450 rows of raw daily signals."""
    rows: list[dict] = []
    total = len(ALL_SKUS) * len(METROS) * NUM_DAYS
    count = 0

    for sku in ALL_SKUS:
        scenario_fn = SCENARIO_FUNCS.get(sku.scenario_type, _scenario_R)

        for metro_name in METROS:
            mp = METRO_PROFILES[metro_name]
            income_mult = _income_sales_multiplier(metro_name, sku.price)
            # Monthly permits baseline for this metro
            permits_base = mp.base_permits_monthly

            for day_idx in range(NUM_DAYS):
                d = DATES[day_idx]
                hf = HOLIDAY_FACTORS[d]

                # Get scenario-specific modifiers
                sales_m, search_val, permits_override = scenario_fn(day_idx, metro_name, sku)

                # ── Sales ──
                base = sku.base_daily_sales * income_mult * sales_m
                # Outdoor furniture gets seasonal adjustment
                if sku.category == "Outdoor":
                    base *= _seasonal_outdoor_factor(d)
                # Holiday boost for gift categories
                if sku.category in ("Kitchen", "Entertaining", "Accessories", "Bedding", "Decor", "Lighting"):
                    base *= (1.0 + hf * 0.5)
                # Add noise
                noise = random.uniform(0.85, 1.15)
                units_sold = max(0, round(base * noise))

                # ── Search (already computed by scenario) ──
                search_index = round(search_val, 1)

                # ── Housing Permits ──
                if permits_override is not None:
                    permits = max(0, round(permits_override))
                else:
                    # Month-level value with slight daily noise
                    month_noise = random.uniform(-15, 15)
                    permits = max(0, round(permits_base + month_noise))

                # ── Median Income (static per metro) ──
                median_income = mp.median_income

                # ── Income Factor ──
                income_factor = mp.income_factor

                rows.append({
                    "day_index": day_idx,
                    "date": d.isoformat(),
                    "sku_id": sku.sku_id,
                    "metro": metro_name,
                    "units_sold": units_sold,
                    "search_index": search_index,
                    "housing_permits": permits,
                    "median_income": median_income,
                    "income_factor": income_factor,
                    "holiday_factor": round(hf, 3),
                    "scenario_type": sku.scenario_type,
                })

                count += 1
                if count % 50000 == 0:
                    print(f"  Generated {count:,}/{total:,} rows ({100*count/total:.0f}%)")

    print(f"  Generated {count:,}/{total:,} rows (100%)")
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — POST-PROCESSING (Velocities & Surge Score)
# ═══════════════════════════════════════════════════════════════════════════════
def compute_velocities_and_scores(rows: list[dict]) -> list[dict]:
    """Compute rolling velocities and surge scores using pandas."""
    try:
        import pandas as pd
    except ImportError:
        print("  [WARN] pandas not available — skipping velocity computation")
        for r in rows:
            r.update({"sales_velocity_7d": 0, "sales_velocity_30d": 0,
                       "search_velocity_7d": 0, "search_velocity_30d": 0,
                       "permit_velocity_30d": 0, "surge_score": 0})
        return rows

    print("  Computing velocities with pandas...")
    df = pd.DataFrame(rows)
    df = df.sort_values(["sku_id", "metro", "day_index"]).reset_index(drop=True)

    # Group by (sku, metro) for rolling calculations
    grp = df.groupby(["sku_id", "metro"], sort=False)

    # Rolling averages
    df["sales_7d_avg"]  = grp["units_sold"].transform(lambda x: x.rolling(7, min_periods=1).mean())
    df["sales_7d_prev"] = grp["units_sold"].transform(lambda x: x.rolling(7, min_periods=1).mean().shift(7))
    df["sales_30d_avg"]  = grp["units_sold"].transform(lambda x: x.rolling(30, min_periods=1).mean())
    df["sales_30d_prev"] = grp["units_sold"].transform(lambda x: x.rolling(30, min_periods=1).mean().shift(30))

    df["search_7d_avg"]  = grp["search_index"].transform(lambda x: x.rolling(7, min_periods=1).mean())
    df["search_7d_prev"] = grp["search_index"].transform(lambda x: x.rolling(7, min_periods=1).mean().shift(7))
    df["search_30d_avg"]  = grp["search_index"].transform(lambda x: x.rolling(30, min_periods=1).mean())
    df["search_30d_prev"] = grp["search_index"].transform(lambda x: x.rolling(30, min_periods=1).mean().shift(30))

    df["permits_30d_avg"]  = grp["housing_permits"].transform(lambda x: x.rolling(30, min_periods=1).mean())
    df["permits_30d_prev"] = grp["housing_permits"].transform(lambda x: x.rolling(30, min_periods=1).mean().shift(30))

    # Velocities (% change)
    eps = 0.1  # avoid division by zero
    df["sales_velocity_7d"]  = ((df["sales_7d_avg"] - df["sales_7d_prev"]) / df["sales_7d_prev"].clip(lower=eps) * 100).round(1).fillna(0)
    df["sales_velocity_30d"] = ((df["sales_30d_avg"] - df["sales_30d_prev"]) / df["sales_30d_prev"].clip(lower=eps) * 100).round(1).fillna(0)
    df["search_velocity_7d"] = ((df["search_7d_avg"] - df["search_7d_prev"]) / df["search_7d_prev"].clip(lower=eps) * 100).round(1).fillna(0)
    df["search_velocity_30d"]= ((df["search_30d_avg"] - df["search_30d_prev"]) / df["search_30d_prev"].clip(lower=eps) * 100).round(1).fillna(0)
    df["permit_velocity_30d"]= ((df["permits_30d_avg"] - df["permits_30d_prev"]) / df["permits_30d_prev"].clip(lower=eps) * 100).round(1).fillna(0)

    # ── Surge Score Components ──
    # 1. Sales component (40%): normalize velocity to 0-100
    df["_sales_comp"] = df["sales_velocity_7d"].clip(-50, 200).apply(lambda v: max(0, min(100, (v + 50) / 250 * 100)))

    # 2. Income + Real Estate component (25%):
    #    Only high-income RE matters: permit_velocity × income_factor
    df["_re_raw"] = df["permit_velocity_30d"].clip(0, 100)  # only positive permit growth matters
    df["_income_re_comp"] = (df["_re_raw"] * df["income_factor"]).clip(0, 100)

    # 3. Holiday component (20%): directly from holiday_factor × 100
    df["_holiday_comp"] = (df["holiday_factor"] * 100).clip(0, 100)

    # 4. Search component (15%): normalize velocity to 0-100
    df["_search_comp"] = df["search_velocity_7d"].clip(-50, 200).apply(lambda v: max(0, min(100, (v + 50) / 250 * 100)))

    # Blended surge score
    df["surge_score"] = (
        W_SALES * df["_sales_comp"] +
        W_INCOME_RE * df["_income_re_comp"] +
        W_HOLIDAY * df["_holiday_comp"] +
        W_SEARCH * df["_search_comp"]
    ).round(1).clip(0, 100)

    # Rolling 7-day average sales (for inventory)
    df["rolling_7d_avg_sales"] = df["sales_7d_avg"].round(1)

    # Select final columns
    keep = [
        "day_index", "date", "sku_id", "metro",
        "units_sold", "search_index", "housing_permits", "median_income",
        "income_factor", "holiday_factor",
        "sales_velocity_7d", "sales_velocity_30d",
        "search_velocity_7d", "search_velocity_30d",
        "permit_velocity_30d",
        "rolling_7d_avg_sales", "surge_score", "scenario_type",
    ]
    df = df[keep]

    # Drop temp columns
    print(f"  Velocity & scoring complete. Shape: {df.shape}")
    return df.to_dict("records")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — INVENTORY GENERATION (330 rows)
# ═══════════════════════════════════════════════════════════════════════════════
def generate_inventory(signal_rows: list[dict]) -> list[dict]:
    """Build per-metro inventory snapshot from the latest signal data."""
    import pandas as pd
    df = pd.DataFrame(signal_rows)

    # Get latest day data
    latest = df[df["day_index"] == NUM_DAYS - 1].copy()
    prev_7d = df[df["day_index"] == NUM_DAYS - 8].copy()
    prev_30d = df[df["day_index"] == NUM_DAYS - 31].copy()

    inventory_rows = []

    for _, row in latest.iterrows():
        sku = SKU_MAP[row["sku_id"]]
        mp = METRO_PROFILES[row["metro"]]

        # Generate realistic stock levels per metro
        random.seed(hash(f"{sku.sku_id}_{row['metro']}") % 2**31)
        weekly_demand = row["rolling_7d_avg_sales"] * 7
        weeks_of_stock = random.uniform(3, 14)
        stock = max(10, int(weekly_demand * weeks_of_stock))
        on_order = int(weekly_demand * random.uniform(0, 3)) if random.random() > 0.3 else 0

        avg_daily = max(0.1, row["rolling_7d_avg_sales"])
        days_of_supply = round(stock / avg_daily, 1)

        # Surge direction
        surge_now = row["surge_score"]
        prev7 = prev_7d[(prev_7d["sku_id"] == row["sku_id"]) & (prev_7d["metro"] == row["metro"])]
        prev30 = prev_30d[(prev_30d["sku_id"] == row["sku_id"]) & (prev_30d["metro"] == row["metro"])]
        surge_7d_ago = prev7["surge_score"].values[0] if len(prev7) > 0 else surge_now
        surge_30d_ago = prev30["surge_score"].values[0] if len(prev30) > 0 else surge_now

        delta_7d = round(surge_now - surge_7d_ago, 1)
        delta_30d = round(surge_now - surge_30d_ago, 1)

        if delta_7d >= 15:
            surge_flag = "SURGING"
        elif delta_30d <= -10:
            surge_flag = "FADING"
        else:
            surge_flag = "STEADY"

        # Risk classification
        if days_of_supply < sku.lead_time_days and surge_flag == "SURGING":
            risk = "STOCKOUT_RISK"
        elif days_of_supply < sku.lead_time_days * 1.2:
            risk = "STOCKOUT_RISK"
        elif days_of_supply > sku.lead_time_days * 3 and surge_flag == "FADING":
            risk = "OVERSTOCK_RISK"
        elif days_of_supply > sku.lead_time_days * 2.5:
            risk = "OVERSTOCK_RISK"
        elif surge_flag in ("SURGING", "FADING"):
            risk = "WATCH"
        else:
            risk = "OK"

        # Demo overrides for scripted scenarios (apply only to their "hero" metro)
        DEMO_OVERRIDES = {
            ("PB-BLANKET-42", None):    ("STOCKOUT_RISK", "SURGING", "google_trends", "Search volume +840% in 7 days (viral)", "Expedite supplementary order for 12,200 units"),
            ("PB-PILLOW-71",  None):    ("OVERSTOCK_RISK","FADING",  "google_trends", "Search declining 23% over 8 weeks",     "Pause replenishment; evaluate 15% markdown"),
            ("PB-BED-33",     "Phoenix"):("WATCH",        "STEADY",  "housing_permit","Phoenix SFH permits +34% MoM",          "Pre-position 400 units to Arizona DC"),
            ("PB-SOFA-88",    "Phoenix"):("WATCH",        "SURGING", "multi_signal",  "Search +42% AND permits +28% MoM",      "Increase reorder quantity by 35%"),
            ("WE-RUG-15",     None):    ("OVERSTOCK_RISK","FADING",  "google_trends", "Trend peaked 4 months ago; declining",  "Cancel pending PO; begin markdown"),
            ("PBK-BUNK-22",   None):    ("OVERSTOCK_RISK","FADING",  "sales_collapse","Sales dropped 85% in 3 weeks",          "Halt replenishment; investigate root cause"),
        }

        primary_signal = "baseline"
        signal_detail = f"Surge score {surge_now:.0f}, {surge_flag.lower()}"
        action = "No action needed"

        for (sid, hero_metro), (r, sf, ps, sd, act) in DEMO_OVERRIDES.items():
            if sku.sku_id == sid and (hero_metro is None or row["metro"] == hero_metro):
                risk, surge_flag, primary_signal, signal_detail, action = r, sf, ps, sd, act
                break
        else:
            if sku.scenario_type == "E":
                hf = HOLIDAY_FACTORS[DATES[-1]]
                if hf > 0.5:
                    risk = "WATCH"
                    surge_flag = "SURGING"
                    primary_signal = "holiday_season"
                    signal_detail = "Entering peak holiday season"
                    action = "Verify holiday stock levels vs forecast"
            elif surge_flag == "SURGING":
                primary_signal = "demand_velocity"
                signal_detail = f"Sales velocity +{row['sales_velocity_7d']:.0f}% (7d)"
                action = "Monitor closely; consider early reorder"
            elif surge_flag == "FADING":
                primary_signal = "demand_decline"
                signal_detail = f"Sales velocity {row['sales_velocity_7d']:.0f}% (7d)"
                action = "Review inventory position"

        forecast_60d = int(avg_daily * 60)
        shortfall = max(0, forecast_60d - stock - on_order)

        inventory_rows.append({
            "sku_id": sku.sku_id,
            "metro": row["metro"],
            "product_name": sku.product_name,
            "brand": sku.brand,
            "category": sku.category,
            "price": sku.price,
            "stock_on_hand": stock,
            "on_order": on_order,
            "lead_time_days": sku.lead_time_days,
            "days_of_supply": days_of_supply,
            "rolling_7d_avg_sales": round(avg_daily, 1),
            "risk_level": risk,
            "surge_score": round(surge_now, 1),
            "surge_flag": surge_flag,
            "surge_delta_7d": delta_7d,
            "surge_delta_30d": delta_30d,
            "primary_signal": primary_signal,
            "signal_detail": signal_detail,
            "recommended_action": action,
            "forecast_demand_60d": forecast_60d,
            "demand_shortfall": shortfall,
            "dc": mp.dc_name,
            "median_income": mp.median_income,
            "income_factor": mp.income_factor,
            "scenario_type": sku.scenario_type,
        })

    random.seed(SEED)  # reset seed
    return inventory_rows


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — STORE → METRO → DC MAPPING
# ═══════════════════════════════════════════════════════════════════════════════
# State → Metro assignment for WSI stores
_STATE_TO_METRO = {
    "AL": "Atlanta","AZ": "Phoenix","AR": "Dallas","CO": "Denver",
    "CT": "New York","DC": "New York","DE": "New York","FL": "Miami",
    "GA": "Atlanta","HI": "Los Angeles","ID": "Seattle","IL": "Chicago",
    "IN": "Chicago","IA": "Chicago","KS": "Dallas","KY": "Atlanta",
    "LA": "Houston","MA": "New York","MD": "New York","ME": "New York",
    "MI": "Chicago","MN": "Chicago","MO": "Chicago","MS": "Atlanta",
    "NC": "Atlanta","NE": "Chicago","NH": "New York","NJ": "New York",
    "NM": "Phoenix","NV": "Los Angeles","NY": "New York","OH": "Chicago",
    "OK": "Dallas","OR": "Seattle","PA": "New York","RI": "New York",
    "SC": "Atlanta","TN": "Atlanta","TX": "Dallas","UT": "Denver",
    "VA": "New York","VT": "New York","WA": "Seattle","WI": "Chicago",
}
# Texas special: Houston stores → Houston metro
_TX_HOUSTON_CITIES = {"Houston", "Sugar Land", "Katy", "The Woodlands", "Pearland", "League City"}

# California split: lat > 36.5 → SFO, else → LA
_CA_SFO_CITIES = {
    "Corte Madera","Palo Alto","San Mateo","San Ramon","Santa Clara","Walnut Creek",
    "Sonoma","Vacaville","Roseville","Sacramento","San Jose",
}

def build_store_metro_mapping() -> list[dict]:
    """Build store → metro → DC mapping from the known WSI store list."""
    import json
    stores_path = WORKSPACE / "frontend" / "src" / "real_stores.json"
    if not stores_path.exists():
        # Fallback: use data.js inline — just produce empty mapping
        print("  [WARN] real_stores.json not found, generating partial store mapping")
        return [{"store_name": "Fallback", "store_city": "N/A", "store_state": "N/A",
                 "metro": "N/A", "dc_name": "N/A"}]

    with open(stores_path, "r", encoding="utf-8") as f:
        stores = json.load(f)

    rows = []
    for store in stores:
        name = store.get("name", "")
        city_raw = store.get("city", "")  # format: "Birmingham, AL"
        # Split "City, ST" into city and state
        parts = [p.strip() for p in city_raw.rsplit(",", 1)]
        city = parts[0] if parts else ""
        state = parts[1].upper() if len(parts) > 1 else ""

        # Determine metro
        if state == "TX" and city in _TX_HOUSTON_CITIES:
            metro = "Houston"
        elif state == "CA" and city in _CA_SFO_CITIES:
            metro = "San Francisco"
        elif state == "CA":
            metro = "Los Angeles"
        else:
            metro = _STATE_TO_METRO.get(state, "New York")

        dc = METRO_PROFILES[metro].dc_name
        rows.append({
            "store_name": name,
            "store_city": city,
            "store_state": state,
            "metro": metro,
            "dc_name": dc,
        })

    return rows


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 11 — OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════
def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        print(f"  [WARN] No rows for {path.name}")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    size_mb = path.stat().st_size / 1_048_576
    print(f"  -> {path.name}: {len(rows):,} rows ({size_mb:.1f} MB)")

def _load_sqlite(db_path: Path, table: str, rows: list[dict]) -> None:
    if not rows:
        return
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute(f"DROP TABLE IF EXISTS {table}")
    cols = list(rows[0].keys())
    c.execute(f"CREATE TABLE {table} ({', '.join(f'{col} TEXT' for col in cols)})")
    placeholders = ", ".join(["?"] * len(cols))
    for row in rows:
        c.execute(f"INSERT INTO {table} VALUES ({placeholders})", [str(row.get(col, "")) for col in cols])
    conn.commit()
    conn.close()
    print(f"  -> SQLite table '{table}': {len(rows):,} rows")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 12 — MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("SYNTHETIC DATA GENERATOR v2 — Demand Intelligence System")
    print("=" * 70)
    print(f"SKUs: {len(ALL_SKUS)} | Metros: {len(METROS)} | Days: {NUM_DAYS}")
    print(f"Total signal rows: {len(ALL_SKUS) * len(METROS) * NUM_DAYS:,}")
    print(f"Date range: {START_DATE} to {END_DATE}")
    print(f"Scoring: Sales {W_SALES*100:.0f}% | Income+RE {W_INCOME_RE*100:.0f}% | Holiday {W_HOLIDAY*100:.0f}% | Search {W_SEARCH*100:.0f}%")
    print()

    # 1. Generate raw signals
    print("[1/6] Generating raw signals...")
    raw = generate_raw_signals()

    # 2. Compute velocities & surge scores
    print("[2/6] Computing velocities & surge scores...")
    signals = compute_velocities_and_scores(raw)

    # 3. Generate inventory
    print("[3/6] Generating inventory snapshots...")
    inventory = generate_inventory(signals)

    # 4. Build catalog
    catalog = [
        {"sku_id": s.sku_id, "product_name": s.product_name, "brand": s.brand,
         "category": s.category, "price": s.price, "lead_time_days": s.lead_time_days,
         "scenario_type": s.scenario_type, "scenario_label": s.scenario_label}
        for s in ALL_SKUS
    ]

    # 5. Metro profiles
    metro_rows = [
        {"metro": m.name, "median_income": m.median_income, "income_tier": m.income_tier,
         "income_factor": m.income_factor, "dc_name": m.dc_name,
         "dc_lat": m.dc_lat, "dc_lon": m.dc_lon,
         "base_permits_monthly": m.base_permits_monthly}
        for m in METRO_PROFILES.values()
    ]

    # 6. Store mapping
    print("[4/6] Building store-metro-DC mapping...")
    store_map = build_store_metro_mapping()

    # Write outputs
    print("[5/6] Writing files...")
    db = DATA_DIR / "demand_intelligence.db"
    _write_csv(DATA_DIR / "sku_daily_signals.csv", signals)
    _write_csv(DATA_DIR / "sku_inventory.csv", inventory)
    _write_csv(DATA_DIR / "sku_catalog.csv", catalog)
    _write_csv(DATA_DIR / "metro_profiles.csv", metro_rows)
    _write_csv(DATA_DIR / "metro_dc_stores.csv", store_map)

    _load_sqlite(db, "sku_daily_signals", signals)
    _load_sqlite(db, "sku_inventory", inventory)
    _load_sqlite(db, "sku_catalog", catalog)
    _load_sqlite(db, "metro_profiles", metro_rows)
    _load_sqlite(db, "metro_dc_stores", store_map)

    # Verification
    print("\n[6/6] Verification...")
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")

    # Risk distribution
    risk_counts: dict[str, int] = {}
    for inv in inventory:
        risk_counts[inv["risk_level"]] = risk_counts.get(inv["risk_level"], 0) + 1
    print(f"\nRisk distribution ({len(inventory)} metro-SKU combos):")
    for r in ["STOCKOUT_RISK", "OVERSTOCK_RISK", "WATCH", "OK"]:
        print(f"  {r:<16} {risk_counts.get(r, 0):>4}")

    # Surge distribution
    surge_counts: dict[str, int] = {}
    for inv in inventory:
        surge_counts[inv["surge_flag"]] = surge_counts.get(inv["surge_flag"], 0) + 1
    print(f"\nSurge distribution:")
    for f in ["SURGING", "FADING", "STEADY"]:
        print(f"  {f:<10} {surge_counts.get(f, 0):>4}")

    # Metro coverage check
    metros_in_data = set(r["metro"] for r in signals)
    print(f"\nMetros in data: {len(metros_in_data)} (expected {len(METROS)})")

    # Demo scenario verification
    print(f"\nDemo scenario verification:")
    demo_skus = ["PB-BLANKET-42", "PB-PILLOW-71", "PB-BED-33", "WE-LAMP-19",
                 "WS-MIXER-05", "PB-SOFA-88", "WE-RUG-15", "PBK-BUNK-22",
                 "RJ-PENDANT-11", "MG-TOTE-07"]
    for sid in demo_skus:
        # Show first matching metro
        inv = next((r for r in inventory if r["sku_id"] == sid), None)
        if inv:
            print(f"  {sid:<16} {inv['risk_level']:<16} {inv['surge_flag']:<8} | {inv['signal_detail'][:50]}")

    print(f"\nDone! Files in {DATA_DIR}")


if __name__ == "__main__":
    main()
