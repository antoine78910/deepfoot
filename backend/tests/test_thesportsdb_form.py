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

    def test_cyrillic_alias_used_in_search(self) -> None:
        from unittest.mock import patch

        from app.services import thesportsdb as tsdb

        tsdb._TEAM_RESULTS_MEM.clear()
        tsdb._RESOLVE_MISS.clear()
        calls: list[str] = []

        def fake_http(path: str, params: dict):
            calls.append(str(params.get("t") or ""))
            if params.get("t") == "Bayern Munich":
                return {"teams": [{"strTeam": "Bayern Munich", "strSport": "Soccer", "idTeam": "1", "idLeague": "4331"}]}
            return {"teams": []}

        with patch("app.services.thesportsdb._http_get", side_effect=fake_http), patch(
            "app.services.thesportsdb._read_cache", return_value=None
        ), patch("app.services.thesportsdb._write_cache"):
            info = tsdb.resolve_team("Бавария Германия")
        self.assertIsNotNone(info)
        self.assertEqual(calls[0], "Bayern Munich")

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

    def test_season_fill_when_last_events_lack_scores(self) -> None:
        from unittest.mock import patch

        last = [{"idEvent": "a", "idHomeTeam": "1", "idAwayTeam": "2"}] * 5
        last[0] = {
            "idEvent": "a0",
            "idHomeTeam": "1",
            "idAwayTeam": "2",
            "intHomeScore": "2",
            "intAwayScore": "0",
        }
        season = [
            {
                "idEvent": f"s{i}",
                "idHomeTeam": "1",
                "idAwayTeam": "9",
                "intHomeScore": str(i % 3),
                "intAwayScore": "1",
            }
            for i in range(6)
        ]
        from app.services import thesportsdb as tsdb

        tsdb._TEAM_RESULTS_MEM.clear()
        info = {"idTeam": "1", "idLeague": "4334"}
        with patch("app.services.thesportsdb.resolve_team", return_value=info), patch(
            "app.services.thesportsdb._events_last", return_value=last
        ), patch("app.services.thesportsdb._events_season", return_value=season):
            gf, _ga, form = team_last_results("Lyon")
        self.assertGreaterEqual(len(gf), 5)
        self.assertGreaterEqual(len(form), 5)


if __name__ == "__main__":
    unittest.main()
