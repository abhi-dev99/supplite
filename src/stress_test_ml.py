import pandas as pd
import joblib
import numpy as np
from pathlib import Path

# Paths
ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"

def main():
    print("==================================================================")
    print("OUT-OF-SAMPLE STRESS TEST (UNSEEN DATA)")
    print("==================================================================\n")
    print("Testing the ML model on completely fabricated, extreme edge-case")
    print("data that never existed in the training set to prove generalization.")
    print("------------------------------------------------------------------\n")

    # Load artifacts
    feature_cols = joblib.load(MODELS_DIR / "feature_columns.pkl")
    model_60d = joblib.load(MODELS_DIR / "demand_forecast_60d.pkl")
    iso_forest = joblib.load(MODELS_DIR / "anomaly_detector.pkl")

    # Anomaly features required by Isolation Forest
    anomaly_features = [
        "sales_vel_7d", "sales_vel_14d",
        "search_vel_7d", "search_vel_14d",
        "permit_vel_30d",
    ]

    # Create a completely generic "baseline" row with average/boring values
    base_row = {col: 0.0 for col in feature_cols}
    
    # Set Baseline averages (boring, stable SKU)
    base_row["units_sold"] = 10.0
    base_row["sales_roll_7d_mean"] = 10.0
    base_row["sales_roll_30d_mean"] = 10.0
    base_row["sales_vel_7d"] = 0.0
    base_row["sales_vel_14d"] = 0.0
    base_row["sales_vel_30d"] = 0.0
    
    base_row["search_index"] = 50.0
    base_row["search_roll_7d_mean"] = 50.0
    base_row["search_roll_30d_mean"] = 50.0
    base_row["search_vel_7d"] = 0.0
    base_row["search_vel_14d"] = 0.0
    
    base_row["housing_permits"] = 1000.0
    base_row["permit_vel_30d"] = 0.0
    base_row["permit_vel_60d"] = 0.0
    
    base_row["price"] = 100.0
    base_row["income_factor"] = 0.8
    base_row["month"] = 6
    
    # Define our completely OUT OF SAMPLE, fabricated test cases
    scenarios = [
        {
            "name": "BASELINE (Stable)",
            "desc": "A perfectly stable product doing 10 units a day.",
            "mutations": {}
        },
        {
            "name": "VIRAL TIKTOK MENTION",
            "desc": "Sales velocity jumps 500%. Search jumps 800% in 7 days.",
            "mutations": {
                "sales_vel_7d": 500.0,
                "sales_vel_14d": 300.0,
                "units_sold": 80.0,
                "search_vel_7d": 800.0,
                "search_index": 100.0
            }
        },
        {
            "name": "DEAD PRODUCT",
            "desc": "Sales immediately crash by -95%. Zero search interest.",
            "mutations": {
                "sales_vel_7d": -95.0,
                "sales_vel_14d": -95.0,
                "units_sold": 0.0,
                "search_vel_7d": -90.0,
                "search_index": 5.0
            }
        },
        {
            "name": "HOUSING BOOM (EARLY INDICATOR)",
            "desc": "Sales/Search are perfectly flat, but housing permits jump 400%.",
            "mutations": {
                "permit_vel_30d": 400.0,
                "permit_vel_60d": 350.0,
                "housing_permits": 5000.0
            }
        }
    ]

    for sc in scenarios:
        # Clone base and apply mutations
        row = base_row.copy()
        for k, v in sc["mutations"].items():
            row[k] = v
            
        # Convert to numpy array in correct feature column order
        X = np.array([[row[col] for col in feature_cols]])
        
        # Inference
        forecast_60d = model_60d.predict(X)[0]
        
        # Anomaly Check
        X_iso = np.array([[row[col] for col in anomaly_features]])
        anomaly_pred = iso_forest.predict(X_iso)[0]
        is_anomaly = anomaly_pred == -1
        
        print(f"[{sc['name']}]")
        print(f"Context: {sc['desc']}")
        print(f" -> Isolation Forest Anomaly: {'YES [!] (It detected the crazy behavior)' if is_anomaly else 'NO (Seems normal)'}")
        print(f" -> LightGBM 60-Day Forecast: {int(forecast_60d)} units expected to sell")
        print("------------------------------------------------------------------")

if __name__ == "__main__":
    main()
