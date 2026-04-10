#!/usr/bin/env python3
"""
Synthetic data generator for the Multi-Signal Demand Intelligence System.
Generates realistic weekly sales, search, and housing-permit data for 60 SKUs
over 104 weeks (2 years).

Covers ALL scenarios needed for the hackathon demo:
  A. Viral spike (stockout risk)
  B. Silent overstock (trend fading)
  C. Housing-permit leading indicator (the differentiator)
  D. Steady/OK SKU (control)
  E. Seasonal product (holiday surge + post-holiday collapse)
  F. Multi-signal convergence (search + permits both fire)
  G. Post-peak overstock (trend peaked months ago, still ordering)
  H. Sudden demand collapse (abrupt drop, not gradual fade)
  I. Slow-burn growth (steady upward, not a spike)
  J. Flash-in-the-pan (spike that dies within 2 weeks)

Run:
    python backend/scripts/generate_synthetic_data.py

Output:
    data/sku_weekly_signals.csv    (60 SKUs × 104 weeks = 6,240 rows)
    data/sku_inventory.csv         (60 rows, current snapshot)
    data/sku_catalog.csv           (60 rows, product metadata)
    data/demand_intelligence.db    (SQLite, all tables loaded)
"""

from __future__ import annotations

import csv
import hashlib
import math
import os
import random
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
SEED = 42
random.seed(SEED)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = WORKSPACE_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

SIGNALS_CSV = DATA_DIR / "sku_weekly_signals.csv"
INVENTORY_CSV = DATA_DIR / "sku_inventory.csv"
CATALOG_CSV = DATA_DIR / "sku_catalog.csv"
DB_PATH = DATA_DIR / "demand_intelligence.db"

# ---------------------------------------------------------------------------
# Time config — 104 weeks ending "this week"
# ---------------------------------------------------------------------------
NUM_WEEKS = 104
# We label weeks as week_index 0..103  (0 = oldest, 103 = current week)
# For display: "2024-W14" style or just "Week -103" to "Week 0"


# ---------------------------------------------------------------------------
# Brand / Category / Product catalog
# ---------------------------------------------------------------------------
BRANDS = ["Pottery Barn", "West Elm", "Williams Sonoma", "Pottery Barn Kids", "Rejuvenation", "Mark & Graham"]

CATEGORIES_BY_BRAND: dict[str, list[tuple[str, list[str]]]] = {
    "Pottery Barn": [
        ("Bedding", ["Throw Blanket", "Duvet Cover", "Quilt Set", "Sheet Set", "Comforter"]),
        ("Furniture", ["Bed Frame King", "Sectional Sofa", "Dining Table", "Bookcase", "Nightstand"]),
        ("Decor", ["Decorative Pillow", "Table Centerpiece", "Wall Mirror", "Candle Set", "Vase"]),
        ("Lighting", ["Table Lamp", "Floor Lamp", "Pendant Light", "Chandelier", "Sconce"]),
        ("Outdoor", ["Patio Chair", "Outdoor Rug", "Planter", "Fire Pit", "Umbrella"]),
    ],
    "West Elm": [
        ("Furniture", ["Mid-Century Sofa", "Coffee Table", "TV Stand", "Side Table", "Storage Bench"]),
        ("Decor", ["Art Print", "Decorative Bowl", "Throw Pillow", "Area Rug", "Wall Shelf"]),
        ("Lighting", ["Table Lamp", "Arc Floor Lamp", "Desk Lamp", "String Lights", "LED Panel"]),
    ],
    "Williams Sonoma": [
        ("Kitchen", ["Chef Knife Set", "Copper Cookware", "Stand Mixer", "Cutting Board", "Dutch Oven"]),
        ("Entertaining", ["Wine Glasses Set", "Serving Platter", "Cocktail Shaker", "Cheese Board", "Ice Bucket"]),
    ],
    "Pottery Barn Kids": [
        ("Bedding", ["Kids Duvet", "Crib Sheet Set", "Character Pillow"]),
        ("Furniture", ["Bunk Bed", "Kids Desk"]),
    ],
    "Rejuvenation": [
        ("Lighting", ["Industrial Pendant", "Bathroom Vanity Light"]),
        ("Hardware", ["Door Handle Set", "Cabinet Knobs"]),
    ],
    "Mark & Graham": [
        ("Accessories", ["Leather Weekender Bag", "Monogram Tote"]),
        ("Home", ["Personalized Cutting Board", "Engraved Wine Box"]),
    ],
}

# Metro areas for housing permits
METRO_AREAS = [
    "Phoenix", "Los Angeles", "Dallas", "New York", "Chicago",
    "Houston", "Miami", "Atlanta", "Denver", "Seattle",
    "Charlotte", "Nashville", "San Francisco", "Boston", "Portland",
]

# DC mapping for metros
METRO_TO_DC = {
    "Phoenix": "Litchfield Park DC",
    "Los Angeles": "City of Industry DC",
    "Dallas": "Dallas DC",
    "New York": "South Brunswick DC",
    "Chicago": "Olive Branch DC",
    "Houston": "Dallas DC",
    "Miami": "Pompano Beach Hub",
    "Atlanta": "Braselton DC",
    "Denver": "Denver Hub",
    "Seattle": "Tracy DC",
    "Charlotte": "Braselton DC",
    "Nashville": "Memphis DC",
    "San Francisco": "Tracy DC",
    "Boston": "Boston Hub",
    "Portland": "Tracy DC",
}


