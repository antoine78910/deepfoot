"""Unused-month refund when a subscriber buys Lifetime while Starter/Pro is still running."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.services.whop_plans import app_plan_from_whop

logger = logging.getLogger(__name__)

MIN_REFUND = 0.5
DEFAULT_MONTH_DAYS = 30


def parse_whop_datetime(raw: Any) -> Optional[datetime]:
    if raw is None or raw == "":
        return None
    if isinstance(raw, datetime):
        dt = raw
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    if isinstance(raw, (int, float)):
        ts = float(raw)
        if ts > 1e12:
            ts = ts / 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    s = str(raw).strip()
    if not s:
        return None
    try:
        if s.isdigit():
            return parse_whop_datetime(int(s))
        iso = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def payment_total_units(payment: dict | None) -> Optional[float]:
    """Payment total in currency units (euros/dollars), never cents."""
    if not isinstance(payment, dict):
        return None
    for key in ("total", "subtotal", "amount_after_fees", "usd_total"):
        raw = payment.get(key)
        if raw is None or raw == "":
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if value > 0:
            return round(value, 2)
    raw = payment.get("final_amount") or payment.get("amount")
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    # Legacy webhook payloads send whole cents (900 = 9.00).
    if value == int(value) and value >= 100:
        value = value / 100.0
    return round(value, 2)


def refundable_remaining(payment: dict | None) -> Optional[float]:
    total = payment_total_units(payment)
    if total is None:
        return None
    already = 0.0
    raw = (payment or {}).get("refunded_amount")
    if raw not in (None, ""):
        try:
            already = max(0.0, float(raw))
        except (TypeError, ValueError):
            already = 0.0
    return round(max(0.0, total - already), 2)


def unused_month_refund_amount(
    paid_amount: float,
    period_start: datetime | None,
    period_end: datetime | None,
    now: datetime | None = None,
) -> float:
    """Unused fraction of the current billing period, capped to that period only."""
    if paid_amount <= 0:
        return 0.0
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    if period_end is None:
        return 0.0
    if period_end.tzinfo is None:
        period_end = period_end.replace(tzinfo=timezone.utc)
    if now >= period_end:
        return 0.0
    if period_start is None:
        period_start = period_end - timedelta(days=DEFAULT_MONTH_DAYS)
    if period_start.tzinfo is None:
        period_start = period_start.replace(tzinfo=timezone.utc)
    if period_start >= period_end:
        return 0.0
    total_seconds = (period_end - period_start).total_seconds()
    unused_seconds = (period_end - now).total_seconds()
    if total_seconds <= 0 or unused_seconds <= 0:
        return 0.0
    ratio = min(1.0, unused_seconds / total_seconds)
    return round(paid_amount * ratio, 2)


def _membership_id_of_payment(payment: dict) -> str:
    mem = payment.get("membership")
    if isinstance(mem, dict):
        return str(mem.get("id") or mem.get("membership_id") or "").strip()
    return str(payment.get("membership_id") or "").strip()


def _payment_is_refundable(payment: dict) -> bool:
    if payment.get("refundable") is False:
        return False
    status = str(payment.get("status") or "").strip().lower()
    sub = str(payment.get("substatus") or "").strip().lower()
    if status in ("void", "uncollectible"):
        return False
    if sub in ("refunded", "auto_refunded"):
        return False
    return True


def period_window(membership: dict | None, payment: dict | None) -> tuple[datetime | None, datetime | None]:
    membership = membership if isinstance(membership, dict) else {}
    payment = payment if isinstance(payment, dict) else {}
    end = parse_whop_datetime(
        membership.get("renewal_period_end")
        or membership.get("renewal_period_end_at")
        or membership.get("current_period_end")
    )
    start = parse_whop_datetime(
        membership.get("renewal_period_start")
        or membership.get("renewal_period_start_at")
        or membership.get("current_period_start")
        or payment.get("paid_at")
        or payment.get("created_at")
    )
    if start is None and end is not None:
        start = end - timedelta(days=DEFAULT_MONTH_DAYS)
    return start, end


async def _get_membership(membership_id: str, whop_key: str) -> dict:
    import httpx

    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://api.whop.com/api/v1/memberships/{membership_id}",
            headers={"Authorization": f"Bearer {whop_key}"},
            timeout=15.0,
        )
    if r.status_code >= 400:
        logger.warning("Whop GET membership %s: %s %s", membership_id[:12], r.status_code, r.text[:200])
        return {}
    data = r.json() if r.content else {}
    if isinstance(data.get("data"), dict):
        return data["data"]
    return data if isinstance(data, dict) else {}


async def _list_membership_payments(membership_id: str, whop_key: str, company_id: str) -> list[dict]:
    import httpx

    params: dict[str, Any] = {"first": 20, "query": membership_id}
    if company_id:
        params["account_id"] = company_id
        params["company_id"] = company_id
    params["membership_id"] = membership_id
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://api.whop.com/api/v1/payments",
            params=params,
            headers={"Authorization": f"Bearer {whop_key}"},
            timeout=20.0,
        )
    if r.status_code >= 400:
        logger.warning("Whop list payments for %s: %s %s", membership_id[:12], r.status_code, r.text[:200])
        return []
    data = r.json() if r.content else {}
    rows = data.get("data") if isinstance(data.get("data"), list) else []
    matched = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        mid = _membership_id_of_payment(row)
        if mid and mid != membership_id:
            continue
        matched.append(row)
    return matched or [row for row in rows if isinstance(row, dict)]


def _latest_paid_payment(payments: list[dict]) -> Optional[dict]:
    ranked: list[tuple[float, dict]] = []
    for payment in payments:
        if not _payment_is_refundable(payment):
            continue
        if refundable_remaining(payment) in (None, 0):
            continue
        ts = parse_whop_datetime(payment.get("paid_at") or payment.get("created_at"))
        ranked.append((ts.timestamp() if ts else 0.0, payment))
    if not ranked:
        return None
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked[0][1]


async def _refund_payment(payment_id: str, amount: float, whop_key: str, membership_id: str) -> bool:
    import httpx

    url = f"https://api.whop.com/api/v1/payments/{payment_id}/refund"
    headers = {
        "Authorization": f"Bearer {whop_key}",
        "Idempotency-Key": f"lifetime-prorata-{membership_id}",
        "Content-Type": "application/json",
    }
    body = {
        "partial_amount": amount,
        "metadata": {"reason": "lifetime_upgrade_unused_month"},
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=headers, json=body, timeout=20.0)
        if r.status_code == 400 and "metadata" in (r.text or "").lower():
            r = await client.post(url, headers=headers, json={"partial_amount": amount}, timeout=20.0)
    if r.status_code >= 400:
        logger.warning("Whop refund %s amount=%s: %s %s", payment_id, amount, r.status_code, r.text[:300])
        return False
    logger.info("Whop refund unused month: payment=%s amount=%s membership=%s", payment_id, amount, membership_id[:12])
    return True


async def refund_unused_month_for_membership(
    membership_id: str,
    membership: dict | None,
    whop_key: str,
    company_id: str,
) -> dict[str, Any]:
    """Partial-refund unused days of the current Starter/Pro period. Never refunds Lifetime."""
    mid = (membership_id or "").strip()
    if not mid or not whop_key:
        return {"refunded": False, "amount": 0.0, "reason": "missing_id"}
    if app_plan_from_whop(membership) == "lifetime":
        return {"refunded": False, "amount": 0.0, "reason": "lifetime"}
    details = membership if isinstance(membership, dict) and membership.get("renewal_period_end") else None
    details = details or await _get_membership(mid, whop_key)
    if app_plan_from_whop(details) == "lifetime":
        return {"refunded": False, "amount": 0.0, "reason": "lifetime"}
    payments = await _list_membership_payments(mid, whop_key, company_id)
    payment = _latest_paid_payment(payments)
    if not payment:
        return {"refunded": False, "amount": 0.0, "reason": "no_refundable_payment"}
    remaining = refundable_remaining(payment)
    if remaining is None or remaining < MIN_REFUND:
        return {"refunded": False, "amount": 0.0, "reason": "nothing_refundable"}
    start, end = period_window(details, payment)
    amount = unused_month_refund_amount(remaining, start, end)
    amount = min(amount, remaining)
    if amount < MIN_REFUND:
        return {"refunded": False, "amount": 0.0, "reason": "unused_too_small", "computed": amount}
    pay_id = str(payment.get("id") or "").strip()
    if not pay_id:
        return {"refunded": False, "amount": 0.0, "reason": "missing_payment_id"}
    ok = await _refund_payment(pay_id, amount, whop_key, mid)
    return {
        "refunded": ok,
        "amount": amount if ok else 0.0,
        "payment_id": pay_id,
        "reason": "ok" if ok else "whop_refund_failed",
    }
