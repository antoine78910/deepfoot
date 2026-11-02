"""Lifetime Whop memberships are status=completed, not active."""
from __future__ import annotations

import unittest

from app.services.whop_plans import (
    app_plan_from_whop,
    membership_plan_id,
    pick_best_membership,
)
from app.api.webhooks import _extract_whop_member_plan_and_membership


class WhopLifetimeMembershipTests(unittest.TestCase):
    def test_plan_id_nested_on_membership_get(self) -> None:
        obj = {
            "id": "mem_lifetime",
            "status": "completed",
            "plan_id": None,
            "plan": {"id": "plan_ErLwV2KgiMiC1"},
        }
        self.assertEqual(membership_plan_id(obj), "plan_ErLwV2KgiMiC1")
        self.assertEqual(app_plan_from_whop(obj), "lifetime")

    def test_pick_completed_lifetime_over_cancelling_pro(self) -> None:
        pro = {
            "id": "mem_old_pro",
            "status": "active",
            "cancel_at_period_end": True,
            "created_at": "2026-03-01T00:00:00Z",
            "plan": {"id": "plan_35zzQVid4lE9Z"},
        }
        lifetime = {
            "id": "mem_new_life",
            "status": "completed",
            "cancel_at_period_end": False,
            "created_at": "2026-11-02T09:22:05Z",
            "plan": {"id": "plan_ErLwV2KgiMiC1"},
        }
        best = pick_best_membership([pro, lifetime])
        self.assertIsNotNone(best)
        self.assertEqual(best["id"], "mem_new_life")
        self.assertEqual(app_plan_from_whop(best), "lifetime")

    def test_active_only_list_misses_lifetime(self) -> None:
        """Documents the production bug: filtering active/trialing hides Lifetime."""
        lifetime = {
            "id": "mem_new_life",
            "status": "completed",
            "plan": {"id": "plan_ErLwV2KgiMiC1"},
        }
        self.assertIsNone(pick_best_membership([]))
        self.assertEqual(pick_best_membership([lifetime])["id"], "mem_new_life")

    def test_webhook_extracts_nested_plan_and_membership(self) -> None:
        body = {
            "event": "payment.succeeded",
            "data": {
                "object": {
                    "id": "pay_x",
                    "user": {"email": "buyer@example.com"},
                    "plan": {"id": "plan_ErLwV2KgiMiC1"},
                    "membership": {"id": "mem_new_life"},
                }
            },
        }
        email, app_plan, mid = _extract_whop_member_plan_and_membership(body)
        self.assertEqual(email, "buyer@example.com")
        self.assertEqual(app_plan, "lifetime")
        self.assertEqual(mid, "mem_new_life")


if __name__ == "__main__":
    unittest.main()
