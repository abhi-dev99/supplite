"""
feature_engineering.py
======================
Transforms raw daily signals into ML-ready features.

Input:  data/new/sku_daily_signals.csv
        data/new/sku_catalog.csv
Output: data/new/features.parquet   (training-ready DataFrame)

Feature groups:
  1. Lag features        — sales, search, permits at t-7, t-14, t-30, t-60
  2. Velocity features   — % change over 7d, 14d, 30d windows
  3. Rolling statistics  — mean, std over 7d, 30d windows
  4. Seasonal features   — day_of_week, month, is_weekend, is_peak_season, holiday proximity
  5. Categorical         — brand, category, metro (label-encoded)
  6. Context             — price, lead_time_days, median_income, income_factor
  7. Target variables    — forward sum of units_sold over 30/60/90 days

Run:
    python src/feature_engineering.py
"""

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "new"

# ---------------------------------------------------------------------------
# Load raw data
# ---------------------------------------------------------------------------
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load daily signals and catalog."""
    signals = pd.read_csv(DATA_DIR / "sku_daily_signals.csv", parse_dates=["date"])
    catalog = pd.read_csv(DATA_DIR / "sku_catalog.csv")
    return signals, catalog


# ---------------------------------------------------------------------------
# Lag features
# ---------------------------------------------------------------------------
def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add lagged values for sales, search, and permits."""
    group_cols = ["sku_id", "metro"]

    # Sales lags
    for lag in [7, 14, 30, 60]:
        df[f"sales_lag_{lag}d"] = (
            df.groupby(group_cols)["units_sold"]
            .shift(lag)
        )

    # Search lags
    for lag in [7, 14, 30]:
        df[f"search_lag_{lag}d"] = (
            df.groupby(group_cols)["search_index"]
            .shift(lag)
        )

    # Permit lags (monthly cadence so 30d and 60d make sense)
    for lag in [30, 60]:
        df[f"permits_lag_{lag}d"] = (
            df.groupby(group_cols)["housing_permits"]
            .shift(lag)
        )

    return df


# ---------------------------------------------------------------------------
# Velocity features
# ---------------------------------------------------------------------------
def add_velocity_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute % change velocity features."""
    group_cols = ["sku_id", "metro"]

    # Sales velocity
    for window in [7, 14, 30]:
        current = df.groupby(group_cols)["units_sold"].transform(
            lambda x: x.rolling(window, min_periods=1).mean()
        )
        lagged = df.groupby(group_cols)["units_sold"].transform(
            lambda x: x.shift(window).rolling(window, min_periods=1).mean()
        )
        df[f"sales_vel_{window}d"] = ((current - lagged) / lagged.clip(lower=0.1)) * 100

    # Search velocity
    for window in [7, 14]:
        current = df.groupby(group_cols)["search_index"].transform(
            lambda x: x.rolling(window, min_periods=1).mean()
        )
        lagged = df.groupby(group_cols)["search_index"].transform(
            lambda x: x.shift(window).rolling(window, min_periods=1).mean()
        )
        df[f"search_vel_{window}d"] = ((current - lagged) / lagged.clip(lower=0.1)) * 100

    # Permit velocity (30d and 60d)
    for window in [30, 60]:
        current = df.groupby(group_cols)["housing_permits"].transform(
            lambda x: x.rolling(window, min_periods=1).mean()
        )
        lagged = df.groupby(group_cols)["housing_permits"].transform(
            lambda x: x.shift(window).rolling(window, min_periods=1).mean()
        )
        df[f"permit_vel_{window}d"] = ((current - lagged) / lagged.clip(lower=1)) * 100

    return df


# ---------------------------------------------------------------------------
# Rolling statistics
# ---------------------------------------------------------------------------
def add_rolling_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Add rolling mean and std for sales and search."""
    group_cols = ["sku_id", "metro"]

    for window in [7, 30]:
        df[f"sales_roll_{window}d_mean"] = (
            df.groupby(group_cols)["units_sold"]
            .transform(lambda x: x.rolling(window, min_periods=1).mean())
        )
        df[f"sales_roll_{window}d_std"] = (
            df.groupby(group_cols)["units_sold"]
            .transform(lambda x: x.rolling(window, min_periods=1).std().fillna(0))
        )

    for window in [7, 30]:
        df[f"search_roll_{window}d_mean"] = (
            df.groupby(group_cols)["search_index"]
            .transform(lambda x: x.rolling(window, min_periods=1).mean())
        )

    return df


# ---------------------------------------------------------------------------
# Seasonal features
# ---------------------------------------------------------------------------
def add_seasonal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add temporal and seasonal features."""
    df["day_of_week"] = df["date"].dt.dayofweek
    df["month"] = df["date"].dt.month
    df["day_of_year"] = df["date"].dt.dayofyear
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["is_peak_season"] = df["month"].isin([10, 11, 12]).astype(int)

    # Cyclical encoding for month and day_of_week
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)

    return df


# ---------------------------------------------------------------------------
# Categorical encoding
# ---------------------------------------------------------------------------
def add_categorical_features(df: pd.DataFrame, catalog: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Label-encode brand, category, metro. Returns df and encoders dict."""
    # Merge catalog info
    catalog_cols = ["sku_id", "brand", "category", "price", "cost_price",
                    "lead_time_days", "scenario_type"]
    df = df.merge(catalog[catalog_cols], on="sku_id", how="left", suffixes=("", "_cat"))

    # Use existing scenario_type from signals if duplicate
    if "scenario_type_cat" in df.columns:
        df.drop(columns=["scenario_type_cat"], inplace=True)

    encoders = {}
    for col in ["brand", "category", "metro"]:
        le = LabelEncoder()
        df[f"{col}_encoded"] = le.fit_transform(df[col].astype(str))
        encoders[col] = le

    return df, encoders


