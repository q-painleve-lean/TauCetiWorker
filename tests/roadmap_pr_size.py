"""QPainleve's roadmap authors aim for ~1200–2000 lines, and a shorter PR that closes a milestone still wins.

Upstream's roadmap prompt aims for ~500–1200 lines. QPainleve's roadmap PRs stayed well below that
(median 363 of the last 60 merged on 2026-11-23), so this fork raises the target. The guidance sits
under "Hard rules of the repo", which an operator's extra roadmap prompt is told it cannot override,
so the number itself is changed. The next sentence, which lets a shorter PR that closes a milestone
beat a longer peripheral one, keeps the balance and must stay. Default workers render prompts/v0, so
both variants are checked.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SizeTarget(unittest.TestCase):
    def test_both_variants_aim_for_1200_to_2000_lines(self):
        for name in ("prompts/roadmap.md", "prompts/v0/roadmap.md"):
            with self.subTest(prompt=name):
                text = (ROOT / name).read_text()
                self.assertEqual(text.count("Aim for ~1200–2000 lines of genuine, non-vacuous content."), 1)
                self.assertNotIn("500–1200", text)
                self.assertIn("A shorter PR that closes a milestone beats a longer peripheral one", text)


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
