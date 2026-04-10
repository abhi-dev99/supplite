"""
generate_synthetic_data_v2.py
=============================
Synthetic data pipeline for the Supply Chain Sees the Future hackathon.

Changes from v1:
  - 30 SKUs (down from 84), biased PB/WE
  - Daily granularity (365 days) instead of weekly (104 weeks)
  - Each SKU has data for ALL 11 metro cities
  - Census B19013 median household income per metro
  - US holiday calendar with pre-holiday search ramps
  - Composite scoring: sales_velocity 40%, income+RE 25%, holiday_search 20%, base_search 15%
  - Scenarios A-K (11 named) + R (random/routine)

Output files (all in ../data/):
  sku_catalog.csv          30 rows
  sku_daily_signals.csv    ~120k rows (30 SKUs x 11 metros x 365 days)
  sku_inventory.csv        330 rows  (30 SKUs x 11 metros snapshot)
  metro_income.csv         11 rows
  frontend_data.json       Pre-computed for dashboard
"""

import csv
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEED = 42
NUM_DAYS = 365
START_DATE = date(2025, 4, 11)
END_DATE = date(2026, 4, 10)

# Scoring weights (user-specified)
W_SALES_VELOCITY = 0.40
W_INCOME_RE = 0.25
W_HOLIDAY_SEARCH = 0.20
W_BASE_SEARCH = 0.15

# Income threshold for "premium buyer territory"
INCOME_PREMIUM_THRESHOLD = 120_000  # USD

# ---------------------------------------------------------------------------
# 11 Metro cities with Census B19013 median household income (ACS 2024 est.)
# and realistic zip-code-level samples, plus DC assignments
# ---------------------------------------------------------------------------
METROS = [
    {
        "name": "Atlanta",
        "state": "GA",
        "median_income": 82_100,
        "sample_zips": ["30301", "30305", "30309", "30318", "30324"],
        "dc": "Braselton DC",
        "lat": 33.749,
        "lng": -84.388,
        "baseline_permits": 2800,
        "permit_growth": 0.015,
    },
    {
        "name": "Chicago",
        "state": "IL",
        "median_income": 78_300,
        "sample_zips": ["60601", "60611", "60614", "60657", "60610"],
        "dc": "Olive Branch DC",
        "lat": 41.878,
        "lng": -87.630,
        "baseline_permits": 3200,
        "permit_growth": 0.005,
    },
    {
        "name": "Dallas",
        "state": "TX",
        "median_income": 74_600,
        "sample_zips": ["75201", "75204", "75205", "75225", "75230"],
        "dc": "Dallas DC",
        "lat": 32.777,
        "lng": -96.797,
        "baseline_permits": 5600,
        "permit_growth": 0.022,
    },
    {
        "name": "Denver",
        "state": "CO",
        "median_income": 105_200,
        "sample_zips": ["80202", "80205", "80209", "80210", "80218"],
        "dc": "Denver Hub",
        "lat": 39.739,
        "lng": -104.990,
        "baseline_permits": 2100,
        "permit_growth": 0.018,
    },
    {
        "name": "Houston",
        "state": "TX",
        "median_income": 67_200,
        "sample_zips": ["77002", "77005", "77006", "77019", "77027"],
        "dc": "Dallas DC",
        "lat": 29.760,
        "lng": -95.370,
        "baseline_permits": 4800,
        "permit_growth": 0.020,
    },
    {
        "name": "Los Angeles",
        "state": "CA",
        "median_income": 83_400,
        "sample_zips": ["90001", "90024", "90036", "90048", "90210"],
        "dc": "City of Industry DC",
        "lat": 34.052,
        "lng": -118.244,
        "baseline_permits": 3400,
        "permit_growth": 0.008,
    },
    {
        "name": "Miami",
        "state": "FL",
        "median_income": 59_600,
        "sample_zips": ["33101", "33125", "33130", "33131", "33139"],
        "dc": "Pompano Beach Hub",
        "lat": 25.762,
        "lng": -80.192,
        "baseline_permits": 3800,
        "permit_growth": 0.025,
    },
    {
        "name": "New York",
        "state": "NY",
        "median_income": 117_400,
        "sample_zips": ["10001", "10011", "10013", "10021", "10028"],
        "dc": "South Brunswick DC",
        "lat": 40.713,
        "lng": -74.006,
        "baseline_permits": 4200,
        "permit_growth": 0.006,
    },
    {
        "name": "Phoenix",
        "state": "AZ",
        "median_income": 72_800,
        "sample_zips": ["85001", "85003", "85004", "85006", "85016"],
        "dc": "Litchfield Park DC",
        "lat": 33.449,
        "lng": -112.074,
        "baseline_permits": 6200,
        "permit_growth": 0.028,
    },
    {
        "name": "San Francisco",
        "state": "CA",
        "median_income": 136_700,
        "sample_zips": ["94102", "94103", "94107", "94110", "94114"],
        "dc": "Tracy DC",
        "lat": 37.775,
        "lng": -122.419,
        "baseline_permits": 1800,
        "permit_growth": 0.004,
    },
    {
        "name": "Seattle",
        "state": "WA",
        "median_income": 120_600,
        "sample_zips": ["98101", "98102", "98103", "98105", "98109"],
        "dc": "Tracy DC",
        "lat": 47.606,
        "lng": -122.332,
        "baseline_permits": 2400,
        "permit_growth": 0.012,
    },
]

METRO_NAMES = [m["name"] for m in METROS]

# ---------------------------------------------------------------------------
# US Holiday Calendar (2025-2026 window)
# ---------------------------------------------------------------------------
HOLIDAYS = [
    # 2025 holidays
    {"name": "Memorial Day", "date": date(2025, 5, 26), "ramp_days": 7, "peak_mult": 1.3, "categories": ["Outdoor", "Furniture", "Decor"]},
    {"name": "Independence Day", "date": date(2025, 7, 4), "ramp_days": 7, "peak_mult": 1.2, "categories": ["Outdoor", "Kitchen", "Entertaining"]},
    {"name": "Labor Day", "date": date(2025, 9, 1), "ramp_days": 7, "peak_mult": 1.25, "categories": ["Outdoor", "Furniture", "Bedding"]},
    {"name": "Halloween", "date": date(2025, 10, 31), "ramp_days": 14, "peak_mult": 1.15, "categories": ["Decor", "Entertaining"]},
    {"name": "Thanksgiving", "date": date(2025, 11, 27), "ramp_days": 21, "peak_mult": 1.6, "categories": ["Kitchen", "Entertaining", "Decor", "Furniture"]},
    {"name": "Christmas", "date": date(2025, 12, 25), "ramp_days": 35, "peak_mult": 2.0, "categories": ["Kitchen", "Decor", "Bedding", "Lighting", "Furniture", "Entertaining", "Accessories"]},
    {"name": "Presidents Day", "date": date(2026, 2, 16), "ramp_days": 7, "peak_mult": 1.15, "categories": ["Furniture", "Bedding"]},
    {"name": "Mothers Day", "date": date(2026, 5, 10), "ramp_days": 14, "peak_mult": 1.4, "categories": ["Decor", "Kitchen", "Bedding", "Accessories", "Lighting"]},
    # Easter 2026 (April 5)
    {"name": "Easter", "date": date(2026, 4, 5), "ramp_days": 10, "peak_mult": 1.2, "categories": ["Decor", "Entertaining", "Kitchen"]},
]

