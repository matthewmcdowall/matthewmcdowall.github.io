#!/usr/bin/env python3
"""Reads local ~/.claude/ data and writes claude-stats.json for the portfolio."""

import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
OUTPUT = Path(__file__).parent / "claude-stats.json"


def read_stats_cache():
    """Read the stats-cache.json file."""
    path = CLAUDE_DIR / "stats-cache.json"
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def read_history():
    """Read history.jsonl and count messages per day."""
    path = CLAUDE_DIR / "history.jsonl"
    daily = Counter()
    if not path.exists():
        return daily
    with open(path) as f:
        for line in f:
            try:
                obj = json.loads(line)
                ts = obj.get("timestamp", 0)
                if ts:
                    dt = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
                    daily[dt] += 1
            except (json.JSONDecodeError, ValueError):
                continue
    return daily


def merge_data(stats_cache, history_counts):
    """Merge stats-cache and history data, preferring stats-cache for overlapping dates."""
    daily = {}

    # History data as baseline
    for date, count in history_counts.items():
        daily[date] = {"date": date, "messageCount": count, "sessionCount": 0, "toolCallCount": 0}

    # Stats-cache overrides (more accurate)
    for entry in stats_cache.get("dailyActivity", []):
        d = entry["date"]
        if d not in daily or entry["messageCount"] > daily[d]["messageCount"]:
            daily[d] = {
                "date": d,
                "messageCount": entry.get("messageCount", 0),
                "sessionCount": entry.get("sessionCount", 0),
                "toolCallCount": entry.get("toolCallCount", 0),
            }

    sorted_days = sorted(daily.values(), key=lambda x: x["date"])
    total_messages = sum(d["messageCount"] for d in sorted_days)
    active_days = sum(1 for d in sorted_days if d["messageCount"] > 0)

    return {
        "totalMessages": total_messages,
        "activeDays": active_days,
        "dailyActivity": sorted_days,
    }


def main():
    stats_cache = read_stats_cache()
    history_counts = read_history()
    result = merge_data(stats_cache, history_counts)

    with open(OUTPUT, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Wrote {OUTPUT}")
    print(f"  Total messages: {result['totalMessages']}")
    print(f"  Active days: {result['activeDays']}")
    print(f"  Date range: {result['dailyActivity'][0]['date']} to {result['dailyActivity'][-1]['date']}")


if __name__ == "__main__":
    main()
