"""Quick verification of generated synthetic data."""
import sqlite3, os, sys
from pathlib import Path

# Force UTF-8
sys.stdout.reconfigure(encoding="utf-8")

DB = Path(__file__).resolve().parents[2] / "data" / "demand_intelligence.db"
conn = sqlite3.connect(str(DB))

print("Tables:", [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()])
print()

for table in ["sku_weekly_signals", "sku_inventory", "sku_catalog"]:
    try:
        count = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count} rows")
    except Exception as e:
        print(f"  {table}: ERROR - {e}")

print("\n=== RISK DISTRIBUTION ===")
for row in conn.execute("SELECT risk_level, count(*) FROM sku_inventory GROUP BY risk_level ORDER BY count(*) DESC").fetchall():
    print(f"  {row[0]:<16s} {row[1]:>3d}")

print("\n=== SURGE DISTRIBUTION ===")
for row in conn.execute("SELECT surge_flag, count(*) FROM sku_inventory GROUP BY surge_flag ORDER BY count(*) DESC").fetchall():
    print(f"  {row[0]:<10s} {row[1]:>3d}")

print("\n=== DEMO SKUS ===")
for row in conn.execute("""
    SELECT sku_id, risk_level, surge_score, surge_flag, signal_detail, recommended_action
    FROM sku_inventory
    WHERE scenario_type != 'R'
    ORDER BY sku_id
""").fetchall():
    print(f"  {row[0]:<16s} {row[1]:<16s} surge={row[2]:>5s} {row[3]:<8s}")
    print(f"    Signal: {row[4]}")
    print(f"    Action: {row[5]}")

print("\n=== PB-BLANKET-42 LAST 10 WEEKS (viral spike) ===")
for row in conn.execute("""
    SELECT week_index, units_sold, search_index, search_velocity_1w, search_velocity_4w, surge_score
    FROM sku_weekly_signals
    WHERE sku_id = 'PB-BLANKET-42'
    ORDER BY CAST(week_index AS INTEGER) DESC
    LIMIT 10
""").fetchall():
    wi = int(row[0]) - 103
    print(f"  W{wi:>+4d}  sold={row[1]:>5s}  search={row[2]:>5s}  vel_1w={row[3]:>7s}%  vel_4w={row[4]:>7s}%  surge={row[5]:>5s}")

print("\n=== FILE SIZES ===")
data_dir = Path(__file__).resolve().parents[2] / "data"
for f in ["sku_weekly_signals.csv", "sku_inventory.csv", "sku_catalog.csv", "demand_intelligence.db"]:
    fp = data_dir / f
    if fp.exists():
        size_kb = fp.stat().st_size / 1024
        print(f"  {f:<30s} {size_kb:>8.1f} KB")

conn.close()
print("\nDone!")
