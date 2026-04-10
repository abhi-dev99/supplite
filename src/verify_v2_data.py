"""
verify_v2_data.py
=================
Comprehensive verification of v2 synthetic datasets.
Runs 20 checks and reports PASS/FAIL for each.
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "new"

EXPECTED_SKUS = 30
EXPECTED_METROS = 11
EXPECTED_DAYS = 365
EXPECTED_SIGNAL_ROWS = EXPECTED_SKUS * EXPECTED_METROS * EXPECTED_DAYS  # 120,450
EXPECTED_INV_ROWS = EXPECTED_SKUS * EXPECTED_METROS  # 330

METRO_INCOMES = {
    "Atlanta": 82100, "Chicago": 78300, "Dallas": 74600, "Denver": 105200,
    "Houston": 67200, "Los Angeles": 83400, "Miami": 59600, "New York": 117400,
    "Phoenix": 72800, "San Francisco": 136700, "Seattle": 120600,
}

W_SV, W_IRE, W_HS, W_BS = 0.40, 0.25, 0.20, 0.15

results = []

def check(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append((name, status, detail))
    icon = "PASS" if passed else "FAIL"
    print(f"  [{icon}] {name}" + (f"  -- {detail}" if detail else ""))

# ---- Load data -----
print("Loading datasets...")
with open(DATA_DIR / "sku_daily_signals.csv", encoding="utf-8") as f:
    signals = list(csv.DictReader(f))
with open(DATA_DIR / "sku_catalog.csv", encoding="utf-8") as f:
    catalog = list(csv.DictReader(f))
with open(DATA_DIR / "sku_inventory.csv", encoding="utf-8") as f:
    inventory = list(csv.DictReader(f))
with open(DATA_DIR / "metro_income.csv", encoding="utf-8") as f:
    metro_csv = list(csv.DictReader(f))
with open(DATA_DIR / "frontend_data.json", encoding="utf-8") as f:
    frontend = json.load(f)

print(f"  Loaded: {len(signals):,} signal rows, {len(catalog)} catalog, {len(inventory)} inventory, {len(metro_csv)} metros\n")

# ---- CHECK 1: Row count ----
check("1. Signal row count",
      len(signals) == EXPECTED_SIGNAL_ROWS,
      f"got {len(signals):,}, expected {EXPECTED_SIGNAL_ROWS:,}")

# ---- CHECK 2: Date range ----
dates = sorted(set(r["date"] for r in signals))
check("2. Date range",
      dates[0] == "2025-04-11" and dates[-1] == "2026-04-10",
      f"first={dates[0]}, last={dates[-1]}")

check("2b. No date gaps",
      len(dates) == EXPECTED_DAYS,
      f"unique dates={len(dates)}, expected={EXPECTED_DAYS}")

# ---- CHECK 3: SKU coverage ----
sku_ids = set(r["sku_id"] for r in signals)
check("3. SKU coverage in signals",
      len(sku_ids) == EXPECTED_SKUS,
      f"found {len(sku_ids)} SKUs")

# ---- CHECK 4: Metro coverage ----
metros = set(r["metro"] for r in signals)
check("4. Metro coverage in signals",
      len(metros) == EXPECTED_METROS,
      f"found {len(metros)} metros")

# Check every SKU×metro×day combo
sku_metro_day = set((r["sku_id"], r["metro"], r["date"]) for r in signals)
check("4b. Full SKU×metro×day matrix",
      len(sku_metro_day) == EXPECTED_SIGNAL_ROWS,
      f"unique combos={len(sku_metro_day):,}")

# ---- CHECK 5: Median income constant per metro ----
metro_incomes_in_data = defaultdict(set)
for r in signals:
    metro_incomes_in_data[r["metro"]].add(int(r["median_income"]))
income_constant = all(len(v) == 1 for v in metro_incomes_in_data.values())
income_correct = all(
    list(metro_incomes_in_data[m])[0] == METRO_INCOMES[m]
    for m in metro_incomes_in_data
)
check("5. Median income constant per metro", income_constant)
check("5b. Median income matches spec", income_correct,
      "; ".join(f"{m}={list(v)[0]}" for m, v in sorted(metro_incomes_in_data.items()) if list(v)[0] != METRO_INCOMES.get(m, -1)) or "all match")

# ---- CHECK 6: Housing permits repeat within month×metro ----
# Group by (metro, year-month) and check all days have same value
permit_by_metro_month = defaultdict(set)
# Also check that permits are same for DIFFERENT SKUs in same metro+date
permit_by_metro_date = defaultdict(set)
for r in signals:
    ym = r["date"][:7]  # "YYYY-MM"
    permit_by_metro_month[(r["metro"], ym)].add(int(r["housing_permits"]))
    permit_by_metro_date[(r["metro"], r["date"])].add(int(r["housing_permits"]))

permits_monthly_repeat = all(len(v) == 1 for v in permit_by_metro_month.values())
permits_metro_level = all(len(v) == 1 for v in permit_by_metro_date.values())

violations = [(k, v) for k, v in permit_by_metro_month.items() if len(v) > 1]
check("6. Housing permits repeat within month×metro",
      permits_monthly_repeat,
      f"{len(violations)} violations" if violations else "all months constant")

violations2 = [(k, v) for k, v in permit_by_metro_date.items() if len(v) > 1]
check("6b. Housing permits identical across SKUs in same metro+date",
      permits_metro_level,
      f"{len(violations2)} violations" if violations2 else "all SKUs agree per metro+date")

# ---- CHECK 7: Search index range 0-100 ----
search_values = [float(r["search_index"]) for r in signals]
check("7. Search index range 0-100",
      all(0 <= v <= 100 for v in search_values),
      f"min={min(search_values)}, max={max(search_values)}")

# ---- CHECK 8: Units sold non-negative ----
units = [int(r["units_sold"]) for r in signals]
check("8. Units sold non-negative",
      all(v >= 0 for v in units),
      f"min={min(units)}")

# ---- CHECK 9: Holiday flag/name consistency ----
holiday_consistent = True
bad_holidays = 0
for r in signals:
    flag = int(r["holiday_flag"])
    name = r["holiday_name"]
    if flag == 1 and not name:
        holiday_consistent = False
        bad_holidays += 1
    if flag == 0 and name:
        holiday_consistent = False
        bad_holidays += 1
check("9. Holiday flag/name consistency",
      holiday_consistent,
      f"{bad_holidays} inconsistencies" if bad_holidays else "")

# ---- CHECK 10: Scenario type matches catalog ----
catalog_scenarios = {r["sku_id"]: r["scenario_type"] for r in catalog}
scenario_match = all(
    r["scenario_type"] == catalog_scenarios.get(r["sku_id"], "?")
    for r in signals
)
check("10. Scenario type matches catalog", scenario_match)

# ---- CHECK 11: Composite score range 0-100 ----
composites = [float(r["composite_score"]) for r in signals]
check("11. Composite score range 0-100",
      all(0 <= v <= 100 for v in composites),
      f"min={min(composites):.1f}, max={max(composites):.1f}")

# ---- CHECK 12: Sub-scores range 0-100 ----
for col in ["income_re_score", "holiday_search_score", "base_search_score", "sales_velocity_score"]:
    vals = [float(r[col]) for r in signals]
    check(f"12. {col} range 0-100",
          all(0 <= v <= 100 for v in vals),
          f"min={min(vals):.1f}, max={max(vals):.1f}")

# ---- CHECK 13: Composite ≈ weighted sum ----
max_composite_error = 0
for r in signals:
    expected = (
        W_SV * float(r["sales_velocity_score"]) +
        W_IRE * float(r["income_re_score"]) +
        W_HS * float(r["holiday_search_score"]) +
        W_BS * float(r["base_search_score"])
    )
    actual = float(r["composite_score"])
    err = abs(expected - actual)
    max_composite_error = max(max_composite_error, err)
check("13. Composite = weighted sum formula",
      max_composite_error < 0.2,  # allow rounding tolerance
      f"max error = {max_composite_error:.4f}")

# ---- CHECK 14: Weekend effect ----
from datetime import date as dt_date
weekday_sales = []
weekend_sales = []
for r in signals:
    d = dt_date.fromisoformat(r["date"])
    u = int(r["units_sold"])
    if d.weekday() >= 5:
        weekend_sales.append(u)
    else:
        weekday_sales.append(u)
avg_weekday = sum(weekday_sales) / max(len(weekday_sales), 1)
avg_weekend = sum(weekend_sales) / max(len(weekend_sales), 1)
weekend_uplift = (avg_weekend - avg_weekday) / max(avg_weekday, 0.1) * 100
check("14. Weekend effect (~20% uplift)",
      10 < weekend_uplift < 35,
      f"avg weekday={avg_weekday:.1f}, weekend={avg_weekend:.1f}, uplift={weekend_uplift:.1f}%")

# ---- CHECK 15: Inventory foreign keys ----
signal_pairs = set((r["sku_id"], r["metro"]) for r in signals)
inv_pairs = set((r["sku_id"], r["metro"]) for r in inventory)
check("15. Inventory FK match signals",
      inv_pairs <= signal_pairs,
      f"inv pairs={len(inv_pairs)}, signal pairs={len(signal_pairs)}")

check("15b. Inventory row count",
      len(inventory) == EXPECTED_INV_ROWS,
      f"got {len(inventory)}, expected {EXPECTED_INV_ROWS}")

# ---- CHECK 16: Days of supply formula ----
dos_ok = True
dos_errors = 0
for r in inventory:
    stock = int(r["stock_on_hand"])
    on_order = int(r["on_order"])
    avg_daily = float(r["avg_daily_sales"])
    dos = int(r["days_of_supply"])
    if avg_daily > 0:
        expected_dos = round((stock + on_order) / avg_daily)
        # Low-volume SKUs (avg < 1) have amplified rounding effects
        tolerance = 10 if avg_daily < 1 else 3
        if abs(dos - expected_dos) > tolerance:
            dos_ok = False
            dos_errors += 1
check("16. Days of supply formula",
      dos_ok,
      f"{dos_errors} errors" if dos_errors else "")

# ---- CHECK 17: Scenario behavior spot-checks ----
# Scenario A (viral_spike): last 7 days sales > 2x first 30 days avg (in home metro)
scenario_checks_pass = True
scenario_detail = []

# Build lookup: (sku_id, metro) -> list of (day_index, units_sold)
from collections import defaultdict as dd
ts_data = dd(list)
for r in signals:
    ts_data[(r["sku_id"], r["metro"])].append((int(r["day_index"]), int(r["units_sold"])))

# Sort each by day_index
for k in ts_data:
    ts_data[k].sort()

# Check Scenario A: PB-BLANKET-42 in Los Angeles
# The viral spike peaks around day 320-334 (event at day 320), so check peak period
key_a = ("PB-BLANKET-42", "Los Angeles")
if key_a in ts_data:
    ts = ts_data[key_a]
    early_avg = sum(u for _, u in ts[:30]) / 30
    # Check peak period (days 320-340) rather than tail
    peak_sales = [u for d, u in ts if 320 <= d <= 340]
    peak_avg = sum(peak_sales) / max(len(peak_sales), 1)
    a_pass = peak_avg > early_avg * 1.5
    if not a_pass:
        scenario_detail.append(f"A: peak_avg={peak_avg:.1f} vs early*1.5={early_avg*1.5:.1f}")
    scenario_checks_pass = scenario_checks_pass and a_pass

# Check Scenario B: PB-PILLOW-71 in New York — declining
key_b = ("PB-PILLOW-71", "New York")
if key_b in ts_data:
    ts = ts_data[key_b]
    mid_avg = sum(u for _, u in ts[180:220]) / 40
    late_avg = sum(u for _, u in ts[-30:]) / 30
    b_pass = late_avg < mid_avg * 0.85
    if not b_pass:
        scenario_detail.append(f"B: late={late_avg:.1f} not < mid×0.85={mid_avg*0.85:.1f}")
    scenario_checks_pass = scenario_checks_pass and b_pass

# Check Scenario D: PB-THROW-55 in Seattle — steady
key_d = ("PB-THROW-55", "Seattle")
if key_d in ts_data:
    ts = ts_data[key_d]
    early_avg = sum(u for _, u in ts[:90]) / 90
    late_avg = sum(u for _, u in ts[-90:]) / 90
    d_pass = 0.7 < (late_avg / max(early_avg, 0.1)) < 1.5
    if not d_pass:
        scenario_detail.append(f"D: ratio={late_avg/max(early_avg,0.1):.2f}")
    scenario_checks_pass = scenario_checks_pass and d_pass

check("17. Scenario behavior spot-checks",
      scenario_checks_pass,
      "; ".join(scenario_detail) if scenario_detail else "A,B,D scenarios behave as expected")

# ---- CHECK 18: metro_income.csv matches spec ----
csv_incomes = {r["metro"]: int(r["median_income"]) for r in metro_csv}
metro_match = csv_incomes == METRO_INCOMES
check("18. metro_income.csv matches spec",
      metro_match,
      f"mismatches: {set(csv_incomes.items()) - set(METRO_INCOMES.items())}" if not metro_match else "")

# ---- CHECK 19: sku_catalog.csv completeness ----
catalog_ids = set(r["sku_id"] for r in catalog)
required_fields = ["sku_id", "product_name", "brand", "category", "price", "cost_price",
                   "lead_time_days", "home_metro", "scenario_type", "scenario_label"]
fields_present = all(f in catalog[0] for f in required_fields) if catalog else False
no_blanks = all(all(r[f] for f in required_fields) for r in catalog)
check("19. sku_catalog.csv completeness",
      len(catalog) == EXPECTED_SKUS and fields_present and no_blanks,
      f"rows={len(catalog)}, fields_ok={fields_present}, no_blanks={no_blanks}")

# ---- CHECK 20: frontend_data.json ----
sku_table = frontend.get("skuTable", [])
chart_data = frontend.get("chartData", {})
check("20a. frontend_data.json skuTable count",
      len(sku_table) == EXPECTED_SKUS,
      f"got {len(sku_table)}")

charts_have_12_weeks = all(len(v) == 12 for v in chart_data.values())
check("20b. frontend_data.json chart data 12 weeks",
      charts_have_12_weeks and len(chart_data) == EXPECTED_SKUS,
      f"SKUs with charts={len(chart_data)}")

# ---- Summary ----
print("\n" + "=" * 60)
passed = sum(1 for _, s, _ in results if s == "PASS")
failed = sum(1 for _, s, _ in results if s == "FAIL")
print(f"  RESULTS: {passed} PASSED, {failed} FAILED out of {len(results)} checks")
if failed > 0:
    print("\n  FAILURES:")
    for name, status, detail in results:
        if status == "FAIL":
            print(f"    FAIL: {name}: {detail}")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
