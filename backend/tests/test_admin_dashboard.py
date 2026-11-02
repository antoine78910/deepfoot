"""Admin dashboard helpers: owner email and compact prediction cards."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.api.internal import _check_dashboard_admin, _prediction_summary, is_dashboard_admin_email


class AdminDashboardHelperTests(unittest.TestCase):
    def test_owner_email_is_admin(self) -> None:
        self.assertTrue(is_dashboard_admin_email("Anto.Delbos@gmail.com"))
        self.assertFalse(is_dashboard_admin_email("user@example.com"))
        self.assertFalse(is_dashboard_admin_email(""))

    def test_owner_user_id_skips_token(self) -> None:
        with patch("app.api.internal._email_for_user_id", return_value="anto.delbos@gmail.com"):
            _check_dashboard_admin(None, "owner-id")

    def test_non_admin_is_rejected(self) -> None:
        with patch("app.api.internal._email_for_user_id", return_value="user@example.com"):
            with self.assertRaises(HTTPException) as ctx:
                _check_dashboard_admin("wrong-token", "user-id")
        self.assertEqual(ctx.exception.status_code, 403)

    def test_prediction_summary_from_history(self) -> None:
        card = _prediction_summary(
            {
                "id": "abc",
                "created_at": "2026-11-02T10:00:00+00:00",
                "home_team": "PSG",
                "away_team": "OM",
                "league": "Ligue 1",
                "result": {
                    "prob_home": 52.1,
                    "prob_draw": 24.0,
                    "prob_away": 23.9,
                    "most_likely_score": {"home": 2, "away": 1, "probability": 11.4},
                    "quick_summary": "PSG slightly favoured.",
                },
            }
        )
        self.assertEqual(card["home_team"], "PSG")
        self.assertEqual(card["away_team"], "OM")
        self.assertEqual(card["prob_home"], 52.1)
        self.assertEqual(card["most_likely_score"], "2-1")
        self.assertEqual(card["most_likely_score_pct"], 11.4)


if __name__ == "__main__":
    unittest.main()
