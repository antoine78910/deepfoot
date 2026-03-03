# backend/app/api/me.py
"""Endpoint /me : plan, usage, limite d'analyses ; POST /me/cancel-subscription pour annuler via Whop (at_period_end)."""
import logging
from fastapi import APIRouter, Header, HTTPException

from app.services.subscription import (
    get_plan_and_usage,
    get_analysis_limit,
    reset_if_new_day,
    can_analyze,
)
from app.core.supabase_client import get_supabase_admin
from app.core.config import get_settings
from datetime import date, datetime, timezone

router = APIRouter(tags=["me"])
logger = logging.getLogger(__name__)

CANCELLATION_MODE = "at_period_end"  # User keeps access until end of paid period (tuto Whop)

# Whop plan_id → our plan name (same as webhooks)
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


@router.get("/me")
def me(x_user_id: str | None = Header(None, alias="X-User-Id")):
    """
    Retourne le plan, l'usage du jour et la limite pour l'utilisateur.
    X-User-Id optionnel (id Supabase). Si absent, renvoie free avec limite 1.
    """
    user_id = (x_user_id or "").strip()
    plan, used, last = get_plan_and_usage(user_id)
    today = datetime.now(timezone.utc).date()
    used = reset_if_new_day(used, last, today)
    limit, full_analysis = get_analysis_limit(plan)
    allowed, _msg, next_full, _ = can_analyze(user_id)

    return {
        "plan": plan,
        "analyses_used_today": used,
        "analyses_limit": limit,  # null = illimité
        "full_analysis": next_full,
        "can_analyze": allowed,
    }


def _get_user_email_from_supabase(admin, user_id: str) -> str | None:
    """Récupère l'email de l'utilisateur depuis Supabase Auth (service role)."""
    if not admin or not user_id:
        return None
    try:
        r = admin.auth.admin.get_user_by_id(user_id)
        if getattr(r, "user", None) and getattr(r.user, "email", None):
            return (r.user.email or "").strip() or None
    except Exception as e:
        logger.debug("Could not get user email from Supabase auth: %s", e)
    return None


async def _whop_cancel_membership(membership_id: str, whop_key: str) -> bool:
    """Annule un membership Whop (at_period_end). Retourne True si succès."""
    import httpx
    url = f"https://api.whop.com/api/v1/memberships/{membership_id}/cancel"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {whop_key}"},
                json={"cancellation_mode": CANCELLATION_MODE},
                timeout=15.0,
            )
        if resp.status_code < 400:
            return True
        logger.warning("Whop cancel membership %s: %s %s", membership_id, resp.status_code, resp.text)
    except httpx.HTTPError as e:
        logger.exception("Whop cancel request failed: %s", e)
    return False


async def _whop_find_and_cancel_by_email(email: str, whop_key: str, company_id: str) -> bool:
    """
    Trouve le membre Whop par email, puis son membership actif, et l'annule (at_period_end).
    Suit le tuto: list members → find by email → list memberships active → cancel.
    """
    if not email or not whop_key or not company_id:
        return False
    import httpx
    headers = {"Authorization": f"Bearer {whop_key}"}
    email_lower = email.strip().lower()

    # 1) List members (Whop v5 company members ou v2 members)
    member_id = None
    for base in ["https://api.whop.com/api/v5", "https://api.whop.com/api/v2"]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{base}/company/members",
                    params={"company_id": company_id, "per": 100},
                    headers=headers,
                    timeout=15.0,
                )
            if r.status_code >= 400:
                continue
            data = r.json()
            members = data.get("data") if isinstance(data.get("data"), list) else data.get("members") or []
            if not isinstance(members, list):
                members = []
            for m in members:
                if not isinstance(m, dict):
                    continue
                u = m.get("user") or m.get("user_id")
                if isinstance(u, dict):
                    em = (u.get("email") or "").strip().lower()
                else:
                    em = (m.get("email") or "").strip().lower()
                if em == email_lower:
                    member_id = m.get("id") or m.get("member_id")
                    break
            if member_id:
                break
        except Exception as e:
            logger.debug("Whop list members %s: %s", base, e)
    if not member_id:
        logger.warning("Whop: no member found for email %s", email[:3] + "***")
        return False

    # 2) List active memberships for this member
    membership_id = None
    for base in ["https://api.whop.com/api/v5", "https://api.whop.com/api/v2"]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{base}/company/memberships",
                    params={"company_id": company_id, "member_id": member_id, "status": "active", "per": 10},
                    headers=headers,
                    timeout=15.0,
                )
            if r.status_code >= 400:
                continue
            data = r.json()
            list_ms = data.get("data") if isinstance(data.get("data"), list) else data.get("memberships") or []
            if not isinstance(list_ms, list):
                list_ms = []
            for ms in list_ms:
                if isinstance(ms, dict) and (ms.get("status") or "").lower() == "active":
                    membership_id = ms.get("id") or ms.get("membership_id")
                    break
            if not list_ms and isinstance(data.get("data"), list):
                list_ms = data["data"]
            if not membership_id and list_ms:
                membership_id = list_ms[0].get("id") or list_ms[0].get("membership_id") if isinstance(list_ms[0], dict) else None
            if membership_id:
                break
        except Exception as e:
            logger.debug("Whop list memberships %s: %s", base, e)
    if not membership_id:
        logger.warning("Whop: no active membership for member %s", member_id)
        return False

    return await _whop_cancel_membership(membership_id, whop_key)


