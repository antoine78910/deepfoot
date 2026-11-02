"""TheSportsDB last results must produce match-specific form, not demo scores."""
from __future__ import annotations

import unittest

from app.services.thesportsdb import _pick_team, results_to_goals_and_form, team_last_results


class TheSportsDbFormTests(unittest.TestCase):
    def test_parses_home_and_away_results(self) -> None:
        events = [
            {
                "idHomeTeam": "1",
                "idAwayTeam": "2",
                "intHomeScore": "2",
                "intAwayScore": "0",
            },
            {
                "idHomeTeam": "9",
                "idAwayTeam": "1",
                "intHomeScore": "1",
                "intAwayScore": "1",
            },
            {
                "idHomeTeam": "1",
                "idAwayTeam": "3",
                "intHomeScore": "0",
                "intAwayScore": "3",
            },
        ]
        gf, ga, form = results_to_goals_and_form(events, "1", last_n=10)
        self.assertEqual(gf, [2, 1, 0])
        self.assertEqual(ga, [0, 1, 3])
        self.assertEqual(form, ["W", "D", "L"])

    def test_skips_events_without_scores(self) -> None:
        events = [
            {"idHomeTeam": "1", "idAwayTeam": "2", "intHomeScore": None, "intAwayScore": None},
            {"idHomeTeam": "1", "idAwayTeam": "2", "intHomeScore": "4", "intAwayScore": "1"},
        ]
        gf, ga, form = results_to_goals_and_form(events, "1")
        self.assertEqual(gf, [4])
        self.assertEqual(form, ["W"])

    def test_pick_team_token_and_single_hit(self) -> None:
        kfum = _pick_team(
            [{"strTeam": "KFUM-Kameratene Oslo", "strSport": "Soccer", "strLeague": "Eliteserien"}],
            "KFUM Oslo",
        )
        self.assertEqual(kfum["strTeam"], "KFUM-Kameratene Oslo")
        hamkam = _pick_team(
            [{"strTeam": "Hamarkameratene", "strSport": "Soccer", "strLeague": "Eliteserien"}],
            "HamKam",
        )
        self.assertEqual(hamkam["strTeam"], "Hamarkameratene")

    def test_team_last_results_empty_when_unresolved(self) -> None:
        from unittest.mock import patch

        with patch("app.services.thesportsdb.resolve_team", return_value=None):
            self.assertEqual(team_last_results("Unknown FC"), ([], [], []))


if __name__ == "__main__":
    unittest.main()
