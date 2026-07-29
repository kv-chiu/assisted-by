import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ParseCommitsTest(unittest.TestCase):
    def test_daily_dimensions_count_each_bucket_once_per_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            output = Path(directory) / "output.json"
            subprocess.run(["git", "init", "-q", repo], check=True)
            subprocess.run(
                ["git", "-C", repo, "config", "user.name", "Test"], check=True
            )
            subprocess.run(
                ["git", "-C", repo, "config", "user.email", "test@example.com"],
                check=True,
            )
            (repo / "driver.c").write_text("one\ntwo\n")
            subprocess.run(["git", "-C", repo, "add", "driver.c"], check=True)
            env = {
                **os.environ,
                "GIT_AUTHOR_DATE": "2026-07-29T12:00:00Z",
                "GIT_COMMITTER_DATE": "2026-07-29T12:00:00Z",
            }
            subprocess.run(
                [
                    "git", "-C", repo, "commit", "-qm", "driver: fix probe",
                    "-m", "Assisted-by: Codex:gpt-5.5\nAssisted-by: OpenAI:gpt-5.6",
                ],
                check=True,
                env=env,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "parse_commits.py"),
                    str(repo / ".git"),
                    str(output),
                ],
                check=True,
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            result = json.loads(output.read_text())

        day = result["daily_dimensions"]["2026-07-29"]
        self.assertEqual(day["patches"], 1)
        self.assertEqual(day["vendors"], {"OpenAI": 1})
        self.assertEqual(
            day["models"], {"OpenAI — GPT-5.5": 1, "OpenAI — GPT-5.6": 1}
        )
        self.assertEqual(day["tools"], {"Codex": 1})
        self.assertEqual(day["vendor_lines"]["OpenAI"], {"ins": 2, "del": 0})


if __name__ == "__main__":
    unittest.main()