async def _whop_get_plan_for_email(email: str, whop_key: str, company_id: str) -> tuple[str | None, str | None]:
    """
    Trouve le membre Whop par email et son membership actif ; retourne (app_plan, membership_id).
    Permet de resynchroniser le plan (sync-plan) sans annuler.
    """
    if not email or not whop_key or not company_id:
        return (None, None)
    import httpx
    headers = {"Authorization": f"Bearer {whop_key}"}
    email_lower = email.strip().lower()
    member_id = None
    for base in ["https://api.whop.com/api/v5", "https://api.whop.com/api/v2"]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{base}/company/members",
                    params={"company_id": company_id, "per": 100},
                    headers=headers,
                    timeout=15.0,
                )
            if r.status_code >= 400:
                continue
            data = r.json()
            members = data.get("data") if isinstance(data.get("data"), list) else data.get("members") or []
            if not isinstance(members, list):
                members = []
            for m in members:
                if not isinstance(m, dict):
                    continue
                u = m.get("user") or m.get("user_id")
                if isinstance(u, dict):
                    em = (u.get("email") or "").strip().lower()
                else:
                    em = (m.get("email") or "").strip().lower()
                if em == email_lower:
                    member_id = m.get("id") or m.get("member_id")
                    break
            if member_id:
                break
        except Exception as e:
            logger.debug("Whop list members %s: %s", base, e)
    if not member_id:
        return (None, None)

    membership_id = None
    plan_id = None
    for base in ["https://api.whop.com/api/v5", "https://api.whop.com/api/v2"]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{base}/company/memberships",
                    params={"company_id": company_id, "member_id": member_id, "status": "active", "per": 10},
                    headers=headers,
                    timeout=15.0,
                )
            if r.status_code >= 400:
                continue
            data = r.json()
            list_ms = data.get("data") if isinstance(data.get("data"), list) else data.get("memberships") or []
            if not isinstance(list_ms, list):
                list_ms = []
            for ms in list_ms:
                if isinstance(ms, dict) and (ms.get("status") or "").lower() == "active":
                    membership_id = ms.get("id") or ms.get("membership_id")
                    plan_id = ms.get("plan_id") or (ms.get("plan") or {}).get("id") if isinstance(ms.get("plan"), dict) else None
                    break
            if not membership_id and list_ms and isinstance(list_ms[0], dict):
                ms = list_ms[0]
                membership_id = ms.get("id") or ms.get("membership_id")
                plan_id = ms.get("plan_id") or (ms.get("plan") or {}).get("id") if isinstance(ms.get("plan"), dict) else None
            if membership_id:
                break
        except Exception as e:
            logger.debug("Whop list memberships %s: %s", base, e)
    if not membership_id:
        return (None, None)
    app_plan = WHOP_PLAN_TO_APP.get((plan_id or "").strip()) if plan_id else "starter"
    return (app_plan or "starter", membership_id)


