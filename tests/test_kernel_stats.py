import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from kernel_stats import compute


class KernelStatsTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name) / "repo"
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        subprocess.run(
            ["git", "-C", self.repo, "config", "user.name", "Test"], check=True
        )
        subprocess.run(
            ["git", "-C", self.repo, "config", "user.email", "test@example.com"],
            check=True,
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def commit(self, message: str, day: int) -> str:
        env = {
            **os.environ,
            "GIT_AUTHOR_DATE": f"2026-01-{day:02d}T12:00:00Z",
            "GIT_COMMITTER_DATE": f"2026-01-{day:02d}T12:00:00Z",
        }
        subprocess.run(["git", "-C", self.repo, "add", "."], check=True)
        subprocess.run(
            ["git", "-C", self.repo, "commit", "-qm", message],
            check=True,
            env=env,
        )
        return subprocess.check_output(
            ["git", "-C", self.repo, "rev-parse", "HEAD"], text=True
        ).strip()

    def test_incremental_result_matches_full_result(self):
        (self.repo / "one.txt").write_text("one\ntwo\n")
        previous_head = self.commit("first", 2)
        baseline = compute(str(self.repo / ".git"), None, None)
        self.assertEqual(baseline["calculation"], "full")
        self.assertEqual(baseline["total_loc_at_head"], 2)

        (self.repo / "one.txt").write_text("one\ntwo changed\nthree\n")
        (self.repo / "two.txt").write_text("four\n")
        self.commit("second", 3)

        incremental = compute(
            str(self.repo / ".git"), previous_head, baseline
        )
        full = compute(str(self.repo / ".git"), None, None)

        self.assertEqual(incremental["calculation"], "incremental")
        for key in (
            "head", "commits", "insertions", "deletions", "total_loc_at_head"
        ):
            self.assertEqual(incremental[key], full[key], key)

    def test_mismatched_baseline_falls_back_to_full(self):
        (self.repo / "one.txt").write_text("one\n")
        previous_head = self.commit("first", 2)
        baseline = compute(str(self.repo / ".git"), None, None)
        baseline["head"] = "0" * 40

        result = compute(str(self.repo / ".git"), previous_head, baseline)
        self.assertEqual(result["calculation"], "full")


if __name__ == "__main__":
    unittest.main()