def get_holiday_effect(d: date, category: str) -> tuple[float, str]:
    """Return (search_multiplier, holiday_name) for a given date and category."""
    best_mult = 1.0
    best_name = ""
    for h in HOLIDAYS:
        if category not in h["categories"]:
            continue
        days_before = (h["date"] - d).days
        if 0 <= days_before <= h["ramp_days"]:
            # Ramp up: multiplier increases linearly as we approach the holiday
            progress = 1.0 - (days_before / h["ramp_days"])
            mult = 1.0 + (h["peak_mult"] - 1.0) * progress
            if mult > best_mult:
                best_mult = mult
                best_name = h["name"]
        elif -3 <= days_before < 0:
            # Post-holiday falloff (3 days after)
            falloff = 1.0 + (h["peak_mult"] - 1.0) * max(0, 1.0 + days_before / 3)
            if falloff > best_mult:
                best_mult = falloff
                best_name = h["name"]
    return best_mult, best_name


# ---------------------------------------------------------------------------
# 30 SKU definitions
# ---------------------------------------------------------------------------
# Scenarios:
#   A = viral_spike         (search explosion, stockout risk)
#   B = silent_overstock    (trend peaked, demand fading, excess inventory)
#   C = housing_leading     (permit spike predicts furniture demand)
#   D = steady_ok           (control/baseline, no action needed)
#   E = seasonal_surge      (holiday-driven spike)
#   F = multi_signal        (search + permits + income all converge)
#   G = post_peak_overstock (was hot, now overstocked post-holiday)
#   H = sudden_collapse     (demand drops sharply, cancel orders)
#   I = slow_burn           (gradual growth over months)
#   J = flash_pan           (1-week spike then back to baseline)
#   K = holiday_gifting     (only spikes during gifting holidays)
#   R = routine             (normal demand, no special pattern)

