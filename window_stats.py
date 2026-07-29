#!/usr/bin/env python3
"""Build fixed, comparable time-window aggregates for the web page."""

from collections import Counter, defaultdict
from datetime import date, timedelta


WINDOW_DAYS = (7, 30, 45, 60, 90, 180)
DIMENSIONS = ("vendors", "models", "tools")
LINE_DIMENSIONS = ("vendor_lines", "model_lines", "tool_lines")


def aggregate_daily(daily: dict, start: str, end: str) -> dict:
    dimensions = {name: Counter() for name in DIMENSIONS}
    line_dimensions = {
        name: defaultdict(lambda: [0, 0]) for name in LINE_DIMENSIONS
    }
    patches = insertions = deletions = 0

    for day, bucket in daily.items():
        if day < start or day > end:
            continue
        patches += bucket.get("patches", 0)
        lines = bucket.get("lines", {})
        insertions += lines.get("ins", 0)
        deletions += lines.get("del", 0)
        for name in DIMENSIONS:
            dimensions[name].update(bucket.get(name, {}))
        for name in LINE_DIMENSIONS:
            for key, value in bucket.get(name, {}).items():
                line_dimensions[name][key][0] += value.get("ins", 0)
                line_dimensions[name][key][1] += value.get("del", 0)

    out = {
        "patches": patches,
        "lines": {"ins": insertions, "del": deletions},
    }
    out.update({name: dict(values) for name, values in dimensions.items()})
    out.update({
        name: {
            key: {"ins": value[0], "del": value[1]}
            for key, value in values.items()
        }
        for name, values in line_dimensions.items()
    })
    return out


def build_windows(
    merged_daily: dict,
    submitted_daily: dict,
    as_of: str,
    since: str,
) -> dict:
    anchor = date.fromisoformat(as_of)
    windows = {}

    for days in WINDOW_DAYS:
        start_date = anchor - timedelta(days=days - 1)
        previous_end = start_date - timedelta(days=1)
        previous_start = previous_end - timedelta(days=days - 1)
        start = start_date.isoformat()
        end = anchor.isoformat()
        prev_start = previous_start.isoformat()
        prev_end = previous_end.isoformat()
        windows[str(days)] = {
            "days": days,
            "start": start,
            "end": end,
            "merged": aggregate_daily(merged_daily, start, end),
            "submitted": aggregate_daily(submitted_daily, start, end),
            "previous": {
                "start": prev_start,
                "end": prev_end,
                "merged": aggregate_daily(merged_daily, prev_start, prev_end),
                "submitted": aggregate_daily(
                    submitted_daily, prev_start, prev_end
                ),
            },
        }

    windows["all"] = {
        "days": None,
        "start": since,
        "end": as_of,
        "merged": aggregate_daily(merged_daily, since, as_of),
        "submitted": aggregate_daily(submitted_daily, since, as_of),
        "previous": None,
    }
    return windows