@router.post("/me/sync-plan")
async def sync_plan(x_user_id: str | None = Header(None, alias="X-User-Id")):
    """
    Resynchronise le plan depuis Whop (par email). Si un abonnement actif est trouvé,
    met à jour profiles.plan et whop_membership_id. Utile si l'utilisateur est affiché en free par erreur.
    """
    user_id = (x_user_id or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User-Id required")
    admin = get_supabase_admin()
    if not admin:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    settings = get_settings()
    whop_key = (settings.whop_api_key or "").strip()
    company_id = (settings.whop_company_id or "").strip()
    if not whop_key or not company_id:
        raise HTTPException(status_code=503, detail="Whop not configured (API key + company ID)")
    email = _get_user_email_from_supabase(admin, user_id)
    if not email:
        return {"ok": False, "plan": "free", "updated": False, "reason": "no_email"}
    app_plan, membership_id = await _whop_get_plan_for_email(email, whop_key, company_id)
    if not app_plan or not membership_id:
        return {"ok": True, "plan": "free", "updated": False, "reason": "no_active_membership"}
    try:
        admin.table("profiles").upsert(
            {"id": user_id, "plan": app_plan, "whop_membership_id": membership_id},
            on_conflict="id",
        ).execute()
        logger.info("Sync plan: user %s updated to %s (membership_id=%s)", user_id, app_plan, membership_id[:12] + "...")
        return {"ok": True, "plan": app_plan, "updated": True}
    except Exception as e:
        logger.exception("Sync plan: %s", e)
        raise HTTPException(status_code=500, detail="Failed to update profile")


@router.post("/me/cancel-subscription")
async def cancel_subscription(x_user_id: str | None = Header(None, alias="X-User-Id")):
    """
    Annule l'abonnement Whop (at_period_end: l'utilisateur garde l'accès jusqu'à la fin de la période)
    et repasse le plan en free dans notre DB.
    Si whop_membership_id est présent → annule ce membership. Sinon, tente par email (Whop company members).
    """
    user_id = (x_user_id or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User-Id required")

    admin = get_supabase_admin()
    if not admin:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    try:
        r = admin.table("profiles").select("plan, whop_membership_id").eq("id", user_id).execute()
    except Exception as e:
        msg = str(e).lower()
        code = getattr(e, "code", None) or (e.args[0].get("code") if e.args and isinstance(e.args[0], dict) else None)
        if code == "42703" or "whop_membership_id" in msg or "does not exist" in msg:
            raise HTTPException(
                status_code=503,
                detail="Database migration required: run 004_profiles_whop_membership_id.sql in Supabase SQL Editor.",
            )
        raise

    if not r.data or len(r.data) == 0:
        raise HTTPException(status_code=404, detail="Profile not found")
    row = r.data[0]
    membership_id = (row.get("whop_membership_id") or "").strip()

    settings = get_settings()
    whop_key = (settings.whop_api_key or "").strip()
    company_id = (settings.whop_company_id or "").strip()
    cancelled_via_whop = False

    if membership_id and whop_key:
        cancelled_via_whop = await _whop_cancel_membership(membership_id, whop_key)
        if cancelled_via_whop:
            logger.info("Cancel subscription: user %s cancelled via Whop API (membership_id)", user_id)
    elif not membership_id and whop_key and company_id:
        email = _get_user_email_from_supabase(admin, user_id)
        if email:
            cancelled_via_whop = await _whop_find_and_cancel_by_email(email, whop_key, company_id)
            if cancelled_via_whop:
                logger.info("Cancel subscription: user %s cancelled via Whop API (by email)", user_id)

    # Ne passer le plan en free qu si l'annulation Whop a réellement réussi (évite de downgrader par erreur)
    if cancelled_via_whop:
        admin.table("profiles").upsert(
            {"id": user_id, "plan": "free", "whop_membership_id": None},
            on_conflict="id",
        ).execute()
        logger.info("Cancel subscription: user %s plan set to free", user_id)
        return {"ok": True, "plan": "free", "cancelled_via_whop": True}
    # Annulation Whop impossible (pas de membership_id, ou API / cancel-by-email a échoué) : on ne touche pas au plan
    logger.info("Cancel subscription: user %s — Whop cancel not done, plan unchanged", user_id)
    current_plan = (row.get("plan") or "free").strip() or "free"
    return {"ok": True, "plan": current_plan, "cancelled_via_whop": False}
