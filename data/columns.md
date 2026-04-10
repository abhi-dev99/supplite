# Data Dictionary — Demand Intelligence System

## Overview

The synthetic dataset models **30 SKUs** across **11 US metro markets** over **365 days** of daily signals, enabling SKU-level demand surge detection for Williams-Sonoma Inc (WSI) brands.

### File Summary

| File | Rows | Description |
|---|---|---|
| `sku_daily_signals.csv` | 120,450 | Daily demand signals (30 SKUs × 11 metros × 365 days) |
| `sku_inventory.csv` | 330 | Current inventory snapshot (30 SKUs × 11 metros) |
| `sku_catalog.csv` | 30 | Product metadata catalog |
| `metro_profiles.csv` | 11 | Metro market profiles with income & DC data |
| `metro_dc_stores.csv` | 154 | Store → Metro → Distribution Center mapping |
| `demand_intelligence.db` | — | SQLite database containing all tables above |

---

## sku_daily_signals.csv

The core signals table. Each row represents one SKU's performance in one metro on one day.

| Column | Type | Example | Description |
|---|---|---|---|
| `day_index` | int | `0` – `364` | Sequential day counter. 0 = oldest (2025-04-11), 364 = most recent (2026-04-10) |
| `date` | string | `2025-04-11` | ISO date (YYYY-MM-DD) |
| `sku_id` | string | `PB-BLANKET-42` | Unique product identifier. Prefix indicates brand (PB, WE, WS, PBK, RJ, MG) |
| `metro` | string | `Phoenix` | One of 11 metro markets (see metro_profiles.csv) |
| `units_sold` | int | `22` | Daily units sold in this metro. Adjusted for income level and seasonality |
| `search_index` | float | `14.2` | Google Trends-style search interest (0–100). Represents relative search volume for this product nationally |
| `housing_permits` | int | `1215` | Monthly new single-family housing permits in this metro (Census data). Stays roughly constant within a month |
| `median_income` | int | `89610` | Median household income for this metro (Census B19013, 2024 ACS). Static per metro |
| `income_factor` | float | `0.747` | Income premium factor = min(1.0, median_income / $120,000). Metros with income ≥ $120k get factor = 1.0. Used to weight real estate signals — only high-income RE development predicts WSI demand |
| `holiday_factor` | float | `0.02` – `1.0` | Proximity to major US holidays. 0.02 = normal day, 1.0 = peak holiday (Thanksgiving/Black Friday). Used in the 20% holiday scoring component |
| `sales_velocity_7d` | float | `+15.3` | % change: 7-day rolling average vs the prior 7-day period. Positive = accelerating demand |
| `sales_velocity_30d` | float | `+8.1` | % change: 30-day rolling average vs the prior 30-day period. Smoother, longer-term trend |
| `search_velocity_7d` | float | `+42.0` | % change in 7-day search rolling average vs prior 7-day period |
| `search_velocity_30d` | float | `+18.5` | % change in 30-day search rolling average vs prior 30-day period |
| `permit_velocity_30d` | float | `+12.8` | % change in 30-day permit rolling average vs prior 30-day period. Rising permits in high-income areas predict future furniture demand |
| `rolling_7d_avg_sales` | float | `18.4` | 7-day moving average of units_sold. Used for days-of-supply and forecast calculations |
| `surge_score` | float | `0.0` – `100.0` | Blended demand surge score. Weighted: Sales velocity (40%) + Income×RE (25%) + Holiday (20%) + Search (15%) |
| `scenario_type` | string | `A` | Scenario category code (see Scenario Types below) |

### Velocity Calculation Method

```
sales_velocity_7d  = ((avg of last 7 days) - (avg of days 8–14)) / (avg of days 8–14) × 100
sales_velocity_30d = ((avg of last 30 days) - (avg of days 31–60)) / (avg of days 31–60) × 100
```

### Surge Score Formula

```
surge_score = 0.40 × sales_component      (normalized 7d velocity → 0–100)
            + 0.25 × income_re_component   (permit_velocity_30d × income_factor, clamped 0–100)
            + 0.20 × holiday_component     (holiday_factor × 100)
            + 0.15 × search_component      (normalized 7d search velocity → 0–100)
```

**Why these weights?**
- **Sales (40%):** Actual orders are the most trusted signal. Trend ≠ sales; buyers must prioritize what's actually moving.
- **Income + Real Estate (25%):** Only new construction in HIGH-INCOME areas (≥$120k median) reliably predicts WSI furniture demand. A housing boom in a $60k-income area won't drive Pottery Barn sales.
- **Holiday (20%):** Seasonal gift-giving creates predictable demand spikes (Thanksgiving through Christmas). Baked into the score for proactive stock positioning.
- **Search (15%):** Social media virality is a leading indicator, but intentionally low-weighted because search hype does NOT always convert to sales. Prevents over-ordering on hype alone.

---

## sku_inventory.csv

Point-in-time inventory snapshot per SKU per metro market.

