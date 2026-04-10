"""
model_training.py
=================
Trains the ML models for the Demand Intelligence System.

Models:
  1. LightGBM Regressor  — 30/60/90 day demand forecast
  2. Isolation Forest     — anomaly detection on velocity features
  3. Risk Classifier      — rule-based, combines forecast + anomaly + inventory

Input:  data/new/features.parquet
Output: models/demand_forecast_{30,60,90}d.pkl
        models/anomaly_detector.pkl
        models/training_report.json
        data/new/predictions.json

Run:
    python src/model_training.py
"""

import json
import warnings
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from datetime import datetime

import lightgbm as lgb
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "new"
MODELS_DIR = ROOT / "models"
MODELS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Feature columns (must match feature_engineering.py)
# ---------------------------------------------------------------------------
FEATURE_COLS = joblib.load(MODELS_DIR / "feature_columns.pkl")

ANOMALY_FEATURES = [
    "sales_vel_7d", "sales_vel_14d",
    "search_vel_7d", "search_vel_14d",
    "permit_vel_30d",
]

# ---------------------------------------------------------------------------
# LightGBM hyperparameters (tuned for 56-hour hackathon build)
# ---------------------------------------------------------------------------
LGBM_PARAMS = {
    "n_estimators": 500,
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_child_samples": 20,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.1,
    "reg_lambda": 0.1,
    "random_state": 42,
    "n_jobs": -1,
    "verbose": -1,
}


# ---------------------------------------------------------------------------
# Load features
# ---------------------------------------------------------------------------
def load_features() -> pd.DataFrame:
    """Load the pre-computed features parquet."""
    df = pd.read_parquet(DATA_DIR / "features.parquet")
    return df


# ---------------------------------------------------------------------------
# Train LightGBM demand forecaster
# ---------------------------------------------------------------------------
def train_demand_forecaster(
    df: pd.DataFrame,
    horizon: int,
    n_splits: int = 5,
) -> tuple[lgb.LGBMRegressor, dict]:
    """
    Train a LightGBM regressor to predict sum of units_sold over next `horizon` days.

    Uses TimeSeriesSplit for chronological cross-validation — no data leakage.
    Returns (trained_model, metrics_dict).
    """
    target_col = f"target_{horizon}d"

    # Keep only rows with valid features AND valid target
    valid_mask = df[FEATURE_COLS + [target_col]].notna().all(axis=1)
    clean = df[valid_mask].copy()

    # Sort chronologically for TimeSeriesSplit
    clean = clean.sort_values("day_index").reset_index(drop=True)

    X = clean[FEATURE_COLS].values
    y = clean[target_col].values

    print(f"\n   Training {horizon}d forecaster on {len(clean):,} rows...")
    print(f"   Target stats: mean={y.mean():.1f}, median={np.median(y):.1f}, "
          f"std={y.std():.1f}, min={y.min():.0f}, max={y.max():.0f}")

    # TimeSeriesSplit cross-validation
    tscv = TimeSeriesSplit(n_splits=n_splits)
    fold_metrics = []

    for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        model = lgb.LGBMRegressor(**LGBM_PARAMS)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.log_evaluation(0)],  # suppress per-iteration logs
        )

        y_pred = model.predict(X_val)
        mae = mean_absolute_error(y_val, y_pred)
        rmse = np.sqrt(mean_squared_error(y_val, y_pred))
        # MAPE (avoid division by zero)
        nonzero = y_val > 0
        mape = np.mean(np.abs((y_val[nonzero] - y_pred[nonzero]) / y_val[nonzero])) * 100

        fold_metrics.append({"fold": fold + 1, "mae": mae, "rmse": rmse, "mape": mape})
        print(f"     Fold {fold + 1}: MAE={mae:.1f}, RMSE={rmse:.1f}, MAPE={mape:.1f}%")

    # Final model: train on all data
    print(f"   Training final model on all {len(clean):,} rows...")
    final_model = lgb.LGBMRegressor(**LGBM_PARAMS)
    final_model.fit(X, y)

    # Feature importance
    importances = dict(zip(FEATURE_COLS, final_model.feature_importances_.tolist()))
    top_10 = sorted(importances.items(), key=lambda x: -x[1])[:10]

    avg_mae = np.mean([m["mae"] for m in fold_metrics])
    avg_rmse = np.mean([m["rmse"] for m in fold_metrics])
    avg_mape = np.mean([m["mape"] for m in fold_metrics])

    print(f"   Average: MAE={avg_mae:.1f}, RMSE={avg_rmse:.1f}, MAPE={avg_mape:.1f}%")
    print(f"   Top features: {', '.join(f'{k}({v})' for k, v in top_10[:5])}")

    metrics = {
        "horizon_days": horizon,
        "train_rows": len(clean),
        "folds": fold_metrics,
        "avg_mae": round(avg_mae, 2),
        "avg_rmse": round(avg_rmse, 2),
        "avg_mape": round(avg_mape, 2),
        "target_mean": round(float(y.mean()), 2),
        "feature_importance_top10": {k: int(v) for k, v in top_10},
    }

    return final_model, metrics


