import pandas as pd
import joblib
from pathlib import Path

# Paths
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "new"
MODELS_DIR = ROOT / "models"

def main():
    print("==================================================================")
    print("ML Model Inference Tester")
    print("==================================================================\n")

    # Load the latest predictions we already generated
    predictions = pd.read_json(DATA_DIR / "predictions.json")
    signals = pd.read_csv(DATA_DIR / "sku_daily_signals.csv", parse_dates=["date"])
    
    # Let's test the 4 key demo scenarios
    test_cases = [
        {"sku": "PB-BLANKET-42", "metro": "Los Angeles", "desc": "Scenario A: Viral Spike"},
        {"sku": "PB-PILLOW-71", "metro": "New York", "desc": "Scenario B: Silent Overstock"},
        {"sku": "PB-BED-FRAME-33", "metro": "Phoenix", "desc": "Scenario C: Housing Lead (Permits)"},
        {"sku": "PB-THROW-55", "metro": "Seattle", "desc": "Scenario D: Steady/OK"}
    ]

    for case in test_cases:
        sku = case["sku"]
        metro = case["metro"]
        
        # Get the latest prediction
        pred = predictions[(predictions["sku_id"] == sku) & (predictions["metro"] == metro)].iloc[0]
        
        # Get the recent 30 days of signals to see what the model "saw"
        hist = signals[(signals["sku_id"] == sku) & (signals["metro"] == metro)].tail(30)
        recent_sales = hist["units_sold"].sum()
        recent_search_trend = hist["search_index"].mean()
        permit_trend = hist["housing_permits"].mean()
        
        print(f"--- {case['desc']} ({sku} in {metro}) ---")
        print(f"   What happened in the last 30 days:")
        print(f"     - Total Units Sold: {recent_sales}")
        print(f"     - Avg Search Index: {recent_search_trend:.1f} (7d velocity: {pred['search_vel_7d']}%)")
        print(f"     - Sale Velocity:    {pred['sales_vel_30d']}% MoM")
        if case['desc'].startswith("Scenario C"):
            print(f"     - Housing Permits:  {int(permit_trend)} (30d velocity: {pred['permit_vel_30d']}%)")
            
        print(f"\n   -> ML Model Predictions (Next 30/60/90 Days):")
        print(f"     - 30-Day Forecast:  {pred['forecast_30d']} units")
        print(f"     - 60-Day Forecast:  {pred['forecast_60d']} units")
        print(f"     - 90-Day Forecast:  {pred['forecast_90d']} units")
        
        print(f"\n   -> Risk Engine Output:")
        print(f"     - Anomaly Flag:     {'YES [!]' if pred['anomaly_flag'] else 'NO'}")
        print(f"     - Risk Level:       {pred['risk_level']}")
        print(f"     - Reasoning:        {pred['risk_reasoning']}")
        print("\n" + "="*66 + "\n")

if __name__ == "__main__":
    main()
