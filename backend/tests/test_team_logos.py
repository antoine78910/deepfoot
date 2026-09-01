"""Crest lookup must use the local seed, never HTTP."""
from __future__ import annotations

import unittest

from app.services import api_football as af
from app.services.data_loader import _attach_team_logos


class TeamLogoLookupTests(unittest.TestCase):
    def setUp(self) -> None:
        af._teams_cache = {}
        af._teams_cache_loaded = False
        self._orig_get = af._get

        def _blocked(*_a, **_k):
            raise AssertionError("API-Football should not be called for logo lookup")

        af._get = _blocked  # type: ignore[assignment]

    def tearDown(self) -> None:
        af._get = self._orig_get
        af._teams_cache = {}
        af._teams_cache_loaded = False

    def test_logo_by_api_football_id(self) -> None:
        url = af.logo_url_for_team(team_id=85)
        self.assertIsNotNone(url)
        self.assertIn("teams/85", url or "")

    def test_logo_by_name(self) -> None:
        url = af.logo_url_for_team(name="Paris Saint Germain")
        self.assertIsNotNone(url)
        self.assertTrue((url or "").startswith("http"))

    def test_sportmonks_id_not_used_when_name_matches(self) -> None:
        """SM id 85 is FC København; AF 85 is PSG. Name must win if id is unknown to AF cache."""
        ctx = {
            "home_team": "Paris Saint Germain",
            "away_team": "Marseille",
            "home_team_logo": None,
            "away_team_logo": None,
        }
        filled = _attach_team_logos(ctx, "PSG", "OM", None, None)
        self.assertTrue((filled.get("home_team_logo") or "").startswith("http"))
        self.assertTrue((filled.get("away_team_logo") or "").startswith("http"))
        self.assertNotEqual(filled["home_team_logo"], filled["away_team_logo"])

    def test_does_not_overwrite_existing_logos(self) -> None:
        ctx = {
            "home_team": "PSG",
            "away_team": "OM",
            "home_team_logo": "https://example.com/home.png",
            "away_team_logo": "https://example.com/away.png",
        }
        filled = _attach_team_logos(ctx, "PSG", "OM", 85, 81)
        self.assertEqual(filled["home_team_logo"], "https://example.com/home.png")
        self.assertEqual(filled["away_team_logo"], "https://example.com/away.png")


if __name__ == "__main__":
    unittest.main()
