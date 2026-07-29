#!/usr/bin/env python3
"""Build fixed, comparable time-window aggregates for the web page."""

from collections import Counter, defaultdict
from datetime import date, timedelta


WINDOW_DAYS = (7, 30, 45, 60, 90, 180)
DIMENSIONS = ("vendors", "models", "tools")
LINE_DIMENSIONS = ("vendor_lines", "model_lines", "tool_lines")


def effective_count(counts) -> float:
    """Inverse Simpson concentration: 1 / sum(author_share ** 2)."""
    total = sum(counts)
    if not total:
        return 0.0
    return 1.0 / sum((count / total) ** 2 for count in counts)


def gini(counts) -> float:
    """Gini coefficient for a non-negative contribution distribution."""
    values = sorted(count for count in counts if count >= 0)
    total = sum(values)
    size = len(values)
    if not size or not total:
        return 0.0
    weighted = sum(
        (2 * index - size - 1) * value
        for index, value in enumerate(values, start=1)
    )
    return weighted / (size * total)


def author_dominance(author_counts: Counter, model_authors: dict) -> dict:
    """Build anonymous window-level and per-model concentration summaries."""
    ranked_authors = sorted(
        author_counts.items(), key=lambda item: (-item[1], item[0])
    )
    total_patches = sum(author_counts.values())
    author_count = len(author_counts)
    top1 = {author for author, _ in ranked_authors[:1]}
    top5 = {author for author, _ in ranked_authors[:5]}
    top1_patches = sum(author_counts[author] for author in top1)
    top5_patches = sum(author_counts[author] for author in top5)
    remaining1 = total_patches - top1_patches
    remaining5 = total_patches - top5_patches

    def percentage(numerator, denominator):
        return round(numerator / denominator * 100, 4) if denominator else None

    models = {}
    for model, counts in model_authors.items():
        model_patches = sum(counts.values())
        without1 = sum(
            count for author, count in counts.items() if author not in top1
        )
        without5 = sum(
            count for author, count in counts.items() if author not in top5
        )
        models[model] = {
            "patches": model_patches,
            "authors": len(counts),
            "effective_contributors": round(effective_count(counts.values()), 4),
            "raw_share": percentage(model_patches, total_patches),
            "without_top1_share": percentage(without1, remaining1),
            "without_top5_share": percentage(without5, remaining5),
            "contributor_weighted_share": percentage(len(counts), author_count),
        }

    return {
        "authors": author_count,
        "patches": total_patches,
        "effective_contributors": round(
            effective_count(author_counts.values()), 4
        ),
        "top1_share": percentage(top1_patches, total_patches),
        "top5_share": percentage(top5_patches, total_patches),
        "gini": round(gini(author_counts.values()), 4),
        "models": models,
    }


def aggregate_daily(daily: dict, start: str, end: str) -> dict:
    dimensions = {name: Counter() for name in DIMENSIONS}
    line_dimensions = {
        name: defaultdict(lambda: [0, 0]) for name in LINE_DIMENSIONS
    }
    patches = insertions = deletions = 0
    author_counts = Counter()
    model_authors = defaultdict(Counter)

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
        author_counts.update(bucket.get("authors", {}))
        for model, counts in bucket.get("model_authors", {}).items():
            model_authors[model].update(counts)

    out = {
        "patches": patches,
        "lines": {"ins": insertions, "del": deletions},
        "author_analysis": author_dominance(author_counts, model_authors),
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
        current_merged = aggregate_daily(merged_daily, start, end)
        current_submitted = aggregate_daily(submitted_daily, start, end)
        previous_merged = aggregate_daily(merged_daily, prev_start, prev_end)
        previous_submitted = aggregate_daily(
            submitted_daily, prev_start, prev_end
        )
        current_merged.pop("author_analysis", None)
        previous_merged.pop("author_analysis", None)
        previous_submitted.pop("author_analysis", None)
        windows[str(days)] = {
            "days": days,
            "start": start,
            "end": end,
            "merged": current_merged,
            "submitted": current_submitted,
            "previous": {
                "start": prev_start,
                "end": prev_end,
                "merged": previous_merged,
                "submitted": previous_submitted,
            },
        }

    all_merged = aggregate_daily(merged_daily, since, as_of)
    all_submitted = aggregate_daily(submitted_daily, since, as_of)
    all_merged.pop("author_analysis", None)
    windows["all"] = {
        "days": None,
        "start": since,
        "end": as_of,
        "merged": all_merged,
        "submitted": all_submitted,
        "previous": None,
    }
    return windows