| Column | Type | Example | Description |
|---|---|---|---|
| `sku_id` | string | `PB-BED-33` | Product identifier |
| `metro` | string | `Phoenix` | Metro market |
| `product_name` | string | `Bedroom Set, King` | Human-readable product name |
| `brand` | string | `Pottery Barn` | WSI brand |
| `category` | string | `Furniture` | Product category |
| `price` | float | `1899.0` | Retail price (USD) |
| `stock_on_hand` | int | `860` | Current units in the metro's DC |
| `on_order` | int | `240` | Units on purchase order (in transit or production) |
| `lead_time_days` | int | `68` | Days from PO placement to DC receipt |
| `days_of_supply` | float | `180.2` | stock_on_hand / rolling_7d_avg_sales. How many days the current stock will last at current burn rate |
| `rolling_7d_avg_sales` | float | `4.8` | Average daily sales over last 7 days |
| `risk_level` | string | `WATCH` | Risk classification: `STOCKOUT_RISK`, `OVERSTOCK_RISK`, `WATCH`, `OK` |
| `surge_score` | float | `12.4` | Current day's surge score |
| `surge_flag` | string | `STEADY` | Direction: `SURGING` (delta_7d ≥ 15), `FADING` (delta_30d ≤ −10), `STEADY` |
| `surge_delta_7d` | float | `-2.1` | Change in surge score vs 7 days ago |
| `surge_delta_30d` | float | `-5.8` | Change in surge score vs 30 days ago |
| `primary_signal` | string | `housing_permit` | Which signal type is driving the current risk flag |
| `signal_detail` | string | `Phoenix SFH permits +34% MoM` | Human-readable explanation of the primary signal |
| `recommended_action` | string | `Pre-position 400 units to Arizona DC` | Suggested supply chain action |
| `forecast_demand_60d` | int | `288` | Projected units needed over next 60 days (rolling_7d_avg × 60) |
| `demand_shortfall` | int | `0` | max(0, forecast_60d − stock − on_order). Units gap if demand continues |
| `dc` | string | `Litchfield Park DC` | Distribution center serving this metro |
| `median_income` | int | `89610` | Metro median household income |
| `income_factor` | float | `0.747` | Income premium factor for this metro |
| `scenario_type` | string | `C` | Scenario category code |

### Risk Level Logic

| Risk | Condition |
|---|---|
| `STOCKOUT_RISK` | days_of_supply < lead_time_days × 1.2, OR (days_of_supply < lead_time AND surging) |
| `OVERSTOCK_RISK` | days_of_supply > lead_time_days × 2.5, OR (> 3× lead_time AND fading) |
| `WATCH` | Not at risk but surge_flag is SURGING or FADING |
| `OK` | Comfortable stock levels, steady demand |

---

## sku_catalog.csv

Product master data (30 SKUs).

| Column | Type | Description |
|---|---|---|
| `sku_id` | string | Unique product identifier |
| `product_name` | string | Human-readable name |
| `brand` | string | WSI brand (Pottery Barn, West Elm, Williams Sonoma, PB Kids, Rejuvenation, Mark & Graham) |
| `category` | string | Product category (Bedding, Decor, Furniture, Kitchen, Entertaining, Lighting, Outdoor, Accessories) |
| `price` | float | Retail price (USD) |
| `lead_time_days` | int | Manufacturing + shipping lead time |
| `scenario_type` | string | A–J (scripted) or R (random) |
| `scenario_label` | string | Human-readable scenario name |

### Brand Distribution

| Brand | SKU Count | Focus |
|---|---|---|
| Pottery Barn | 12 | Primary brand, broadest product range |
| West Elm | 8 | Modern/contemporary segment |
| Williams Sonoma | 5 | Kitchen & entertaining |
| Pottery Barn Kids | 2 | Children's furniture |
| Rejuvenation | 2 | Lighting specialty |
| Mark & Graham | 1 | Premium accessories |

---

## metro_profiles.csv

11 US metro market profiles with Census income data.

| Column | Type | Description |
|---|---|---|
| `metro` | string | Metro market name |
| `median_income` | int | Median household income (Census B19013, 2024 ACS) |
| `income_tier` | string | `Premium` (≥$120k), `High` (≥$100k), `Mid` (≥$85k), `Lower` (<$85k) |
| `income_factor` | float | min(1.0, income / $120,000) — premium multiplier |
| `dc_name` | string | Distribution center serving this metro |
| `dc_lat` | float | DC latitude |
| `dc_lon` | float | DC longitude |
| `base_permits_monthly` | int | Baseline monthly housing permit volume for this metro |

---

## metro_dc_stores.csv

Maps every WSI storefront to its serving metro area and distribution center.

| Column | Type | Description |
|---|---|---|
| `store_name` | string | Store address/name |
| `store_city` | string | City where store is located |
| `store_state` | string | US state (2-letter code) |
| `metro` | string | Assigned metro market (from the 11 metros) |
| `dc_name` | string | Distribution center that serves this store |

Supply chain path: **Store → Metro → DC**