# ---------------------------------------------------------------------------
# Scenario definitions — typed for clarity
# ---------------------------------------------------------------------------
@dataclass
class ScenarioConfig:
    """Defines how signals evolve for a particular SKU story."""
    scenario_type: str  # A, B, C, D, E, F, G, H, I, J
    label: str

    # Baseline parameters
    base_sales: float = 100.0        # avg weekly units
    base_search: float = 15.0        # Google Trends baseline (0-100)
    base_permits: float = 100.0      # housing permits baseline
    sales_noise_pct: float = 0.08    # random noise on sales

    # Price & lead time
    price: float = 79.0
    lead_time_days: int = 56

    # Inventory snapshot
    stock_on_hand: int = 3000
    on_order: int = 0

    # Signal evolution overrides (week_index → multiplier or absolute)
    # These are populated per-scenario below
    sales_pattern: dict = field(default_factory=dict)    # week -> multiplier on base
    search_pattern: dict = field(default_factory=dict)   # week -> absolute search index
    permit_pattern: dict = field(default_factory=dict)   # week -> absolute permit count

    metro: str = "Phoenix"
    brand: str = "Pottery Barn"
    category: str = "Bedding"
    product_name: str = "Generic Product"
    sku_id: str = "XX-GENERIC-00"


def _lerp(start: float, end: float, t: float) -> float:
    """Linear interpolation."""
    return start + (end - start) * max(0.0, min(1.0, t))


def _seasonal_factor(week_index: int) -> float:
    """Returns a seasonal multiplier (peak in weeks ~44-52 of year = Oct-Dec)."""
    # Map week_index to approximate week-of-year (assume week 0 = Jan W1 of 2 years ago)
    woy = (week_index + 1) % 52  # 0-51
    # Peak around week 48 (late Nov), trough around week 20 (May)
    return 1.0 + 0.25 * math.sin(2 * math.pi * (woy - 20) / 52)


def _build_scenario_A() -> ScenarioConfig:
    """Viral Spike — PB-BLANKET-42. Steady for 95 weeks, search explodes week 96."""
    sc = ScenarioConfig(
        scenario_type="A",
        label="viral_spike",
        sku_id="PB-BLANKET-42",
        product_name="Throw Blanket, Cognac",
        brand="Pottery Barn",
        category="Bedding",
        base_sales=125.0,
        base_search=11.0,
        base_permits=100.0,
        price=89.0,
        lead_time_days=70,
        stock_on_hand=6200,
        on_order=0,
        metro="Los Angeles",
    )
    # Search spike: starts week 96, peaks week 99-100
    for w in range(NUM_WEEKS):
        if w < 96:
            sc.search_pattern[w] = sc.base_search + random.uniform(-2, 3)
        elif w == 96:
            sc.search_pattern[w] = 28.0
        elif w == 97:
            sc.search_pattern[w] = 52.0
        elif w == 98:
            sc.search_pattern[w] = 78.0
        elif w == 99:
            sc.search_pattern[w] = 89.0
        elif w == 100:
            sc.search_pattern[w] = 94.0
        elif w == 101:
            sc.search_pattern[w] = 88.0
        elif w == 102:
            sc.search_pattern[w] = 82.0
        else:
            sc.search_pattern[w] = 76.0

    # Sales lag search by 2 weeks
    for w in range(NUM_WEEKS):
        if w < 98:
            sc.sales_pattern[w] = 1.0
        elif w == 98:
            sc.sales_pattern[w] = 1.8
        elif w == 99:
            sc.sales_pattern[w] = 3.3
        elif w == 100:
            sc.sales_pattern[w] = 5.4
        elif w == 101:
            sc.sales_pattern[w] = 4.3
        elif w == 102:
            sc.sales_pattern[w] = 3.8
        else:
            sc.sales_pattern[w] = 3.2

    return sc


def _build_scenario_B() -> ScenarioConfig:
    """Silent Overstock — PB-PILLOW-71. Trend peaked in Feb, search fading 8 weeks."""
    sc = ScenarioConfig(
        scenario_type="B",
        label="silent_overstock",
        sku_id="PB-PILLOW-71",
        product_name="Decorative Pillow, Sage Green",
        brand="Pottery Barn",
        category="Decor",
        base_sales=145.0,
        base_search=45.0,
        base_permits=100.0,
        price=65.0,
        lead_time_days=56,
        stock_on_hand=4200,
        on_order=800,
        metro="New York",
    )
    # Search rises through week ~78, peaks at 72, then slow decline
    for w in range(NUM_WEEKS):
        if w < 65:
            sc.search_pattern[w] = 20.0 + (w / 65) * 25.0 + random.uniform(-2, 2)
        elif w < 80:
            # Peak zone
            progress = (w - 65) / 15
            sc.search_pattern[w] = 45.0 + 27.0 * math.sin(progress * math.pi) + random.uniform(-2, 2)
        else:
            # Declining from ~72 down to ~22 over remaining weeks
            weeks_since_peak = w - 80
            decline_rate = 0.04  # 4% per week
            sc.search_pattern[w] = max(8.0, 62.0 * (1 - decline_rate) ** weeks_since_peak + random.uniform(-2, 2))

    # Sales follow search with 2-week lag and smoother curve
    for w in range(NUM_WEEKS):
        if w < 67:
            sc.sales_pattern[w] = 0.5 + (w / 67) * 0.5
        elif w < 82:
            progress = (w - 67) / 15
            sc.sales_pattern[w] = 1.0 + 0.45 * math.sin(progress * math.pi)
        else:
            weeks_since_peak = w - 82
            sc.sales_pattern[w] = max(0.25, 1.3 * (1 - 0.035) ** weeks_since_peak)

    return sc


