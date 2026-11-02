"""OpenAI cost estimates for admin profitability."""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from app.services.prediction_costs import (
    cost_from_result,
    economics_payload,
    estimated_cost_eur,
    revenue_for_plan,
    usage_from_openai,
)


class PredictionCostTests(unittest.TestCase):
    def test_estimated_unit_cost_is_positive_and_small(self) -> None:
        unit = estimated_cost_eur()
        self.assertGreater(unit, 0)
        self.assertLess(unit, 0.02)

    def test_usage_from_openai(self) -> None:
        payload = usage_from_openai(
            SimpleNamespace(usage=SimpleNamespace(prompt_tokens=2500, completion_tokens=1100, total_tokens=3600))
        )
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["model"], "gpt-4o-mini")
        self.assertEqual(payload["prompt_tokens"], 2500)
        self.assertAlmostEqual(payload["cost_eur"], estimated_cost_eur(), places=6)

    def test_cost_from_stored_usage(self) -> None:
        cost, estimated = cost_from_result({"llm_usage": {"cost_eur": 0.0025}})
        self.assertEqual(cost, 0.0025)
        self.assertFalse(estimated)

    def test_economics_profit_when_paid(self) -> None:
        eco = economics_payload(
            predictions_all_time=100,
            predictions_window=40,
            window_days=30,
            plan_counts={"starter": 1, "pro": 1, "lifetime": 1, "free": 10},
        )
        self.assertEqual(eco["mrr_eur"], 28.0)
        self.assertEqual(eco["lifetime_revenue_eur"], 99.0)
        self.assertTrue(eco["profitable_window"])
        self.assertGreater(eco["profit_window_eur"], 0)

    def test_plan_revenue(self) -> None:
        self.assertEqual(revenue_for_plan("starter"), 9)
        self.assertEqual(revenue_for_plan("pro"), 19)
        self.assertEqual(revenue_for_plan("lifetime"), 99)
        self.assertEqual(revenue_for_plan("free"), 0)


if __name__ == "__main__":
    unittest.main()