SKUS = [
    # ---- Pottery Barn (12) ----
    {"id": "PB-BLANKET-42", "name": "Throw Blanket, Cognac", "brand": "Pottery Barn", "category": "Bedding", "price": 89.00, "cost": 38.50, "lead_time": 70, "baseline_daily": 18, "scenario": "A", "home_metro": "Los Angeles"},
    {"id": "PB-PILLOW-71", "name": "Decorative Pillow, Sage Green", "brand": "Pottery Barn", "category": "Decor", "price": 65.00, "cost": 24.00, "lead_time": 56, "baseline_daily": 14, "scenario": "B", "home_metro": "New York"},
    {"id": "PB-BED-FRAME-33", "name": "Bedroom Set, King", "brand": "Pottery Barn", "category": "Furniture", "price": 1899.00, "cost": 820.00, "lead_time": 68, "baseline_daily": 5, "scenario": "C", "home_metro": "Phoenix"},
    {"id": "PB-SOFA-88", "name": "Sectional Sofa, Ivory", "brand": "Pottery Barn", "category": "Furniture", "price": 3499.00, "cost": 1450.00, "lead_time": 84, "baseline_daily": 3, "scenario": "F", "home_metro": "San Francisco"},
    {"id": "PB-QUILT-15", "name": "Handstitched Quilt, Ivory", "brand": "Pottery Barn", "category": "Bedding", "price": 299.00, "cost": 125.00, "lead_time": 56, "baseline_daily": 10, "scenario": "G", "home_metro": "Chicago"},
    {"id": "PB-MIRROR-22", "name": "Oversized Wall Mirror, Gold", "brand": "Pottery Barn", "category": "Decor", "price": 449.00, "cost": 185.00, "lead_time": 63, "baseline_daily": 7, "scenario": "I", "home_metro": "Dallas"},
    {"id": "PB-DINSET-09", "name": "Farmhouse Dining Table, Oak", "brand": "Pottery Barn", "category": "Furniture", "price": 2299.00, "cost": 980.00, "lead_time": 77, "baseline_daily": 4, "scenario": "R", "home_metro": "Atlanta"},
    {"id": "PB-RUG-44", "name": "Hand-Knotted Area Rug, 8x10", "brand": "Pottery Barn", "category": "Decor", "price": 1299.00, "cost": 540.00, "lead_time": 70, "baseline_daily": 3, "scenario": "R", "home_metro": "Denver"},
    {"id": "PB-LAMP-61", "name": "Ceramic Table Lamp, White", "brand": "Pottery Barn", "category": "Lighting", "price": 189.00, "cost": 78.00, "lead_time": 42, "baseline_daily": 12, "scenario": "R", "home_metro": "Houston"},
    {"id": "PB-CANDLE-77", "name": "Luxury Candle Set, Cedar", "brand": "Pottery Barn", "category": "Decor", "price": 79.00, "cost": 28.00, "lead_time": 35, "baseline_daily": 22, "scenario": "K", "home_metro": "New York"},
    {"id": "PB-PLANTER-30", "name": "Indoor Planter, Terracotta", "brand": "Pottery Barn", "category": "Outdoor", "price": 129.00, "cost": 48.00, "lead_time": 42, "baseline_daily": 9, "scenario": "R", "home_metro": "Miami"},
    {"id": "PB-THROW-55", "name": "Cashmere Throw, Oatmeal", "brand": "Pottery Barn", "category": "Bedding", "price": 249.00, "cost": 105.00, "lead_time": 56, "baseline_daily": 8, "scenario": "D", "home_metro": "Seattle"},

    # ---- West Elm (8) ----
    {"id": "WE-LAMP-19", "name": "Arc Floor Lamp, Brass", "brand": "West Elm", "category": "Lighting", "price": 399.00, "cost": 165.00, "lead_time": 49, "baseline_daily": 8, "scenario": "D", "home_metro": "Chicago"},
    {"id": "WE-SOFA-23", "name": "Mid-Century Sofa, Velvet Blue", "brand": "West Elm", "category": "Furniture", "price": 1899.00, "cost": 780.00, "lead_time": 70, "baseline_daily": 4, "scenario": "R", "home_metro": "Los Angeles"},
    {"id": "WE-RUG-15", "name": "Geometric Area Rug, 6x9", "brand": "West Elm", "category": "Decor", "price": 299.00, "cost": 120.00, "lead_time": 42, "baseline_daily": 6, "scenario": "G", "home_metro": "Atlanta"},
    {"id": "WE-SHELF-31", "name": "Floating Wall Shelf, Walnut", "brand": "West Elm", "category": "Furniture", "price": 149.00, "cost": 58.00, "lead_time": 35, "baseline_daily": 15, "scenario": "J", "home_metro": "Denver"},
    {"id": "WE-DUVET-40", "name": "Linen Duvet Cover, Sand", "brand": "West Elm", "category": "Bedding", "price": 199.00, "cost": 82.00, "lead_time": 49, "baseline_daily": 11, "scenario": "R", "home_metro": "San Francisco"},
    {"id": "WE-CHAIR-52", "name": "Accent Chair, Boucle", "brand": "West Elm", "category": "Furniture", "price": 799.00, "cost": 330.00, "lead_time": 63, "baseline_daily": 5, "scenario": "R", "home_metro": "New York"},
    {"id": "WE-PLNTR-18", "name": "Ceramic Planter Set, Speckled", "brand": "West Elm", "category": "Outdoor", "price": 89.00, "cost": 32.00, "lead_time": 28, "baseline_daily": 16, "scenario": "E", "home_metro": "Miami"},
    {"id": "WE-CLOCK-66", "name": "Oversized Wall Clock, Black", "brand": "West Elm", "category": "Decor", "price": 129.00, "cost": 48.00, "lead_time": 35, "baseline_daily": 10, "scenario": "R", "home_metro": "Phoenix"},

    # ---- Williams Sonoma (5) ----
    {"id": "WS-MIXER-05", "name": "Stand Mixer, Heritage Red", "brand": "Williams Sonoma", "category": "Kitchen", "price": 449.00, "cost": 185.00, "lead_time": 49, "baseline_daily": 12, "scenario": "E", "home_metro": "Dallas"},
    {"id": "WS-KNIFE-60", "name": "Chef Knife Set, Damascus", "brand": "Williams Sonoma", "category": "Kitchen", "price": 349.00, "cost": 145.00, "lead_time": 42, "baseline_daily": 8, "scenario": "K", "home_metro": "San Francisco"},
    {"id": "WS-DUTCH-64", "name": "Dutch Oven, Le Creuset Blue", "brand": "Williams Sonoma", "category": "Kitchen", "price": 399.00, "cost": 200.00, "lead_time": 42, "baseline_daily": 7, "scenario": "R", "home_metro": "Seattle"},
    {"id": "WS-WINE-65", "name": "Crystal Wine Glass Set", "brand": "Williams Sonoma", "category": "Entertaining", "price": 129.00, "cost": 45.00, "lead_time": 35, "baseline_daily": 14, "scenario": "R", "home_metro": "Houston"},
    {"id": "WS-BOARD-68", "name": "Artisan Cheese Board, Olive", "brand": "Williams Sonoma", "category": "Entertaining", "price": 89.00, "cost": 32.00, "lead_time": 28, "baseline_daily": 18, "scenario": "H", "home_metro": "Atlanta"},

    # ---- Pottery Barn Kids (3) ----
    {"id": "PBK-CRIB-12", "name": "Convertible Crib, White", "brand": "Pottery Barn Kids", "category": "Furniture", "price": 699.00, "cost": 295.00, "lead_time": 56, "baseline_daily": 3, "scenario": "C", "home_metro": "Denver"},
    {"id": "PBK-BUNK-22", "name": "Bunk Bed, Natural Wood", "brand": "Pottery Barn Kids", "category": "Furniture", "price": 1299.00, "cost": 540.00, "lead_time": 63, "baseline_daily": 2, "scenario": "H", "home_metro": "Phoenix"},
    {"id": "PBK-QUILT-08", "name": "Kids Quilt Set, Rainbow", "brand": "Pottery Barn Kids", "category": "Bedding", "price": 149.00, "cost": 58.00, "lead_time": 42, "baseline_daily": 8, "scenario": "R", "home_metro": "Dallas"},

    # ---- Rejuvenation (2) ----
    {"id": "RJ-PENDANT-11", "name": "Industrial Pendant, Matte Black", "brand": "Rejuvenation", "category": "Lighting", "price": 329.00, "cost": 135.00, "lead_time": 49, "baseline_daily": 5, "scenario": "I", "home_metro": "Seattle"},
    {"id": "RJ-SCONCE-04", "name": "Brass Wall Sconce, Pair", "brand": "Rejuvenation", "category": "Lighting", "price": 249.00, "cost": 98.00, "lead_time": 42, "baseline_daily": 7, "scenario": "R", "home_metro": "Los Angeles"},
]

# Scenario labels for readability
SCENARIO_LABELS = {
    "A": "viral_spike",
    "B": "silent_overstock",
    "C": "housing_leading",
    "D": "steady_ok",
    "E": "seasonal_surge",
    "F": "multi_signal",
    "G": "post_peak_overstock",
    "H": "sudden_collapse",
    "I": "slow_burn",
    "J": "flash_pan",
    "K": "holiday_gifting",
    "R": "routine",
}

# ---------------------------------------------------------------------------
# Seasonality curves
# ---------------------------------------------------------------------------
def home_furnishings_seasonality(d: date) -> float:
    """NRF home furnishings index approximation."""
    monthly = {
        1: 0.82, 2: 0.85, 3: 0.95, 4: 1.00, 5: 1.02,
        6: 0.88, 7: 0.85, 8: 0.90, 9: 0.98, 10: 1.15,
        11: 1.30, 12: 1.25,
    }
    return monthly.get(d.month, 1.0)

def outdoor_seasonality(d: date) -> float:
    monthly = {
        1: 0.40, 2: 0.55, 3: 1.20, 4: 1.40, 5: 1.35,
        6: 1.10, 7: 0.95, 8: 0.80, 9: 0.65, 10: 0.55,
        11: 0.45, 12: 0.40,
    }
    return monthly.get(d.month, 1.0)

