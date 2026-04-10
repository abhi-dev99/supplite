"""Convert frontend_data.json into a JS module for data.js."""
import json
from pathlib import Path

data_dir = Path(__file__).resolve().parent.parent / "data" / "new"

with open(data_dir / "frontend_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# --- INJECT ML PREDICTIONS ---
with open(data_dir / "predictions.json", "r", encoding="utf-8") as f:
    preds = json.load(f)

# Aggregate ML predictions globally per SKU
ml_sku_map = {}
for p in preds:
    sku = p["sku_id"]
    if sku not in ml_sku_map:
        ml_sku_map[sku] = {
            "mlForecast60d": 0,
            "anomalyFlag": False,
            "riskLevel": "OK",
            "mlReasoning": "Stable demand.",
            "riskScore": 0  # Score for sorting severity
        }
    
    # Sum global forecast
    ml_sku_map[sku]["mlForecast60d"] += p["forecast_60d"]
    
    # Any anomaly makes the global SKU an anomaly
    if p["anomaly_flag"] == 1:
        ml_sku_map[sku]["anomalyFlag"] = True

    # Risk ranking: STOCKOUT (4) > OVERSTOCK (3) > WATCH (2) > OK (1)
    def risk_to_score(level):
        if level == "STOCKOUT_RISK": return 4
        if level == "OVERSTOCK_RISK": return 3
        if level == "WATCH": return 2
        return 1

    current_score = ml_sku_map[sku]["riskScore"]
    new_score = risk_to_score(p["risk_level"])
    
    if new_score > current_score:
        ml_sku_map[sku]["riskScore"] = new_score
        ml_sku_map[sku]["riskLevel"] = p["risk_level"]
        ml_sku_map[sku]["mlReasoning"] = f"{p['metro']} Metro: {p['risk_reasoning']}"

# Map back into skuTable
for sku in data["skuTable"]:
    ml_data = ml_sku_map.get(sku["id"])
    if ml_data:
        sku["riskLevel"] = ml_data["riskLevel"] # Override mock risk
        sku["mlForecast60d"] = ml_data["mlForecast60d"]
        sku["anomalyFlag"] = ml_data["anomalyFlag"]
        sku["mlReasoning"] = ml_data["mlReasoning"]
    else:
        # Fallbacks
        sku["mlForecast60d"] = 0
        sku["anomalyFlag"] = False
        sku["mlReasoning"] = "No ML Data"

lines = []
lines.append("// Auto-generated from src/build_frontend_data.py")
lines.append("// Contains ML Predictions injected from predictions.json")
lines.append("")
lines.append("export const mockSkus = " + json.dumps(data["skuTable"], indent=2) + ";")
lines.append("")
lines.append("export const mockChartData = " + json.dumps(data["chartData"].get("PB-BLANKET-42", []), indent=2) + ";")
lines.append("")
lines.append("export const allChartData = " + json.dumps(data["chartData"], indent=2) + ";")
lines.append("")

output = "\n".join(lines)

# Write to a staging file. The user will copy this into data.js 
# (preserving geoClusters, distributionCenters, wsStores which remain unchanged)
staging = data_dir / "generated_sku_exports.js"
with open(staging, "w", encoding="utf-8") as f:
    f.write(output)

print(f"Wrote {staging}")
print(f"  mockSkus: {len(data['skuTable'])} items")
print(f"  allChartData: {len(data['chartData'])} entries")
print(f"  File size: {len(output):,} bytes")
