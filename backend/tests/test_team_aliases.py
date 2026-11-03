"""National-team and multilingual aliases must map to searchable English names."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services.team_aliases import canonical_search_name


class TeamAliasTests(unittest.TestCase):
    def test_user_examples_map_to_english(self) -> None:
        cases = {
            "Чехия": "Czech Republic",
            "Англия": "England",
            "Italia": "Italy",
            "Belgie": "Belgium",
            "Israeli": "Israel",
            "Irlandid": "Ireland",
            "Валенсия": "Valencia",
            "Реал Сосьсс": "Real Sociedad",
            "Czechia": "Czech Republic",
            "Angleterre": "England",
            "Belgique": "Belgium",
            "Irlande": "Ireland",
        }
        for raw, expected in cases.items():
            self.assertEqual(canonical_search_name(raw), expected, msg=raw)

    def test_resolve_searches_english_alias(self) -> None:
        from app.services import thesportsdb as tsdb

        tsdb._RESOLVE_MISS.clear()
        calls: list[str] = []

        def fake_http(path: str, params: dict):
            calls.append(str(params.get("t") or ""))
            if params.get("t") == "Czech Republic":
                return {
                    "teams": [
                        {
                            "strTeam": "Czech Republic",
                            "strSport": "Soccer",
                            "idTeam": "111",
                            "idLeague": "4429",
                            "strLeague": "FIFA World Cup",
                        }
                    ]
                }
            return {"teams": []}

        with patch("app.services.thesportsdb._http_get", side_effect=fake_http), patch(
            "app.services.thesportsdb._read_cache", return_value=None
        ), patch("app.services.thesportsdb._write_cache"):
            info = tsdb.resolve_team("Чехия")
        self.assertIsNotNone(info)
        self.assertEqual(info["strTeam"], "Czech Republic")
        self.assertEqual(calls[0], "Czech Republic")

    def test_ireland_typo_skips_youth_and_uses_senior_side(self) -> None:
        from app.services import thesportsdb as tsdb

        tsdb._RESOLVE_MISS.clear()
        calls: list[str] = []

        def fake_http(path: str, params: dict):
            term = str(params.get("t") or "")
            calls.append(term)
            if term == "Ireland":
                return {
                    "teams": [
                        {
                            "strTeam": "Ireland",
                            "strSport": "Soccer",
                            "idTeam": "133911",
                            "idLeague": "4429",
                            "strLeague": "World Cup Qualifying UEFA",
                        }
                    ]
                }
            return {"teams": []}

        with patch("app.services.thesportsdb._http_get", side_effect=fake_http), patch(
            "app.services.thesportsdb._read_cache", return_value=None
        ), patch("app.services.thesportsdb._write_cache"):
            info = tsdb.resolve_team("Irlandid")
        self.assertIsNotNone(info)
        self.assertEqual(info["strTeam"], "Ireland")
        self.assertEqual(calls[0], "Ireland")


if __name__ == "__main__":
    unittest.main()