# ---------------------------------------------------------------------------
# Forward-looking targets
# ---------------------------------------------------------------------------
def add_targets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create forward-looking targets: sum of units_sold over next N days.
    These MUST NOT be used as features — only as targets.
    """
    group_cols = ["sku_id", "metro"]

    for horizon in [30, 60, 90]:
        df[f"target_{horizon}d"] = (
            df.groupby(group_cols)["units_sold"]
            .transform(lambda x: x.shift(-1).rolling(horizon, min_periods=1).sum().shift(-(horizon - 1)))
        )

    return df


# ---------------------------------------------------------------------------
# Income factor (already in CSV but let's ensure consistency)
# ---------------------------------------------------------------------------
def add_income_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derive income_factor from median_income."""
    df["income_factor"] = (df["median_income"] / 120_000).clip(upper=1.0)
    return df


# ---------------------------------------------------------------------------
# Feature column specification
# ---------------------------------------------------------------------------
FEATURE_COLS = [
    # Lag features
    "sales_lag_7d", "sales_lag_14d", "sales_lag_30d", "sales_lag_60d",
    "search_lag_7d", "search_lag_14d", "search_lag_30d",
    "permits_lag_30d", "permits_lag_60d",
    # Velocity features
    "sales_vel_7d", "sales_vel_14d", "sales_vel_30d",
    "search_vel_7d", "search_vel_14d",
    "permit_vel_30d", "permit_vel_60d",
    # Rolling stats
    "sales_roll_7d_mean", "sales_roll_30d_mean",
    "sales_roll_7d_std", "sales_roll_30d_std",
    "search_roll_7d_mean", "search_roll_30d_mean",
    # Seasonal
    "day_of_week", "month", "is_weekend", "is_peak_season",
    "month_sin", "month_cos", "dow_sin", "dow_cos",
    # Raw signals (current values)
    "units_sold", "search_index", "housing_permits",
    "composite_score", "holiday_flag",
    # Categorical
    "brand_encoded", "category_encoded", "metro_encoded",
    # Context
    "price", "lead_time_days", "median_income", "income_factor",
]

TARGET_COLS = ["target_30d", "target_60d", "target_90d"]

# Anomaly detection features
ANOMALY_FEATURES = [
    "sales_vel_7d", "sales_vel_14d",
    "search_vel_7d", "search_vel_14d",
    "permit_vel_30d",
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("  Feature Engineering Pipeline")
    print("=" * 60)

    # Load
    print("\n1. Loading data...")
    signals, catalog = load_data()
    print(f"   Signals: {len(signals):,} rows")
    print(f"   Catalog: {len(catalog)} SKUs")

    # Sort for rolling/shift operations
    signals = signals.sort_values(["sku_id", "metro", "date"]).reset_index(drop=True)

    # Feature engineering
    print("\n2. Computing lag features...")
    signals = add_lag_features(signals)

    print("3. Computing velocity features...")
    signals = add_velocity_features(signals)

    print("4. Computing rolling statistics...")
    signals = add_rolling_stats(signals)

    print("5. Adding seasonal features...")
    signals = add_seasonal_features(signals)

    print("6. Encoding categoricals...")
    signals, encoders = add_categorical_features(signals, catalog)

    print("7. Computing income features...")
    signals = add_income_features(signals)

    print("8. Computing forward targets (30d/60d/90d)...")
    signals = add_targets(signals)

    # Summary
    print(f"\n   Total columns: {len(signals.columns)}")
    print(f"   Feature columns: {len(FEATURE_COLS)}")
    print(f"   Target columns: {len(TARGET_COLS)}")

    # Check for NaN coverage
    total_rows = len(signals)
    valid_rows_30d = signals["target_30d"].notna().sum()
    valid_rows_60d = signals["target_60d"].notna().sum()
    valid_rows_90d = signals["target_90d"].notna().sum()
    feature_valid = signals[FEATURE_COLS].dropna().shape[0]

    print(f"\n   Rows with valid features: {feature_valid:,} / {total_rows:,} ({feature_valid/total_rows:.1%})")
    print(f"   Rows with target_30d:     {valid_rows_30d:,}")
    print(f"   Rows with target_60d:     {valid_rows_60d:,}")
    print(f"   Rows with target_90d:     {valid_rows_90d:,}")

    # Save
    output_path = DATA_DIR / "features.parquet"
    signals.to_parquet(output_path, index=False)
    print(f"\n   Saved: {output_path}")
    print(f"   Size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")

    # Also save feature column spec and encoders
    import joblib
    models_dir = ROOT / "models"
    models_dir.mkdir(exist_ok=True)
    joblib.dump(FEATURE_COLS, models_dir / "feature_columns.pkl")
    joblib.dump(encoders, models_dir / "label_encoders.pkl")
    print(f"   Saved: {models_dir / 'feature_columns.pkl'}")
    print(f"   Saved: {models_dir / 'label_encoders.pkl'}")

    print("\n" + "=" * 60)
    print("  Feature engineering complete!")
    print("=" * 60)

    return signals


if __name__ == "__main__":
    main()
