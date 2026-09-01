"""Missing Supabase tables must not crash analysis."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services.subscription import can_analyze, consume_analysis, get_plan_and_usage


class _MissingProfilesQuery:
    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def upsert(self, *_a, **_k):
        return self

    def insert(self, *_a, **_k):
        return self

    def execute(self):
        raise Exception(
            "{'message': \"Could not find the table 'public.profiles' in the schema cache\", 'code': 'PGRST205'}"
        )


class _MissingProfilesClient:
    def table(self, name: str):
        return _MissingProfilesQuery()


class SubscriptionMissingTableTests(unittest.TestCase):
    def test_get_plan_and_usage_when_profiles_missing(self) -> None:
        with (
            patch("app.services.subscription._use_supabase", return_value=True),
            patch("app.services.subscription.get_supabase_admin", return_value=_MissingProfilesClient()),
            patch("app.services.subscription.get_supabase", return_value=_MissingProfilesClient()),
        ):
            plan, used, last, *_ = get_plan_and_usage("user-123")
        self.assertEqual(plan, "free")
        self.assertEqual(used, 0)
        self.assertIsNone(last)

    def test_can_analyze_when_profiles_missing(self) -> None:
        with (
            patch("app.services.subscription._use_supabase", return_value=True),
            patch("app.services.subscription.get_supabase_admin", return_value=_MissingProfilesClient()),
            patch("app.services.subscription.get_supabase", return_value=_MissingProfilesClient()),
        ):
            allowed, _msg, _full, _reason = can_analyze("user-123")
        self.assertTrue(allowed)

    def test_consume_analysis_when_profiles_missing(self) -> None:
        with (
            patch("app.services.subscription._use_supabase", return_value=True),
            patch("app.services.subscription.get_supabase_admin", return_value=_MissingProfilesClient()),
            patch("app.services.subscription.get_supabase", return_value=_MissingProfilesClient()),
        ):
            consume_analysis("user-123", home_team="PSG", away_team="OM")