def kitchen_seasonality(d: date) -> float:
    monthly = {
        1: 0.75, 2: 0.78, 3: 0.82, 4: 0.88, 5: 1.05,
        6: 0.85, 7: 0.80, 8: 0.82, 9: 0.90, 10: 1.05,
        11: 1.45, 12: 1.50,
    }
    return monthly.get(d.month, 1.0)

def get_seasonality(d: date, category: str) -> float:
    if category == "Outdoor":
        return outdoor_seasonality(d)
    elif category in ("Kitchen", "Entertaining"):
        return kitchen_seasonality(d)
    else:
        return home_furnishings_seasonality(d)

# ---------------------------------------------------------------------------
# Metro demand modulation
# ---------------------------------------------------------------------------
def metro_demand_factor(metro: dict, sku: dict) -> float:
    """
    Modulate baseline demand by metro characteristics.
    High-income metros buy more premium products.
    Home metro gets a 1.5x boost.
    """
    income = metro["median_income"]
    price = sku["price"]

    # Income affinity: premium products sell better in high-income metros
    if price >= 500:
        # High-ticket: strong income correlation
        income_factor = min(1.4, max(0.5, income / 100_000))
    elif price >= 150:
        # Mid-ticket: moderate income correlation
        income_factor = min(1.2, max(0.7, income / 90_000))
    else:
        # Low-ticket: weak income correlation
        income_factor = min(1.1, max(0.85, income / 80_000))

    # Home metro boost
    home_boost = 1.5 if metro["name"] == sku["home_metro"] else 1.0

    # Population-proxy normalization (larger metros sell more baseline)
    pop_proxies = {
        "New York": 1.4, "Los Angeles": 1.3, "Chicago": 1.1, "Dallas": 1.05,
        "Houston": 1.0, "Phoenix": 0.95, "San Francisco": 1.15, "Seattle": 1.0,
        "Atlanta": 0.95, "Miami": 0.9, "Denver": 0.85,
    }
    pop_factor = pop_proxies.get(metro["name"], 1.0)

    return income_factor * home_boost * pop_factor


# ---------------------------------------------------------------------------
# Daily sales generator per scenario
# ---------------------------------------------------------------------------
def generate_daily_sales(
    rng: random.Random,
    sku: dict,
    metro: dict,
    dates: list[date],
) -> list[int]:
    """Generate 365-day sales series for a SKU in a specific metro."""
    scenario = sku["scenario"]
    baseline = sku["baseline_daily"]
    category = sku["category"]
    mfactor = metro_demand_factor(metro, sku)
    is_home = metro["name"] == sku["home_metro"]

    sales = []
    for i, d in enumerate(dates):
        day_frac = i / len(dates)
        season = get_seasonality(d, category)
        holiday_mult, _ = get_holiday_effect(d, category)

        # Scenario-specific modulation
        if scenario == "A":  # viral_spike
            # Influencer event around day 320 (~ March 2026)
            event_day = 320
            dist = i - event_day
            if dist < -14:
                trend = 1.0
            elif -14 <= dist < 0:
                trend = 1.0 + (14 + dist) / 14 * 0.3  # pre-buzz
            elif 0 <= dist < 7:
                trend = 2.5 + dist * 0.3 if is_home else 1.8 + dist * 0.15
            elif 7 <= dist < 21:
                trend = max(1.3, 4.0 - (dist - 7) * 0.15) if is_home else max(1.1, 2.5 - (dist - 7) * 0.08)
            else:
                trend = max(1.1, 1.3 - (dist - 21) * 0.01)

        elif scenario == "B":  # silent_overstock
            # Peaked around day 200, declining since
            peak_day = 200
            if i < peak_day - 60:
                trend = 1.0 + (i / (peak_day - 60)) * 0.8
            elif i < peak_day:
                trend = 1.8 + (i - peak_day + 60) / 60 * 0.4
            else:
                decay = max(0.35, 1.0 - (i - peak_day) / 300)
                trend = 2.2 * decay

        elif scenario == "C":  # housing_leading
            # Permits spike around day 250, sales follow 60 days later (~day 310)
            permit_spike_day = 250
            sales_response_day = permit_spike_day + 60
            if i < sales_response_day:
                trend = 1.0
            elif i < sales_response_day + 30:
                progress = (i - sales_response_day) / 30
                boost = 0.5 if is_home else 0.2
                trend = 1.0 + progress * boost
            else:
                boost = 0.5 if is_home else 0.2
                trend = 1.0 + boost

        elif scenario == "D":  # steady_ok
            trend = 1.0

        elif scenario == "E":  # seasonal_surge
            # Extra amplification during holiday season (already in season+holiday)
            trend = 1.0
            season = 1.0 + (season - 1.0) * 1.5
            holiday_mult = 1.0 + (holiday_mult - 1.0) * 1.8

        elif scenario == "F":  # multi_signal
            # All signals converge upward starting day 280
            convergence_day = 280
            if i < convergence_day:
                trend = 1.0
            else:
                progress = min(1.0, (i - convergence_day) / 60)
                # Stronger in high-income metros
                income_boost = 1.0 if metro["median_income"] >= INCOME_PREMIUM_THRESHOLD else 0.5
                trend = 1.0 + progress * 0.6 * income_boost

        elif scenario == "G":  # post_peak_overstock
            # Was hot during holiday 2025, now declining
            xmas_day = (date(2025, 12, 25) - START_DATE).days  # ~259
            if i < xmas_day - 30:
                trend = 1.0 + max(0, (i - (xmas_day - 60)) / 30) * 0.8
            elif i < xmas_day:
                trend = 1.8
            elif i < xmas_day + 14:
                trend = 1.8 - (i - xmas_day) / 14 * 0.8
            else:
                trend = max(0.4, 1.0 - (i - xmas_day - 14) / 200 * 0.6)

        elif scenario == "H":  # sudden_collapse
            # Sharp drop at day 300
            collapse_day = 300
            if i < collapse_day:
                trend = 1.0 + rng.gauss(0, 0.05)
            elif i < collapse_day + 14:
                trend = max(0.15, 1.0 - (i - collapse_day) / 14 * 0.85)
            else:
                trend = 0.15 + rng.gauss(0, 0.03)

        elif scenario == "I":  # slow_burn
            trend = 1.0 + day_frac * 0.6

        elif scenario == "J":  # flash_pan
            # 1-week spike around day 270, then back
            spike_center = 270
            dist = abs(i - spike_center)
            if dist < 4:
                spike = 2.5 - dist * 0.4 if is_home else 1.8 - dist * 0.2
                trend = max(1.0, spike)
            else:
                trend = 1.0

        elif scenario == "K":  # holiday_gifting
            # Minimal baseline, only holiday_mult drives sales
            trend = 0.6  # Low baseline
            holiday_mult = 1.0 + (holiday_mult - 1.0) * 2.5  # Amplify holidays

        else:  # R = routine
            trend = 1.0 + rng.gauss(0, 0.03)

        noise = rng.gauss(1.0, 0.10)
        value = baseline * mfactor * season * holiday_mult * trend * noise

        # Day-of-week effect: weekends ~20% higher for retail
        dow = d.weekday()
        if dow >= 5:  # Saturday, Sunday
            value *= 1.2

        sales.append(max(0, round(value)))

    return sales


