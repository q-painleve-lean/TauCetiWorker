"""Roadmap authors read the live author claims before claiming their own target.

A free-choice author derives its own slug, so `claim.sh acquire` collides only when two agents
derive the same one, and work without a pull request is visible nowhere else (QPainleve #296 and
#297: one target, slugs `sum-basemultiplicity-le-boundaryintersection` and
`boundary-base-multiplicity-bound`, both acquired). The roadmap prompt therefore lists the live
claims before claiming. This test checks that both prompt variants carry the step, and that
`claim.sh list --full` prints what the step relies on: one key and lease per line, the lease
naming its owner and `expires_at`, filterable to one roadmap's author claims.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAIM_SH = ROOT / "scripts" / "claim.sh"
STEP = "**Check the claims other agents hold.**"
LIST = '"__BIN__/claim.sh" list --full | grep \'^author/<target-roadmap>/\''


class PromptStep(unittest.TestCase):
    def test_both_variants_list_claims_before_claiming(self):
        for name in ("prompts/roadmap.md", "prompts/v0/roadmap.md"):
            with self.subTest(prompt=name):
                text = (ROOT / name).read_text()
                self.assertEqual(text.count(STEP), 1)
                self.assertIn(LIST, text)
                self.assertLess(text.index(STEP), text.index("- **Claim it:**"))
                self.assertIn("in any wording", text)


class ClaimList(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="claim-list-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        origin = root / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
        # claim.sh always talks to https://github.com/$CLAIM_REPO; point that URL at the local bare repo.
        self.env = {
            **os.environ,
            "CLAIM_REPO": "example/claims",
            "CLAIM_GITDIR": str(root / "scratch.git"),
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": f"url.{origin.as_uri()}.insteadOf",
            "GIT_CONFIG_VALUE_0": "https://github.com/example/claims",
        }

    def claim(self, owner, *args):
        env = {**self.env, "TAUCETI_WORKER_ID": owner}
        return subprocess.run(["bash", str(CLAIM_SH), *args], env=env, capture_output=True, text=True)

    def test_list_full_shows_each_lease_with_owner_and_expiry(self):
        self.assertEqual(self.claim("qp-sol", "acquire", "author/Area/sum-basemultiplicity-le-boundaryintersection", "600").returncode, 0)
        # A different slug for the same target is not refused: the gap the prompt step covers.
        self.assertEqual(self.claim("qp-sol-3", "acquire", "author/Area/boundary-base-multiplicity-bound", "600").returncode, 0)
        self.assertEqual(self.claim("qp-fixci", "acquire", "branch/163", "600").returncode, 0)
        self.assertEqual(self.claim("qp-sol-3", "acquire", "author/Area/sum-basemultiplicity-le-boundaryintersection", "600").returncode, 1)

        listed = self.claim("qp-sol-2", "list", "--full")
        self.assertEqual(listed.returncode, 0, listed.stderr)
        rows = dict(line.split("\t", 1) for line in listed.stdout.splitlines())
        authors = {key: json.loads(lease) for key, lease in rows.items() if key.startswith("author/Area/")}
        self.assertEqual(
            set(authors),
            {"author/Area/sum-basemultiplicity-le-boundaryintersection", "author/Area/boundary-base-multiplicity-bound"},
        )
        self.assertIn("branch/163", rows)
        self.assertEqual(authors["author/Area/boundary-base-multiplicity-bound"]["owner"], "qp-sol-3")
        for lease in authors.values():
            self.assertIsInstance(lease["expires_at"], int)


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