# ---------------------------------------------------------------------------
# Train Isolation Forest anomaly detector
# ---------------------------------------------------------------------------
def train_anomaly_detector(df: pd.DataFrame) -> tuple[IsolationForest, dict]:
    """
    Train an Isolation Forest on velocity features.
    contamination=0.05 → expect ~5% of observations to be anomalous.
    """
    valid_mask = df[ANOMALY_FEATURES].notna().all(axis=1)
    clean = df[valid_mask].copy()
    X = clean[ANOMALY_FEATURES].values

    print(f"\n   Training Isolation Forest on {len(clean):,} rows, {len(ANOMALY_FEATURES)} features...")

    iso = IsolationForest(
        contamination=0.05,
        n_estimators=100,
        max_samples="auto",
        random_state=42,
        n_jobs=-1,
    )
    iso.fit(X)

    # Predict on training data to get anomaly stats
    preds = iso.predict(X)  # -1 = anomaly, 1 = normal
    scores = iso.decision_function(X)

    n_anomalies = (preds == -1).sum()
    anomaly_pct = n_anomalies / len(preds) * 100

    print(f"   Anomalies detected: {n_anomalies:,} / {len(preds):,} ({anomaly_pct:.1f}%)")
    print(f"   Decision function: mean={scores.mean():.4f}, std={scores.std():.4f}")

    # Z-score fallback stats (for runtime use)
    zscore_means = clean[ANOMALY_FEATURES].mean().to_dict()
    zscore_stds = clean[ANOMALY_FEATURES].std().to_dict()

    metrics = {
        "train_rows": len(clean),
        "features": ANOMALY_FEATURES,
        "contamination": 0.05,
        "anomalies_detected": int(n_anomalies),
        "anomaly_pct": round(anomaly_pct, 2),
        "decision_score_mean": round(float(scores.mean()), 4),
        "decision_score_std": round(float(scores.std()), 4),
        "zscore_means": {k: round(v, 4) for k, v in zscore_means.items()},
        "zscore_stds": {k: round(v, 4) for k, v in zscore_stds.items()},
    }

    return iso, metrics


# ---------------------------------------------------------------------------
# Risk classifier (rule-based, per PRD FR-M3)
# ---------------------------------------------------------------------------
def classify_risk(row: dict) -> dict:
    """
    Rule-based risk classification combining forecast, anomaly, and inventory.

    Returns dict with risk_level, confidence, and reasoning.
    """
    days_supply = row.get("days_of_supply", 999)
    lead_time = row.get("lead_time_days", 56)
    stock = row.get("stock_on_hand", 0)
    on_order = row.get("on_order", 0)
    forecast_60d = row.get("forecast_60d", 0)
    sales_vel_30d = row.get("sales_vel_30d", 0)
    is_anomaly = row.get("is_anomaly", False)
    composite = row.get("composite_score", 50)

    # STOCKOUT_RISK: insufficient supply to cover forecast demand
    if days_supply < lead_time * 1.2 and forecast_60d > (stock + on_order):
        shortfall = forecast_60d - (stock + on_order)
        return {
            "risk_level": "STOCKOUT_RISK",
            "confidence": min(0.95, 0.6 + (1 - days_supply / lead_time) * 0.35),
            "reasoning": f"Days of supply ({days_supply:.0f}) < lead time ({lead_time}d). "
                        f"Forecast shortfall: {shortfall:.0f} units over 60d.",
        }

    # OVERSTOCK_RISK: excess inventory with declining demand
    if days_supply > lead_time * 3 and sales_vel_30d < -15:
        excess = stock + on_order - forecast_60d
        return {
            "risk_level": "OVERSTOCK_RISK",
            "confidence": min(0.90, 0.5 + abs(sales_vel_30d) / 100),
            "reasoning": f"Days of supply ({days_supply:.0f}) = {days_supply/lead_time:.1f}x lead time. "
                        f"Demand declining {sales_vel_30d:.1f}% MoM. Excess: ~{excess:.0f} units.",
        }

    # WATCH: anomaly detected but not yet critical
    if is_anomaly:
        return {
            "risk_level": "WATCH",
            "confidence": 0.65,
            "reasoning": f"Velocity anomaly detected (composite={composite:.1f}). "
                        f"Monitoring for trend confirmation.",
        }

    # WATCH: composite score elevated
    if composite > 65:
        return {
            "risk_level": "WATCH",
            "confidence": 0.55,
            "reasoning": f"Elevated composite score ({composite:.1f}). Pre-emptive monitoring.",
        }

    # OK
    return {
        "risk_level": "OK",
        "confidence": 0.80,
        "reasoning": f"Stable demand (composite={composite:.1f}). "
                    f"Supply coverage: {days_supply:.0f}d vs {lead_time}d lead time.",
    }


