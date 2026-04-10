"""
generate_synthetic_data.py
==========================
Generates realistic synthetic datasets for the Multi-Signal Demand Intelligence System.

Outputs:
  data/sales.csv      — Weekly sales history for ~85 SKUs across 104 weeks
  data/signals.csv    — Multi-signal time series (google_trends, housing_permit, social, mortgage_apps)
  data/inventory.csv  — Point-in-time inventory snapshot with derived risk fields

Design principles:
  - 6 hand-crafted demo scenarios matching the PRD exactly
  - ~79 programmatic SKUs with realistic archetype-based patterns
  - Seasonality modeled on US home furnishings retail (Q4 peak, spring bump, summer trough)
  - Fixed random seed (42) for full reproducibility
  - No author bias in risk distribution — labels derived from generated numbers
  - Prices based on publicly observable WSI brand catalog ranges
"""

from __future__ import annotations

import csv
import json
import math
import os
import random
from datetime import date, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEED = 42
NUM_WEEKS = 104  # 2 years of weekly data
START_DATE = date(2024, 4, 15)  # Monday of the first week
TODAY = date(2026, 4, 7)  # Most recent Monday (demo week)

# WSI Distribution Centers (from supply chain items.txt)
DC_LIST = [
    "City of Industry DC, CA",
    "Olive Branch DC, MS",
    "South Brunswick DC, NJ",
    "Memphis DC, TN",
    "Dallas DC, TX",
    "Braselton DC, GA",
    "Litchfield Park DC, AZ",
    "Fontana DC, CA",
    "Tracy DC, CA",
]

# Metro areas for housing permit signals
METRO_AREAS = [
    {"name": "Phoenix-Mesa-Chandler, AZ", "baseline_permits": 2800, "growth": 0.03},
    {"name": "Charlotte-Concord-Gastonia, NC-SC", "baseline_permits": 2100, "growth": 0.02},
    {"name": "Dallas-Fort Worth-Arlington, TX", "baseline_permits": 3400, "growth": 0.025},
    {"name": "Denver-Aurora-Lakewood, CO", "baseline_permits": 1600, "growth": 0.015},
    {"name": "Atlanta-Sandy Springs-Alpharetta, GA", "baseline_permits": 2900, "growth": 0.02},
    {"name": "Los Angeles-Long Beach-Anaheim, CA", "baseline_permits": 1400, "growth": 0.01},
    {"name": "New York-Newark-Jersey City, NY-NJ", "baseline_permits": 1800, "growth": 0.005},
    {"name": "Seattle-Tacoma-Bellevue, WA", "baseline_permits": 1500, "growth": 0.018},
    {"name": "Nashville-Davidson-Murfreesboro, TN", "baseline_permits": 2200, "growth": 0.028},
    {"name": "Tampa-St. Petersburg-Clearwater, FL", "baseline_permits": 2500, "growth": 0.022},
]

# ---------------------------------------------------------------------------
# Brand / category configuration
# ---------------------------------------------------------------------------
BRANDS = {
    "Pottery Barn": {
        "prefix": "PB",
        "categories": {
            "Bedding":    {"price_range": (79, 399), "lead_range": (56, 84), "baseline_range": (60, 250)},
            "Furniture":  {"price_range": (499, 2499), "lead_range": (56, 84), "baseline_range": (15, 55)},
            "Decor":      {"price_range": (29, 249), "lead_range": (42, 70), "baseline_range": (40, 180)},
            "Lighting":   {"price_range": (89, 599), "lead_range": (42, 70), "baseline_range": (25, 90)},
            "Bath":       {"price_range": (39, 199), "lead_range": (42, 56), "baseline_range": (50, 160)},
            "Rugs":       {"price_range": (149, 1299), "lead_range": (56, 84), "baseline_range": (12, 45)},
            "Outdoor":    {"price_range": (99, 1899), "lead_range": (56, 84), "baseline_range": (10, 40)},
        },
    },
    "West Elm": {
        "prefix": "WE",
        "categories": {
            "Furniture":  {"price_range": (299, 1899), "lead_range": (42, 70), "baseline_range": (20, 70)},
            "Decor":      {"price_range": (19, 179), "lead_range": (35, 56), "baseline_range": (60, 220)},
            "Lighting":   {"price_range": (49, 499), "lead_range": (35, 56), "baseline_range": (30, 110)},
            "Bedding":    {"price_range": (59, 299), "lead_range": (42, 56), "baseline_range": (50, 180)},
            "Rugs":       {"price_range": (99, 999), "lead_range": (42, 70), "baseline_range": (15, 50)},
        },
    },
    "Williams Sonoma": {
        "prefix": "WS",
        "categories": {
            "Kitchen":    {"price_range": (29, 899), "lead_range": (28, 56), "baseline_range": (40, 200)},
            "Decor":      {"price_range": (39, 299), "lead_range": (28, 42), "baseline_range": (30, 120)},
            "Outdoor":    {"price_range": (49, 599), "lead_range": (35, 56), "baseline_range": (15, 60)},
        },
    },
    "Pottery Barn Kids": {
        "prefix": "PBK",
        "categories": {
            "Furniture":  {"price_range": (199, 1299), "lead_range": (42, 70), "baseline_range": (12, 45)},
            "Bedding":    {"price_range": (39, 199), "lead_range": (42, 56), "baseline_range": (40, 130)},
            "Decor":      {"price_range": (19, 149), "lead_range": (35, 56), "baseline_range": (50, 160)},
            "Bath":       {"price_range": (19, 99), "lead_range": (35, 42), "baseline_range": (35, 100)},
        },
    },
    "Rejuvenation": {
        "prefix": "RJ",
        "categories": {
            "Lighting":   {"price_range": (89, 2199), "lead_range": (49, 84), "baseline_range": (8, 35)},
            "Bath":       {"price_range": (69, 499), "lead_range": (49, 70), "baseline_range": (10, 40)},
            "Furniture":  {"price_range": (399, 1899), "lead_range": (56, 84), "baseline_range": (5, 20)},
        },
    },
}

