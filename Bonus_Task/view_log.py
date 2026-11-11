"""Bonus: read route_log.csv and print every logged question + time per route."""
import csv

from route_logger import LOG_FILE

if not LOG_FILE.exists():
    raise SystemExit(f"{LOG_FILE} not found. Run: python run_tests.py")

with open(LOG_FILE, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

print(f"Logged questions: {len(rows)}\n")
print(f"{'#':<3} {'Route':<5} {'Time ms':>8}  Question")
for i, r in enumerate(rows, start=1):
    print(f"{i:<3} {r['route']:<5} {float(r['time_ms']):>8.2f}  {r['question']}")

by_route = {}
for r in rows:
    by_route.setdefault(r["route"], []).append(float(r["time_ms"]))

print("\nTime taken per route")
print(f"{'Route':<6} {'Questions':>9} {'Min ms':>8} {'Avg ms':>8} {'Max ms':>8} {'Total ms':>9}")
for route in ("RAG", "SQL", "BOTH"):
    t = by_route.get(route)
    if t:
        print(f"{route:<6} {len(t):>9} {min(t):>8.2f} {sum(t) / len(t):>8.2f} {max(t):>8.2f} {sum(t):>9.2f}")