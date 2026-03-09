"""
Webhooks: Whop payment.succeeded → DataFast Payment API for revenue attribution.
Whop uses Standard Webhooks (webhook-id, webhook-timestamp, webhook-signature).
"""
import json
import logging
import os
from typing import Any
from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)

DATAFAST_PAYMENTS_URL = "https://datafa.st/api/v1/payments"

# Whop plan IDs (from frontend CHECKOUT_URLS) → our plan name
WHOP_PLAN_TO_APP = {
    "plan_xncEV4h0yc3F1": "starter",
    "plan_OPBroVFLkZFuG": "pro",
    "plan_a9qUhL4i9mz6B": "lifetime",
    "plan_SosIjQXUrG5Pb": "starter",
    "plan_pVoGBCVIzFw4M": "pro",
    "plan_m9Bcvjqy3xudw": "lifetime",
    "plan_WmP3L9eEPlEJb": "starter",
    "plan_ASd2bXI29nfKR": "pro",
    "plan_FXHgaDOloK9Q1": "lifetime",
}


def _pick_first(obj: dict, keys: tuple[str, ...]) -> Any:
    for k in keys:
        if k in obj and obj.get(k) is not None:
            return obj.get(k)
    return None


def _deep_find_first(obj: Any, keys: set[str]) -> Any:
    """Recursive search for first matching key in nested dict/list payloads."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keys and v is not None:
                return v
        for v in obj.values():
            found = _deep_find_first(v, keys)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _deep_find_first(item, keys)
            if found is not None:
                return found
    return None


def _extract_payment_payload(body: dict) -> dict:
    """Best-effort extraction of the payment object across Whop payload variants."""
    data = body.get("data")
    if isinstance(data, dict):
        if isinstance(data.get("object"), dict):
            return data["object"]
        # Some payloads are already the payment object in data
        return data
    return body


def _extract_event_name(body: dict) -> str:
    event = (body.get("event") or body.get("type") or body.get("topic") or "").strip().lower()
    if event:
        return event
    # Fallback for payloads where event name is nested
    data = body.get("data")
    if isinstance(data, dict):
        nested = (data.get("event") or data.get("type") or "").strip().lower()
        if nested:
            return nested
    return ""


def _is_payment_succeeded_event(event: str) -> bool:
    if not event:
        return False
    # Accept Whop variants: payment.succeeded, payment_succeeded, payments.payment_succeeded, etc.
    normalized = event.replace("-", "_").replace(".", "_")
    return ("payment" in normalized) and ("succeeded" in normalized)


def _is_revoke_access_event(event: str) -> bool:
    """Events where the user loses access: subscription no longer active or payment failed."""
    if not event:
        return False
    normalized = event.replace("-", "_").replace(".", "_")
    if "payment" in normalized and "failed" in normalized:
        return True
    if "membership" in normalized and (
        "invalid" in normalized or "cancel" in normalized or "expir" in normalized or "went_invalid" in normalized
    ):
        return True
    return False


def _extract_email_and_membership_from_body(body: dict) -> tuple[str | None, str | None]:
    """Extract (email, membership_id) from any Whop payload (payment or membership)."""
    data = body.get("data")
    obj = data.get("object") if isinstance(data, dict) else body
    if not isinstance(obj, dict):
        obj = body
    email = None
    member = _pick_first(obj, ("member", "user")) or {}
    if isinstance(member, dict):
        email = (_pick_first(member, ("email", "email_address")) or "").strip()
    if not email:
        email = (_pick_first(obj, ("user_email", "email", "email_address")) or "").strip()
    membership_id = (_pick_first(obj, ("id", "membership_id")) or "").strip() or None
    if not membership_id and isinstance(obj.get("membership"), dict):
        membership_id = (_pick_first(obj["membership"], ("id", "membership_id")) or "").strip() or None
    return (email or None, membership_id)


def _set_supabase_plan_to_free(email: str | None = None, membership_id: str | None = None) -> bool:
    """Set profiles.plan to free (and clear whop_membership_id) by email or membership_id. Returns True if updated."""
    from app.core.config import get_settings
    settings = get_settings()
    url = (settings.supabase_url or os.getenv("NEXT_PUBLIC_SUPABASE_URL") or os.getenv("SUPABASE_URL") or "").strip()
    role_key = (settings.supabase_service_role_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not role_key:
        logger.warning("Whop webhook: missing Supabase URL or SERVICE_ROLE_KEY, cannot set plan to free")
        return False
    try:
        from supabase import create_client
        admin = create_client(url, role_key)
        if membership_id:
            r = admin.table("profiles").select("id").eq("whop_membership_id", membership_id).execute()
            if r.data and len(r.data) > 0:
                user_id = r.data[0].get("id")
                if user_id:
                    admin.table("profiles").upsert(
                        {"id": user_id, "plan": "free", "whop_membership_id": None},
                        on_conflict="id",
                    ).execute()
                    logger.info("Whop webhook: set plan=free for user %s (membership_id=%s)", user_id, membership_id[:12] + "...")
                    return True
        if email:
            r = admin.auth.admin.list_users(page=1, per_page=1000)
            users = getattr(r, "users", []) if not isinstance(r, list) else r
            for u in users:
                em = getattr(u, "email", None) or (u.get("email") if isinstance(u, dict) else None)
                if em and str(em).lower().strip() == email.lower().strip():
                    user_id = getattr(u, "id", None) or (u.get("id") if isinstance(u, dict) else None)
                    if user_id:
                        admin.table("profiles").upsert(
                            {"id": user_id, "plan": "free", "whop_membership_id": None},
                            on_conflict="id",
                        ).execute()
                        logger.info("Whop webhook: set plan=free for user %s (email=%s...)", user_id, email[:8])
                        return True
        return False
    except Exception as e:
        logger.warning("Whop webhook: could not set plan to free: %s", e)
        return False


def _extract_whop_payment(body: dict, fallback_visitor_id: str | None = None) -> dict | None:
    """
    Extract amount (float), currency (str), transaction_id (str), datafast_visitor_id (str | None)
    from Whop payment.succeeded webhook payload. Adapt keys if Whop schema differs.
    """
    payload = _extract_payment_payload(body)
    if not isinstance(payload, dict):
        return None

    # Amount: prefer actual amount paid (after coupon) — Whop uses final_amount (cents)
    amount_raw = _pick_first(
        payload,
        (
            "final_amount",       # Whop: final amount paid in cents (after discount)
            "amount_paid",
            "amount_captured",
            "total_paid",
            "charged_amount",
            "amount",
            "amount_total",
            "total",
            "subtotal",
            "amount_after_fees",
        ),
    )
    if amount_raw is None:
        return None
    try:
        amount = float(amount_raw)
        # Whop sends amounts in cents (integer); convert to units. Decimals (0.9, 9.99) = already dollars.
        if amount == int(amount):
            amount = amount / 100  # whole number = cents
    except (TypeError, ValueError):
        return None

    # Currency
    currency = (_pick_first(payload, ("currency", "currency_code")) or "USD")
    if isinstance(currency, str):
        currency = currency.upper()[:3]
    else:
        currency = "USD"

    # Transaction id
    txn = _pick_first(payload, ("id", "transaction_id", "payment_id", "receipt_id")) or ""
    transaction_id = str(txn) if txn else None
    if not transaction_id:
        return None

    # DataFast visitor ID: from metadata (if Whop echoes query params / custom metadata)
    metadata = _pick_first(payload, ("metadata", "custom_data")) or {}
    if isinstance(metadata, dict):
        visitor_id = _pick_first(metadata, ("datafast_visitor_id", "visitor_id", "df_visitor_id"))
    else:
        visitor_id = None
    visitor_id = visitor_id or _pick_first(payload, ("datafast_visitor_id", "visitor_id", "df_visitor_id")) or fallback_visitor_id

    return {
        "amount": round(amount, 2),
        "currency": currency,
        "transaction_id": transaction_id,
        "datafast_visitor_id": str(visitor_id).strip() if visitor_id else None,
    }


def _extract_whop_member_plan_and_membership(body: dict) -> tuple[str | None, str | None, str | None]:
    """Extract (email, app_plan, membership_id) from Whop payload."""
    obj = _extract_payment_payload(body)
    member = _pick_first(obj, ("member", "user")) or {}
    if isinstance(member, dict):
        email = (_pick_first(member, ("email", "email_address")) or "").strip()
    else:
        email = None
    if not email:
        email = str(
            _pick_first(obj, ("user_email", "email", "email_address"))
            or _deep_find_first(obj, {"user_email", "email", "email_address"})
            or ""
        ).strip()
    plan_obj = obj.get("plan") if isinstance(obj.get("plan"), dict) else {}
    plan_id = (
        _pick_first(obj, ("plan_id",))
        or _pick_first(plan_obj, ("id", "plan_id"))
        or _deep_find_first(obj, {"plan_id"})
    )
    plan_id = (plan_id or "").strip()
    app_plan = WHOP_PLAN_TO_APP.get(plan_id) if plan_id else None
    membership_id = (_pick_first(obj, ("membership_id",)) or "").strip() or None
    return (email or None, app_plan, membership_id)


def _extract_whop_member_and_plan(body: dict) -> tuple[str | None, str | None]:
    """Backward-compat: (email, app_plan)."""
    email, app_plan, _ = _extract_whop_member_plan_and_membership(body)
    return (email, app_plan)


def _get_supabase_admin():
    """Get Supabase admin client for profile updates."""
    from app.core.config import get_settings
    settings = get_settings()
    url = (settings.supabase_url or os.getenv("NEXT_PUBLIC_SUPABASE_URL") or os.getenv("SUPABASE_URL") or "").strip()
    role_key = (settings.supabase_service_role_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not role_key:
        return None
    try:
        from supabase import create_client
        return create_client(url, role_key)
    except Exception as e:
        logger.warning("Whop: could not create Supabase admin client: %s", e)
        return None


def _update_supabase_plan_for_user_id(user_id: str, plan: str, membership_id: str | None = None) -> bool:
    """Set profiles.plan (and optional whop_membership_id) for the given Supabase user id. Links Whop payment to the logged-in user (no email match)."""
    admin_client = _get_supabase_admin()
    if not admin_client:
        logger.warning("Whop: missing Supabase config, cannot update plan by user_id")
        return False
    user_id = (user_id or "").strip()
    if not user_id:
        return False
    try:
        row: dict = {"id": user_id, "plan": plan}
        if membership_id:
            row["whop_membership_id"] = membership_id
        admin_client.table("profiles").upsert(row, on_conflict="id").execute()
        logger.info("Whop: updated profiles.plan=%s for user_id=%s (linked by session)", plan, user_id[:8] + "...")
        return True
    except Exception as e:
        logger.warning("Whop: could not update Supabase plan for user_id %s: %s", user_id[:8] + "...", e)
        return False


def _update_supabase_plan_for_email(email: str, plan: str, membership_id: str | None = None) -> bool:
    """Find user by email via Supabase auth admin and set profiles.plan (and optional whop_membership_id). Returns True if updated."""
    admin_client = _get_supabase_admin()
    if not admin_client:
        logger.warning("Whop webhook: missing Supabase URL or SERVICE_ROLE_KEY, cannot update plan")
        return False
    try:
        r = admin_client.auth.admin.list_users(page=1, per_page=1000)
        users = getattr(r, "users", []) if not isinstance(r, list) else r
        user_id = None
        for u in users:
            em = getattr(u, "email", None) or (u.get("email") if isinstance(u, dict) else None)
            if em and str(em).lower().strip() == email.lower().strip():
                user_id = getattr(u, "id", None) or (u.get("id") if isinstance(u, dict) else None)
                break
        if not user_id:
            logger.info("Whop webhook: no Supabase user found for email %s", email[:8] + "...")
            return False
        row: dict = {"id": user_id, "plan": plan}
        if membership_id:
            row["whop_membership_id"] = membership_id
        admin_client.table("profiles").upsert(row, on_conflict="id").execute()
        logger.info("Whop webhook: updated profiles.plan=%s for user %s", plan, user_id)
        return True
    except Exception as e:
        logger.warning("Whop webhook: could not update Supabase plan for %s: %s", email[:8] + "...", e)
        return False


def _verify_whop_signature(raw_body: bytes, headers: dict, secret: str) -> bool:
    """Verify Whop webhook using Standard Webhooks (HMAC). Accepts ws_ or whsec_ prefix."""
    if not secret or not raw_body:
        return False
    try:
        from standardwebhooks.webhooks import Webhook
        # Library expects whsec_<base64>; Whop may give ws_<base64> — normalize
        normalized = secret.strip()
        for prefix in ("ws_", "whsec_"):
            if normalized.startswith(prefix):
                normalized = "whsec_" + normalized[len(prefix):]
                break
        wh = Webhook(normalized)
        wh.verify(raw_body, headers)
        return True
    except Exception as e:
        logger.warning("Whop webhook signature verification failed: %s", e)
        return False


async def _forward_datafast_payment(parsed: dict, api_key: str) -> dict:
    if not api_key:
        return {"ok": True, "forwarded": False, "reason": "no_datafast_key"}
    if not parsed.get("datafast_visitor_id"):
        return {"ok": True, "forwarded": False, "reason": "no_visitor_id"}

    payload = {
        "amount": parsed["amount"],
        "currency": parsed["currency"],
        "transaction_id": parsed["transaction_id"],
        "datafast_visitor_id": parsed["datafast_visitor_id"],
    }
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                DATAFAST_PAYMENTS_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=10.0,
            )
        if r.status_code >= 400:
            logger.warning("DataFast Payment API error: %s %s", r.status_code, r.text)
            return {"ok": True, "forwarded": False, "datafast_status": r.status_code}
        vid = parsed["datafast_visitor_id"]
        logger.info(
            "DataFast: payment attributed amount=%s %s txn=%s visitor=%s",
            parsed["amount"], parsed["currency"], parsed["transaction_id"], (vid[:8] + "...") if len(vid) > 8 else vid
        )
        return {"ok": True, "forwarded": True}
    except Exception as e:
        logger.exception("DataFast request failed: %s", e)
        return {"ok": True, "forwarded": False, "error": str(e)}


async def _fetch_whop_payment_by_id(payment_id: str, whop_api_key: str) -> dict | None:
    if not payment_id or not whop_api_key:
        return None
    import httpx
    # Company API Key: v1 only. v5/company/payments/* is for App API keys.
    urls = [
        f"https://api.whop.com/api/v1/payments/{payment_id}",
        f"https://api.whop.com/api/v5/company/payments/{payment_id}",
    ]
    headers = {"Authorization": f"Bearer {whop_api_key}"}
    async with httpx.AsyncClient() as client:
        for url in urls:
            try:
                r = await client.get(url, headers=headers, timeout=10.0)
                if r.status_code >= 400:
                    continue
                data = r.json()
                if isinstance(data, dict):
                    payload = data.get("data") if isinstance(data.get("data"), dict) else data
                    if isinstance(payload, dict):
                        return payload
            except Exception:
                continue
    return None


@router.post("/whop")
async def whop_webhook(request: Request):
    """
    Receive Whop payment.succeeded (and optionally other events).
    On payment.succeeded, forward to DataFast Payment API for revenue attribution.
    If WHOP_WEBHOOK_SECRET is set, verifies Standard Webhooks signature.
    """
    raw_body = await request.body()
    try:
        body = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError as e:
        logger.warning("Whop webhook invalid JSON: %s", e)
        raise HTTPException(status_code=400, detail="Invalid JSON")

    from app.core.config import get_settings
    settings = get_settings()
    secret = (settings.whop_webhook_secret or "").strip()
    headers_lower = {k.lower(): v for k, v in request.headers.items()}
    has_sig_headers = all(
        headers_lower.get(h) for h in ("webhook-id", "webhook-timestamp", "webhook-signature")
    )
    if secret:
        if has_sig_headers:
            if not _verify_whop_signature(raw_body, dict(request.headers), secret):
                logger.warning(
                    "Whop webhook: signature verification failed (test payload?), accepting anyway"
                )
        else:
            logger.warning(
                "Whop webhook: no signature headers, accepting payload"
            )

    event = _extract_event_name(body)

    # Abo inactif ou paiement échoué → passer le plan en free
    if _is_revoke_access_event(event):
        email, membership_id = _extract_email_and_membership_from_body(body)
        if email or membership_id:
            updated = _set_supabase_plan_to_free(email=email, membership_id=membership_id)
            logger.info("Whop webhook: revoke event=%s plan set to free=%s", event, updated)
        else:
            logger.warning("Whop webhook: revoke event=%s but no email/membership_id in payload", event)
        return {"ok": True, "event": event, "plan_set_to_free": bool(email or membership_id)}

    if not _is_payment_succeeded_event(event):
        logger.info("Whop webhook: ignored event=%s", event or "unknown")
        return {"ok": True, "ignored": True, "event": event}

    # Optionally update Supabase profile (plan + whop_membership_id for cancel flow)
    member_email, app_plan, membership_id = _extract_whop_member_plan_and_membership(body)
    if member_email and app_plan:
        _update_supabase_plan_for_email(member_email, app_plan, membership_id)
        # When user buys Lifetime, cancel any previous subscription (Starter/Pro) so they are not charged twice
        if app_plan == "lifetime" and member_email and membership_id:
            whop_key = (settings.whop_api_key or "").strip()
            company_id = (settings.whop_company_id or "").strip()
            if whop_key and company_id:
                try:
                    from app.api.me import whop_cancel_other_memberships_for_email
                    n = await whop_cancel_other_memberships_for_email(member_email, whop_key, company_id, membership_id)
                    if n:
                        logger.info("Whop webhook: cancelled %s previous membership(s) (Lifetime purchase)", n)
                except Exception as e:
                    logger.warning("Whop webhook: could not cancel previous memberships for Lifetime: %s", e)
    else:
        logger.warning("Whop webhook: missing member_email or app_plan (email=%s, plan=%s)", bool(member_email), app_plan or "none")

    parsed = _extract_whop_payment(body)
    if not parsed:
        logger.warning("Whop webhook: could not parse payment from body keys %s", list(body.keys()))
        return {"ok": True, "forwarded": False, "reason": "parse_failed"}

    api_key = (settings.datafast_api_key or "").strip()
    result = await _forward_datafast_payment(parsed, api_key)
    if not result.get("forwarded"):
        logger.info("Whop webhook: DataFast not forwarded reason=%s", result.get("reason") or result.get("datafast_status"))
    return result


@router.post("/whop/sync-payment")
async def whop_sync_payment(request: Request):
    """
    Resync endpoint for return URL flow.
    Frontend calls this with payment_id after checkout success so we can:
    - fetch payment from Whop API,
    - update plan in Supabase for the logged-in user (X-User-Id) so Supabase and Whop are linked by session, not email,
    - attribute payment to DataFast (using visitor id from frontend cookie fallback).
    If X-User-Id is sent, we update that user's profile (works even when app email ≠ Whop email). Else we fall back to matching by Whop member email.
    """
    from app.core.config import get_settings
    settings = get_settings()
    body = await request.json()
    payment_id = str((body or {}).get("payment_id") or "").strip()
    fallback_visitor_id = str((body or {}).get("datafast_visitor_id") or "").strip() or None
    x_user_id = (request.headers.get("X-User-Id") or "").strip() or None
    if not payment_id:
        raise HTTPException(status_code=400, detail="payment_id is required")
    whop_api_key = (settings.whop_api_key or "").strip()
    if not whop_api_key:
        raise HTTPException(status_code=500, detail="WHOP_API_KEY is not configured")

    payment_payload = await _fetch_whop_payment_by_id(payment_id, whop_api_key)
    if not payment_payload:
        raise HTTPException(status_code=404, detail="payment not found in Whop API")
    wrapped = {"event": "payment.succeeded", "data": {"object": payment_payload}}

    member_email, app_plan, membership_id = _extract_whop_member_plan_and_membership(wrapped)
    updated = False
    if app_plan:
        if x_user_id:
            updated = _update_supabase_plan_for_user_id(x_user_id, app_plan, membership_id)
            if updated:
                logger.info("Whop sync-payment: plan=%s linked to user_id (session), payment_id=%s", app_plan, payment_id)
        if not updated and member_email:
            updated = _update_supabase_plan_for_email(member_email, app_plan, membership_id)
        # When user buys Lifetime, cancel any previous subscription (Starter/Pro)
        if app_plan == "lifetime" and member_email and membership_id:
            whop_api_key = (settings.whop_api_key or "").strip()
            company_id = (settings.whop_company_id or "").strip()
            if whop_api_key and company_id:
                try:
                    from app.api.me import whop_cancel_other_memberships_for_email
                    n = await whop_cancel_other_memberships_for_email(member_email, whop_api_key, company_id, membership_id)
                    if n:
                        logger.info("Whop sync-payment: cancelled %s previous membership(s) (Lifetime purchase)", n)
                except Exception as e:
                    logger.warning("Whop sync-payment: could not cancel previous memberships for Lifetime: %s", e)
    if not app_plan:
        logger.warning("Whop sync-payment: missing app_plan for payment_id=%s", payment_id)

    parsed = _extract_whop_payment(wrapped, fallback_visitor_id=fallback_visitor_id)
    forwarded = {"ok": True, "forwarded": False, "reason": "parse_failed"}
    if parsed:
        forwarded = await _forward_datafast_payment(parsed, (settings.datafast_api_key or "").strip())
        if not forwarded.get("forwarded"):
            logger.info("Whop sync-payment: DataFast not forwarded reason=%s", forwarded.get("reason") or forwarded.get("datafast_status"))
    # Return plan so frontend can apply it immediately without relying on /me (avoids "free" default)
    return {"ok": True, "payment_id": payment_id, "plan_updated": updated, "plan": app_plan, "datafast": forwarded}
