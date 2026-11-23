#!/usr/bin/env python3
"""Rounds of a downstream restore TauCeti from its public cache and never compile it.

A downstream such as QPainleve pins TauCeti as an `[[upstreams]]` entry with its own public Lake
cache, but has no root-package cache service. Its rounds got no TauCeti outputs, so every worker
compiled TauCeti in its own checkout after each pin change, which takes unrealistically long.
Before the agent starts, the round now runs the same script CI runs (Tools'
dependency-cache-get.py) and hands its Lake settings to the agent; if the fetch fails the round
does not start. Every round's prompt also says never to build TauCeti from source.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from tauceti_worker import agents

UPSTREAMS = json.dumps([
    {"repo": "leanprover-community/mathlib4", "package": "mathlib", "update": False},
    {"repo": "TauCetiProject/TauCeti", "package": "TauCeti",
     "cache_artifact_url": "https://cache.taucetiproject.org/artifacts",
     "cache_revision_url": "https://cache.taucetiproject.org/revisions"},
])


class StopLaunch(Exception):
    pass


class DependencyCache(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "lakefile.toml").write_text('name = "QPainleve"\n')

    def fetch_with(self, lines):
        calls = []

        def fake(command, cwd, env, output, timeout):
            calls.append((command, env))
            Path(env["GITHUB_ENV"]).write_text("".join(line + "\n" for line in lines))
            return 0

        env = {"PATH": os.environ["PATH"]}
        with patch.dict(os.environ, {"TAUCETI_UPSTREAMS": UPSTREAMS}), patch.object(agents, "_cache_fetch", fake):
            agents._fetch_dependency_caches(self.root, env, self.root / "logs", ("view",))
        return calls, env

    def test_runs_the_ci_script_and_hands_its_settings_to_the_round(self):
        cache = str(self.root / ".lake/cache")
        calls, env = self.fetch_with([f"LAKE_CACHE_DIR={cache}", "LAKE_ARTIFACT_CACHE=true", "LAKE_RESTORE_ARTIFACTS=true"])
        (command, _), = calls
        self.assertEqual(command[:2], ["view", "python3"])
        self.assertTrue(command[2].endswith("scripts/dependency-cache-get.py"))
        self.assertTrue(Path(command[2]).is_file())
        self.assertEqual(command[3], str(self.root))
        self.assertEqual(env["LAKE_CACHE_DIR"], cache)
        self.assertEqual(env["LAKE_ARTIFACT_CACHE"], "true")
        self.assertEqual(env["LAKE_RESTORE_ARTIFACTS"], "true")

    def test_a_failed_fetch_does_not_start_the_round(self):
        with self.assertRaises(agents.BuildCacheUnavailable):
            self.fetch_with(["LAKE_ARTIFACT_CACHE=false", "LAKE_RESTORE_ARTIFACTS=false", "LAKE_CACHE_DIR="])
        with self.assertRaises(agents.BuildCacheUnavailable):
            self.fetch_with([])

    def test_no_upstream_cache_changes_nothing(self):
        calls = []
        env = {}
        with patch.dict(os.environ, {"TAUCETI_UPSTREAMS": "[]"}), patch.object(agents, "_cache_fetch", lambda *a: calls.append(a) or 0):
            agents._fetch_dependency_caches(self.root, env, self.root / "logs")
        self.assertEqual((calls, env), ([], {}))

    def prompt(self, upstreams):
        captured = []

        def launch(prompt, profile):
            captured.append(prompt)
            raise StopLaunch

        with (
            patch.object(agents, "TAUCETI_CACHE_SERVICE", ""),
            patch.object(agents, "host_agent_launch", launch),
            patch.dict(os.environ, {"TAUCETI_UPSTREAMS": upstreams}),
        ):
            with self.assertRaises(StopLaunch):
                agents.run_agent_host(self.root, "task", "codex", self.root / "logs")
        return captured[0]

    def test_every_round_is_told_never_to_build_tauceti(self):
        text = self.prompt(UPSTREAMS)
        self.assertIn("Never build TauCeti from source", text)
        self.assertIn("scripts/dependency-cache-get.py .", text)
        self.assertNotIn("Never build TauCeti from source", self.prompt("[]"))


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