def _build_scenario_C() -> ScenarioConfig:
    """Housing Permit Leading Indicator — PB-BED-FRAME-33. Search flat, permits climbing."""
    sc = ScenarioConfig(
        scenario_type="C",
        label="housing_leading",
        sku_id="PB-BED-FRAME-33",
        product_name="Bedroom Set, King",
        brand="Pottery Barn",
        category="Furniture",
        base_sales=34.0,
        base_search=12.0,
        base_permits=85.0,
        price=1899.0,
        lead_time_days=68,
        stock_on_hand=860,
        on_order=240,
        metro="Phoenix",
    )
    # Search stays flat
    for w in range(NUM_WEEKS):
        sc.search_pattern[w] = sc.base_search + random.uniform(-2, 3)

    # Permits start climbing from week 88
    for w in range(NUM_WEEKS):
        if w < 88:
            sc.permit_pattern[w] = sc.base_permits + random.uniform(-8, 8)
        else:
            weeks_rising = w - 88
            sc.permit_pattern[w] = sc.base_permits + weeks_rising * 4.5 + random.uniform(-3, 3)

    # Sales still flat — the point is: permits predict FUTURE sales
    for w in range(NUM_WEEKS):
        sc.sales_pattern[w] = 1.0

    return sc


def _build_scenario_D() -> ScenarioConfig:
    """Steady OK — WE-LAMP-19. Everything normal, no action needed."""
    sc = ScenarioConfig(
        scenario_type="D",
        label="steady_ok",
        sku_id="WE-LAMP-19",
        product_name="Table Lamp, Brass",
        brand="West Elm",
        category="Lighting",
        base_sales=67.0,
        base_search=18.0,
        base_permits=100.0,
        price=179.0,
        lead_time_days=42,
        stock_on_hand=890,
        on_order=200,
        metro="Chicago",
    )
    for w in range(NUM_WEEKS):
        sc.search_pattern[w] = sc.base_search + random.uniform(-3, 3)
        sc.sales_pattern[w] = 1.0
        sc.permit_pattern[w] = sc.base_permits + random.uniform(-6, 6)
    return sc


def _build_scenario_E() -> ScenarioConfig:
    """Seasonal Product — WS-MIXER-05. Holiday surge (Thanksgiving-Christmas) then cliff."""
    sc = ScenarioConfig(
        scenario_type="E",
        label="seasonal_surge",
        sku_id="WS-MIXER-05",
        product_name="Stand Mixer, Red",
        brand="Williams Sonoma",
        category="Kitchen",
        base_sales=42.0,
        base_search=22.0,
        base_permits=100.0,
        price=449.0,
        lead_time_days=49,
        stock_on_hand=1800,
        on_order=600,
        metro="Dallas",
    )
    for w in range(NUM_WEEKS):
        woy = (w + 1) % 52
        # Massive search + sales surge weeks 44-52 (holiday gift season)
        if 44 <= woy <= 51:
            surge = 1.0 + 2.5 * math.sin(math.pi * (woy - 44) / 7)
            sc.sales_pattern[w] = surge
            sc.search_pattern[w] = 22.0 + 55.0 * math.sin(math.pi * (woy - 44) / 7) + random.uniform(-3, 3)
        elif woy == 0 or woy == 1:
            # Post-holiday cliff
            sc.sales_pattern[w] = 0.35
            sc.search_pattern[w] = 10.0 + random.uniform(-2, 2)
        else:
            sc.sales_pattern[w] = 1.0
            sc.search_pattern[w] = sc.base_search + random.uniform(-3, 3)
        sc.permit_pattern[w] = sc.base_permits + random.uniform(-5, 5)
    return sc


def _build_scenario_F() -> ScenarioConfig:
    """Multi-Signal Convergence — PB-SOFA-88. Search AND permits both firing."""
    sc = ScenarioConfig(
        scenario_type="F",
        label="multi_signal",
        sku_id="PB-SOFA-88",
        product_name="Sectional Sofa, Ivory",
        brand="Pottery Barn",
        category="Furniture",
        base_sales=22.0,
        base_search=14.0,
        base_permits=90.0,
        price=3499.0,
        lead_time_days=84,
        stock_on_hand=380,
        on_order=100,
        metro="Phoenix",
    )
    for w in range(NUM_WEEKS):
        if w < 85:
            sc.search_pattern[w] = sc.base_search + random.uniform(-2, 2)
            sc.permit_pattern[w] = sc.base_permits + random.uniform(-5, 5)
            sc.sales_pattern[w] = 1.0
        else:
            weeks_in = w - 85
            # Both signals rise together
            sc.search_pattern[w] = sc.base_search + weeks_in * 3.8 + random.uniform(-2, 2)
            sc.permit_pattern[w] = sc.base_permits + weeks_in * 5.2 + random.uniform(-3, 3)
            sc.sales_pattern[w] = 1.0 + weeks_in * 0.12
    return sc


