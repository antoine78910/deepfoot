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

    @patch("app.services.sportmonks.team_upcoming_fixtures", return_value=[])
    @patch("app.services.sportmonks._get_allow_404", return_value={"data": []})
    @patch("app.services.sportmonks._get")
    @patch("app.services.sportmonks._subscribed_fixtures_window")
    @patch("app.services.sportmonks.fixtures_search", return_value=[])
    @patch("app.services.sportmonks._resolve_team_candidate", return_value=None)
    @patch("app.services.sportmonks._use_sportmonks", return_value=True)
    def test_resolves_via_subscribed_fixture_window(
        self,
        _use_sm,
        _resolve_team,
        _search,
        window,
        get_mock,
        _h2h,
        _upcoming,
    ) -> None:
        kickoff = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        window.return_value = [
            {"id": 19713878, "name": "Sonderjyske Fodbold vs FC Kobenhavn", "starting_at": kickoff},
        ]

        def fake_get(path, params=None, include=None):
            if str(path).startswith("/fixtures/19713878"):
                return {
                    "data": {
                        "id": 19713878,
                        "name": "Sonderjyske Fodbold vs FC Kobenhavn",
                        "participants": [
                            {"id": 390, "name": "Sonderjyske Fodbold", "meta": {"location": "home"}},
                            {"id": 85, "name": "FC Kobenhavn", "meta": {"location": "away"}},
                        ],
                    }
                }
            return {}

        get_mock.side_effect = fake_get
        out = resolve_fixture_and_teams("Sonderjyske Fodbold", "FC Kobenhavn")
        self.assertIsNotNone(out)
        self.assertEqual(out["id"], 19713878)


class TheSportsDbFormEnrichTests(unittest.TestCase):
    def test_empty_sportmonks_context_gets_match_specific_lambdas(self) -> None:
        from app.ml.poisson import predict_all
        from app.services.data_loader import apply_thesportsdb_form_if_missing

        def fake_results(name: str, last_n: int = 10):
            if "Liverpool" in name:
                return ([2, 1, 3, 0, 2], [1, 1, 1, 1, 0], ["W", "D", "W", "L", "W"])
            if "Arsenal" in name:
                return ([1, 0, 2, 1, 1], [1, 2, 0, 0, 2], ["D", "L", "W", "W", "L"])
            if "HamKam" in name:
                return ([0, 1, 0, 2, 0], [3, 2, 1, 1, 2], ["L", "L", "L", "W", "L"])
            return ([2, 2, 1, 3, 1], [2, 0, 1, 1, 1], ["D", "W", "D", "W", "D"])

        empty = {"lambda_home": 1.2, "lambda_away": 1.2, "data_recap": {"placeholder_form": True}}
        with patch("app.services.thesportsdb.team_last_results", side_effect=fake_results):
            liv = apply_thesportsdb_form_if_missing(
                {**empty, "home_team": "Liverpool", "away_team": "Arsenal"},
                "Liverpool",
                "Arsenal",
            )
            kfum = apply_thesportsdb_form_if_missing(
                {**empty, "home_team": "KFUM Oslo", "away_team": "HamKam"},
                "KFUM Oslo",
                "HamKam",
            )
        self.assertNotEqual(
            (round(float(liv["lambda_home"]), 2), round(float(liv["lambda_away"]), 2)),
            (round(float(kfum["lambda_home"]), 2), round(float(kfum["lambda_away"]), 2)),
        )
        p1 = predict_all(liv["lambda_home"], liv["lambda_away"])
        p2 = predict_all(kfum["lambda_home"], kfum["lambda_away"])
        self.assertNotEqual(
            (p1["prob_home"], p1["prob_draw"], p1["prob_away"]),
            (p2["prob_home"], p2["prob_draw"], p2["prob_away"]),
        )
        self.assertFalse(liv["data_recap"]["placeholder_form"])
        self.assertFalse(kfum["data_recap"]["placeholder_form"])

    def test_keeps_real_form_without_calling_thesportsdb(self) -> None:
        from app.services.data_loader import apply_thesportsdb_form_if_missing

        ctx = {
            "lambda_home": 1.8,
            "lambda_away": 1.1,
            "data_recap": {
                "raw_home_goals_for": [1, 2, 0],
                "raw_away_goals_for": [3, 1, 1],
            },
        }
        with patch("app.services.thesportsdb.team_last_results") as mocked:
            out = apply_thesportsdb_form_if_missing(ctx, "A", "B")
        mocked.assert_not_called()
        self.assertEqual(out["lambda_home"], 1.8)
        self.assertFalse(out["data_recap"]["placeholder_form"])


if __name__ == "__main__":
    unittest.main()