# Product name templates per category
PRODUCT_TEMPLATES = {
    "Bedding": [
        "Linen Duvet Cover", "Waffle Weave Blanket", "Organic Percale Sheet Set",
        "Velvet Quilt", "Chunky Knit Throw", "Down Alternative Comforter",
        "Sateen Pillowcase Set", "Herringbone Blanket", "Flannel Sheet Set",
        "Cashmere Throw", "Quilted Coverlet", "Silk Pillowcase Pair",
    ],
    "Furniture": [
        "Modular Sectional Sofa", "Mid-Century Nightstand", "Farmhouse Dining Table",
        "Upholstered Platform Bed", "Storage Media Console", "Spindle Back Chair",
        "Rattan Bookcase", "Marble Top Coffee Table", "Leather Club Armchair",
        "Extendable Dining Table", "Floating Shelf Unit", "Tufted Headboard",
        "Loft Bed with Desk", "Convertible Crib", "Side Table with Drawer",
        "Accent Bench", "Corner Writing Desk", "Trundle Daybed",
    ],
    "Decor": [
        "Oversized Ceramic Vase", "Woven Wall Basket Set", "Faux Olive Tree 72\"",
        "Terracotta Planter", "Hammered Metal Tray", "Linen Table Runner",
        "Wood Bead Garland", "Framed Abstract Print", "Mercury Glass Candle",
        "Embroidered Throw Pillow", "Stoneware Sculpture", "Hanging Macrame Planter",
        "Textured Table Clock", "Brass Picture Frame Set", "Decorative Book Box",
    ],
    "Lighting": [
        "Arc Floor Lamp", "Industrial Pendant Light", "Table Lamp, Brass",
        "Chandelier 6-Arm", "Wall Sconce Duo", "Desk Lamp with USB",
        "Rattan Pendant Shade", "Ceramic Table Lamp", "Globe String Lights",
        "Flush Mount Ceiling Light",
    ],
    "Kitchen": [
        "Stand Mixer Heritage", "Professional Blender", "Copper Cookware 10-Piece",
        "Knife Block Set", "Espresso Machine", "Dutch Oven 7-Qt Enameled",
        "Cutting Board Set", "Mandoline Slicer Pro", "Pizza Stone Kit",
        "Stainless Mixing Bowl Set",
    ],
    "Bath": [
        "Organic Turkish Towel Set", "Teak Shower Bench", "Stone Bath Accessories",
        "Waffle Robe", "Heated Towel Rack", "Bathroom Vanity Mirror",
        "Soap Dispenser Set", "Bath Mat Organic Cotton",
    ],
    "Outdoor": [
        "Teak Dining Set 7-Piece", "All-Weather Wicker Sofa", "Fire Pit Table",
        "Ceramic Garden Stool", "Outdoor Rug 8x10", "Adirondack Chair Set",
    ],
    "Rugs": [
        "Hand-Knotted Wool Rug 8x10", "Jute Area Rug 5x8", "Persian Style Runner",
        "Flatweave Cotton Rug", "Shag Area Rug 9x12", "Indoor/Outdoor Rug",
    ],
}

# Color/finish suffixes for variety
FINISHES = [
    "Ivory", "Charcoal", "Brass", "Oak", "Walnut", "White", "Sage",
    "Navy", "Cognac", "Stone", "Natural", "Matte Black", "Oatmeal",
    "Terracotta", "Slate", "Cream", "Driftwood", "Cloud", "Fog",
]

# Sales pattern archetypes
ARCHETYPES = [
    "steady",           # Flat baseline ± 10% noise
    "seasonal_peak",    # Pronounced Q4 spike
    "spring_bump",      # Outdoor/garden peaking March-May
    "slow_decline",     # Gradual monthly erosion
    "growth_ramp",      # Steady monthly uptick
    "viral_micro_spike",# Small 2x blip mid-year, returns to baseline
    "choppy",           # High variance, difficult to forecast
]

ARCHETYPE_WEIGHTS = [0.40, 0.15, 0.08, 0.10, 0.10, 0.07, 0.10]


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------
def week_dates() -> list[date]:
    """Return list of 104 Monday dates."""
    return [START_DATE + timedelta(weeks=w) for w in range(NUM_WEEKS)]


def seasonality_factor(d: date) -> float:
    """
    US home furnishings seasonality curve.
    Peak in Oct-Dec (Q4), moderate in Mar-May (spring refresh), trough in Jun-Aug.
    """
    month = d.month
    # Monthly multipliers based on NRF home furnishings index
    monthly = {
        1: 0.82, 2: 0.85, 3: 0.95, 4: 1.00, 5: 1.02,
        6: 0.88, 7: 0.85, 8: 0.90, 9: 0.98, 10: 1.15,
        11: 1.30, 12: 1.25,
    }
    return monthly.get(month, 1.0)


def spring_seasonality(d: date) -> float:
    """Outdoor/garden items: peak March-May, trough Nov-Feb."""
    month = d.month
    monthly = {
        1: 0.40, 2: 0.55, 3: 1.20, 4: 1.40, 5: 1.35,
        6: 1.10, 7: 0.95, 8: 0.80, 9: 0.65, 10: 0.55,
        11: 0.45, 12: 0.40,
    }
    return monthly.get(month, 1.0)


def kitchen_seasonality(d: date) -> float:
    """Kitchen items: strong holiday gifting in Nov-Dec, moderate Mother's Day bump."""
    month = d.month
    monthly = {
        1: 0.75, 2: 0.78, 3: 0.82, 4: 0.88, 5: 1.05,
        6: 0.85, 7: 0.80, 8: 0.82, 9: 0.90, 10: 1.05,
        11: 1.45, 12: 1.50,
    }
    return monthly.get(month, 1.0)


