#!/usr/bin/env python3
"""Compute kernel-wide change totals since 2026-01-01.

When a cached kernel repository is available, update the published totals from
the cached HEAD instead of walking every commit and recounting the full tree.
"""

import argparse
import json
import re
import subprocess
from pathlib import Path


SINCE = "2026-01-01"
SHORTSTAT_RE = re.compile(
    r"(\d+) files? changed"
    r"(?:, (\d+) insertions?\(\+\))?"
    r"(?:, (\d+) deletions?\(-\))?"
)


def git(repo: str, *args: str) -> str:
    return subprocess.check_output(
        ["git", "--git-dir", repo, *args], text=True
    )


def parse_shortstat(raw: str) -> dict:
    insertions = deletions = commits = boundary_artifacts = 0
    for line in raw.splitlines():
        line = line.strip()
        if line == "COMMIT":
            commits += 1
            continue
        match = SHORTSTAT_RE.match(line)
        if not match:
            continue
        files = int(match.group(1))
        # A shallow boundary commit is compared with an empty parent and looks
        # like the entire kernel was added.  Do not count that synthetic diff.
        if files > 50000:
            boundary_artifacts += 1
            continue
        insertions += int(match.group(2) or 0)
        deletions += int(match.group(3) or 0)
    return {
        "commits": commits,
        "insertions": insertions,
        "deletions": deletions,
        "boundary_artifacts_skipped": boundary_artifacts,
    }


def current_line_count(repo: str) -> int:
    """Count lines in HEAD blobs without materializing a multi-GB tar stream."""
    proc = subprocess.run(
        ["git", "--git-dir", repo, "grep", "-a", "-c", "-e", "", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode not in (0, 1):
        raise subprocess.CalledProcessError(
            proc.returncode, proc.args, proc.stdout, proc.stderr
        )
    total = 0
    for line in proc.stdout.splitlines():
        try:
            total += int(line.rsplit(":", 1)[1])
        except (IndexError, ValueError) as exc:
            raise ValueError(f"unexpected git grep output: {line!r}") from exc
    return total


def endpoint_line_delta(repo: str, previous_head: str, head: str) -> int:
    """Return the exact text-line delta between two trees."""
    delta = 0
    raw = git(repo, "diff", "--numstat", previous_head, head)
    for line in raw.splitlines():
        fields = line.split("\t", 2)
        if len(fields) < 2 or fields[0] == "-" or fields[1] == "-":
            continue
        delta += int(fields[0]) - int(fields[1])
    return delta


def is_ancestor(repo: str, previous_head: str, head: str) -> bool:
    return subprocess.run(
        [
            "git", "--git-dir", repo, "merge-base", "--is-ancestor",
            previous_head, head,
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def load_baseline(path: str | None) -> dict | None:
    if not path:
        return None
    baseline_path = Path(path)
    if not baseline_path.exists():
        return None
    return json.loads(baseline_path.read_text())


def compute(repo: str, previous_head: str | None, baseline: dict | None) -> dict:
    head = git(repo, "rev-parse", "HEAD").strip()
    can_increment = bool(
        previous_head
        and baseline
        and baseline.get("since") == SINCE
        and baseline.get("total_loc_at_head", 0) > 0
        and (not baseline.get("head") or baseline["head"] == previous_head)
        and is_ancestor(repo, previous_head, head)
    )

    if can_increment:
        raw = git(
            repo, "log", "--no-merges", "--shortstat",
            "--pretty=format:COMMIT", f"{previous_head}..{head}",
        )
        delta = parse_shortstat(raw)
        out = {
            "since": SINCE,
            "head": head,
            "commits": baseline["commits"] + delta["commits"],
            "insertions": baseline["insertions"] + delta["insertions"],
            "deletions": baseline["deletions"] + delta["deletions"],
            "boundary_artifacts_skipped": (
                baseline.get("boundary_artifacts_skipped", 0)
                + delta["boundary_artifacts_skipped"]
            ),
            "total_loc_at_head": (
                baseline["total_loc_at_head"]
                + endpoint_line_delta(repo, previous_head, head)
            ),
            "calculation": "incremental",
        }
    else:
        raw = git(
            repo, "log", f"--since={SINCE}", "--no-merges", "--shortstat",
            "--pretty=format:COMMIT",
        )
        out = {"since": SINCE, "head": head, **parse_shortstat(raw)}
        out["total_loc_at_head"] = current_line_count(repo)
        out["calculation"] = "full"

    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default="linux-full.git")
    parser.add_argument("out", nargs="?", default="kernel_stats.json")
    parser.add_argument("--previous-head")
    parser.add_argument("--baseline")
    args = parser.parse_args()

    out = compute(
        args.repo, args.previous_head, load_baseline(args.baseline)
    )
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
