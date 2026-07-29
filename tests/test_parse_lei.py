import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def message(sender, date, subject, body, message_id):
    return (
        "From sender@example.com Thu Jan  1 00:00:00 2026\n"
        f"From: {sender}\n"
        f"Date: {date}\n"
        f"Subject: {subject}\n"
        f"Message-ID: <{message_id}>\n"
        "Content-Type: text/plain; charset=utf-8\n"
        "\n"
        f"{body}\n"
    )


class ParseLeiTest(unittest.TestCase):
    def test_latest_same_day_revision_wins_and_quotes_are_not_counted(self):
        mailbox = "".join([
            message(
                "Developer <dev@example.com>",
                "Wed, 1 Jul 2026 10:00:00 +0000",
                "[PATCH v1] driver: improve probe",
                "Assisted-by: Claude:claude-opus-4-6\nSigned-off-by: Developer <dev@example.com>",
                "v1@example.com",
            ),
            message(
                "Developer <dev@example.com>",
                "Wed, 1 Jul 2026 12:00:00 +0000",
                "[PATCH v2] driver: improve probe",
                "Assisted-by: Antigravity:gemini-3.5-flash\nSigned-off-by: Developer <dev@example.com>",
                "v2@example.com",
            ),
            message(
                "Other <other@example.com>",
                "Wed, 1 Jul 2026 13:00:00 +0000",
                "[PATCH] docs: quote example",
                "> Assisted-by: Claude:claude-opus-4-6",
                "quote@example.com",
            ),
            message(
                "Reviewer <reviewer@example.com>",
                "Wed, 1 Jul 2026 14:00:00 +0000",
                "Re: [PATCH v2] driver: improve probe",
                "> Assisted-by: Antigravity:gemini-3.5-flash",
                "reply@example.com",
            ),
        ])

        with tempfile.TemporaryDirectory() as directory:
            mbox = Path(directory) / "input.mbox"
            output = Path(directory) / "output.json"
            mbox.write_text(mailbox)
            subprocess.run(
                [sys.executable, str(ROOT / "parse_lei.py"), str(mbox), str(output)],
                check=True,
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            result = json.loads(output.read_text())

        self.assertEqual(result["input_messages"], 4)
        self.assertEqual(result["patch_messages_with_tag"], 2)
        self.assertEqual(result["unique_patches_with_tag"], 1)
        self.assertEqual(result["quote_only_skipped"], 1)
        self.assertEqual(result["non_patch_or_reply"], 1)
        self.assertEqual(result["latest"], "2026-07-01")
        self.assertEqual(result["vendor_counts"], [["Google", 1]])
        self.assertEqual(result["tool_counts"], [["Antigravity", 1]])
        self.assertEqual(
            result["daily_dimensions"]["2026-07-01"],
            {
                "patches": 1,
                "vendors": {"Google": 1},
                "models": {"Google — Gemini 3.5": 1},
                "tools": {"Antigravity": 1},
                "authors": {
                    hashlib.sha256(b"dev@example.com").hexdigest()[:16]: 1
                },
                "model_authors": {
                    "Google — Gemini 3.5": {
                        hashlib.sha256(b"dev@example.com").hexdigest()[:16]: 1
                    }
                },
            },
        )


if __name__ == "__main__":
    unittest.main()