def _build_scenario_G() -> ScenarioConfig:
    """Post-Peak Overstock — WE-RUG-15. Trend peaked 4 months ago, inventory still loaded."""
    sc = ScenarioConfig(
        scenario_type="G",
        label="post_peak_overstock",
        sku_id="WE-RUG-15",
        product_name="Area Rug, Geometric",
        brand="West Elm",
        category="Decor",
        base_sales=55.0,
        base_search=30.0,
        base_permits=100.0,
        price=299.0,
        lead_time_days=42,
        stock_on_hand=3800,
        on_order=1200,
        metro="Atlanta",
    )
    for w in range(NUM_WEEKS):
        if w < 60:
            sc.search_pattern[w] = 20.0 + (w / 60) * 40.0 + random.uniform(-3, 3)
            sc.sales_pattern[w] = 0.6 + (w / 60) * 0.6
        elif w < 75:
            progress = (w - 60) / 15
            sc.search_pattern[w] = 60.0 + 25.0 * math.sin(progress * math.pi) + random.uniform(-3, 3)
            sc.sales_pattern[w] = 1.2 + 0.6 * math.sin(progress * math.pi)
        else:
            weeks_since = w - 75
            sc.search_pattern[w] = max(6.0, 70.0 * (0.955) ** weeks_since + random.uniform(-2, 2))
            sc.sales_pattern[w] = max(0.2, 1.5 * (0.96) ** weeks_since)
        sc.permit_pattern[w] = sc.base_permits + random.uniform(-5, 5)
    return sc


def _build_scenario_H() -> ScenarioConfig:
    """Sudden Collapse — PBK-BUNK-22. Sales were healthy, then abruptly drop (product recall / competitor launch)."""
    sc = ScenarioConfig(
        scenario_type="H",
        label="sudden_collapse",
        sku_id="PBK-BUNK-22",
        product_name="Bunk Bed, White",
        brand="Pottery Barn Kids",
        category="Furniture",
        base_sales=28.0,
        base_search=16.0,
        base_permits=100.0,
        price=1299.0,
        lead_time_days=56,
        stock_on_hand=340,
        on_order=150,
        metro="Charlotte",
    )
    for w in range(NUM_WEEKS):
        if w < 92:
            sc.search_pattern[w] = sc.base_search + random.uniform(-2, 3)
            sc.sales_pattern[w] = 1.0
        elif w == 92:
            # Sudden negative search spike (competitor launch / bad press)
            sc.search_pattern[w] = 45.0  # spike of searches (people looking at alternatives)
            sc.sales_pattern[w] = 0.8
        else:
            weeks_after = w - 92
            sc.search_pattern[w] = max(4.0, 45.0 * (0.7) ** weeks_after)
            sc.sales_pattern[w] = max(0.15, 0.8 * (0.65) ** weeks_after)
        sc.permit_pattern[w] = sc.base_permits + random.uniform(-5, 5)
    return sc


def _build_scenario_I() -> ScenarioConfig:
    """Slow-Burn Growth — RJ-PENDANT-11. Gradual upward trend over many months."""
    sc = ScenarioConfig(
        scenario_type="I",
        label="slow_burn",
        sku_id="RJ-PENDANT-11",
        product_name="Industrial Pendant, Matte Black",
        brand="Rejuvenation",
        category="Lighting",
        base_sales=18.0,
        base_search=8.0,
        base_permits=100.0,
        price=329.0,
        lead_time_days=42,
        stock_on_hand=420,
        on_order=80,
        metro="Portland",
    )
    for w in range(NUM_WEEKS):
        # Steady compounding growth: ~1.5% per week on search + sales
        growth = 1.015 ** w
        sc.search_pattern[w] = min(85.0, sc.base_search * (growth ** 0.4) + random.uniform(-1, 1))
        sc.sales_pattern[w] = min(4.0, growth ** 0.35)
        sc.permit_pattern[w] = sc.base_permits + w * 0.15 + random.uniform(-3, 3)
    return sc


def _build_scenario_J() -> ScenarioConfig:
    """Flash in the Pan — MG-TOTE-07. Spike that dies in 2 weeks (false alarm pattern)."""
    sc = ScenarioConfig(
        scenario_type="J",
        label="flash_pan",
        sku_id="MG-TOTE-07",
        product_name="Monogram Tote, Navy",
        brand="Mark & Graham",
        category="Accessories",
        base_sales=35.0,
        base_search=10.0,
        base_permits=100.0,
        price=129.0,
        lead_time_days=35,
        stock_on_hand=1100,
        on_order=0,
        metro="New York",
    )
    for w in range(NUM_WEEKS):
        if w < 94:
            sc.search_pattern[w] = sc.base_search + random.uniform(-2, 2)
            sc.sales_pattern[w] = 1.0
        elif w == 94:
            sc.search_pattern[w] = 55.0  # sudden spike
            sc.sales_pattern[w] = 1.6
        elif w == 95:
            sc.search_pattern[w] = 72.0  # peaks
            sc.sales_pattern[w] = 2.1
        elif w == 96:
            sc.search_pattern[w] = 38.0  # already dropping
            sc.sales_pattern[w] = 1.4
        elif w == 97:
            sc.search_pattern[w] = 18.0  # back to near baseline
            sc.sales_pattern[w] = 1.1
        else:
            sc.search_pattern[w] = sc.base_search + random.uniform(-2, 3)
            sc.sales_pattern[w] = 1.0
        sc.permit_pattern[w] = sc.base_permits + random.uniform(-5, 5)
    return sc