# ---------------------------------------------------------------------------
# Signal generators
# ---------------------------------------------------------------------------
def generate_search_index(
    rng: random.Random,
    sales: list[int],
    dates: list[date],
    sku: dict,
    metro: dict,
) -> list[float]:
    """Google Trends search index (0-100), correlated to upcoming sales with 7-14 day lead."""
    max_sale = max(max(sales), 1)
    trends = []
    is_home = metro["name"] == sku["home_metro"]

    for i, d in enumerate(dates):
        # Look ahead 7-10 days
        future_idx = min(i + 10, len(sales) - 1)
        future_sale = sales[future_idx]

        base = (future_sale / max_sale) * 60 + rng.gauss(0, 4)

        # Holiday search prediction: search rises BEFORE holiday
        holiday_mult, _ = get_holiday_effect(d, sku["category"])
        if holiday_mult > 1.0:
            base *= min(1.8, holiday_mult)

        # Home metro gets more search volume
        if is_home:
            base *= 1.3

        trends.append(max(0, min(100, round(base, 1))))

    return trends


def generate_housing_permits(
    rng: random.Random,
    metro: dict,
    dates: list[date],
) -> list[int]:
    """
    Housing permits for a metro — pure metro-level economic indicator.

    Returns one value per day, but values repeat (are constant) within each
    calendar month.  This matches real Census Building Permits Survey cadence
    (monthly release, not daily).

    Scenario-specific effects (C, F) are NOT applied here; they live in the
    scoring layer so that raw permit data stays identical for every SKU in the
    same metro.
    """
    # --- Step 1: compute one permit value per calendar month ---------------
    from collections import OrderedDict
    monthly_permits: OrderedDict[tuple[int, int], int] = OrderedDict()

    for i, d in enumerate(dates):
        key = (d.year, d.month)
        if key in monthly_permits:
            continue  # already computed for this month

        # Use mid-month day index for trend calculation
        mid_month_day = i + 14  # approximate mid-month
        month_offset = mid_month_day / 30.44
        base_trend = 1.0 + metro["permit_growth"] * month_offset

        # Construction seasonality
        cs = {
            1: 0.65, 2: 0.70, 3: 0.90, 4: 1.10, 5: 1.20,
            6: 1.25, 7: 1.20, 8: 1.15, 9: 1.05, 10: 0.90,
            11: 0.75, 12: 0.60,
        }.get(d.month, 1.0)

        noise = rng.gauss(1.0, 0.05)
        val = metro["baseline_permits"] * base_trend * cs * noise
        monthly_permits[key] = max(0, round(val))

    # --- Step 2: repeat monthly value for every day in that month ---------
    permits = []
    for d in dates:
        permits.append(monthly_permits[(d.year, d.month)])

    return permits


# ---------------------------------------------------------------------------
# Composite scoring
# ---------------------------------------------------------------------------
def compute_composite_score(
    sales: list[int],
    search: list[float],
    permits: list[int],
    metro_income: int,
    dates: list[date],
    category: str,
    day_idx: int,
    scenario: str = "R",
    is_home_metro: bool = False,
) -> dict:
    """
    Compute the composite demand risk score for a given day.

    Weights:
      sales_velocity:  40%
      income + RE:     25%
      holiday_search:  20%
      base_search:     15%

    Scenario C/F get an RE boost at scoring level (not in raw data) so
    that the raw housing_permits stay identical for every SKU in the metro.

    Returns dict with sub-scores and composite.
    """
    # --- Sales velocity sub-score (0-100) ---
    if day_idx >= 30:
        recent_7d = sum(sales[day_idx - 6:day_idx + 1]) / 7
        prior_7d = sum(sales[day_idx - 13:day_idx - 6]) / 7
        prior_30d = sum(sales[day_idx - 29:day_idx + 1]) / 30
        prior_30d_before = sum(sales[max(0, day_idx - 59):max(1, day_idx - 29)]) / 30

        # WoW velocity
        wow_vel = (recent_7d - prior_7d) / max(prior_7d, 0.1) * 100
        # MoM velocity
        mom_vel = (prior_30d - prior_30d_before) / max(prior_30d_before, 0.1) * 100

        # Normalize to 0-100 (clamp at -100 to +200)
        sales_score = min(100, max(0, (wow_vel + 100) / 3))
        sales_vel_7d = round(wow_vel, 1)
        sales_vel_30d = round(mom_vel, 1)
    else:
        sales_score = 50  # neutral
        sales_vel_7d = 0.0
        sales_vel_30d = 0.0

    # --- Income + Real Estate sub-score (0-100) ---
    # Income component: higher income = higher score for premium
    income_norm = min(1.0, metro_income / INCOME_PREMIUM_THRESHOLD)
    income_component = income_norm * 50  # max 50 from income

    # RE component: permit velocity
    if day_idx >= 30:
        recent_permits = sum(permits[day_idx - 29:day_idx + 1]) / 30
        prior_permits = sum(permits[max(0, day_idx - 59):max(1, day_idx - 29)]) / 30
        permit_vel = (recent_permits - prior_permits) / max(prior_permits, 1) * 100
        permit_vel_30d = round(permit_vel, 1)
        # Positive permit velocity = positive signal, normalized
        re_component = min(50, max(0, (permit_vel + 20) / 40 * 50))
    else:
        re_component = 25
        permit_vel_30d = 0.0

    # Scenario-aware RE boost (applied at scoring, not raw data)
    # Scenario C (housing_leading) in home metro: permits are THE signal
    scenario_re_boost = 0
    if scenario == "C" and is_home_metro and day_idx >= 250:
        # Progressive boost as the housing leading indicator fires
        progress = min(1.0, (day_idx - 250) / 60)
        scenario_re_boost = 20 * progress  # up to +20 pts on RE score
    # Scenario F (multi_signal): convergence includes RE
    elif scenario == "F" and day_idx >= 280:
        progress = min(1.0, (day_idx - 280) / 60)
        scenario_re_boost = 12 * progress  # up to +12 pts

    # Correlation bonus: if BOTH income > threshold AND permits rising, extra boost
    if metro_income >= INCOME_PREMIUM_THRESHOLD and day_idx >= 30:
        if permit_vel_30d > 5:
            correlation_bonus = 10
        else:
            correlation_bonus = 0
    else:
        correlation_bonus = 0

    income_re_score = min(100, income_component + re_component + correlation_bonus + scenario_re_boost)

    # --- Holiday search sub-score (0-100) ---
    holiday_mult, holiday_name = get_holiday_effect(dates[day_idx], category)
    if holiday_mult > 1.0:
        # During holiday ramp, search prediction is high
        holiday_search_score = min(100, (holiday_mult - 1.0) * 100)
    else:
        holiday_search_score = 0.0

    # --- Base search sub-score (0-100) ---
    current_search = search[day_idx]
    base_search_score = current_search  # already 0-100

    if day_idx >= 7:
        search_vel_7d = round(
            (search[day_idx] - search[max(0, day_idx - 7)]) /
            max(search[max(0, day_idx - 7)], 0.1) * 100, 1
        )
    else:
        search_vel_7d = 0.0

    # --- Composite ---
    composite = (
        W_SALES_VELOCITY * sales_score +
        W_INCOME_RE * income_re_score +
        W_HOLIDAY_SEARCH * holiday_search_score +
        W_BASE_SEARCH * base_search_score
    )

    return {
        "composite_score": round(composite, 1),
        "sales_velocity_score": round(sales_score, 1),
        "income_re_score": round(income_re_score, 1),
        "holiday_search_score": round(holiday_search_score, 1),
        "base_search_score": round(base_search_score, 1),
        "sales_vel_7d": sales_vel_7d,
        "sales_vel_30d": sales_vel_30d,
        "search_vel_7d": search_vel_7d,
        "permit_vel_30d": permit_vel_30d,
        "holiday_flag": 1 if holiday_mult > 1.0 else 0,
        "holiday_name": holiday_name,
    }


