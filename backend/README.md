# Supply Chain Brief Backend

Backend service for the hackathon feature "Weekly Demand Intelligence Brief".

## What it does

- Exposes a secured, validated API for generating a weekly buyer brief.
- Exposes a real-estate demand heatmap API using Census ACS data at ZCTA level.
- Caches generated briefs in SQLite.
- Falls back to a deterministic offline brief generator if no LLM provider is configured.
- Keeps the contract small so the frontend can consume it without coupling to the data pipeline.

## Run

```bash
uvicorn supply_chain_brief.main:app --app-dir src --reload
```

## Real data endpoints

- `GET /api/signals/real-estate-heatmap?year=2024&compare_year=2023&limit=40`
	- Pulls live Census ACS data (DP04 tenure + ACS5 enrichments) by ZCTA.
	- Returns owner/renter counts, year-over-year changes, demand index, and risk bucket.
	- Falls back to deterministic data if live fetch is unavailable.

## Export training data for Colab

```bash
python scripts/export_real_estate_training_data.py --year 2024 --compare-year 2023 --output ../data/real_estate_training_data.csv
```

Then open `notebooks/real_estate_demand_colab.ipynb` in Google Colab and upload the exported CSV.

## Environment

Copy `.env.example` to `.env` and fill in provider keys if you want remote LLM generation.

Optional:

- `CENSUS_API_KEY` for higher Census API throughput.