# ---------------------------------------------------------------------------
# Random SKU generator for the remaining ~50 SKUs
# ---------------------------------------------------------------------------
def _random_sku_id(brand: str, category: str, idx: int) -> str:
    prefix_map = {
        "Pottery Barn": "PB",
        "West Elm": "WE",
        "Williams Sonoma": "WS",
        "Pottery Barn Kids": "PBK",
        "Rejuvenation": "RJ",
        "Mark & Graham": "MG",
    }
    cat_short = category[:3].upper()
    return f"{prefix_map.get(brand, 'XX')}-{cat_short}-{idx:02d}"


def _generate_random_scenario(sku_id: str, brand: str, category: str,
                               product_name: str, idx: int) -> ScenarioConfig:
    """Generate a realistic but random signal pattern for a filler SKU."""
    metro = random.choice(METRO_AREAS)
    base_sales = random.uniform(15, 200)
    base_search = random.uniform(5, 40)
    base_permits = random.uniform(60, 140)
    price = random.choice([49, 69, 89, 129, 179, 249, 349, 499, 699, 899, 1299, 1899, 2499])
    lead_time = random.choice([28, 35, 42, 49, 56, 63, 70, 84])

    # Random inventory
    weekly_consumption = base_sales
    weeks_of_stock = random.uniform(3, 16)
    stock = int(weekly_consumption * weeks_of_stock)
    on_order = int(weekly_consumption * random.uniform(0, 4)) if random.random() > 0.3 else 0

    sc = ScenarioConfig(
        scenario_type="R",
        label=f"random_{idx}",
        sku_id=sku_id,
        product_name=product_name,
        brand=brand,
        category=category,
        base_sales=base_sales,
        base_search=base_search,
        base_permits=base_permits,
        price=price,
        lead_time_days=lead_time,
        stock_on_hand=stock,
        on_order=on_order,
        metro=metro,
    )

    # Choose a random pattern type
    pattern = random.choice(["steady", "gentle_up", "gentle_down", "mid_bump", "noisy_flat", "late_uptick"])

    for w in range(NUM_WEEKS):
        seasonal = _seasonal_factor(w)
        noise_s = random.uniform(-2, 2)
        noise_sale = random.uniform(0.9, 1.1)

        if pattern == "steady":
            sc.search_pattern[w] = base_search * seasonal + noise_s
            sc.sales_pattern[w] = seasonal * noise_sale
        elif pattern == "gentle_up":
            trend = 1.0 + (w / NUM_WEEKS) * 0.5
            sc.search_pattern[w] = base_search * trend * 0.7 + noise_s
            sc.sales_pattern[w] = trend * 0.85 * seasonal * noise_sale
        elif pattern == "gentle_down":
            trend = 1.0 - (w / NUM_WEEKS) * 0.35
            sc.search_pattern[w] = base_search * max(0.3, trend) + noise_s
            sc.sales_pattern[w] = max(0.3, trend) * seasonal * noise_sale
        elif pattern == "mid_bump":
            bump_center = random.randint(40, 70)
            bump_width = random.randint(5, 12)
            dist = abs(w - bump_center)
            bump = max(0, 1.0 - dist / bump_width) * 1.8
            sc.search_pattern[w] = base_search * (1 + bump) + noise_s
            sc.sales_pattern[w] = (1 + bump * 0.6) * seasonal * noise_sale
        elif pattern == "noisy_flat":
            sc.search_pattern[w] = base_search + random.uniform(-6, 6)
            sc.sales_pattern[w] = random.uniform(0.7, 1.3) * seasonal
        elif pattern == "late_uptick":
            if w > 90:
                uptick = (w - 90) * 0.08
                sc.search_pattern[w] = base_search * (1 + uptick) + noise_s
                sc.sales_pattern[w] = (1 + uptick * 0.5) * seasonal * noise_sale
            else:
                sc.search_pattern[w] = base_search + noise_s
                sc.sales_pattern[w] = seasonal * noise_sale

        sc.permit_pattern[w] = base_permits + random.uniform(-8, 8)

    return sc


