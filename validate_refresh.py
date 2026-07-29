#!/usr/bin/env python3
"""Reject incomplete refresh results before they replace published data."""

import json
import os
import sys
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_shape(merged: dict, lore: dict) -> None:
    require(merged.get("total_commits", 0) > 0, "merged result has no commits")
    require(merged.get("total_tags", 0) >= merged["total_commits"],
            "merged tag count is smaller than commit count")
    require(len(merged.get("commits", [])) == merged["total_commits"],
            "merged commit list does not match total_commits")

    require(lore.get("input_messages", 0) > 0, "lore query returned no messages")
    require(lore.get("patch_messages_with_tag", 0) > 0,
            "lore query returned no tagged patch messages")
    require(lore.get("unique_patches_with_tag", 0) > 0,
            "lore query returned no unique tagged patches")
    require(lore["patch_messages_with_tag"] >= lore["unique_patches_with_tag"],
            "unique lore patch count exceeds tagged message count")
    require(bool(lore.get("latest")), "lore result has no latest date")


def validate_progress(old_merged: dict, old_lore: dict,
                      new_merged: dict, new_lore: dict) -> None:
    if os.environ.get("ALLOW_DATA_REGRESSION") == "1":
        return

    for key in ("total_commits", "total_tags"):
        require(new_merged[key] >= old_merged.get(key, 0),
                f"merged {key} regressed: {old_merged.get(key, 0)} -> {new_merged[key]}")
    for key in ("input_messages", "patch_messages_with_tag", "unique_patches_with_tag"):
        require(new_lore[key] >= old_lore.get(key, 0),
                f"lore {key} regressed: {old_lore.get(key, 0)} -> {new_lore[key]}")

    old_latest = old_lore.get("latest")
    if old_latest:
        require(new_lore["latest"] >= old_latest,
                f"lore latest date regressed: {old_latest} -> {new_lore['latest']}")


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit(
            "usage: validate_refresh.py OLD_MERGED OLD_LORE NEW_MERGED NEW_LORE"
        )
    old_merged, old_lore, new_merged, new_lore = map(load, sys.argv[1:])
    validate_shape(new_merged, new_lore)
    validate_progress(old_merged, old_lore, new_merged, new_lore)
    print(
        "validated refresh: "
        f"{new_merged['total_commits']} merged commits, "
        f"{new_lore['unique_patches_with_tag']} submitted patches, "
        f"latest submission {new_lore['latest']}"
    )


if __name__ == "__main__":
    main()
