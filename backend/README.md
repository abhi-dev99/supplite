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
- `GET /api/signals/real-estate-heatmap?scope=national&year=2025&compare_year=2024&limit=5000`
	- Pulls all available ZCTAs (national scope) and maps them with Census Gazetteer centroids.
	- If requested years are not yet published, backend auto-falls back to the latest available ACS year pair.
	- Recommended for full-US heatmap generation.

- `GET /api/signals/scored-real-estate-heatmap?limit=5000`
	- Serves model-scored CSV output.
	- Automatically prefers `data/scored_real_estate_demand_full.csv` when present.

## Export training data for Colab

```bash
python scripts/export_real_estate_training_data.py --year 2024 --compare-year 2023 --output ../data/real_estate_training_data.csv
```

For full-US training export (recommended):

```bash
python scripts/export_real_estate_training_data.py --scope national --year 2025 --compare-year 2024 --limit 0 --output ../data/real_estate_training_data_full.csv
```

`--limit 0` means no cap and exports all available ZCTAs.

Train and score the full exported dataset:

```bash
python scripts/train_real_estate_model.py --input ../data/real_estate_training_data_full.csv --output ../data/scored_real_estate_demand_full.csv
```

The backend endpoint `GET /api/signals/scored-real-estate-heatmap` automatically serves `scored_real_estate_demand_full.csv` when present.

Then open `notebooks/real_estate_demand_colab.ipynb` in Google Colab and upload the exported CSV.

## Environment

Copy `.env.example` to `.env` and fill in provider keys if you want remote LLM generation.

Optional:

- `CENSUS_API_KEY` for higher Census API throughput.