# ---------------------------------------------------------------------------
# Generate time-series rows from scenarios
# ---------------------------------------------------------------------------
def _generate_weekly_rows(sc: ScenarioConfig) -> list[dict]:
    """Turn a ScenarioConfig into 104 weekly signal rows."""
    rows = []
    for w in range(NUM_WEEKS):
        # Sales
        sales_mult = sc.sales_pattern.get(w, 1.0)
        seasonal = _seasonal_factor(w) if sc.scenario_type == "R" else 1.0
        noise = 1.0 + random.uniform(-sc.sales_noise_pct, sc.sales_noise_pct)
        units_sold = max(0, int(sc.base_sales * sales_mult * seasonal * noise))

        # Search index (clamp 0-100)
        search_raw = sc.search_pattern.get(w, sc.base_search)
        search_index = max(0.0, min(100.0, search_raw))

        # Permits
        permits_raw = sc.permit_pattern.get(w, sc.base_permits)
        permits = max(0, int(permits_raw))

        # Compute rolling averages for velocity (using previous rows)
        # We'll compute these in a post-processing pass for accuracy

        rows.append({
            "week_index": w,
            "week_label": f"W{w - NUM_WEEKS + 1:+d}" if w < NUM_WEEKS - 1 else "W0",
            "sku_id": sc.sku_id,
            "units_sold": units_sold,
            "search_index": round(search_index, 1),
            "housing_permits": permits,
            "metro": sc.metro,
            "scenario_type": sc.scenario_type,
        })

    # Post-process: add velocity features
    for i, row in enumerate(rows):
        # Sales velocity (vs 4-week avg)
        if i >= 4:
            avg_4w = sum(rows[j]["units_sold"] for j in range(i - 4, i)) / 4
            row["sales_velocity_4w"] = round((row["units_sold"] - avg_4w) / max(avg_4w, 1) * 100, 1)
        else:
            row["sales_velocity_4w"] = 0.0

        # Sales velocity (vs 1-week)
        if i >= 1:
            prev = rows[i - 1]["units_sold"]
            row["sales_velocity_1w"] = round((row["units_sold"] - prev) / max(prev, 1) * 100, 1)
        else:
            row["sales_velocity_1w"] = 0.0

        # Search velocity (vs 4-week avg)
        if i >= 4:
            avg_4w_search = sum(rows[j]["search_index"] for j in range(i - 4, i)) / 4
            row["search_velocity_4w"] = round((row["search_index"] - avg_4w_search) / max(avg_4w_search, 0.1) * 100, 1)
        else:
            row["search_velocity_4w"] = 0.0

        # Search velocity (vs 1-week)
        if i >= 1:
            prev_search = rows[i - 1]["search_index"]
            row["search_velocity_1w"] = round((row["search_index"] - prev_search) / max(prev_search, 0.1) * 100, 1)
        else:
            row["search_velocity_1w"] = 0.0

        # Permit velocity (vs 4-week)
        if i >= 4:
            avg_4w_perm = sum(rows[j]["housing_permits"] for j in range(i - 4, i)) / 4
            row["permit_velocity_4w"] = round((row["housing_permits"] - avg_4w_perm) / max(avg_4w_perm, 1) * 100, 1)
        else:
            row["permit_velocity_4w"] = 0.0

        # Rolling 7-week average sales (for days-of-supply calc)
        lookback = min(i + 1, 7)
        row["rolling_7w_avg_sales"] = round(sum(rows[j]["units_sold"] for j in range(i - lookback + 1, i + 1)) / lookback, 1)

    return rows


def _compute_surge_score(row: dict) -> float:
    """Compute a 0-100 surge score from velocity features."""
    # Normalize velocities to 0-100 contribution
    def _velocity_to_score(v: float, max_v: float = 200.0) -> float:
        """Map a velocity % to 0-100 score, clamped."""
        return max(0.0, min(100.0, (v / max_v) * 100.0))

    search_score = _velocity_to_score(row.get("search_velocity_4w", 0), 150.0)
    sales_score = _velocity_to_score(row.get("sales_velocity_4w", 0), 100.0)
    permit_score = _velocity_to_score(row.get("permit_velocity_4w", 0), 50.0)

    # Weighted combination
    combined = 0.50 * search_score + 0.30 * sales_score + 0.20 * permit_score
    return round(max(0.0, min(100.0, combined)), 1)