def generate_sales_series(
    rng: random.Random,
    baseline: float,
    archetype: str,
    category: str,
    dates: list[date],
) -> list[int]:
    """Generate a 104-week sales series for a given archetype."""
    sales = []
    for i, d in enumerate(dates):
        week_frac = i / len(dates)

        # Base seasonality
        if category == "Outdoor":
            season = spring_seasonality(d)
        elif category == "Kitchen":
            season = kitchen_seasonality(d)
        else:
            season = seasonality_factor(d)

        # Archetype-specific modulation
        if archetype == "steady":
            trend = 1.0
        elif archetype == "seasonal_peak":
            # Extra Q4 amplification
            season = 1.0 + (season - 1.0) * 1.6
            trend = 1.0
        elif archetype == "spring_bump":
            season = spring_seasonality(d)
            trend = 1.0
        elif archetype == "slow_decline":
            trend = max(0.55, 1.0 - week_frac * 0.45)
        elif archetype == "growth_ramp":
            trend = 1.0 + week_frac * 0.5
        elif archetype == "viral_micro_spike":
            # Small spike around week 60-65
            spike_center = 62
            dist = abs(i - spike_center)
            spike = max(0, 1.8 - dist * 0.3) if dist < 6 else 0
            trend = 1.0 + spike
        elif archetype == "choppy":
            trend = 1.0 + rng.gauss(0, 0.25)
        else:
            trend = 1.0

        noise = rng.gauss(1.0, 0.08)
        value = baseline * season * trend * noise
        sales.append(max(0, round(value)))

    return sales


def generate_google_trends(
    rng: random.Random,
    sales: list[int],
    dates: list[date],
    archetype: str,
) -> list[float]:
    """
    Generate search index correlated to sales with 2-3 week lead.
    Normalized 0-100 scale.
    """
    max_sale = max(sales) if max(sales) > 0 else 1
    trends = []
    for i, d in enumerate(dates):
        # Look ahead 2-3 weeks for the sales signal
        future_idx = min(i + 2, len(sales) - 1)
        future_sale = sales[future_idx]

        # Base correlation: search is roughly proportional to upcoming sales
        base = (future_sale / max_sale) * 70 + rng.gauss(0, 5)

        # Archetype modulations
        if archetype == "slow_decline":
            # Search declines faster than sales (leading indicator)
            decay = max(0.3, 1.0 - (i / len(dates)) * 0.7)
            base *= decay
        elif archetype == "growth_ramp":
            # Search rises ahead of sales
            ramp = 1.0 + (i / len(dates)) * 0.4
            base *= ramp

        trends.append(max(0, min(100, round(base, 1))))

    return trends


def generate_housing_permits(
    rng: random.Random,
    metro_idx: int,
    dates: list[date],
) -> list[int]:
    """Generate monthly housing permit counts for a metro area, sampled weekly."""
    metro = METRO_AREAS[metro_idx % len(METRO_AREAS)]
    permits = []
    for i, d in enumerate(dates):
        month_offset = i / 4.33  # Approximate weeks to months
        # Trend growth
        trend = 1.0 + metro["growth"] * month_offset
        # Seasonal construction pattern (spring/summer peak)
        month = d.month
        construction_season = {
            1: 0.65, 2: 0.70, 3: 0.90, 4: 1.10, 5: 1.20,
            6: 1.25, 7: 1.20, 8: 1.15, 9: 1.05, 10: 0.90,
            11: 0.75, 12: 0.60,
        }
        season = construction_season.get(month, 1.0)
        noise = rng.gauss(1.0, 0.06)
        value = metro["baseline_permits"] * trend * season * noise
        permits.append(max(0, round(value)))

    return permits


def generate_mortgage_apps(rng: random.Random, dates: list[date]) -> list[float]:
    """
    MBA Purchase Applications Index (national, same for all SKUs).
    Realistic range: 140-280.
    """
    values = []
    for i, d in enumerate(dates):
        # Base level with rate-sensitive fluctuation
        base = 210
        # Seasonal: spring purchase season peak
        month = d.month
        seasonal = {
            1: 0.85, 2: 0.92, 3: 1.08, 4: 1.15, 5: 1.12,
            6: 1.05, 7: 0.98, 8: 0.95, 9: 0.90, 10: 0.88,
            11: 0.82, 12: 0.78,
        }
        season = seasonal.get(month, 1.0)
        # Gradual rate-driven decline 2024-2026
        week_frac = i / len(dates)
        rate_effect = 1.0 - week_frac * 0.12
        noise = rng.gauss(1.0, 0.04)
        value = base * season * rate_effect * noise
        values.append(round(value, 1))

    return values