# ---------------------------------------------------------------------------
# Risk classification
# ---------------------------------------------------------------------------
def classify_risk(
    sku: dict,
    metro: dict,
    sales: list[int],
    composite_scores: list[dict],
) -> tuple[str, str, str]:
    """
    Determine risk level from inventory metrics + composite score.
    Returns (risk_level, primary_signal, recommended_action).
    """
    # Recent sales pattern
    recent_avg = max(0.1, sum(sales[-30:]) / 30)
    daily_rate = recent_avg
    lead_time = sku["lead_time"]

    # Stock simulation: derive from scenario
    scenario = sku["scenario"]
    is_home = metro["name"] == sku["home_metro"]

    if scenario == "A" and is_home:
        stock = round(daily_rate * lead_time * 0.5)  # Understocked due to spike
        on_order = 0
        days_supply = stock / max(daily_rate, 0.1)
        return "STOCKOUT_RISK", f"Search spike +{round((sales[-1] / max(sales[-60], 1) - 1) * 100)}%", "Expedite supplementary order"

    elif scenario == "B" and is_home:
        stock = round(daily_rate * lead_time * 4.0)  # Overstocked from previous peak
        on_order = round(daily_rate * lead_time * 0.8)
        return "OVERSTOCK_RISK", "Demand declining, excess inventory", "Pause replenishment; evaluate markdown"

    elif scenario == "C" and is_home:
        stock = round(daily_rate * lead_time * 1.8)
        on_order = round(daily_rate * lead_time * 0.5)
        return "WATCH", f"Housing permits +34% in {metro['name']}", f"Pre-position to {metro['dc']}"

    elif scenario == "F" and is_home:
        stock = round(daily_rate * lead_time * 1.2)
        on_order = round(daily_rate * lead_time * 0.3)
        return "WATCH", "Multi-signal convergence detected", "Increase order quantity 20%"

    elif scenario == "G":
        stock = round(daily_rate * lead_time * 3.5)
        on_order = round(daily_rate * lead_time * 0.5)
        return "OVERSTOCK_RISK", "Post-holiday demand decline", "Cancel pending orders; markdown 15%"

    elif scenario == "H" and is_home:
        stock = round(daily_rate * lead_time * 2.0)
        on_order = round(daily_rate * lead_time * 0.8)
        return "STOCKOUT_RISK" if daily_rate < 1 else "WATCH", "Sudden demand collapse", "Halt all replenishment"

    elif scenario == "E":
        # During holiday = WATCH, off-season = OK
        latest_composite = composite_scores[-1] if composite_scores else {}
        if latest_composite.get("holiday_flag", 0) == 1:
            return "WATCH", f"Holiday surge: {latest_composite.get('holiday_name', 'Holiday')}", "Pre-stock for holiday demand"
        stock = round(daily_rate * lead_time * 1.5)
        on_order = round(daily_rate * lead_time * 0.4)
        return "OK", "Stable demand pattern", "Maintain current replenishment"

    else:
        # Routine: derive from metrics
        latest_composite = composite_scores[-1] if composite_scores else {"composite_score": 50}
        comp = latest_composite["composite_score"]
        if comp > 70:
            return "WATCH", f"Composite score elevated ({comp})", "Monitor closely"
        elif comp < 25:
            return "OVERSTOCK_RISK", "Low composite demand score", "Review replenishment cadence"
        else:
            return "OK", "Stable demand pattern", "Maintain current replenishment"