# ---------------------------------------------------------------------------
# Main generation
# ---------------------------------------------------------------------------
def generate_all() -> tuple[list[dict], list[dict], list[dict]]:
    """Generate all data. Returns (signal_rows, inventory_rows, catalog_rows)."""

    # 1. Build the 10 scripted scenarios
    scripted = [
        _build_scenario_A(),
        _build_scenario_B(),
        _build_scenario_C(),
        _build_scenario_D(),
        _build_scenario_E(),
        _build_scenario_F(),
        _build_scenario_G(),
        _build_scenario_H(),
        _build_scenario_I(),
        _build_scenario_J(),
    ]

    # 2. Generate 50 random SKUs to fill out the catalog
    random_scenarios: list[ScenarioConfig] = []
    used_ids = {s.sku_id for s in scripted}
    idx = 20  # start numbering from 20 to avoid collisions

    for brand, cat_list in CATEGORIES_BY_BRAND.items():
        for category, products in cat_list:
            for product_name in products:
                sku_id = _random_sku_id(brand, category, idx)
                if sku_id in used_ids:
                    idx += 1
                    sku_id = _random_sku_id(brand, category, idx)
                used_ids.add(sku_id)
                random_scenarios.append(
                    _generate_random_scenario(sku_id, brand, category, product_name, idx)
                )
                idx += 1
                if len(random_scenarios) >= 50:
                    break
            if len(random_scenarios) >= 50:
                break
        if len(random_scenarios) >= 50:
            break

    all_scenarios = scripted + random_scenarios
    print(f"Total SKUs: {len(all_scenarios)} ({len(scripted)} scripted + {len(random_scenarios)} random)")

    # 3. Generate weekly signal rows
    all_signal_rows: list[dict] = []
    for sc in all_scenarios:
        rows = _generate_weekly_rows(sc)
        # Add surge score to each row
        for r in rows:
            r["surge_score"] = _compute_surge_score(r)
        all_signal_rows.extend(rows)

    # 4. Current-week surge direction for each SKU
    sku_latest: dict[str, dict] = {}
    for r in all_signal_rows:
        if r["week_index"] == NUM_WEEKS - 1:
            sku_latest[r["sku_id"]] = r

    sku_prev_week: dict[str, dict] = {}
    for r in all_signal_rows:
        if r["week_index"] == NUM_WEEKS - 2:
            sku_prev_week[r["sku_id"]] = r

    sku_3w_ago: dict[str, dict] = {}
    for r in all_signal_rows:
        if r["week_index"] == NUM_WEEKS - 4:
            sku_3w_ago[r["sku_id"]] = r

    # 5. Build inventory snapshot
    inventory_rows = []
    for sc in all_scenarios:
        latest = sku_latest.get(sc.sku_id, {})
        prev = sku_prev_week.get(sc.sku_id, {})
        three_w = sku_3w_ago.get(sc.sku_id, {})

        rolling_avg = latest.get("rolling_7w_avg_sales", sc.base_sales)
        days_of_supply = round((sc.stock_on_hand / max(rolling_avg / 7, 0.1)), 1)

        surge_now = latest.get("surge_score", 0)
        surge_prev = prev.get("surge_score", 0)
        surge_3w = three_w.get("surge_score", 0)

        # Determine surge direction
        delta_1w = surge_now - surge_prev
        delta_3w = surge_now - surge_3w
        if delta_1w >= 25:
            surge_flag = "SURGING"
        elif delta_3w <= -15:
            surge_flag = "FADING"
        else:
            surge_flag = "STEADY"

        # Determine risk level
        if days_of_supply < sc.lead_time_days and surge_flag == "SURGING":
            risk_level = "STOCKOUT_RISK"
        elif days_of_supply < sc.lead_time_days * 1.2:
            risk_level = "STOCKOUT_RISK"
        elif days_of_supply > sc.lead_time_days * 3 and surge_flag == "FADING":
            risk_level = "OVERSTOCK_RISK"
        elif days_of_supply > sc.lead_time_days * 2.5:
            risk_level = "OVERSTOCK_RISK"
        elif surge_flag in ("SURGING", "FADING"):
            risk_level = "WATCH"
        else:
            risk_level = "OK"

        # Override for demo scenarios to guarantee correct flags
        DEMO_OVERRIDES = {
            "PB-BLANKET-42": ("STOCKOUT_RISK", "SURGING",
                              "google_trends", "Search volume +840% WoW",
                              "Expedite supplementary order for 12,200 units"),
            "PB-PILLOW-71": ("OVERSTOCK_RISK", "FADING",
                             "google_trends", "Search declining 23% over 8 weeks",
                             "Pause replenishment; evaluate 15% markdown"),
            "PB-BED-FRAME-33": ("WATCH", "STEADY",
                                "housing_permit", "Phoenix metro SFH permits +34% MoM",
                                "Pre-position 400 units to Arizona DC"),
            "WE-LAMP-19": ("OK", "STEADY",
                           "baseline", "All signals within normal range",
                           "No action needed"),
            "PB-SOFA-88": ("WATCH", "SURGING",
                           "multi_signal", "Search +42% AND permits +28% MoM",
                           "Increase reorder quantity by 35%"),
            "WE-RUG-15": ("OVERSTOCK_RISK", "FADING",
                          "google_trends", "Trend peaked 4 months ago; declining since",
                          "Cancel pending PO; begin markdown sequence"),
            "PBK-BUNK-22": ("OVERSTOCK_RISK", "FADING",
                            "sales_collapse", "Sales dropped 85% in 3 weeks",
                            "Halt all replenishment; investigate root cause"),
            "WS-MIXER-05": ("WATCH", "SURGING",
                            "seasonal", "Entering peak holiday season (Wk 44-52)",
                            "Verify holiday stock levels vs forecast"),
        }
        if sc.sku_id in DEMO_OVERRIDES:
            risk_level, surge_flag, primary_signal, signal_detail, action = DEMO_OVERRIDES[sc.sku_id]
        else:
            primary_signal = "baseline"
            signal_detail = f"Surge score {surge_now:.0f}, {surge_flag.lower()}"
            if surge_flag == "SURGING":
                primary_signal = "google_trends"
                signal_detail = f"Search velocity +{latest.get('search_velocity_4w', 0):.0f}% (4w)"
                action = "Monitor closely; consider early reorder"
            elif surge_flag == "FADING":
                primary_signal = "google_trends"
                signal_detail = f"Search velocity {latest.get('search_velocity_4w', 0):.0f}% (4w)"
                action = "Review inventory position"
            else:
                action = "No action needed"

        # Forecast demand 60d (simple projection: rolling avg * 8.5 weeks)
        forecast_60d = int(rolling_avg * 8.5)
        demand_shortfall = max(0, forecast_60d - sc.stock_on_hand - sc.on_order)

        inventory_rows.append({
            "sku_id": sc.sku_id,
            "product_name": sc.product_name,
            "brand": sc.brand,
            "category": sc.category,
            "price": sc.price,
            "stock_on_hand": sc.stock_on_hand,
            "on_order": sc.on_order,
            "lead_time_days": sc.lead_time_days,
            "days_of_supply": days_of_supply,
            "rolling_7w_avg_sales": rolling_avg,
            "risk_level": risk_level,
            "surge_score": surge_now,
            "surge_flag": surge_flag,
            "surge_delta_1w": round(delta_1w, 1),
            "surge_delta_3w": round(delta_3w, 1),
            "primary_signal": primary_signal,
            "signal_detail": signal_detail,
            "recommended_action": action,
            "forecast_demand_60d": forecast_60d,
            "demand_shortfall": demand_shortfall,
            "metro": sc.metro,
            "dc": METRO_TO_DC.get(sc.metro, "Unknown"),
            "scenario_type": sc.scenario_type,
        })

    # 6. Build catalog
    catalog_rows = []
    for sc in all_scenarios:
        catalog_rows.append({
            "sku_id": sc.sku_id,
            "product_name": sc.product_name,
            "brand": sc.brand,
            "category": sc.category,
            "price": sc.price,
            "lead_time_days": sc.lead_time_days,
            "metro": sc.metro,
            "dc": METRO_TO_DC.get(sc.metro, "Unknown"),
            "scenario_type": sc.scenario_type,
            "scenario_label": sc.label,
        })

    return all_signal_rows, inventory_rows, catalog_rows


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        print(f"  [WARN] No rows to write to {path.name}")
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  ✓ {path.name}: {len(rows):,} rows × {len(fieldnames)} cols")


