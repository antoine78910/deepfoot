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

    def test_looked_up_owner_email_allows(self) -> None:
        with patch("app.api.internal._email_for_user_id", return_value="anto.delbos@gmail.com"):
            _check_dashboard_admin(x_user_id="owner-id")

    def test_claimed_owner_email_allows_when_lookup_fails(self) -> None:
        with patch("app.api.internal._email_for_user_id", return_value=None):
            _check_dashboard_admin(x_user_id="owner-id", x_user_email="Anto.Delbos@gmail.com")

    def test_claimed_owner_email_without_user_id_is_rejected(self) -> None:
        with patch("app.api.internal._email_for_user_id", return_value=None):
            with self.assertRaises(HTTPException) as ctx:
                _check_dashboard_admin(x_user_email="anto.delbos@gmail.com")
        self.assertEqual(ctx.exception.status_code, 403)

    def test_non_admin_is_rejected(self) -> None:
        with patch("app.api.internal._email_for_user_id", return_value="user@example.com"):
            with self.assertRaises(HTTPException) as ctx:
                _check_dashboard_admin(x_user_id="user-id", x_user_email="user@example.com")
        self.assertEqual(ctx.exception.status_code, 403)

    def test_prediction_summary_from_history(self) -> None:
        card = _prediction_summary(
            {
                "id": "abc",
                "user_id": "u1",
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
        self.assertEqual(card["user_id"], "u1")
        self.assertEqual(card["prob_home"], 52.1)
        self.assertEqual(card["most_likely_score"], "2-1")
        self.assertEqual(card["most_likely_score_pct"], 11.4)
        self.assertTrue(card["cost_estimated"])
        self.assertGreater(card["cost_eur"], 0)
        self.assertFalse(card["placeholder_form"])

    def test_placeholder_form_detected_from_demo_signature(self) -> None:
        card = _prediction_summary(
            {
                "home_team": "Liverpool",
                "away_team": "Arsenal",
                "result": {
                    "prob_home": 46.7,
                    "prob_draw": 33.1,
                    "prob_away": 20.2,
                    "xg_home": 1.07,
                    "xg_away": 0.59,
                    "most_likely_score": {"home": 1, "away": 0, "probability": 20.3},
                    "analysis_recap": {
                        "data_source": "API-Football",
                        "pipeline_steps": [
                            {
                                "detail": "Home: goals_for=[1, 2, 1, 0, 2]. Away: goals_for=[0, 1, 1, 2, 0].",
                            }
                        ],
                    },
                },
            }
        )
        self.assertTrue(card["placeholder_form"])
        self.assertEqual(card["data_source"], "API-Football")

    def test_placeholder_form_detected_from_xg_signature(self) -> None:
        card = _prediction_summary(
            {
                "home_team": "KFUM Oslo",
                "away_team": "HamKam",
                "result": {
                    "prob_home": 46.7,
                    "prob_draw": 33.1,
                    "prob_away": 20.2,
                    "xg_home": 1.07,
                    "xg_away": 0.59,
                    "most_likely_score": {"home": 1, "away": 0, "probability": 20.3},
                },
            }
        )
        self.assertTrue(card["placeholder_form"])

    def test_recalculated_form_is_not_flagged_placeholder(self) -> None:
        card = _prediction_summary(
            {
                "home_team": "Liverpool",
                "away_team": "Arsenal",
                "result": {
                    "prob_home": 61.2,
                    "prob_draw": 22.0,
                    "prob_away": 16.8,
                    "xg_home": 1.66,
                    "xg_away": 0.44,
                    "recalculated_from_form": True,
                    "analysis_recap": {
                        "placeholder_form": False,
                        "recalculated_from_form": True,
                        "pipeline_steps": [
                            {
                                "detail": "Home: goals_for=[1, 2, 1, 0, 2]. Away: goals_for=[0, 1, 1, 2, 0].",
                            }
                        ],
                    },
                },
            }
        )
        self.assertFalse(card["placeholder_form"])


if __name__ == "__main__":
    unittest.main()
