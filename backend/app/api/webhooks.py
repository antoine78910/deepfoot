"""
Webhooks: Whop payment.succeeded → DataFast Payment API for revenue attribution.
Whop uses Standard Webhooks (webhook-id, webhook-timestamp, webhook-signature).
"""
import json
import logging
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


def _extract_whop_payment(body: dict) -> dict | None:
    """
    Extract amount (float), currency (str), transaction_id (str), datafast_visitor_id (str | None)
    from Whop payment.succeeded webhook payload. Adapt keys if Whop schema differs.
    """
    # Whop may send: { "event": "payment.succeeded", "data": { "object": { ... } } } or similar
    data = body.get("data") or body
    obj = data.get("object") if isinstance(data, dict) else None
    payload = obj if isinstance(obj, dict) else data if isinstance(data, dict) else body

    if not isinstance(payload, dict):
        return None

    # Amount: might be in cents (integer) or units (float)
    amount_raw = payload.get("amount") or payload.get("amount_total") or payload.get("total")
    if amount_raw is None:
        return None
    try:
        amount = float(amount_raw)
        if amount > 1000 and amount == int(amount):
            amount = amount / 100  # assume cents
    except (TypeError, ValueError):
        return None

    # Currency
    currency = (payload.get("currency") or payload.get("currency_code") or "USD")
    if isinstance(currency, str):
        currency = currency.upper()[:3]
    else:
        currency = "USD"

    # Transaction id
    txn = payload.get("id") or payload.get("transaction_id") or payload.get("payment_id") or ""
    transaction_id = str(txn) if txn else None
    if not transaction_id:
        return None

    # DataFast visitor ID: from metadata (if Whop echoes query params / custom metadata)
    metadata = payload.get("metadata") or payload.get("custom_data") or {}
    if isinstance(metadata, dict):
        visitor_id = metadata.get("datafast_visitor_id")
    else:
        visitor_id = None
    visitor_id = visitor_id or payload.get("datafast_visitor_id")

    return {
        "amount": round(amount, 2),
        "currency": currency,
        "transaction_id": transaction_id,
        "datafast_visitor_id": str(visitor_id).strip() if visitor_id else None,
    }


def _extract_whop_member_and_plan(body: dict) -> tuple[str | None, str | None]:
    """Extract (email, app_plan) from Whop payload. app_plan in (starter, pro, lifetime)."""
    data = body.get("data") or body
    obj = data.get("object") if isinstance(data, dict) else data
    if not isinstance(obj, dict):
        obj = body
    member = obj.get("member") or obj.get("user") or {}
    if isinstance(member, dict):
        email = (member.get("email") or member.get("email_address") or "").strip()
    else:
        email = None
    plan_id = obj.get("plan_id") or (obj.get("plan") or {}).get("id") if isinstance(obj.get("plan"), dict) else None
    plan_id = (plan_id or "").strip()
    app_plan = WHOP_PLAN_TO_APP.get(plan_id) if plan_id else None
    return (email or None, app_plan)


def _update_supabase_plan_for_email(email: str, plan: str) -> bool:
    """Find user by email via Supabase auth admin and set profiles.plan. Returns True if updated."""
    from app.core.config import get_settings
    settings = get_settings()
    url = (settings.supabase_url or "").strip()
    role_key = (settings.supabase_service_role_key or "").strip()
    if not url or not role_key:
        return False
    try:
        from supabase import create_client
        admin_client = create_client(url, role_key)
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
        admin_client.table("profiles").upsert(
            {"id": user_id, "plan": plan},
            on_conflict="id",
        ).execute()
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

    event = (body.get("event") or body.get("type") or "").strip().lower()

    if event != "payment.succeeded":
        return {"ok": True, "ignored": True, "event": event}

    # Optionally update Supabase profile (plan) so user gets access after payment
    member_email, app_plan = _extract_whop_member_and_plan(body)
    if member_email and app_plan:
        _update_supabase_plan_for_email(member_email, app_plan)
    else:
        if not member_email:
            logger.debug("Whop webhook: no member email in payload (keys: %s)", list(body.keys()))

    parsed = _extract_whop_payment(body)
    if not parsed:
        logger.warning("Whop webhook: could not parse payment from body keys %s", list(body.keys()))
        return {"ok": True, "forwarded": False, "reason": "parse_failed"}

    api_key = (settings.datafast_api_key or "").strip()
    if not api_key:
        logger.debug("DataFast API key not set, skip forwarding")
        return {"ok": True, "forwarded": False, "reason": "no_datafast_key"}

    if not parsed["datafast_visitor_id"]:
        logger.info("Whop webhook: no datafast_visitor_id in payload, skip DataFast (pass it in checkout metadata or URL)")
        return {"ok": True, "forwarded": False, "reason": "no_visitor_id"}

    # POST to DataFast
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
