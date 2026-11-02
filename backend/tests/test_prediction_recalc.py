"""Stored history 1X2 must be rebuilt from match-specific form, not the cloned demo."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services.prediction_recalc import apply_recomputed_probs, recompute_match_model


class PredictionRecalcTests(unittest.TestCase):
    def test_two_matches_get_different_probabilities(self) -> None:
        def fake_results(name: str, last_n: int = 10):
            if "Liverpool" in name:
                return ([2, 3, 1, 2, 0], [0, 1, 1, 0, 1], ["W", "W", "D", "W", "L"])
            if "Arsenal" in name:
                return ([1, 1, 0, 2, 1], [1, 2, 1, 1, 2], ["D", "L", "L", "W", "L"])
            if "HamKam" in name:
                return ([0, 1, 0, 1, 0], [2, 3, 1, 2, 2], ["L", "L", "L", "L", "L"])
            return ([2, 1, 2, 3, 1], [1, 1, 0, 1, 1], ["W", "D", "W", "W", "D"])

        with patch("app.services.thesportsdb.team_last_results", side_effect=fake_results):
            liv = recompute_match_model("Liverpool", "Arsenal")
            kfum = recompute_match_model("KFUM Oslo", "HamKam")
        self.assertIsNotNone(liv)
        self.assertIsNotNone(kfum)
        assert liv is not None and kfum is not None
        self.assertNotEqual(
            (liv["prob_home"], liv["prob_draw"], liv["prob_away"]),
            (kfum["prob_home"], kfum["prob_draw"], kfum["prob_away"]),
        )
        self.assertNotEqual(liv["internal_prob_home"], 46.7)
        self.assertEqual(liv["prob_home"], liv["internal_prob_home"])

    def test_apply_keeps_ai_copy_and_clears_placeholder(self) -> None:
        stored = {
            "prob_home": 46.7,
            "prob_draw": 33.1,
            "prob_away": 20.2,
            "quick_summary": "Original AI text",
            "analysis_recap": {
                "placeholder_form": True,
                "data_source": "API-Football",
                "pipeline_steps": [
                    {"detail": "Home: goals_for=[1, 2, 1, 0, 2]. Away: goals_for=[0, 1, 1, 2, 0]."}
                ],
            },
        }
        computed = {
            "prob_home": 61.2,
            "prob_draw": 22.0,
            "prob_away": 16.8,
            "internal_prob_home": 61.2,
            "internal_prob_draw": 22.0,
            "internal_prob_away": 16.8,
            "form_source": "TheSportsDB",
            "recalculated_at": "2026-11-02T00:00:00+00:00",
        }
        with patch("app.services.thesportsdb.team_last_results"):
            merged = apply_recomputed_probs(stored, computed)
        self.assertEqual(merged["prob_home"], 61.2)
        self.assertEqual(merged["quick_summary"], "Original AI text")
        self.assertFalse(merged["analysis_recap"]["placeholder_form"])
        self.assertTrue(merged["recalculated_from_form"])
        self.assertNotIn("goals_for=[1, 2, 1, 0, 2]", merged["analysis_recap"]["pipeline_steps"][0]["detail"])


if __name__ == "__main__":
    unittest.main()
