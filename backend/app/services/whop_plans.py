"""Whop plan IDs, membership access, and best-membership selection.

Lifetime is a one-time purchase. Whop keeps that membership as status
``completed`` (not ``active``). Listing only active/trialing therefore
misses Lifetime and can keep the user on an older Starter/Pro.
"""
from __future__ import annotations

from typing import Any

# Checkout URLs in frontend/lib/whopCheckout.ts. Single product, 3 plans × 3 currencies.
WHOP_PLAN_TO_APP = {
    # GBP (9 / 19 / 99)
    "plan_PEt1oIDXTTimX": "starter",
    "plan_4txPPDCv7OjiR": "pro",
    "plan_h5Om2F0ga6UhT": "lifetime",
    # EUR (9 / 19 / 99)
    "plan_3pzB8Vw1GIjSb": "starter",
    "plan_35zzQVid4lE9Z": "pro",
    "plan_ErLwV2KgiMiC1": "lifetime",
    # USD (9 / 19.99 / 99.99)
    "plan_XNiSpw7OKJoIi": "starter",
    "plan_LwCFHHdytBkM6": "pro",
    "plan_MlCRcQibssX37": "lifetime",
}

# Statuses that still grant product access. v1 rejects unknown buckets like one_time.
WHOP_ACCESS_STATUSES = ["active", "trialing", "completed"]
WHOP_RECURRING_STATUSES = ["active", "trialing"]


def plan_tier(app_plan: str | None) -> int:
    return {"lifetime": 3, "pro": 2, "starter": 1}.get((app_plan or "").strip().lower(), 0)


def membership_plan_id(obj: dict | None) -> str | None:
    """plan_id is often nested as plan.id on GET /memberships/{id}."""
    if not isinstance(obj, dict):
        return None
    plan_obj = obj.get("plan") if isinstance(obj.get("plan"), dict) else {}
    pid = obj.get("plan_id") or plan_obj.get("id") or plan_obj.get("plan_id")
    pid = str(pid or "").strip()
    return pid or None


def app_plan_from_whop(obj: dict | None) -> str | None:
    pid = membership_plan_id(obj)
    if not pid:
        return None
    return WHOP_PLAN_TO_APP.get(pid)


def membership_status(obj: dict | None) -> str:
    if not isinstance(obj, dict):
        return ""
    return str(obj.get("status") or "").strip().lower()


def membership_grants_access(obj: dict | None) -> bool:
    status = membership_status(obj)
    if status == "completed":
        return True
    if status in ("active", "trialing"):
        return True
    return False


def membership_is_canceled(obj: dict | None) -> bool:
    """True when the recurring membership will not renew. Completed lifetime is never canceled."""
    if not isinstance(obj, dict):
        return False
    if membership_status(obj) == "completed":
        return False
    status = membership_status(obj)
    if status in ("canceled", "cancelled", "expired"):
        return True
    raw = obj.get("cancel_at_period_end")
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in ("true", "1", "yes")
    return bool(raw) if raw is not None else False


def _created_ts(obj: dict) -> float:
    raw = obj.get("created_at")
    if raw is None:
        return 0.0
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip()
    try:
        return float(s)
    except ValueError:
        pass
    # ISO timestamps: later string still sorts if we use a crude parse
    try:
        from datetime import datetime, timezone
        iso = s.replace("Z", "+00:00")
        return datetime.fromisoformat(iso).timestamp()
    except Exception:
        return 0.0


def pick_best_membership(memberships: list[Any]) -> dict | None:
    """
    Choose the membership that should drive the app plan.
    Lifetime (completed) beats an older Pro still marked active/cancel_at_period_end.
    """
    ranked: list[tuple[int, int, float, dict]] = []
    for raw in memberships or []:
        if not isinstance(raw, dict):
            continue
        if not membership_grants_access(raw):
            continue
        app_plan = app_plan_from_whop(raw) or "starter"
        canceled = 1 if membership_is_canceled(raw) else 0
        ranked.append((-plan_tier(app_plan), canceled, -_created_ts(raw), raw))
    if not ranked:
        return None
    ranked.sort()
    return ranked[0][3]
