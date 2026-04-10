"""Convert frontend_data.json into a JS module for data.js."""
import json
from pathlib import Path

data_dir = Path(__file__).resolve().parent.parent / "data" / "new"

with open(data_dir / "frontend_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

lines = []
lines.append("// Auto-generated from src/generate_synthetic_data_v2.py")
lines.append("// 30 SKUs across 5 WSI brands, 11 metro cities, 365 days of daily data")
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