# ---------------------------------------------------------------------------
# Inventory snapshot builder
# ---------------------------------------------------------------------------
def build_inventory_snapshot(
    sku: dict,
    metro: dict,
    sales: list[int],
    composite_scores: list[dict],
) -> dict:
    """Build point-in-time inventory row."""
    recent_avg_daily = max(0.1, sum(sales[-30:]) / 30)
    lead_time = sku["lead_time"]
    scenario = sku["scenario"]
    is_home = metro["name"] == sku["home_metro"]

    rng = random.Random(hash(f"{sku['id']}-{metro['name']}"))

    # Stock levels depend on scenario
    if scenario == "A" and is_home:
        stock = round(recent_avg_daily * lead_time * 0.4)
        on_order = 0
    elif scenario == "B" and is_home:
        stock = round(recent_avg_daily * lead_time * 4.5)
        on_order = round(recent_avg_daily * lead_time * 0.8)
    elif scenario == "G":
        stock = round(recent_avg_daily * lead_time * 3.5)
        on_order = round(recent_avg_daily * lead_time * 0.5)
    elif scenario == "H" and is_home:
        stock = round(recent_avg_daily * lead_time * 2.5)
        on_order = round(recent_avg_daily * lead_time * 1.0)
    else:
        stock = round(recent_avg_daily * lead_time * rng.uniform(1.0, 2.2))
        on_order = round(recent_avg_daily * lead_time * rng.uniform(0.2, 0.7))

    days_supply = round((stock + on_order) / max(recent_avg_daily, 0.1))
    forecast_60d = round(recent_avg_daily * 60)

    risk_level, signal, action = classify_risk(sku, metro, sales, composite_scores)

    # Surge metrics
    if len(sales) >= 14:
        vel_7d = (sum(sales[-7:]) / 7 - sum(sales[-14:-7]) / 7) / max(sum(sales[-14:-7]) / 7, 0.1) * 100
    else:
        vel_7d = 0
    surge_score = round(abs(vel_7d), 1)
    if vel_7d > 20:
        surge_flag = "SURGING"
    elif vel_7d < -20:
        surge_flag = "FADING"
    else:
        surge_flag = "STEADY"

    return {
        "sku_id": sku["id"],
        "product_name": sku["name"],
        "brand": sku["brand"],
        "category": sku["category"],
        "price": sku["price"],
        "stock_on_hand": max(0, stock),
        "on_order": max(0, on_order),
        "lead_time_days": lead_time,
        "days_of_supply": days_supply,
        "avg_daily_sales": round(recent_avg_daily, 1),
        "risk_level": risk_level,
        "surge_score": surge_score,
        "surge_flag": surge_flag,
        "surge_delta_7d": round(vel_7d, 1),
        "primary_signal": signal,
        "recommended_action": action,
        "forecast_demand_60d": forecast_60d,
        "metro": metro["name"],
        "dc": metro["dc"],
        "scenario_type": sku["scenario"],
        "median_income": metro["median_income"],
    }


