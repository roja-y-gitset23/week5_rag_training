"""Bonus: log every routed question and the time it took (route_log.csv)."""
import csv
from datetime import datetime
from pathlib import Path

LOG_FILE = Path("route_log.csv")
HEADER = ["timestamp", "question", "route", "tool", "sources", "time_ms"]


def reset_log():
    """Delete the old log so a new test run starts with an empty file."""
    LOG_FILE.unlink(missing_ok=True)


def log_route(question, route, tool, sources, seconds):
    """Append one row per routed question."""
    is_new = not LOG_FILE.exists()
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(HEADER)
        w.writerow([
            datetime.now().isoformat(timespec="seconds"),
            question,
            route,
            tool,
            " | ".join(sources),
            f"{seconds * 1000:.2f}",
        ])