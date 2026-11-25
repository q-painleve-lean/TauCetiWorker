#!/usr/bin/env python3
"""QPainleve's roadmap authors avoid meaningless piecemeal PRs and open coherent units of work.

Upstream's roadmap prompt adds "smaller-but-green beats bigger-but-broken" to its size guidance.
With the ~1200–2000 line target in place, QPainleve's merged roadmap PRs still stayed small: of the
298 merged from 2026-11-24 00:49 to 2026-11-25 02:00, the median added 276 lines and none reached
1200. QPainleve's policy is that work should not be released in meaningless small pieces, so the
sentence is replaced by "Avoid meaningless piecemeal PRs: open a PR for a coherent, substantial unit
of work." The guidance sits under "Hard rules of the repo", which an operator's extra roadmap prompt
cannot override. Default workers render prompts/v0, so both variants are checked.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CoherentUnits(unittest.TestCase):
    def test_both_variants_ask_for_coherent_units_instead_of_smaller_but_green(self):
        for name in ("prompts/roadmap.md", "prompts/v0/roadmap.md"):
            with self.subTest(prompt=name):
                text = (ROOT / name).read_text()
                self.assertNotIn("smaller-but-green", text)
                self.assertEqual(
                    text.count("Avoid meaningless piecemeal PRs: open a PR for a coherent, substantial unit of work."), 1
                )
                self.assertIn("A shorter PR that closes a milestone beats a longer peripheral one.", text)


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