# ---------------------------------------------------------------------------
# Hand-crafted demo scenarios
# ---------------------------------------------------------------------------
def craft_demo_skus(dates: list[date], mortgage_series: list[float]) -> dict:
    """
    Returns a dict of {sku_id: {meta, sales, signals}} for the 6 PRD demo SKUs.
    """
    rng = random.Random(SEED + 999)
    demos = {}

    # --- PB-BLANKET-42: Viral spike (influencer post March 12, 2026) ---
    sku_id = "PB-BLANKET-42"
    baseline_sales = 124
    sales = []
    trends_sig = []
    social_sig = []

    influencer_date = date(2026, 3, 12)

    for i, d in enumerate(dates):
        season = seasonality_factor(d)

        # Check distance to influencer event
        days_from_event = (d - influencer_date).days
        weeks_from_event = days_from_event / 7

        if weeks_from_event < -2:
            # Pre-event: normal
            sale = baseline_sales * season * rng.gauss(1.0, 0.06)
            trend = rng.gauss(10, 2)
            social = 0
        elif -2 <= weeks_from_event < 0:
            # Search starts rising before sales
            sale = baseline_sales * season * rng.gauss(1.05, 0.05)
            trend = 10 + (weeks_from_event + 2) * 25
            social = 0
        elif 0 <= weeks_from_event < 1:
            # Week of the event
            sale = baseline_sales * season * 2.2
            trend = 89
            social = 2400000  # Influencer reach
        elif 1 <= weeks_from_event < 2:
            sale = 412 * rng.gauss(1.0, 0.05)
            trend = 82
            social = 0
        elif 2 <= weeks_from_event < 3:
            sale = 680 * rng.gauss(1.0, 0.05)
            trend = 71
            social = 0
        elif 3 <= weeks_from_event < 4:
            sale = 540 * rng.gauss(1.0, 0.05)
            trend = 58
            social = 0
        else:
            # Gradually tail off
            decay = max(0.8, 1.0 - (weeks_from_event - 4) * 0.08)
            sale = baseline_sales * season * decay * 1.6 * rng.gauss(1.0, 0.08)
            trend = max(12, 58 - (weeks_from_event - 4) * 6)
            social = 0

        sales.append(max(0, round(sale)))
        trends_sig.append(max(0, min(100, round(trend, 1))))
        social_sig.append(social)

    metro_permits = generate_housing_permits(rng, 5, dates)  # LA area

    demos[sku_id] = {
        "meta": {
            "product_name": "Throw Blanket, Cognac",
            "brand": "Pottery Barn",
            "category": "Bedding",
            "price": 89.00,
            "cost_price": 38.50,
            "lead_time_days": 70,
            "stock_on_hand": 6200,
            "on_order": 0,
            "warehouse_id": "City of Industry DC, CA",
        },
        "sales": sales,
        "signals": {
            "google_trends": trends_sig,
            "housing_permit": metro_permits,
            "social": social_sig,
            "mortgage_apps": mortgage_series,
        },
    }

    # --- PB-PILLOW-71: Silent overstock (trend peaked Feb, declining) ---
    sku_id = "PB-PILLOW-71"
    sales = []
    trends_sig = []

    peak_date = date(2026, 2, 10)

    for i, d in enumerate(dates):
        season = seasonality_factor(d)
        days_from_peak = (d - peak_date).days
        weeks_from_peak = days_from_peak / 7

        if weeks_from_peak < -12:
            # Pre-hype: moderate growth
            growth = 1.0 + max(0, (weeks_from_peak + 40) * 0.02)
            sale = 95 * season * growth * rng.gauss(1.0, 0.07)
            trend = min(55, 15 + max(0, (weeks_from_peak + 40) * 1.0))
        elif -12 <= weeks_from_peak < 0:
            # Rising toward peak
            ramp = 1.0 + (12 + weeks_from_peak) / 12 * 1.2
            sale = 95 * season * ramp * rng.gauss(1.0, 0.06)
            trend = min(78, 55 + (12 + weeks_from_peak) * 1.9)
        elif 0 <= weeks_from_peak < 2:
            # Peak weeks
            sale = 210 * season * rng.gauss(1.0, 0.05)
            trend = 78 - weeks_from_peak * 3
        else:
            # Declining
            decay = max(0.22, 1.0 - weeks_from_peak * 0.05)
            sale = 210 * season * decay * rng.gauss(1.0, 0.08)
            trend = max(8, 72 - weeks_from_peak * 4.5)

        sales.append(max(0, round(sale)))
        trends_sig.append(max(0, min(100, round(trend, 1))))

    metro_permits = generate_housing_permits(rng, 1, dates)  # Charlotte

    demos[sku_id] = {
        "meta": {
            "product_name": "Decorative Pillow, Sage",
            "brand": "Pottery Barn",
            "category": "Decor",
            "price": 59.50,
            "cost_price": 24.00,
            "lead_time_days": 56,
            "stock_on_hand": 4200,
            "on_order": 800,
            "warehouse_id": "South Brunswick DC, NJ",
        },
        "sales": sales,
        "signals": {
            "google_trends": trends_sig,
            "housing_permit": metro_permits,
            "social": [0] * NUM_WEEKS,
            "mortgage_apps": mortgage_series,
        },
    }

    # --- PB-BED-FRAME-33: Housing permit leading indicator (Phoenix) ---
    sku_id = "PB-BED-FRAME-33"
    sales = []
    trends_sig = []

    # Phoenix permits spike starting ~8 weeks before April 2026
    phoenix_permits = []
    permit_spike_start = date(2026, 1, 20)

    for i, d in enumerate(dates):
        season = seasonality_factor(d)
        days_from_spike = (d - permit_spike_start).days
        weeks_from_spike = days_from_spike / 7

        # Sales: steady, with a FUTURE uptick only after search catches up
        if weeks_from_spike < 8:
            sale = 34 * season * rng.gauss(1.0, 0.08)
            trend = rng.gauss(12, 2)
        elif 8 <= weeks_from_spike < 12:
            # Search just starting to tick up
            sale = 34 * season * (1.0 + (weeks_from_spike - 8) * 0.06) * rng.gauss(1.0, 0.07)
            trend = 12 + (weeks_from_spike - 8) * 4
        else:
            # Demand beginning to arrive (but demo shows it BEFORE this)
            sale = 34 * season * 1.3 * rng.gauss(1.0, 0.08)
            trend = 26 + rng.gauss(0, 3)

        sales.append(max(0, round(sale)))
        trends_sig.append(max(0, min(100, round(trend, 1))))

        # Phoenix permits: spike in construction
        metro = METRO_AREAS[0]  # Phoenix
        month_offset = i / 4.33
        base_trend = 1.0 + metro["growth"] * month_offset
        construction_season = {
            1: 0.65, 2: 0.70, 3: 0.90, 4: 1.10, 5: 1.20,
            6: 1.25, 7: 1.20, 8: 1.15, 9: 1.05, 10: 0.90,
            11: 0.75, 12: 0.60,
        }
        cs = construction_season.get(d.month, 1.0)

        # The spike: +34% MoM starting at permit_spike_start
        if 0 <= weeks_from_spike < 12:
            permit_boost = 1.0 + 0.34 * min(1.0, weeks_from_spike / 4)
        elif weeks_from_spike >= 12:
            permit_boost = 1.34
        else:
            permit_boost = 1.0

        permit_val = metro["baseline_permits"] * base_trend * cs * permit_boost * rng.gauss(1.0, 0.05)
        phoenix_permits.append(max(0, round(permit_val)))

    demos[sku_id] = {
        "meta": {
            "product_name": "Bedroom Set, King",
            "brand": "Pottery Barn",
            "category": "Furniture",
            "price": 1899.00,
            "cost_price": 820.00,
            "lead_time_days": 84,
            "stock_on_hand": 860,
            "on_order": 240,
            "warehouse_id": "Litchfield Park DC, AZ",
        },
        "sales": sales,
        "signals": {
            "google_trends": trends_sig,
            "housing_permit": phoenix_permits,
            "social": [0] * NUM_WEEKS,
            "mortgage_apps": mortgage_series,
        },
    }

    # --- WE-LAMP-19: Stable baseline (control) ---
    sku_id = "WE-LAMP-19"
    sales = []
    trends_sig = []

    for d in dates:
        season = seasonality_factor(d)
        sale = 67 * season * rng.gauss(1.0, 0.07)
        trend = rng.gauss(18, 3)
        sales.append(max(0, round(sale)))
        trends_sig.append(max(0, min(100, round(trend, 1))))

    demos[sku_id] = {
        "meta": {
            "product_name": "Table Lamp, Brass",
            "brand": "West Elm",
            "category": "Lighting",
            "price": 149.00,
            "cost_price": 62.00,
            "lead_time_days": 42,
            "stock_on_hand": 890,
            "on_order": 120,
            "warehouse_id": "Tracy DC, CA",
        },
        "sales": sales,
        "signals": {
            "google_trends": trends_sig,
            "housing_permit": generate_housing_permits(rng, 7, dates),
            "social": [0] * NUM_WEEKS,
            "mortgage_apps": mortgage_series,
        },
    }

    # --- WS-MIXER-55: Seasonal holiday spike approaching ---
    sku_id = "WS-MIXER-55"
    sales = []
    trends_sig = []

    for d in dates:
        season = kitchen_seasonality(d)
        sale = 85 * season * rng.gauss(1.0, 0.06)
        # Search leads: gifting search rises in Sept-Oct
        month_search = {
            1: 12, 2: 10, 3: 11, 4: 13, 5: 18,
            6: 12, 7: 10, 8: 14, 9: 32, 10: 55,
            11: 78, 12: 65,
        }
        trend = month_search.get(d.month, 15) + rng.gauss(0, 4)
        sales.append(max(0, round(sale)))
        trends_sig.append(max(0, min(100, round(trend, 1))))

    demos[sku_id] = {
        "meta": {
            "product_name": "Stand Mixer, Heritage",
            "brand": "Williams Sonoma",
            "category": "Kitchen",
            "price": 449.95,
            "cost_price": 185.00,
            "lead_time_days": 42,
            "stock_on_hand": 1450,
            "on_order": 600,
            "warehouse_id": "Memphis DC, TN",
        },
        "sales": sales,
        "signals": {
            "google_trends": trends_sig,
            "housing_permit": generate_housing_permits(rng, 8, dates),
            "social": [0] * NUM_WEEKS,
            "mortgage_apps": mortgage_series,
        },
    }

    # --- PBK-CRIB-12: Housing-driven baby furniture demand ---
    sku_id = "PBK-CRIB-12"
    sales = []
    trends_sig = []

    # Denver metro permits rising → nursery furniture demand
    denver_permits = []
    permit_rise_start = date(2025, 11, 1)

    for i, d in enumerate(dates):
        season = seasonality_factor(d)
        days_from_rise = (d - permit_rise_start).days
        weeks_from_rise = days_from_rise / 7

        if weeks_from_rise < 0:
            sale = 22 * season * rng.gauss(1.0, 0.09)
            trend = rng.gauss(8, 2)
        elif 0 <= weeks_from_rise < 16:
            # Gradual demand increase lagging permits by ~8 weeks
            lag_effect = max(0, weeks_from_rise - 8) / 8
            sale = 22 * season * (1.0 + lag_effect * 0.5) * rng.gauss(1.0, 0.08)
            trend = 8 + max(0, weeks_from_rise - 6) * 1.5
        else:
            sale = 22 * season * 1.5 * rng.gauss(1.0, 0.08)
            trend = min(45, 8 + (weeks_from_rise - 6) * 1.5) + rng.gauss(0, 2)

        sales.append(max(0, round(sale)))
        trends_sig.append(max(0, min(100, round(trend, 1))))

        # Denver permits with sustained growth
        metro = METRO_AREAS[3]  # Denver
        month_offset = i / 4.33
        base_trend = 1.0 + metro["growth"] * month_offset
        cs = {1: 0.45, 2: 0.50, 3: 0.85, 4: 1.10, 5: 1.30,
              6: 1.35, 7: 1.30, 8: 1.20, 9: 1.00, 10: 0.80,
              11: 0.55, 12: 0.40}.get(d.month, 1.0)
        permit_boost = 1.0 + max(0, weeks_from_rise) * 0.012 if weeks_from_rise >= 0 else 1.0
        permit_val = metro["baseline_permits"] * base_trend * cs * permit_boost * rng.gauss(1.0, 0.06)
        denver_permits.append(max(0, round(permit_val)))

    demos[sku_id] = {
        "meta": {
            "product_name": "Convertible Crib, White",
            "brand": "Pottery Barn Kids",
            "category": "Furniture",
            "price": 699.00,
            "cost_price": 295.00,
            "lead_time_days": 56,
            "stock_on_hand": 340,
            "on_order": 80,
            "warehouse_id": "Denver, CO",  # Hub
        },
        "sales": sales,
        "signals": {
            "google_trends": trends_sig,
            "housing_permit": denver_permits,
            "social": [0] * NUM_WEEKS,
            "mortgage_apps": mortgage_series,
        },
    }

    return demos


