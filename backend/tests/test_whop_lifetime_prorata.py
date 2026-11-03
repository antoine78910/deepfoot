"""Unused-month refund math when upgrading to Lifetime."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from app.services.whop_lifetime_prorata import (
    payment_total_units,
    refundable_remaining,
    unused_month_refund_amount,
)


class UnusedMonthRefundTests(unittest.TestCase):
    def test_half_month_left_refunds_half(self) -> None:
        start = datetime(2026, 11, 1, tzinfo=timezone.utc)
        end = datetime(2026, 12, 1, tzinfo=timezone.utc)
        now = datetime(2026, 11, 16, tzinfo=timezone.utc)
        self.assertEqual(unused_month_refund_amount(19.0, start, end, now), 9.5)

    def test_period_already_ended_is_zero(self) -> None:
        start = datetime(2026, 10, 1, tzinfo=timezone.utc)
        end = datetime(2026, 11, 1, tzinfo=timezone.utc)
        now = datetime(2026, 11, 3, tzinfo=timezone.utc)
        self.assertEqual(unused_month_refund_amount(9.0, start, end, now), 0.0)

    def test_missing_start_assumes_thirty_days(self) -> None:
        end = datetime(2026, 12, 1, tzinfo=timezone.utc)
        now = datetime(2026, 11, 16, tzinfo=timezone.utc)
        amount = unused_month_refund_amount(9.0, None, end, now)
        self.assertGreater(amount, 4.0)
        self.assertLess(amount, 5.0)

    def test_never_refunds_more_than_paid(self) -> None:
        start = datetime(2026, 11, 1, tzinfo=timezone.utc)
        end = datetime(2026, 12, 1, tzinfo=timezone.utc)
        now = datetime(2026, 11, 1, 1, tzinfo=timezone.utc)
        self.assertLessEqual(unused_month_refund_amount(9.0, start, end, now), 9.0)

    def test_payment_total_prefers_currency_units(self) -> None:
        self.assertEqual(payment_total_units({"total": 19.0}), 19.0)
        self.assertEqual(payment_total_units({"final_amount": 900}), 9.0)

    def test_refundable_remaining_subtracts_prior_refund(self) -> None:
        self.assertEqual(refundable_remaining({"total": 19.0, "refunded_amount": 4.0}), 15.0)
        self.assertEqual(refundable_remaining({"total": 9.0, "refunded_amount": 9.0}), 0.0)


if __name__ == "__main__":
    unittest.main()
