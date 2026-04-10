"""Assemble final data.js by combining generated SKU data with existing geo data."""
from pathlib import Path

root = Path(__file__).resolve().parent.parent
data_dir = root / "data" / "new"
frontend_src = root / "frontend" / "src"

# Read the generated SKU exports
with open(data_dir / "generated_sku_exports.js", "r", encoding="utf-8") as f:
    sku_js = f.read()

# Read the existing data.js to extract geoClusters, distributionCenters, wsStores
with open(frontend_src / "data.js", "r", encoding="utf-8") as f:
    existing = f.read()

# Find where geoClusters starts
geo_start = existing.find("export const geoClusters")
if geo_start == -1:
    raise ValueError("Could not find geoClusters in existing data.js")

# Everything from geoClusters onward (distributionCenters + wsStores are after it)
geo_section = existing[geo_start:]

# Assemble final file
final = sku_js.rstrip() + "\n\n" + geo_section

with open(frontend_src / "data.js", "w", encoding="utf-8") as f:
    f.write(final)

print(f"Wrote {frontend_src / 'data.js'}")
print(f"  Total size: {len(final):,} bytes")
print(f"  SKU data: {len(sku_js):,} bytes")
print(f"  Geo/DC/Store data: {len(geo_section):,} bytes")
