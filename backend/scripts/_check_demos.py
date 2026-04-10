import sqlite3
c = sqlite3.connect("data/demand_intelligence.db")
rows = c.execute(
    "SELECT sku_id, risk_level, surge_flag, signal_detail "
    "FROM sku_inventory WHERE scenario_type != 'R' ORDER BY sku_id"
).fetchall()
for r in rows:
    print(f"{r[0]:16s} {r[1]:16s} {r[2]:8s} {r[3]}")
c.close()
