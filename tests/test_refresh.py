import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RefreshShellTest(unittest.TestCase):
    def registered(self, configured: str, expected: str) -> bool:
        script = f"""
lei() {{
  if [[ "$1" == "ls-external" ]]; then
    printf '%s\\n' {configured!r}
  fi
}}
source ./refresh.sh
lei_external_registered {expected!r}
"""
        return subprocess.run(
            ["bash", "-c", script], cwd=ROOT, check=False
        ).returncode == 0

    def test_accepts_trailing_slash_added_by_lei(self):
        self.assertTrue(
            self.registered(
                "https://lore.kernel.org/all/", "https://lore.kernel.org/all"
            )
        )

    def test_accepts_trailing_slash_removed_by_lei(self):
        self.assertTrue(
            self.registered(
                "https://lore.kernel.org/all", "https://lore.kernel.org/all/"
            )
        )

    def test_rejects_a_different_external(self):
        self.assertFalse(
            self.registered(
                "https://lore.kernel.org/lkml/", "https://lore.kernel.org/all/"
            )
        )


if __name__ == "__main__":
    unittest.main()
