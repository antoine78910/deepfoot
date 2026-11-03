"""AI chat: compact prediction context + Whop plan quotas."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app.services.openai_summary import build_chat_prediction_brief
from app.services.subscription import get_chat_limit, get_chat_quota


class ChatPredictionBriefTests(unittest.TestCase):
    def test_prefers_internal_1x2_and_keeps_news_ready_fields(self) -> None:
        brief = build_chat_prediction_brief(
            {
                "home_team": "Lyon",
                "away_team": "PSG",
                "league": "Ligue 1",
                "prob_home": 46.7,
                "prob_draw": 33.1,
                "prob_away": 20.2,
                "internal_prob_home": 28.4,
                "internal_prob_draw": 26.1,
                "internal_prob_away": 45.5,
                "xg_home": 1.1,
                "xg_away": 1.8,
                "xg_total": 2.9,
                "btts_yes_pct": 54.0,
                "home_form": ["W", "D", "L", "W", "W"],
                "away_form": ["W", "W", "D", "W", "L"],
                "most_likely_score": {"home": 1, "away": 2, "probability": 12.4},
                "over_under": [{"line": "2.5", "over_pct": 48.2, "under_pct": 51.8}],
                "quick_summary": "PSG are favored away.",
                "exact_scores": [{"home": 0, "away": 0, "probability": 8.1}] * 20,
            }
        )
        self.assertEqual(brief["match"], "Lyon vs PSG")
        self.assertEqual(brief["probabilities_1x2_pct"]["home"], 28.4)
        self.assertEqual(brief["probabilities_1x2_pct"]["away"], 45.5)
        self.assertEqual(brief["most_likely_score"]["home"], 1)
        self.assertEqual(brief["most_likely_score"]["away"], 2)
        self.assertEqual(brief["over_under"][0]["line"], "2.5")
        self.assertEqual(brief["home_form"], ["W", "D", "L", "W", "W"])
        self.assertNotIn("exact_scores", brief)

    def test_empty_or_invalid_input(self) -> None:
        self.assertEqual(build_chat_prediction_brief(None), {})
        self.assertEqual(build_chat_prediction_brief({}), {})


class ChatQuotaTests(unittest.TestCase):
    def test_whop_plan_limits(self) -> None:
        self.assertEqual(get_chat_limit("pro"), 1)
        self.assertEqual(get_chat_limit("premium"), 1)
        self.assertIsNone(get_chat_limit("lifetime"))
        self.assertEqual(get_chat_limit("free"), 0)
        self.assertEqual(get_chat_limit("starter"), 0)

    def test_quota_uses_plan_from_db(self) -> None:
        with (
            patch("app.services.subscription._use_supabase", return_value=True),
            patch(
                "app.services.subscription.get_plan_and_usage",
                return_value=("lifetime", 0, None, None, None, None),
            ),
            patch("app.services.subscription.get_chat_usage", return_value=(0, None)),
        ):
            quota = get_chat_quota("user-1")
        self.assertTrue(quota["chat_allowed"])
        self.assertIsNone(quota["chat_remaining"])
        self.assertIsNone(quota["chat_limit"])

    def test_pro_exhausted_is_blocked(self) -> None:
        today = datetime.now(timezone.utc).date()
        with (
            patch("app.services.subscription._use_supabase", return_value=True),
            patch(
                "app.services.subscription.get_plan_and_usage",
                return_value=("pro", 0, None, None, None, None),
            ),
            patch("app.services.subscription.get_chat_usage", return_value=(1, today)),
        ):
            quota = get_chat_quota("user-2")
        self.assertFalse(quota["chat_allowed"])
        self.assertEqual(quota["chat_remaining"], 0)
        self.assertEqual(quota["chat_limit"], 1)


if __name__ == "__main__":
    unittest.main()
