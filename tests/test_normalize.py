import unittest

from parse_commits import normalize


class NormalizeTest(unittest.TestCase):
    def test_antigravity_gemini(self):
        self.assertEqual(
            normalize("Antigravity:gemini-3.5-flash"),
            {"vendor": "Google", "model": "Gemini 3.5", "tool": "Antigravity"},
        )

    def test_copilot_keeps_wrapper_separate_from_vendor(self):
        self.assertEqual(
            normalize("GitHub Copilot:claude-sonnet-4-6"),
            {"vendor": "Anthropic", "model": "Sonnet 4.6", "tool": "GitHub Copilot"},
        )


if __name__ == "__main__":
    unittest.main()
