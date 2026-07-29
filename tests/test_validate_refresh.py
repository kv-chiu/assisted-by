import unittest

from validate_refresh import validate_progress, validate_shape


def merged(total=2, tags=2):
    return {
        "total_commits": total,
        "total_tags": tags,
        "commits": [{} for _ in range(total)],
        "daily_dimensions": {"2026-07-01": {"patches": total}},
    }


def lore(messages=5, tagged=4, unique=3, latest="2026-07-01"):
    return {
        "input_messages": messages,
        "patch_messages_with_tag": tagged,
        "unique_patches_with_tag": unique,
        "latest": latest,
        "daily_dimensions": {
            "2026-07-01": {
                "patches": unique,
                "authors": {"anonymous-author": unique},
                "models": {},
                "model_authors": {},
            }
        },
    }


class ValidateRefreshTest(unittest.TestCase):
    def test_accepts_monotonic_refresh(self):
        old_merged = merged()
        old_lore = lore()
        new_merged = merged(3, 4)
        new_lore = lore(7, 6, 4, "2026-07-02")
        validate_shape(new_merged, new_lore)
        validate_progress(old_merged, old_lore, new_merged, new_lore)

    def test_rejects_partial_lore_result(self):
        with self.assertRaisesRegex(ValueError, "input_messages regressed"):
            validate_progress(merged(), lore(), merged(), lore(messages=4))

    def test_rejects_empty_result(self):
        with self.assertRaisesRegex(ValueError, "no commits"):
            validate_shape(merged(total=0, tags=0), lore())


if __name__ == "__main__":
    unittest.main()