# ---------------------------------------------------------------------------
# Programmatic SKU generation
# ---------------------------------------------------------------------------
def generate_programmatic_skus(
    rng: random.Random,
    dates: list[date],
    mortgage_series: list[float],
    existing_ids: set[str],
) -> dict:
    """Generate ~79 programmatic SKUs across all brands/categories."""
    skus = {}
    sku_counter = {}
    used_names: set[str] = set()

    # Build a flat list of (brand, category) slots to fill
    target_counts = {
        ("Pottery Barn", "Bedding"): 5, ("Pottery Barn", "Furniture"): 6,
        ("Pottery Barn", "Decor"): 5, ("Pottery Barn", "Lighting"): 3,
        ("Pottery Barn", "Bath"): 2, ("Pottery Barn", "Rugs"): 2,
        ("Pottery Barn", "Outdoor"): 2,
        ("West Elm", "Furniture"): 5, ("West Elm", "Decor"): 5,
        ("West Elm", "Lighting"): 3, ("West Elm", "Bedding"): 4,
        ("West Elm", "Rugs"): 2,
        ("Williams Sonoma", "Kitchen"): 7, ("Williams Sonoma", "Decor"): 3,
        ("Williams Sonoma", "Outdoor"): 2,
        ("Pottery Barn Kids", "Furniture"): 3, ("Pottery Barn Kids", "Bedding"): 3,
        ("Pottery Barn Kids", "Decor"): 3, ("Pottery Barn Kids", "Bath"): 2,
        ("Rejuvenation", "Lighting"): 5, ("Rejuvenation", "Bath"): 3,
        ("Rejuvenation", "Furniture"): 3,
    }

    for (brand_name, category), count in target_counts.items():
        brand_cfg = BRANDS[brand_name]
        cat_cfg = brand_cfg["categories"].get(category)
        if not cat_cfg:
            continue

        prefix = brand_cfg["prefix"]
        cat_short = category[:3].upper()
        templates = PRODUCT_TEMPLATES.get(category, ["Item"])

        for _ in range(count):
            # Generate unique SKU ID
            key = f"{prefix}-{cat_short}"
            sku_counter[key] = sku_counter.get(key, 0) + 1
            num = sku_counter[key]
            sku_id = f"{prefix}-{cat_short}-{num:02d}"

            # Skip if conflicts with demo SKUs
            if sku_id in existing_ids:
                sku_counter[key] += 1
                num = sku_counter[key]
                sku_id = f"{prefix}-{cat_short}-{num:02d}"

            # Pick product name
            template = rng.choice(templates)
            finish = rng.choice(FINISHES)
            product_name = f"{template}, {finish}"
            # Avoid duplicates
            while product_name in used_names:
                finish = rng.choice(FINISHES)
                product_name = f"{template}, {finish}"
            used_names.add(product_name)

            # Price and cost
            price_lo, price_hi = cat_cfg["price_range"]
            price = round(rng.uniform(price_lo, price_hi), 2)
            # Round to .00 or .95 for realism
            price = round(price / 5) * 5 - 0.05 if price > 50 else round(price, 2)
            if price <= 0:
                price = price_lo
            cost_ratio = rng.uniform(0.38, 0.55)
            cost_price = round(price * cost_ratio, 2)

            # Lead time
            lead_lo, lead_hi = cat_cfg["lead_range"]
            lead_time = rng.randint(lead_lo // 7, lead_hi // 7) * 7  # Round to weeks

            # Baseline sales
            base_lo, base_hi = cat_cfg["baseline_range"]
            baseline = rng.uniform(base_lo, base_hi)

            # Archetype
            archetype = rng.choices(ARCHETYPES, weights=ARCHETYPE_WEIGHTS, k=1)[0]

            # Generate sales
            sales = generate_sales_series(rng, baseline, archetype, category, dates)

            # Generate signals
            trends = generate_google_trends(rng, sales, dates, archetype)
            metro_idx = rng.randint(0, len(METRO_AREAS) - 1)
            permits = generate_housing_permits(rng, metro_idx, dates)

            # Inventory snapshot (current state based on recent sales)
            recent_avg = max(1, sum(sales[-8:]) / 8)
            rolling_daily = recent_avg / 7

            # Stock levels based on archetype
            if archetype == "slow_decline":
                # Declining demand → likely overstock
                stock = round(rng.uniform(2.5, 4.0) * lead_time * rolling_daily)
                on_order = round(rng.uniform(0.3, 0.8) * lead_time * rolling_daily)
            elif archetype == "growth_ramp":
                # Growing demand → possibly understocked
                stock = round(rng.uniform(0.6, 1.2) * lead_time * rolling_daily)
                on_order = round(rng.uniform(0.5, 1.0) * lead_time * rolling_daily)
            elif archetype == "viral_micro_spike":
                stock = round(rng.uniform(0.8, 1.5) * lead_time * rolling_daily)
                on_order = round(rng.uniform(0.2, 0.6) * lead_time * rolling_daily)
            else:
                stock = round(rng.uniform(1.0, 2.0) * lead_time * rolling_daily)
                on_order = round(rng.uniform(0.3, 0.8) * lead_time * rolling_daily)

            warehouse = rng.choice(DC_LIST)

            skus[sku_id] = {
                "meta": {
                    "product_name": product_name,
                    "brand": brand_name,
                    "category": category,
                    "price": price,
                    "cost_price": cost_price,
                    "lead_time_days": lead_time,
                    "stock_on_hand": max(0, stock),
                    "on_order": max(0, on_order),
                    "warehouse_id": warehouse,
                },
                "sales": sales,
                "signals": {
                    "google_trends": trends,
                    "housing_permit": permits,
                    "social": [0] * NUM_WEEKS,
                    "mortgage_apps": mortgage_series,
                },
            }

    return skus


# ---------------------------------------------------------------------------
# Risk classification (derived, not hardcoded)
# ---------------------------------------------------------------------------
def classify_risk(meta: dict, sales: list[int]) -> tuple[str, str, str]:
    """
    Derive risk level from inventory metrics.
    Returns (risk_level, primary_signal, recommended_action).
    """
    stock = meta["stock_on_hand"]
    on_order = meta["on_order"]
    lead_time = meta["lead_time_days"]

    recent_sales = sales[-4:]  # Last 4 weeks
    avg_weekly = max(0.1, sum(recent_sales) / len(recent_sales))
    daily_rate = avg_weekly / 7
    days_of_supply = (stock + on_order) / daily_rate if daily_rate > 0 else 999

    # Velocity: compare last 4 weeks to prior 4 weeks
    prior_sales = sales[-8:-4]
    avg_prior = max(0.1, sum(prior_sales) / len(prior_sales))
    velocity = (avg_weekly - avg_prior) / avg_prior

    # 60-day forecast (simple linear projection)
    forecast_60d = round(avg_weekly * (60 / 7))

    if days_of_supply < lead_time and forecast_60d > stock + on_order:
        risk = "STOCKOUT_RISK"
        signal = f"Demand velocity +{round(velocity * 100)}%" if velocity > 0.1 else "Low supply coverage"
        action = "Expedite supplementary order"
    elif days_of_supply < lead_time * 1.3 and velocity > 0.3:
        risk = "STOCKOUT_RISK"
        signal = f"Acceleration +{round(velocity * 100)}% WoW"
        action = "Expedite order or source alternate vendor"
    elif days_of_supply > lead_time * 3 and velocity < -0.1:
        risk = "OVERSTOCK_RISK"
        signal = f"Demand declining {round(abs(velocity) * 100)}%"
        action = "Consider markdown or cancel pending orders"
    elif days_of_supply > lead_time * 2.5:
        risk = "OVERSTOCK_RISK"
        signal = "Excess inventory vs. demand rate"
        action = "Review replenishment cadence"
    elif abs(velocity) > 0.2 or (days_of_supply < lead_time * 1.5 and velocity > 0.1):
        risk = "WATCH"
        signal = f"Velocity shift {'+' if velocity > 0 else ''}{round(velocity * 100)}%"
        action = "Monitor for 2 weeks before acting"
    else:
        risk = "OK"
        signal = "Stable demand pattern"
        action = "Maintain current replenishment"

    return risk, signal, action


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------
def write_sales_csv(all_skus: dict, dates: list[date], output_path: Path) -> None:
    """Write sales.csv: one row per SKU per week."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "sku_id", "date", "units_sold", "store_id", "category", "price", "brand",
        ])
        writer.writeheader()
        for sku_id in sorted(all_skus.keys()):
            data = all_skus[sku_id]
            meta = data["meta"]
            for i, d in enumerate(dates):
                writer.writerow({
                    "sku_id": sku_id,
                    "date": d.isoformat(),
                    "units_sold": data["sales"][i],
                    "store_id": "ALL",
                    "category": meta["category"],
                    "price": meta["price"],
                    "brand": meta["brand"],
                })


def write_signals_csv(all_skus: dict, dates: list[date], output_path: Path) -> None:
    """Write signals.csv: one row per SKU per week per signal type."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "date", "sku_id", "signal_type", "value", "source",
        ])
        writer.writeheader()
        for sku_id in sorted(all_skus.keys()):
            signals = all_skus[sku_id]["signals"]
            for i, d in enumerate(dates):
                # Google Trends
                writer.writerow({
                    "date": d.isoformat(),
                    "sku_id": sku_id,
                    "signal_type": "google_trends",
                    "value": signals["google_trends"][i],
                    "source": "pytrends",
                })
                # Housing Permits
                writer.writerow({
                    "date": d.isoformat(),
                    "sku_id": sku_id,
                    "signal_type": "housing_permit",
                    "value": signals["housing_permit"][i],
                    "source": "census_bps",
                })
                # Mortgage Apps
                writer.writerow({
                    "date": d.isoformat(),
                    "sku_id": sku_id,
                    "signal_type": "mortgage_apps",
                    "value": signals["mortgage_apps"][i],
                    "source": "fred",
                })
                # Social (only write non-zero)
                if signals["social"][i] > 0:
                    writer.writerow({
                        "date": d.isoformat(),
                        "sku_id": sku_id,
                        "signal_type": "social",
                        "value": signals["social"][i],
                        "source": "instagram_proxy",
                    })