# ---------------------------------------------------------------------------
# Generate predictions
# ---------------------------------------------------------------------------
def generate_predictions(
    df: pd.DataFrame,
    models: dict[str, lgb.LGBMRegressor],
    iso_forest: IsolationForest,
    inventory: pd.DataFrame,
) -> list[dict]:
    """
    Generate per-SKU×metro predictions on the most recent data point.
    Combines LightGBM forecasts + Isolation Forest anomalies + risk classification.
    """
    # Find the latest row per SKU×metro where ALL features are valid
    feature_valid = df[FEATURE_COLS].notna().all(axis=1)
    valid_df = df[feature_valid].copy()

    # Get the max day_index per SKU×metro from valid rows
    latest_idx = valid_df.groupby(["sku_id", "metro"])["day_index"].idxmax()
    latest = valid_df.loc[latest_idx].copy().reset_index(drop=True)

    print(f"\n   Prediction rows: {len(latest)} (latest valid feature row per SKU×metro)")

    X = latest[FEATURE_COLS].values

    # LightGBM forecasts — model keys are like "forecast_30d", we want columns "pred_30d"
    for key, model in models.items():
        # key is "forecast_30d" etc — extract the horizon part
        horizon = key.replace("forecast_", "")  # "30d", "60d", "90d"
        col_name = f"pred_{horizon}"
        latest[col_name] = model.predict(X).clip(min=0).round(0)

    # Isolation Forest
    anomaly_mask = latest[ANOMALY_FEATURES].notna().all(axis=1)
    if anomaly_mask.any():
        X_anomaly = latest.loc[anomaly_mask, ANOMALY_FEATURES].values
        anomaly_preds = iso_forest.predict(X_anomaly)
        anomaly_scores = iso_forest.decision_function(X_anomaly)
        latest.loc[anomaly_mask, "anomaly_flag"] = (anomaly_preds == -1).astype(int)
        latest.loc[anomaly_mask, "anomaly_score"] = anomaly_scores

    latest["anomaly_flag"] = latest["anomaly_flag"].fillna(0).astype(int)
    latest["anomaly_score"] = latest.get("anomaly_score", pd.Series(0, index=latest.index)).fillna(0)

    # Merge inventory for risk classification
    inv_cols = ["sku_id", "metro", "stock_on_hand", "on_order", "days_of_supply",
                "lead_time_days", "avg_daily_sales"]
    inv_available = [c for c in inv_cols if c in inventory.columns]
    latest = latest.merge(
        inventory[inv_available], on=["sku_id", "metro"], how="left", suffixes=("", "_inv")
    )

    # Use lead_time from catalog if not in inventory
    if "lead_time_days" not in latest.columns:
        latest["lead_time_days"] = latest.get("lead_time", 56)

    # Risk classification
    predictions = []
    for _, row in latest.iterrows():
        forecast_60d = float(row.get("pred_60d", 0))
        risk_input = {
            "days_of_supply": float(row.get("days_of_supply", 999)),
            "lead_time_days": float(row.get("lead_time_days", 56)),
            "stock_on_hand": float(row.get("stock_on_hand", 0)),
            "on_order": float(row.get("on_order", 0)),
            "forecast_60d": forecast_60d,
            "sales_vel_30d": float(row.get("sales_vel_30d", 0)),
            "is_anomaly": int(row.get("anomaly_flag", 0)) == 1,
            "composite_score": float(row.get("composite_score", 50)),
        }
        risk_result = classify_risk(risk_input)

        pred = {
            "sku_id": row["sku_id"],
            "metro": row["metro"],
            "forecast_30d": int(row.get("pred_30d", 0)),
            "forecast_60d": int(row.get("pred_60d", 0)),
            "forecast_90d": int(row.get("pred_90d", 0)),
            "anomaly_flag": int(row.get("anomaly_flag", 0)),
            "anomaly_score": round(float(row.get("anomaly_score", 0)), 4),
            "risk_level": risk_result["risk_level"],
            "risk_confidence": round(risk_result["confidence"], 2),
            "risk_reasoning": risk_result["reasoning"],
            "composite_score": round(float(row.get("composite_score", 50)), 1),
            "sales_vel_7d": round(float(row.get("sales_vel_7d", 0)), 1),
            "sales_vel_30d": round(float(row.get("sales_vel_30d", 0)), 1),
            "search_vel_7d": round(float(row.get("search_vel_7d", 0)), 1),
            "permit_vel_30d": round(float(row.get("permit_vel_30d", 0)), 1),
            "scenario_type": row.get("scenario_type", "R"),
        }
        predictions.append(pred)

    return predictions


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("  ML Model Training Pipeline — Demand Intelligence System")
    print("=" * 70)

    # Load
    print("\n1. Loading features...")
    df = load_features()
    inventory = pd.read_csv(DATA_DIR / "sku_inventory.csv")
    print(f"   Features: {len(df):,} rows × {len(df.columns)} columns")
    print(f"   Inventory: {len(inventory)} rows")

    # -------------------------------------------------------------------
    # Model 1: LightGBM Demand Forecasters
    # -------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("  MODEL 1: LightGBM Demand Forecaster")
    print("-" * 70)

    models = {}
    all_metrics = {}

    for horizon in [30, 60, 90]:
        model, metrics = train_demand_forecaster(df, horizon)
        models[f"forecast_{horizon}d"] = model
        all_metrics[f"lightgbm_{horizon}d"] = metrics

        # Save model
        model_path = MODELS_DIR / f"demand_forecast_{horizon}d.pkl"
        joblib.dump(model, model_path)
        print(f"   Saved: {model_path}")

    # -------------------------------------------------------------------
    # Model 2: Isolation Forest Anomaly Detector
    # -------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("  MODEL 2: Isolation Forest Anomaly Detector")
    print("-" * 70)

    iso_forest, iso_metrics = train_anomaly_detector(df)
    all_metrics["isolation_forest"] = iso_metrics

    iso_path = MODELS_DIR / "anomaly_detector.pkl"
    joblib.dump(iso_forest, iso_path)
    print(f"   Saved: {iso_path}")

    # -------------------------------------------------------------------
    # Generate predictions
    # -------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("  PREDICTIONS: Generating per-SKU×metro forecasts + risk classifications")
    print("-" * 70)

    predictions = generate_predictions(df, models, iso_forest, inventory)

    # Summary
    risk_counts = {}
    for p in predictions:
        risk_counts[p["risk_level"]] = risk_counts.get(p["risk_level"], 0) + 1

    print(f"\n   Total predictions: {len(predictions)}")
    for level, count in sorted(risk_counts.items()):
        print(f"     {level}: {count}")

    # Anomaly summary
    n_anomalies = sum(1 for p in predictions if p["anomaly_flag"] == 1)
    print(f"   Anomalies flagged: {n_anomalies}")

    # Scenario spot-checks
    print("\n   Scenario spot-checks:")
    scenario_checks = {
        "A": "PB-BLANKET-42",
        "B": "PB-PILLOW-71",
        "C": "PB-BED-FRAME-33",
        "D": "PB-THROW-55",
    }
    for scenario, sku_id in scenario_checks.items():
        sku_preds = [p for p in predictions if p["sku_id"] == sku_id]
        if sku_preds:
            home_pred = sku_preds[0]  # First metro
            for p in sku_preds:
                if scenario == "A" and p["metro"] == "Los Angeles":
                    home_pred = p
                elif scenario == "B" and p["metro"] == "New York":
                    home_pred = p
                elif scenario == "C" and p["metro"] == "Phoenix":
                    home_pred = p
                elif scenario == "D" and p["metro"] == "Seattle":
                    home_pred = p

            status = "PASS" if (
                (scenario == "A" and home_pred["risk_level"] in ["STOCKOUT_RISK", "WATCH"]) or
                (scenario == "B" and home_pred["risk_level"] in ["OVERSTOCK_RISK", "WATCH"]) or
                (scenario == "C" and home_pred["risk_level"] in ["WATCH", "OK"]) or
                (scenario == "D" and home_pred["risk_level"] == "OK")
            ) else "CHECK"
            print(f"     [{status}] Scenario {scenario} ({sku_id}): "
                  f"{home_pred['risk_level']} (forecast_60d={home_pred['forecast_60d']}, "
                  f"anomaly={home_pred['anomaly_flag']})")

    # Save predictions
    pred_path = DATA_DIR / "predictions.json"
    with open(pred_path, "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=2)
    print(f"\n   Saved: {pred_path}")

    # -------------------------------------------------------------------
    # Training report
    # -------------------------------------------------------------------
    report = {
        "generated_at": datetime.now().isoformat(),
        "dataset": {
            "total_rows": len(df),
            "features": len(FEATURE_COLS),
            "skus": df["sku_id"].nunique(),
            "metros": df["metro"].nunique(),
            "days": df["day_index"].nunique(),
        },
        "models": all_metrics,
        "predictions_summary": {
            "total": len(predictions),
            "risk_distribution": risk_counts,
            "anomalies_flagged": n_anomalies,
        },
    }

    report_path = MODELS_DIR / "training_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"   Saved: {report_path}")

    print("\n" + "=" * 70)
    print("  Training complete!")
    print(f"  Models saved to: {MODELS_DIR}")
    print(f"  Predictions saved to: {pred_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
