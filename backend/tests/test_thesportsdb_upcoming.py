"""TheSportsDB event formatting must match the LP upcoming card shape."""
from __future__ import annotations

import unittest

from app.services.thesportsdb import format_event_for_upcoming


class TheSportsDbFormatTests(unittest.TestCase):
    def test_formats_psg_next_match(self) -> None:
        row = format_event_for_upcoming(
            {
                "dateEvent": "2026-09-04",
                "strTimestamp": "2026-09-04T19:05:00",
                "strTime": "19:05:00",
                "strStatus": "NS",
                "strLeague": "French Ligue 1",
                "strHomeTeam": "Paris Saint-Germain",
                "strAwayTeam": "Monaco",
                "strHomeTeamBadge": "https://example.com/psg.png",
                "strAwayTeamBadge": "https://example.com/monaco.png",
            }
        )
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["date"], "04/09")
        self.assertEqual(row["time"], "19:05")
        self.assertEqual(row["league"]["name"], "French Ligue 1")
        self.assertEqual(row["home"]["name"], "Paris Saint-Germain")
        self.assertEqual(row["away"]["name"], "Monaco")
        self.assertEqual(row["home"]["logo"], "https://example.com/psg.png")
        self.assertEqual(row["away"]["logo"], "https://example.com/monaco.png")

    def test_collects_multiple_upcoming_for_one_team(self) -> None:
        from app.services.thesportsdb import fixtures_for_team_from_events

        events = [
            {
                "strTimestamp": "2026-09-04T19:05:00",
                "strStatus": "NS",
                "strLeague": "French Ligue 1",
                "strHomeTeam": "Paris Saint-Germain",
                "strAwayTeam": "Monaco",
                "idHomeTeam": "133714",
                "idAwayTeam": "133823",
            },
            {
                "strTimestamp": "2026-09-04T17:00:00",
                "strStatus": "NS",
                "strLeague": "French Ligue 1",
                "strHomeTeam": "Lyon",
                "strAwayTeam": "Auxerre",
                "idHomeTeam": "1",
                "idAwayTeam": "2",
            },
            {
                "strTimestamp": "2026-09-13T19:00:00",
                "strStatus": "NS",
                "strLeague": "French Ligue 1",
                "strHomeTeam": "Brest",
                "strAwayTeam": "Paris Saint-Germain",
                "idHomeTeam": "3",
                "idAwayTeam": "133714",
            },
        ]
        rows = fixtures_for_team_from_events(events, team_id="133714", team_name="Paris Saint Germain", limit=8)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["away"]["name"], "Monaco")
        self.assertEqual(rows[1]["home"]["name"], "Brest")

    def test_skips_finished_matches(self) -> None:
        row = format_event_for_upcoming(
            {
                "strTimestamp": "2026-08-31T19:00:00",
                "strStatus": "Match Finished",
                "strHomeTeam": "Aston Villa",
                "strAwayTeam": "Arsenal",
            }
        )
        self.assertIsNone(row)
