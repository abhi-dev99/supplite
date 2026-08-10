# Supplite

**Multi-Signal Demand Intelligence & Predictive Inventory Pre-Positioning for Williams-Sonoma, Inc.**

![Status](https://img.shields.io/badge/Status-Active-success)
![Stack](https://img.shields.io/badge/Stack-FastAPI%20%7C%20React%2019%20%7C%20Deck.gl-blue)
![ML](https://img.shields.io/badge/ML-RandomForest%20%7C%20IsolationForest-orange)
![License](https://img.shields.io/badge/License-Proprietary-red)

> Every other forecasting system sees demand after it happens. Supplite sees it 60 days before — and tells buyers exactly what to do about it.

---

## The Problem

WSI places furniture orders with 8–12 week overseas lead times. Current forecasting tools are backward-looking — they catch demand spikes 2–3 weeks after they start, by which point the reorder window has already closed.

Two failure modes happen simultaneously, across different SKUs, in the same company:
- **Stockout:** A product goes viral. Sales triple in two weeks. The last order was placed on historical averages. Nothing can be done.
- **Silent overstock:** A trend peaked undetected months ago. 4,000+ units pile up, consuming warehouse space and triggering forced markdowns.

Neither failure is visible in traditional ERP. There is no unified, forward-looking signal layer.

---

## Core USPs

### 1. 60-Day Real Estate Leading Signal
- A family signs a purchase agreement on a new home. They won't search for furniture for 5–6 more weeks. Sales won't spike for 9 weeks. But the building permit was filed 4 weeks ago.
- Supplite ingests live **US Census ACS housing tenure data** at ZIP Code Tabulation Area (ZCTA) granularity — owner/renter counts, YoY deltas, median rent — and trains a demand pressure model on 33,772 national ZCTAs.
- No other retail demand intelligence system uses housing permit data as a leading indicator. The WSI problem statement itself named this signal in Scenario 4.

### 2. Three-Signal Weighted Demand Scoring

| Signal | Weight | Lead Time |
|---|---|---|
| Historical sales velocity | 40% | Baseline |
| Real estate + metro income | 25% | 60–90 days |
| Holiday proximity calendar | 20% | 7–30 days |
| Google Trends search virality | 15% | 14–21 days |

- Covers 30 SKUs across 11 metro markets with 365 days of daily granularity
- 9 distinct demand scenario archetypes: `viral_spike`, `silent_overstock`, `housing_leading`, `multi_signal`, `seasonal_surge`, `sudden_collapse`, `post_peak_overstock`, `slow_burn`, `flash_pan`

### 3. Deterministic Risk Classifier — Zero Hallucination Risk

| Risk Level | Trigger Condition |
|---|---|
| `STOCKOUT_RISK` | Days of supply < lead time AND forecast demand exceeds stock + on-order |
| `OVERSTOCK_RISK` | Days of supply > 3× lead time AND search velocity declining >15% |
| `WATCH` | Anomaly detected, no immediate inventory breach |
| `OK` | All other cases |

- Pure rule-based logic — no LLM involvement in classification
- Every flag traces directly to a deterministic, auditable rule

### 4. LLM Executive Buyer Brief
- Pipes flagged SKU data — stock levels, signal details, demand shortfall, recommended actions — into the **Claude API** as a structured JSON context object
- Output: concise, dollar-impact-framed weekly brief in plain English. *"PB-BLANKET-42: 12,200 unit shortfall at $89/unit = $1.09M revenue at risk. Expedite supplementary order now."*
- Provider waterfall: Claude → OpenAI → deterministic offline fallback
- SHA-256 content hashing prevents redundant API calls; 3-attempt retry before fallback

### 5. Live National ZCTA Demand Heatmap
- Fetches up to 45,000 US ZCTAs from the Census API; auto-resolves to the latest published ACS year pair
- Returns per-ZCTA: `demand_index`, `owner_yoy_pct`, `renter_yoy_pct`, `housing_units_yoy_pct`, `median_rent_usd`, ML-predicted risk bucket
- In-memory TTL cache (configurable, default 60 min) — Census API downtime is fully shielded from the frontend

### 6. Interactive 3D WebGL Supply Chain Map
- Built on **Deck.gl 9.2** / React 19 / Vite 8
- Simultaneous layers: demand heatmap (45k points), actual WSI retail storefronts, US state boundaries, DC service territories
- Pitch 45°, bearing −10°, with 1500ms animated DC-focus transitions
- Toggle layers independently: Heatmap, Store Network, DC Radius — light and dark modes

### 7. Scenario Simulator — Quantified Cost of Inaction
- Replay historical demand events and toggle mitigation parameters: expedite freight lead time (10–90 days), emergency supply injection
- Live stock projection updates in real-time as parameters change
- Surfaces a binary verdict: will this SKU stockout? By when? At what dollar cost?

---

## Architecture

```
External Signal Streams
    ├── US Census API — ACS5 housing tenure data (ZCTA level)
    ├── Census Gazetteer — National ZCTA centroid coordinates
    ├── FRED API — MBA Purchase Applications Index (MBAVCH)
    └── Google Trends (pytrends) — Search virality, national + state
         │
         ▼
FastAPI Backend (Python 3.12)
    ├── ACS signal fetch, ACS year resolution, demand_index computation
    ├── DemandBriefService — Provider waterfall + SHA-256 content cache
    ├── AppConfig — Typed frozen dataclass, fully env-driven
    └── API Endpoints (see reference below)
         │
         ▼
ML Training Pipeline (offline, run once)
    ├── Export 33,772 ZCTA rows from Census ACS
    └── Train RandomForestRegressor (n=500) → scored demand pressure CSV
         Thresholds: ≥125 = STOCKOUT_RISK | ≤92 = OVERSTOCK_RISK
         │
         ▼
Synthetic Demand Data Generator
    └── 30 SKUs × 11 metros × 365 days → SQLite + CSV
         Composite signal: Sales 40% / RE+Income 25% / Holiday 20% / Trends 15%
         │
         ▼
React 19 + Vite 8 Frontend
    ├── SciFiMap        — Deck.gl 9.2 full 3D supply chain map
    ├── SkuRiskOverview — Intelligence hub + sortable SKU risk matrix
    ├── SignalTimeline  — Dual-axis chart: Sales + Trends + Permits
    ├── BuyerBrief      — LLM-generated exec brief with PDF export
    └── Simulation      — What-if scenario replay with live chart
```

---

## Project Structure

```
supplite/
├── backend/
│   ├── scripts/
│   │   ├── generate_synthetic_data.py       # 30 SKUs × 11 metros × 365 days → SQLite + CSV
│   │   ├── export_real_estate_training_data.py  # ACS → 33,772-row ZCTA training CSV
│   │   └── train_real_estate_model.py       # RandomForest → scored_real_estate_demand_full.csv
│   └── src/supply_chain_brief/
│       ├── main.py           # FastAPI app, all routes, in-memory TTL cache
│       ├── housing_signals.py   # ACS fetch, Gazetteer centroid load, demand_index
│       ├── service.py        # DemandBriefService: provider waterfall, SHA-256 caching
│       └── config.py         # AppConfig: frozen dataclass, env-driven
├── data/
│   ├── demand_intelligence.db               # SQLite: all signal rows
│   ├── sku_daily_signals.csv
│   ├── sku_inventory.csv                    # 30 SKUs × 11 metro snapshot
│   ├── metro_profiles.csv                   # 11 metros, Census B19013 income data
│   └── scored_real_estate_demand_full.csv   # ML-scored ZCTA output
└── frontend/src/
    ├── data.js                  # Static hydrated state: SKUs, metros, chart data
    ├── real_stores.json         # Actual WSI retail locations
    ├── components/
    │   ├── SciFiMap.jsx         # Deck.gl 9.2: HeatmapLayer, ScatterplotLayer, GeoJsonLayer
    │   └── RiskHeatmap.jsx
    └── views/
        ├── SkuRiskOverview.jsx  # Intelligence hub + SKU risk matrix
        ├── SignalTimeline.jsx   # Multi-axis signal drill-down (Recharts)
        ├── BuyerBrief.jsx       # LLM exec brief with export
        └── Simulation.jsx       # Scenario replay
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI, Python 3.12, Uvicorn, Pydantic v2 |
| **ML — Demand Scoring** | scikit-learn `RandomForestRegressor` (n=500, n_jobs=-1) |
| **ML — Anomaly Detection** | scikit-learn `IsolationForest` (contamination=0.05) |
| **Generative AI** | Anthropic Claude (primary) → OpenAI (fallback) → Deterministic (offline) |
| **Signal — Real Estate** | US Census API (`acs/acs5/profile`, `acs/acs5`) — ZCTA level |
| **Signal — Virality** | Google Trends (`pytrends`) — weekly, national + state |
| **Signal — Mortgage** | FRED API (`MBAVCH` — MBA Purchase Applications Index) |
| **Data Storage** | SQLite (`demand_intelligence.db`) |
| **Frontend** | React 19, Vite 8, Deck.gl 9.2, Recharts 3.8 |

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Service health, DB and cache readiness |
| `/api/briefs/weekly` | GET/POST | Weekly demand intelligence brief (LLM or deterministic) |
| `/api/signals/real-estate-heatmap` | GET | 30 curated seed ZCTAs — live ACS fetch |
| `/api/signals/real-estate-heatmap?scope=national&limit=45000` | GET | Full-US ZCTA fetch, auto-resolves to latest available ACS year pair |
| `/api/signals/real-estate-heatmap/live` | GET | National ZCTA with in-memory TTL cache (`cache_ttl_minutes`, `force_refresh`) |
| `/api/signals/scored-real-estate-heatmap` | GET | ML-scored ZCTA demand pressure; falls back to deterministic if CSV missing |

---

## Getting Started

### Prerequisites
- Python 3.12+, Node.js 18+, Census API key (free), Anthropic API key (optional)

### Backend
```bash
cd backend
cp .env.example .env
# Fill in: ANTHROPIC_API_KEY, CENSUS_API_KEY (optional), LLM_PROVIDER=auto

# Generate synthetic demand dataset
python scripts/generate_synthetic_data.py

# Export national ZCTA training data from Census ACS
python scripts/export_real_estate_training_data.py \
  --scope national --year 2025 --compare-year 2024 \
  --limit 0 --output ../data/real_estate_training_data_full.csv

# Train RandomForest → scored demand pressure CSV
python scripts/train_real_estate_model.py \
  --input ../data/real_estate_training_data_full.csv \
  --output ../data/scored_real_estate_demand_full.csv

# Start API server
uvicorn supply_chain_brief.main:app --app-dir src --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### Environment Variables
```env
ANTHROPIC_API_KEY=sk-ant-...    # Claude API (primary LLM)
OPENAI_API_KEY=sk-...           # OpenAI (fallback)
CENSUS_API_KEY=...              # Optional — higher Census API rate limits
LLM_PROVIDER=auto               # anthropic | openai | deterministic | auto
CACHE_TTL_MINUTES=1440          # Heatmap cache TTL (default: 24h)
MAX_BRIEF_SKUS=5                # Max SKUs per brief section
```

---

## The Three Key Scenarios

**Scenario A — Viral Spike (`STOCKOUT_RISK`):** `PB-BLANKET-42` runs at steady 18 units/day for 5 months. A creator posts it. Google Trends spikes from 11 → 89 in 7 days. The model flags a 12,200-unit shortfall against a 70-day lead time. **The buyer still has 3 weeks to act.**

**Scenario B — Silent Overstock (`OVERSTOCK_RISK`):** `PB-PILLOW-71` — 4,200 units on hand, 800 more on order already placed. Search index declining 23% over 8 consecutive weeks. Days of supply: 89. The trend peaked in February. The brief recommends a markdown trigger and cancelling the active order before it lands.

**Scenario C — Real Estate Signal (`WATCH` → `STOCKOUT`):** `PB-BED-33` — search flat, sales completely steady. Phoenix metro single-family home permits up 34% MoM. Supplite flags `WATCH` and projects a flip to `STOCKOUT_RISK` in 8–10 weeks. **60 days before any other signal would have caught it.**

---

*Built in 56 hours at the Cummins CCOEW AI-Thon powered by Williams-Sonoma, 2026.*