def _load_to_sqlite(db_path: Path, table_name: str, rows: list[dict]) -> None:
    if not rows:
        return
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Drop + recreate
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    cols = list(rows[0].keys())
    col_defs = ", ".join(f'"{c}" TEXT' for c in cols)
    cursor.execute(f"CREATE TABLE {table_name} ({col_defs})")

    placeholders = ", ".join(["?"] * len(cols))
    insert_sql = f"INSERT INTO {table_name} ({', '.join(f'\"' + c + '\"' for c in cols)}) VALUES ({placeholders})"

    for row in rows:
        cursor.execute(insert_sql, [str(row.get(c, "")) for c in cols])

    conn.commit()
    conn.close()
    print(f"  ✓ SQLite table '{table_name}': {len(rows):,} rows loaded")


def main() -> None:
    print("=" * 60)
    print("SYNTHETIC DATA GENERATOR — Demand Intelligence System")
    print("=" * 60)
    print()

    signal_rows, inventory_rows, catalog_rows = generate_all()

    print(f"\nWriting CSVs to {DATA_DIR}...")
    _write_csv(SIGNALS_CSV, signal_rows)
    _write_csv(INVENTORY_CSV, inventory_rows)
    _write_csv(CATALOG_CSV, catalog_rows)

    print(f"\nLoading into SQLite: {DB_PATH}...")
    _load_to_sqlite(DB_PATH, "sku_weekly_signals", signal_rows)
    _load_to_sqlite(DB_PATH, "sku_inventory", inventory_rows)
    _load_to_sqlite(DB_PATH, "sku_catalog", catalog_rows)

    # Print summary stats
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total SKUs:         {len(catalog_rows)}")
    print(f"Signal rows:        {len(signal_rows):,}  ({len(catalog_rows)} SKUs × {NUM_WEEKS} weeks)")
    print(f"Inventory snapshot: {len(inventory_rows)} rows")

    # Risk distribution
    risk_counts: dict[str, int] = {}
    for inv in inventory_rows:
        risk_counts[inv["risk_level"]] = risk_counts.get(inv["risk_level"], 0) + 1
    print(f"\nRisk distribution:")
    for risk in ["STOCKOUT_RISK", "OVERSTOCK_RISK", "WATCH", "OK"]:
        count = risk_counts.get(risk, 0)
        bar = "█" * count
        print(f"  {risk:<16} {count:3d}  {bar}")

    # Surge distribution
    surge_counts: dict[str, int] = {}
    for inv in inventory_rows:
        surge_counts[inv["surge_flag"]] = surge_counts.get(inv["surge_flag"], 0) + 1
    print(f"\nSurge distribution:")
    for flag in ["SURGING", "FADING", "STEADY"]:
        count = surge_counts.get(flag, 0)
        bar = "█" * count
        print(f"  {flag:<10} {count:3d}  {bar}")

    # Demo scenario check
    print(f"\nDemo scenario verification:")
    demo_skus = ["PB-BLANKET-42", "PB-PILLOW-71", "PB-BED-FRAME-33", "WE-LAMP-19",
                 "WS-MIXER-05", "PB-SOFA-88", "WE-RUG-15", "PBK-BUNK-22",
                 "RJ-PENDANT-11", "MG-TOTE-07"]
    for sku_id in demo_skus:
        inv = next((r for r in inventory_rows if r["sku_id"] == sku_id), None)
        if inv:
            print(f"  ✓ {sku_id:<16} {inv['risk_level']:<16} surge={inv['surge_score']:>5}  {inv['surge_flag']:<8}  {inv['signal_detail'][:50]}")
        else:
            print(f"  ✗ {sku_id} NOT FOUND")

    print(f"\n✅ Done! All files written to {DATA_DIR}")
    print(f"   CSVs:   {SIGNALS_CSV.name}, {INVENTORY_CSV.name}, {CATALOG_CSV.name}")
    print(f"   SQLite: {DB_PATH.name}")


if __name__ == "__main__":
    main()
