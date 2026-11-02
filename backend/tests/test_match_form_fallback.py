"""Missing form must not be replaced with cloned demo scores."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.services.data_loader import get_team_form, get_team_results
from app.services.sportmonks import (
    _extract_participants,
    _fixture_search_queries,
    resolve_fixture_and_teams,
)


class DemoFormDisabledTests(unittest.TestCase):
    def test_team_results_empty_without_supabase(self) -> None:
        with patch("app.services.data_loader._use_supabase", return_value=False):
            self.assertEqual(get_team_results("liverpool", is_home=True), ([], []))
            self.assertEqual(get_team_results("arsenal", is_home=False), ([], []))

    def test_team_form_empty_without_supabase(self) -> None:
        with patch("app.services.data_loader._use_supabase", return_value=False):
            self.assertEqual(get_team_form("liverpool"), ([], 0, 0, 0))

    def test_demo_goal_arrays_are_not_returned(self) -> None:
        with patch("app.services.data_loader._use_supabase", return_value=False):
            home_for, _ = get_team_results("any", is_home=True)
            away_for, _ = get_team_results("any", is_home=False)
            self.assertNotEqual(home_for, [1, 2, 1, 0, 2])
            self.assertNotEqual(away_for, [0, 1, 1, 2, 0])


class FixtureSearchResolveTests(unittest.TestCase):
    def test_search_queries_include_vs_and_single_names(self) -> None:
        queries = _fixture_search_queries("KFUM Oslo", "HamKam")
        self.assertIn("KFUM Oslo vs HamKam", queries)
        self.assertIn("HamKam vs KFUM Oslo", queries)
        self.assertIn("KFUM Oslo", queries)
        self.assertIn("HamKam", queries)

    @patch("app.services.sportmonks.team_upcoming_fixtures", return_value=[])
    @patch("app.services.sportmonks._get_allow_404", return_value={"data": []})
    @patch("app.services.sportmonks._get")
    @patch("app.services.sportmonks.fixtures_search")
    @patch("app.services.sportmonks._resolve_team_candidate", return_value=None)
    @patch("app.services.sportmonks._use_sportmonks", return_value=True)
    def test_resolves_via_fixtures_search_when_teams_search_empty(
        self,
        _use_sm,
        _resolve_team,
        fixtures_search,
        get_mock,
        _h2h,
        _upcoming,
    ) -> None:
        kickoff = (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S")
        fixtures_search.return_value = [
            {"id": 99, "name": "KFUM Oslo vs HamKam", "starting_at": kickoff},
        ]

        def fake_get(path, params=None, include=None):
            if str(path).startswith("/fixtures/99"):
                return {
                    "data": {
                        "id": 99,
                        "name": "KFUM Oslo vs HamKam",
                        "starting_at": kickoff,
                        "participants": [
                            {"id": 111, "name": "KFUM Oslo", "meta": {"location": "home"}},
                            {"id": 222, "name": "HamKam", "meta": {"location": "away"}},
                        ],
                    }
                }
            return {}

        get_mock.side_effect = fake_get
        out = resolve_fixture_and_teams("KFUM Oslo", "HamKam")
        self.assertIsNotNone(out)
        self.assertEqual(out["id"], 99)
        home_p, away_p = _extract_participants(out)
        self.assertEqual(home_p["id"], 111)
        self.assertEqual(away_p["id"], 222)
        self.assertTrue(fixtures_search.called)


if __name__ == "__main__":
    unittest.main()