# ---------------------------------------------------------------------------
# CSV Writers
# ---------------------------------------------------------------------------
def write_sku_catalog(skus: list[dict], output: Path):
    fields = [
        "sku_id", "product_name", "brand", "category", "price", "cost_price",
        "lead_time_days", "home_metro", "scenario_type", "scenario_label",
    ]
    with open(output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for s in skus:
            w.writerow({
                "sku_id": s["id"],
                "product_name": s["name"],
                "brand": s["brand"],
                "category": s["category"],
                "price": s["price"],
                "cost_price": s["cost"],
                "lead_time_days": s["lead_time"],
                "home_metro": s["home_metro"],
                "scenario_type": s["scenario"],
                "scenario_label": SCENARIO_LABELS.get(s["scenario"], "unknown"),
            })


def write_metro_income(metros: list[dict], output: Path):
    fields = ["metro", "state", "median_income", "sample_zips", "dc", "lat", "lng"]
    with open(output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for m in metros:
            w.writerow({
                "metro": m["name"],
                "state": m["state"],
                "median_income": m["median_income"],
                "sample_zips": "|".join(m["sample_zips"]),
                "dc": m["dc"],
                "lat": m["lat"],
                "lng": m["lng"],
            })


def write_daily_signals(
    all_data: dict,
    dates: list[date],
    output: Path,
):
    """Write sku_daily_signals.csv — the big one."""
    fields = [
        "day_index", "date", "sku_id", "metro", "units_sold",
        "search_index", "housing_permits", "median_income",
        "holiday_flag", "holiday_name", "scenario_type",
        "sales_velocity_7d", "sales_velocity_30d",
        "search_velocity_7d", "permit_velocity_30d",
        "composite_score", "income_re_score", "holiday_search_score",
        "base_search_score", "sales_velocity_score",
    ]
    with open(output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for key, data in sorted(all_data.items()):
            sku_id, metro_name = key
            for i in range(len(dates)):
                cs = data["composites"][i]
                w.writerow({
                    "day_index": i,
                    "date": dates[i].isoformat(),
                    "sku_id": sku_id,
                    "metro": metro_name,
                    "units_sold": data["sales"][i],
                    "search_index": data["search"][i],
                    "housing_permits": data["permits"][i],
                    "median_income": data["income"],
                    "holiday_flag": cs["holiday_flag"],
                    "holiday_name": cs["holiday_name"],
                    "scenario_type": data["scenario"],
                    "sales_velocity_7d": cs["sales_vel_7d"],
                    "sales_velocity_30d": cs["sales_vel_30d"],
                    "search_velocity_7d": cs["search_vel_7d"],
                    "permit_velocity_30d": cs["permit_vel_30d"],
                    "composite_score": cs["composite_score"],
                    "income_re_score": cs["income_re_score"],
                    "holiday_search_score": cs["holiday_search_score"],
                    "base_search_score": cs["base_search_score"],
                    "sales_velocity_score": cs["sales_velocity_score"],
                })


def write_inventory(
    inventory_rows: list[dict],
    output: Path,
):
    fields = [
        "sku_id", "product_name", "brand", "category", "price",
        "stock_on_hand", "on_order", "lead_time_days", "days_of_supply",
        "avg_daily_sales", "risk_level", "surge_score", "surge_flag",
        "surge_delta_7d", "primary_signal", "recommended_action",
        "forecast_demand_60d", "metro", "dc", "scenario_type", "median_income",
    ]
    with open(output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in sorted(inventory_rows, key=lambda r: (r["sku_id"], r["metro"])):
            w.writerow(row)


# ---------------------------------------------------------------------------
# Frontend JSON builder
# ---------------------------------------------------------------------------
def build_frontend_json(
    all_data: dict,
    inventory_rows: list[dict],
    dates: list[date],
) -> dict:
    """Build pre-computed JSON for the dashboard, aggregated to weekly."""
    # SKU table: aggregate across all metros (use home metro for display)
    sku_table = []
    chart_data = {}

    # Group inventory by SKU, pick home metro for primary display
    inv_by_sku = {}
    for row in inventory_rows:
        sid = row["sku_id"]
        if sid not in inv_by_sku:
            inv_by_sku[sid] = []
        inv_by_sku[sid].append(row)

    for sku in SKUS:
        sid = sku["id"]
        rows = inv_by_sku.get(sid, [])
        # Find home metro row
        home_row = next((r for r in rows if r["metro"] == sku["home_metro"]), rows[0] if rows else None)
        if not home_row:
            continue

        # Aggregate stock across metros
        total_stock = sum(r["stock_on_hand"] for r in rows)
        total_on_order = sum(r["on_order"] for r in rows)
        total_daily = sum(r["avg_daily_sales"] for r in rows)
        overall_dos = round((total_stock + total_on_order) / max(total_daily, 0.1))

        sku_table.append({
            "id": sid,
            "name": f"{sku['brand']} {sku['name']}",
            "brand": sku["brand"],
            "category": sku["category"],
            "stock": total_stock,
            "onOrder": total_on_order,
            "daysOfSupply": overall_dos,
            "leadTimeDays": sku["lead_time"],
            "riskLevel": home_row["risk_level"],
            "signal": home_row["primary_signal"],
            "action": home_row["recommended_action"],
            "price": sku["price"],
        })

        # Chart data: aggregate home metro daily -> weekly (last 12 weeks)
        home_key = (sid, sku["home_metro"])
        if home_key in all_data:
            hd = all_data[home_key]
            # Last 84 days -> 12 weeks
            chart_entries = []
            start_day = max(0, NUM_DAYS - 84)
            for w in range(12):
                w_start = start_day + w * 7
                w_end = min(w_start + 7, NUM_DAYS)
                if w_start >= NUM_DAYS:
                    break
                week_sales = sum(hd["sales"][w_start:w_end])
                week_search = round(sum(hd["search"][w_start:w_end]) / max(1, w_end - w_start), 1)
                week_permits = round(sum(hd["permits"][w_start:w_end]) / max(1, w_end - w_start))

                label = f"W-{11 - w}" if w < 11 else "Current"
                chart_entries.append({
                    "name": label,
                    "sales": week_sales,
                    "search": week_search,
                    "permits": week_permits,
                })
            chart_data[sid] = chart_entries

    return {"skuTable": sku_table, "chartData": chart_data}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    rng = random.Random(SEED)
    dates = [START_DATE + timedelta(days=i) for i in range(NUM_DAYS)]

    print(f"Generating data for {NUM_DAYS} days ({START_DATE} to {END_DATE})")
    print(f"  SKUs: {len(SKUS)}")
    print(f"  Metros: {len(METROS)}")
    print(f"  Total rows: ~{len(SKUS) * len(METROS) * NUM_DAYS:,}")
    print(f"  Scoring: sales {W_SALES_VELOCITY:.0%} | income+RE {W_INCOME_RE:.0%} | holiday {W_HOLIDAY_SEARCH:.0%} | search {W_BASE_SEARCH:.0%}")
    print()

    # --- Pre-generate housing permits per metro (metro-level, not SKU-level)
    metro_permits = {}  # key: metro_name -> list[int] (365 daily values)
    for mi, metro in enumerate(METROS):
        metro_rng = random.Random(SEED + 9000 + mi)  # stable per-metro seed
        metro_permits[metro["name"]] = generate_housing_permits(metro_rng, metro, dates)
    print("  Housing permits generated (metro-level, monthly-repeated)")

    # Generate all data
    all_data = {}  # key: (sku_id, metro_name)
    inventory_rows = []

    for si, sku in enumerate(SKUS):
        for mi, metro in enumerate(METROS):
            # Seed per SKU-metro pair for reproducibility
            pair_rng = random.Random(SEED + si * 100 + mi)

            sales = generate_daily_sales(pair_rng, sku, metro, dates)
            search = generate_search_index(pair_rng, sales, dates, sku, metro)
            permits = metro_permits[metro["name"]]  # reuse metro-level permits

            # Composite scores for every day
            is_home = metro["name"] == sku["home_metro"]
            composites = []
            for day_idx in range(NUM_DAYS):
                cs = compute_composite_score(
                    sales, search, permits,
                    metro["median_income"], dates,
                    sku["category"], day_idx,
                    scenario=sku["scenario"],
                    is_home_metro=is_home,
                )
                composites.append(cs)

            key = (sku["id"], metro["name"])
            all_data[key] = {
                "sales": sales,
                "search": search,
                "permits": permits,
                "composites": composites,
                "income": metro["median_income"],
                "scenario": sku["scenario"],
            }

            # Build inventory snapshot
            inv = build_inventory_snapshot(sku, metro, sales, composites)
            inventory_rows.append(inv)

        print(f"  [{si + 1}/{len(SKUS)}] {sku['id']} ({sku['scenario']}: {SCENARIO_LABELS[sku['scenario']]})")

    # Write output files
    data_dir = Path(__file__).resolve().parent.parent / "data" / "new"
    data_dir.mkdir(exist_ok=True)

    print("\nWriting output files...")

    # 1. SKU catalog
    catalog_path = data_dir / "sku_catalog.csv"
    write_sku_catalog(SKUS, catalog_path)
    print(f"  sku_catalog.csv: {len(SKUS)} rows -> {catalog_path}")

    # 2. Metro income
    income_path = data_dir / "metro_income.csv"
    write_metro_income(METROS, income_path)
    print(f"  metro_income.csv: {len(METROS)} rows -> {income_path}")

    # 3. Daily signals (big file)
    signals_path = data_dir / "sku_daily_signals.csv"
    write_daily_signals(all_data, dates, signals_path)
    total_signal_rows = len(SKUS) * len(METROS) * NUM_DAYS
    print(f"  sku_daily_signals.csv: {total_signal_rows:,} rows -> {signals_path}")

    # 4. Inventory
    inv_path = data_dir / "sku_inventory.csv"
    write_inventory(inventory_rows, inv_path)
    print(f"  sku_inventory.csv: {len(inventory_rows)} rows -> {inv_path}")

    # 5. Frontend JSON
    frontend_json = build_frontend_json(all_data, inventory_rows, dates)
    json_path = data_dir / "frontend_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(frontend_json, f, indent=2)
    print(f"  frontend_data.json -> {json_path}")

    # Verification
    print("\n--- Verification ---")
    from collections import Counter
    risk_counts = Counter(r["risk_level"] for r in inventory_rows)
    total = len(inventory_rows)
    for level, count in sorted(risk_counts.items()):
        print(f"  {level}: {count} ({count / total * 100:.1f}%)")

    # Check metro distribution evenness
    metro_counts = Counter(r["metro"] for r in inventory_rows)
    print("\n  SKUs per metro:")
    for m, c in sorted(metro_counts.items()):
        print(f"    {m}: {c}")

    # Scenario coverage
    scenario_counts = Counter(s["scenario"] for s in SKUS)
    print("\n  Scenario coverage:")
    for sc, c in sorted(scenario_counts.items()):
        print(f"    {sc} ({SCENARIO_LABELS[sc]}): {c} SKUs")

    print(f"\n[OK] Dataset v2 generation complete. {len(SKUS)} SKUs x {len(METROS)} metros x {NUM_DAYS} days.")


if __name__ == "__main__":
    main()
