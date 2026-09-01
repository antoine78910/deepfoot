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
