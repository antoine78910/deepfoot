"""Local teams seed must serve autocomplete without calling the network."""
from __future__ import annotations

import unittest

from app.services import api_football as af


class TeamsLocalCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        af._teams_cache = {}
        af._teams_cache_loaded = False
        self._orig_get = af._get

        def _blocked(*_a, **_k):
            raise AssertionError("API-Football should not be called for seeded autocomplete")

        af._get = _blocked  # type: ignore[assignment]

    def tearDown(self) -> None:
        af._get = self._orig_get
        af._teams_cache = {}
        af._teams_cache_loaded = False

    def test_preload_returns_seeded_clubs(self) -> None:
        teams = af.get_teams_for_autocomplete(q=None, limit=200)
        names = {((t.get("name") or "").lower()) for t in teams}
        self.assertGreaterEqual(len(teams), 80)
        self.assertTrue(any("paris saint" in n for n in names))

    def test_psg_alias_from_seed(self) -> None:
        teams = af.get_teams_for_autocomplete(q="psg", limit=20)
        names = [((t.get("name") or "").lower()) for t in teams]
        self.assertTrue(any("paris" in n for n in names), names)

    def test_real_prefix_from_seed(self) -> None:
        teams = af.get_teams_for_autocomplete(q="real", limit=20)
        names = [((t.get("name") or "").lower()) for t in teams]
        self.assertTrue(any("real madrid" in n for n in names), names)


if __name__ == "__main__":
    unittest.main()