Example: Scottsdale store → Phoenix metro → Litchfield Park DC

---

## Scenario Types

Each scripted scenario demonstrates a specific demand pattern that tests the surge detection engine's ability to classify risk correctly.

### A — Viral Spike (`PB-BLANKET-42`)
**Pattern:** Search explodes nationally (~day 309), sales follow 14 days later.
**Risk:** STOCKOUT_RISK + SURGING
**What it tests:** Can the system detect a sudden viral trend (e.g., TikTok/Instagram celebrity endorsement) and raise the alarm before existing stock runs out? The 14-day lag between search and sales is the early warning window.
**Key insight:** Search velocity leads sales velocity by ~2 weeks.

### B — Silent Overstock (`PB-PILLOW-71`)
**Pattern:** Trend peaked around day 180, search has been declining for months, but buyer hasn't adjusted orders.
**Risk:** OVERSTOCK_RISK + FADING
**What it tests:** Can the system detect a dying trend BEFORE the warehouse overflows? The search decline is the earliest signal that consumer interest is waning.
**Key insight:** Search fading before sales confirms a trend collapse.

### C — Housing Permit Leading Indicator (`PB-BED-33`)
**Pattern:** Search and sales are flat. But housing permits in Phoenix are climbing steadily from day 270 onward.
**Risk:** WATCH + STEADY (hero metro: Phoenix)
**What it tests:** This is the **differentiator**. Can the system detect future demand from construction activity when NO other signal is visible? New homes = new furniture needs, with a 60-90 day lag.
**Key insight:** Permits predict demand 2-3 months before search or sales data shows it. Only matters in high-income areas.

### D — Steady / OK (`WE-LAMP-19`)
**Pattern:** Everything normal — no spikes, no declines, no permit changes.
**Risk:** OK + STEADY
**What it tests:** The system should NOT raise false alarms. A steady product should stay "OK."
**Key insight:** Control scenario. If this triggers alerts, the thresholds are too sensitive.

### E — Seasonal Holiday Surge (`WS-MIXER-05`)
**Pattern:** Massive sales and search spike during Thanksgiving-Christmas (Nov 10 – Dec 25), followed by a post-holiday cliff.
**Risk:** WATCH during holiday season
**What it tests:** Stand mixers are classic holiday gifts. The system should use the holiday_factor to anticipate the surge and pre-position stock BEFORE Thanksgiving.
**Key insight:** The 20% holiday weight ensures seasonal products get flagged proactively.

### F — Multi-Signal Convergence (`PB-SOFA-88`)
**Pattern:** Both search AND housing permits rise simultaneously (from day 260), especially in Phoenix/Denver.
**Risk:** WATCH + SURGING (hero metro: Phoenix)
**What it tests:** When multiple independent signals converge, confidence should be highest. Search says "people want sofas" AND permits say "people are moving into new homes" = very strong buy signal.
**Key insight:** Convergence of search + RE in high-income areas is the strongest demand predictor.

### G — Post-Peak Overstock (`WE-RUG-15`)
**Pattern:** Trend peaked around day 140, has been declining for 7+ months. Inventory is still loaded from peak-era orders.
**Risk:** OVERSTOCK_RISK + FADING
**What it tests:** A longer, slower decline than Scenario B. The buyer ordered aggressively during the peak and never adjusted. Can the system detect this overhang?
**Key insight:** Long-term fading trends require markdown or PO cancellation.

### H — Sudden Demand Collapse (`PBK-BUNK-22`)
**Pattern:** Sales healthy until day 300, then abrupt collapse (product recall, competitor launch, safety concern).
**Risk:** OVERSTOCK_RISK + FADING
**What it tests:** Unlike a gradual fade, this is an instant cliff. The system must detect and flag the collapse within days, not weeks.
**Key insight:** Rapid sales_velocity_7d decline is the fastest indicator.

### I — Slow-Burn Growth (`RJ-PENDANT-11`)
**Pattern:** Gradual, compounding growth over the entire year. No spike, just steady upward.
**Risk:** Evolves from OK to STOCKOUT_RISK over time
**What it tests:** Not all demand changes are sudden. Can the system detect a product that's slowly becoming a bestseller before it hits a stockout?
**Key insight:** sales_velocity_30d catches slow trends that 7d misses.

### J — Flash in the Pan (`MG-TOTE-07`)
**Pattern:** Sharp spike at days 310-315, completely dies by day 325.
**Risk:** Should return to OK within 2 weeks
**What it tests:** A false alarm scenario. Celebrity tweets about the product, search spikes, but interest dies almost immediately. The system should NOT trigger a massive reorder.
**Key insight:** If search drops back to baseline within 10 days, it's not sustained — don't overreact.

### R — Random (Filler SKUs)
**Pattern:** One of: steady, gentle_up, gentle_down, mid_bump, noisy_flat, or late_uptick.
**Risk:** Varies
**What it tests:** Provides realistic background data volume and variety. Not all 30 SKUs should be edge cases.