def write_inventory_csv(all_skus: dict, dates: list[date], output_path: Path) -> None:
    """Write inventory.csv: point-in-time snapshot with derived fields."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "sku_id", "product_name", "brand", "category",
            "warehouse_id", "stock_on_hand", "on_order", "lead_time_days",
            "unit_price", "cost_price",
            "days_of_supply", "risk_level", "primary_signal", "recommended_action",
            "avg_weekly_sales", "forecast_demand_60d",
        ])
        writer.writeheader()
        for sku_id in sorted(all_skus.keys()):
            data = all_skus[sku_id]
            meta = data["meta"]
            sales = data["sales"]

            risk, signal, action = classify_risk(meta, sales)

            # Override risk for demo SKUs to match PRD exactly
            if sku_id == "PB-BLANKET-42":
                risk = "STOCKOUT_RISK"
                signal = "Search spike +840% WoW"
                action = "Expedite supplementary order"
            elif sku_id == "PB-PILLOW-71":
                risk = "OVERSTOCK_RISK"
                signal = "Search declining 23% over 8 weeks"
                action = "Consider markdown trigger"
            elif sku_id == "PB-BED-FRAME-33":
                risk = "WATCH"
                signal = "Housing permits +34% MoM Phoenix"
                action = "Pre-position 400 units to AZ DC"
            elif sku_id == "WE-LAMP-19":
                risk = "OK"
                signal = "Stable demand pattern"
                action = "Maintain current replenishment"
            elif sku_id == "WS-MIXER-55":
                risk = "WATCH"
                signal = "Holiday gifting search rising"
                action = "Increase holiday order 20%"
            elif sku_id == "PBK-CRIB-12":
                risk = "WATCH"
                signal = "Housing permits rising Denver metro"
                action = "Pre-position to Denver Hub"

            recent_avg = max(0.1, sum(sales[-4:]) / 4)
            daily_rate = recent_avg / 7
            dos = round((meta["stock_on_hand"] + meta["on_order"]) / daily_rate) if daily_rate > 0 else 999
            forecast_60d = round(recent_avg * (60 / 7))

            writer.writerow({
                "sku_id": sku_id,
                "product_name": meta["product_name"],
                "brand": meta["brand"],
                "category": meta["category"],
                "warehouse_id": meta["warehouse_id"],
                "stock_on_hand": meta["stock_on_hand"],
                "on_order": meta["on_order"],
                "lead_time_days": meta["lead_time_days"],
                "unit_price": meta["price"],
                "cost_price": meta["cost_price"],
                "days_of_supply": dos,
                "risk_level": risk,
                "primary_signal": signal,
                "recommended_action": action,
                "avg_weekly_sales": round(recent_avg, 1),
                "forecast_demand_60d": forecast_60d,
            })


def write_frontend_json(all_skus: dict, dates: list[date], output_path: Path) -> None:
    """
    Write a JSON file that can be imported into the frontend data.js.
    Contains the full SKU table + per-SKU chart data for the demo SKUs.
    """
    sku_table = []
    chart_data = {}

    for sku_id in sorted(all_skus.keys()):
        data = all_skus[sku_id]
        meta = data["meta"]
        sales = data["sales"]

        risk, signal, action = classify_risk(meta, sales)

        # Override demo SKUs
        if sku_id == "PB-BLANKET-42":
            risk, signal, action = "STOCKOUT_RISK", "Search spike +840%", "Expedite Order"
        elif sku_id == "PB-PILLOW-71":
            risk, signal, action = "OVERSTOCK_RISK", "Search decline -23%", "Markdown Trigger"
        elif sku_id == "PB-BED-FRAME-33":
            risk, signal, action = "WATCH", "Housing permits +34%", "Pre-position 400"
        elif sku_id == "WE-LAMP-19":
            risk, signal, action = "OK", "Baseline", "None"
        elif sku_id == "WS-MIXER-55":
            risk, signal, action = "WATCH", "Holiday search rising", "Increase Order +20%"
        elif sku_id == "PBK-CRIB-12":
            risk, signal, action = "WATCH", "Housing permits Denver", "Pre-position to Denver"

        recent_avg = max(0.1, sum(sales[-4:]) / 4)
        daily_rate = recent_avg / 7
        dos = round((meta["stock_on_hand"] + meta["on_order"]) / daily_rate) if daily_rate > 0 else 999

        sku_table.append({
            "id": sku_id,
            "name": meta["product_name"],
            "brand": meta["brand"],
            "category": meta["category"],
            "stock": meta["stock_on_hand"],
            "onOrder": meta["on_order"],
            "daysOfSupply": dos,
            "leadTimeDays": meta["lead_time_days"],
            "riskLevel": risk,
            "signal": signal,
            "action": action,
            "price": meta["price"],
        })

        # Chart data: last 12 weeks for ALL SKUs (signal timeline)
        chart_weeks = []
        start_idx = max(0, len(dates) - 12)
        for i in range(start_idx, len(dates)):
            chart_weeks.append({
                "name": f"Week {i - len(dates) + 1}" if i < len(dates) - 1 else "Current",
                "sales": sales[i],
                "search": data["signals"]["google_trends"][i],
                "permits": data["signals"]["housing_permit"][i],
            })
        chart_data[sku_id] = chart_weeks

    output = {
        "skuTable": sku_table,
        "chartData": chart_data,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    rng = random.Random(SEED)
    dates = week_dates()

    # National mortgage apps series (shared across all SKUs)
    mortgage_series = generate_mortgage_apps(rng, dates)

    print(f"Generating data for {NUM_WEEKS} weeks ({dates[0]} to {dates[-1]})")

    # Phase 1: Hand-crafted demo SKUs
    demo_skus = craft_demo_skus(dates, mortgage_series)
    print(f"  Demo SKUs: {len(demo_skus)} ({', '.join(demo_skus.keys())})")

    # Phase 2: Programmatic SKUs
    prog_skus = generate_programmatic_skus(rng, dates, mortgage_series, set(demo_skus.keys()))
    print(f"  Programmatic SKUs: {len(prog_skus)}")

    # Merge
    all_skus = {**demo_skus, **prog_skus}
    print(f"  Total SKUs: {len(all_skus)}")

    # Write outputs
    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    sales_path = data_dir / "sales.csv"
    write_sales_csv(all_skus, dates, sales_path)
    # Count rows
    with open(sales_path, encoding="utf-8") as f:
        sales_rows = sum(1 for _ in f) - 1
    print(f"  sales.csv: {sales_rows} rows -> {sales_path}")

    signals_path = data_dir / "signals.csv"
    write_signals_csv(all_skus, dates, signals_path)
    with open(signals_path, encoding="utf-8") as f:
        signals_rows = sum(1 for _ in f) - 1
    print(f"  signals.csv: {signals_rows} rows -> {signals_path}")

    inventory_path = data_dir / "inventory.csv"
    write_inventory_csv(all_skus, dates, inventory_path)
    with open(inventory_path, encoding="utf-8") as f:
        inv_rows = sum(1 for _ in f) - 1
    print(f"  inventory.csv: {inv_rows} rows -> {inventory_path}")

    # Frontend JSON
    frontend_json = data_dir / "frontend_data.json"
    write_frontend_json(all_skus, dates, frontend_json)
    print(f"  frontend_data.json -> {frontend_json}")

    # Verification
    print("\n--- Verification ---")
    risk_counts = {"STOCKOUT_RISK": 0, "OVERSTOCK_RISK": 0, "WATCH": 0, "OK": 0}
    for sku_id, data in all_skus.items():
        risk, _, _ = classify_risk(data["meta"], data["sales"])
        # Use demo overrides
        if sku_id in ("PB-BLANKET-42",):
            risk = "STOCKOUT_RISK"
        elif sku_id in ("PB-PILLOW-71",):
            risk = "OVERSTOCK_RISK"
        elif sku_id in ("PB-BED-FRAME-33", "WS-MIXER-55", "PBK-CRIB-12"):
            risk = "WATCH"
        elif sku_id in ("WE-LAMP-19",):
            risk = "OK"
        risk_counts[risk] = risk_counts.get(risk, 0) + 1

    total = sum(risk_counts.values())
    for level, count in sorted(risk_counts.items()):
        print(f"  {level}: {count} ({count/total*100:.1f}%)")

    print(f"\n[OK] Dataset generation complete. {len(all_skus)} SKUs x {NUM_WEEKS} weeks.")


if __name__ == "__main__":
    main()
