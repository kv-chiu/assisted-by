import unittest

from window_stats import aggregate_daily, build_windows


class WindowStatsTest(unittest.TestCase):
    def setUp(self):
        self.merged = {
            "2026-06-15": {
                "patches": 1,
                "lines": {"ins": 10, "del": 2},
                "vendors": {"Anthropic": 1},
                "models": {"Anthropic — Opus 4.7": 1},
                "tools": {"Claude Code": 1},
                "vendor_lines": {"Anthropic": {"ins": 10, "del": 2}},
                "model_lines": {
                    "Anthropic — Opus 4.7": {"ins": 10, "del": 2}
                },
                "tool_lines": {"Claude Code": {"ins": 10, "del": 2}},
            },
            "2026-07-29": {
                "patches": 2,
                "lines": {"ins": 7, "del": 1},
                "vendors": {"OpenAI": 2},
                "models": {"OpenAI — GPT-5.5": 2},
                "tools": {"Codex": 2},
                "vendor_lines": {"OpenAI": {"ins": 7, "del": 1}},
                "model_lines": {"OpenAI — GPT-5.5": {"ins": 7, "del": 1}},
                "tool_lines": {"Codex": {"ins": 7, "del": 1}},
            },
        }
        self.submitted = {
            "2026-06-15": {
                "patches": 3,
                "vendors": {"Anthropic": 3},
                "models": {"Anthropic — Opus 4.7": 3},
                "tools": {"Claude Code": 3},
            },
            "2026-07-29": {
                "patches": 5,
                "vendors": {"OpenAI": 5},
                "models": {"OpenAI — GPT-5.5": 5},
                "tools": {"Codex": 5},
            },
        }

    def test_aggregate_daily_sums_counts_and_lines(self):
        result = aggregate_daily(self.merged, "2026-06-01", "2026-07-29")
        self.assertEqual(result["patches"], 3)
        self.assertEqual(result["lines"], {"ins": 17, "del": 3})
        self.assertEqual(result["vendors"], {"Anthropic": 1, "OpenAI": 2})
        self.assertEqual(
            result["model_lines"]["OpenAI — GPT-5.5"],
            {"ins": 7, "del": 1},
        )

    def test_default_window_and_previous_window_are_equal_length(self):
        windows = build_windows(
            self.merged, self.submitted, "2026-07-29", "2026-01-01"
        )
        current = windows["45"]
        self.assertEqual(current["start"], "2026-06-15")
        self.assertEqual(current["end"], "2026-07-29")
        self.assertEqual(current["previous"]["start"], "2026-05-01")
        self.assertEqual(current["previous"]["end"], "2026-06-14")
        self.assertEqual(current["submitted"]["patches"], 8)
        self.assertIsNone(windows["all"]["previous"])


if __name__ == "__main__":
    unittest.main()
