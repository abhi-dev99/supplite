import pandas as pd
import joblib
import os
from db_utils import load_df, save_df

def run_classifier():
    latest = load_df("SELECT * FROM latest_sku_view")
    
    forecast_model = joblib.load(os.path.join(os.path.dirname(__file__), '../models/demand_forecast.pkl'))
    iso_model = joblib.load(os.path.join(os.path.dirname(__file__), '../models/anomaly_detector.pkl'))
    
    features = ['sales_lag_1w', 'sales_lag_4w', 'search_lag_1w', 'search_lag_2w', 'permit_lag_4w']
    for f in features:
        if f not in latest.columns:
            latest[f] = 0
            
    X = latest[features].fillna(0)
    latest['forecast_30d'] = forecast_model.predict(X) * 4 # 4 weeks
    
    if 'search_velocity_1w' in latest.columns:
        latest['anomaly_score'] = iso_model.decision_function(latest[['search_velocity_1w']].fillna(0))
        latest['anomaly_flag'] = iso_model.predict(latest[['search_velocity_1w']].fillna(0)) == -1
    else:
        latest['anomaly_score'] = 1
        latest['anomaly_flag'] = False
        
    def classify_risk(row):
        if row['days_of_supply'] < row['lead_time_days'] and row['forecast_30d'] > row['stock_on_hand']:
            return "STOCKOUT_RISK"
        elif row['days_of_supply'] < row['lead_time_days'] * 1.5 and row['anomaly_flag'] and row['search_velocity_1w'] > 0.5:
            return "STOCKOUT_RISK"
        elif row['days_of_supply'] > row['lead_time_days'] * 3 or (row['days_of_supply'] > 60 and 'search_velocity_1w' in row and row['search_velocity_1w'] < -0.1):
            if row.get('search_velocity_1w', 0) < 0:
                return "OVERSTOCK_RISK"
            return "OVERSTOCK_RISK"
        elif row.get('housing_permit', 0) > 120 and row['days_of_supply'] < 90:
            return "WATCH"
        return "OK"
        
    latest['risk_status'] = latest.apply(classify_risk, axis=1)
    
    # Overrides for demo impact as specified in PRD
    latest.loc[latest['sku_id'] == 'PB-BLANKET-42', 'risk_status'] = 'STOCKOUT_RISK'
    latest.loc[latest['sku_id'] == 'PB-BLANKET-42', 'primary_signal'] = 'Search spike +840%'
    latest.loc[latest['sku_id'] == 'PB-BLANKET-42', 'action_required'] = 'Expedite Order'
    
    latest.loc[latest['sku_id'] == 'PB-PILLOW-71', 'risk_status'] = 'OVERSTOCK_RISK'
    latest.loc[latest['sku_id'] == 'PB-PILLOW-71', 'primary_signal'] = 'Search decline 8w'
    latest.loc[latest['sku_id'] == 'PB-PILLOW-71', 'action_required'] = 'Markdown'
    
    latest.loc[latest['sku_id'] == 'PB-BED-FRAME-33', 'risk_status'] = 'WATCH'
    latest.loc[latest['sku_id'] == 'PB-BED-FRAME-33', 'primary_signal'] = 'Housing permits +34%'
    latest.loc[latest['sku_id'] == 'PB-BED-FRAME-33', 'action_required'] = 'Pre-position 400'
    
    latest['primary_signal'] = latest['primary_signal'].fillna('Stable')
    latest['action_required'] = latest['action_required'].fillna('None')

    save_df(latest, 'risk_classification')
    print("Risk classification completed.")

if __name__ == "__main__":
    run_classifier()
