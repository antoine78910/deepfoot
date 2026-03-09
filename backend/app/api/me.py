# backend/app/api/me.py
"""Endpoint /me : plan, usage, limite d'analyses ; POST /me/cancel-subscription pour annuler via Whop (at_period_end).
POST /me/notify-offer-claim : envoie un email à notify_offer_email quand un user clique sur "Claim 50% offer" (Resend si RESEND_API_KEY).

Whop API URLs appelées (Company API Key uniquement — pas de /me ni de routes v5/v2 /company/*) :
  - GET  https://api.whop.com/api/v1/members?company_id=...&first=100
  - GET  https://api.whop.com/api/v1/memberships?company_id=...&statuses=active&user_ids=...&first=50
  - POST https://api.whop.com/api/v1/memberships/{membership_id}/cancel
  - POST https://api.whop.com/api/v1/memberships/{membership_id}/uncancel
"""
import logging
import httpx
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


def _mask_user_id(user_id: str) -> str:
    """Pour les logs : affiche les 8 premiers caractères max."""
    if not user_id:
        return "anonymous"
    return (user_id[:8] + "...") if len(user_id) > 8 else user_id


@router.get("/me")
async def me(x_user_id: str | None = Header(None, alias="X-User-Id")):
    """
    Retourne le plan, l'usage du jour et la limite pour l'utilisateur.
    X-User-Id optionnel (id Supabase). Si absent, renvoie free avec limite 1.
    À chaque appel, si l'utilisateur est identifié et Whop configuré, on resynchronise
    le plan depuis Whop pour éviter d'afficher "free" à tort.
    """
    user_id = (x_user_id or "").strip()
    admin = get_supabase_admin() if user_id else None
    settings = get_settings()
    whop_key = (settings.whop_api_key or "").strip()
    company_id = (settings.whop_company_id or "").strip()

    # Log every GET /me so we see verification runs on Railway
    logger.info(
        "me: GET /me user_id=%s (whop_key=%s company_id=%s)",
        _mask_user_id(user_id) if user_id else "anonymous",
        "yes" if whop_key else "no",
        "yes" if company_id else "no",
    )

    # Resync from Whop: current membership = active/trialing, order created_at desc, first 1 (recommended strategy)
    if user_id and whop_key and company_id and admin:
        email = _get_user_email_from_supabase(admin, user_id)
        if not email:
            logger.info("me: user_id=%s skip Whop (no email)", _mask_user_id(user_id))
        else:
            logger.info("me: user_id=%s fetching current membership from Whop (active/trialing, latest first)", _mask_user_id(user_id))
            whop_plan, membership_id, ends_at, api_err = await _whop_get_current_membership(email, whop_key, company_id)
            if api_err:
                logger.warning("me: user_id=%s Whop api_error=%s", _mask_user_id(user_id), api_err)
            elif whop_plan and membership_id:
                try:
                    admin.table("profiles").upsert(
                        {
                            "id": user_id,
                            "plan": whop_plan,
                            "whop_membership_id": membership_id,
                            "subscription_ends_at": ends_at,
                        },
                        on_conflict="id",
                    ).execute()
                    logger.info(
                        "me: user_id=%s Whop current membership plan=%s membership_id=%s... subscription_ends_at=%s",
                        _mask_user_id(user_id),
                        whop_plan,
                        (membership_id[:12] + "...") if len(membership_id or "") > 12 else membership_id,
                        ends_at[:10] if ends_at else "none",
                    )
                except Exception as e:
                    logger.warning("me: failed to update plan from Whop for user_id=%s: %s", _mask_user_id(user_id), e)
            else:
                logger.info("me: user_id=%s Whop returned no current membership (no active/trialing)", _mask_user_id(user_id))

    plan, used, last, subscription_ends_at, whop_membership_id = get_plan_and_usage(user_id)
    subscription_started_at: str | None = None
    if user_id:
        logger.info(
            "me: user_id=%s plan=%s whop_membership_id=%s",
            _mask_user_id(user_id),
            plan,
            "yes" if whop_membership_id else "no",
        )
    # Always verify with Whop whether the stored membership is renewing or cancelled; update DB and status accordingly.
    if user_id and whop_key and whop_membership_id:
        logger.info(
            "me: verifying membership status with Whop user_id=%s membership_id=%s...",
            _mask_user_id(user_id),
            (whop_membership_id[:12] + "...") if len(whop_membership_id or "") > 12 else (whop_membership_id or ""),
        )
        period_end_iso, is_canceled, whop_ok, subscription_started_at = await _whop_get_membership_status(whop_membership_id, whop_key)
        if whop_ok:
            if is_canceled and period_end_iso:
                subscription_ends_at = period_end_iso
                try:
                    admin = get_supabase_admin()
                    if admin:
                        admin.table("profiles").update({"subscription_ends_at": period_end_iso}).eq("id", user_id).execute()
                        logger.info("me: user_id=%s Whop status=cancelled => subscription_ends_at=%s", _mask_user_id(user_id), period_end_iso[:10])
                except Exception as e:
                    logger.warning("me: failed to persist subscription_ends_at for user_id=%s: %s", _mask_user_id(user_id), e)
            else:
                subscription_ends_at = None
                try:
                    admin = get_supabase_admin()
                    if admin:
                        admin.table("profiles").update({"subscription_ends_at": None}).eq("id", user_id).execute()
                        logger.info("me: user_id=%s Whop status=renewing => subscription_ends_at cleared", _mask_user_id(user_id))
                except Exception as e:
                    logger.warning("me: failed to clear subscription_ends_at for user_id=%s: %s", _mask_user_id(user_id), e)
        else:
            logger.warning("me: user_id=%s Whop status unavailable (API error?), keeping subscription_ends_at=%s", _mask_user_id(user_id), subscription_ends_at[:10] if subscription_ends_at else None)
            subscription_started_at = None
    if user_id and not whop_membership_id:
        logger.info("me: user_id=%s no whop_membership_id in DB, skipping Whop status check (plan=%s)", _mask_user_id(user_id), plan)
    today = datetime.now(timezone.utc).date()
    used = reset_if_new_day(used, last, today)
    limit, full_analysis = get_analysis_limit(plan)
    allowed, _msg, next_full, _ = can_analyze(user_id)

    logger.info(
        "me: user_id=%s plan=%s full_analysis=%s can_analyze=%s subscription_ends_at=%s",
        _mask_user_id(user_id),
        plan,
        next_full,
        allowed,
        subscription_ends_at[:10] if subscription_ends_at else None,
    )
    return {
        "plan": plan,
        "analyses_used_today": used,
        "analyses_limit": limit,  # null = illimité
        "full_analysis": next_full,
        "can_analyze": allowed,
        "subscription_ends_at": subscription_ends_at,
        "subscription_started_at": subscription_started_at,
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


def _whop_parse_membership_status(m: dict) -> tuple[str | None, bool]:
    """
    Parse membership dict from Whop API. Returns (period_end_iso, is_canceled).
    is_canceled = status is canceled/cancelled or cancel_at_period_end is true.
    """
    status = (m.get("status") or "").strip().lower()
    raw_cancel = m.get("cancel_at_period_end")
    if isinstance(raw_cancel, bool):
        cancel_at_end = raw_cancel
    elif isinstance(raw_cancel, str):
        cancel_at_end = raw_cancel.strip().lower() in ("true", "1", "yes")
    else:
        cancel_at_end = bool(raw_cancel) if raw_cancel is not None else False
    is_canceled = status in ("canceled", "cancelled") or cancel_at_end
    raw = m.get("renewal_period_end") or m.get("renewal_period_end_at")
    period_end: str | None = None
    if isinstance(raw, (int, float)):
        period_end = datetime.fromtimestamp(int(raw), tz=timezone.utc).isoformat()
    elif isinstance(raw, str) and raw.strip():
        period_end = raw.strip()
    return (period_end, is_canceled)


def _whop_plan_tier(app_plan: str) -> int:
    """Order for preferring plan: lifetime > pro > starter > free."""
    return {"lifetime": 3, "pro": 2, "starter": 1}.get((app_plan or "").strip().lower(), 0)


async def _whop_get_membership_details(membership_id: str, whop_key: str) -> tuple[str | None, str | None, bool]:
    """
    GET a membership by id. Returns (plan_id, period_end_iso, is_canceled).
    On API error returns (None, None, False).
    """
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"https://api.whop.com/api/v1/memberships/{membership_id}",
                headers={"Authorization": f"Bearer {whop_key}"},
                timeout=10.0,
            )
        if r.status_code >= 400:
            return (None, None, False)
        data = r.json()
        m = data.get("data") if isinstance(data.get("data"), dict) else data
        if not isinstance(m, dict):
            return (None, None, False)
        plan_id = (m.get("plan_id") or "").strip() or None
        if not plan_id and isinstance(m.get("plan"), dict):
            plan_id = (m.get("plan") or {}).get("id") or None
        period_end, is_canceled = _whop_parse_membership_status(m)
        return (plan_id, period_end, is_canceled)
    except Exception as e:
        logger.debug("Whop get membership details: %s", e)
        return (None, None, False)


def _whop_parse_created_at(m: dict) -> str | None:
    """Parse created_at from Whop membership (unix timestamp) to ISO string."""
    raw = m.get("created_at")
    if raw is None:
        return None
    try:
        ts = int(raw) if isinstance(raw, (int, float)) else int(float(str(raw).strip()))
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except (ValueError, TypeError, OSError):
        return None


async def _whop_get_membership_status(membership_id: str, whop_key: str) -> tuple[str | None, bool, bool, str | None]:
    """
    Récupère le statut d'un membership Whop (GET by id).
    Retourne (period_end_iso, is_canceled, ok, created_at_iso). ok=False si l'API échoue.
    """
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"https://api.whop.com/api/v1/memberships/{membership_id}",
                headers={"Authorization": f"Bearer {whop_key}"},
                timeout=10.0,
            )
        if r.status_code >= 400:
            logger.warning("Whop get membership status HTTP %s membership_id=%s", r.status_code, (membership_id or "")[:12] + "...")
            return (None, False, False, None)
        data = r.json()
        m = data.get("data") if isinstance(data.get("data"), dict) else data
        if not isinstance(m, dict):
            return (None, False, False, None)
        period_end, is_canceled = _whop_parse_membership_status(m)
        created_at_iso = _whop_parse_created_at(m)
        return (period_end, is_canceled, True, created_at_iso)
    except Exception as e:
        logger.warning("Whop get membership status failed membership_id=%s: %s", membership_id[:12] + "..." if len(membership_id or "") > 12 else membership_id, e)
        return (None, False, False, None)


async def _whop_get_membership_period_end(membership_id: str, whop_key: str) -> str | None:
    """Récupère renewal_period_end d'un membership Whop (pour affichage date de fin)."""
    period_end, _, _, _ = await _whop_get_membership_status(membership_id, whop_key)
    return period_end


async def _whop_cancel_membership(membership_id: str, whop_key: str) -> tuple[bool, str | None]:
    """
    Annule un membership Whop (at_period_end). Retourne (succès, period_end_iso ou None).
    Si Whop répond 400 "already canceled", on considère succès et on récupère la date de fin via GET.
    """
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
        if resp.status_code >= 400:
            body = (resp.text or "").lower()
            if resp.status_code == 400 and "already canceled" in body:
                logger.info("Whop cancel membership %s: already canceled, fetching period end", membership_id)
                period_end = await _whop_get_membership_period_end(membership_id, whop_key)
                return (True, period_end)
            logger.warning("Whop cancel membership %s: %s %s", membership_id, resp.status_code, resp.text)
            return (False, None)
        period_end = await _whop_get_membership_period_end(membership_id, whop_key)
        return (True, period_end)
    except httpx.HTTPError as e:
        logger.exception("Whop cancel request failed: %s", e)
    return (False, None)


async def _whop_uncancel_membership(membership_id: str, whop_key: str) -> bool:
    """
    Reverse a pending cancellation (cancel_at_period_end) for a Whop membership.
    Returns True if Whop accepted the uncancel (subscription will renew again).
    """
    import httpx
    url = f"https://api.whop.com/api/v1/memberships/{membership_id}/uncancel"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {whop_key}"},
                timeout=15.0,
            )
        if resp.status_code >= 400:
            body = (resp.text or "").lower()
            if resp.status_code == 400 and ("already" in body or "not cancel" in body):
                logger.info("Whop uncancel membership %s: already renewing", membership_id)
                return True
            logger.warning("Whop uncancel membership %s: %s %s", membership_id, resp.status_code, resp.text)
            return False
        logger.info("Whop uncancel membership %s: success", membership_id)
        return True
    except httpx.HTTPError as e:
        logger.exception("Whop uncancel request failed: %s", e)
    return False


async def _whop_find_and_cancel_by_email(email: str, whop_key: str, company_id: str) -> tuple[bool, str | None]:
    """
    Trouve le membre Whop par email, puis son membership actif, et l'annule (at_period_end).
    Retourne (succès, period_end_iso ou None).
    """
    if not email or not whop_key or not company_id:
        return (False, None)
    result = await _whop_get_plan_for_email(email, whop_key, company_id)
    plan, membership_id, api_error = result
    if api_error or not membership_id:
        return (False, None)
    return await _whop_cancel_membership(membership_id, whop_key)


def _extract_members_list(data: dict, base: str) -> list:
    """Extrait la liste des membres depuis la réponse Whop (v1, v5 ou v2)."""
    raw = data.get("data") or data.get("members") or []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and "data" in raw:
        d = raw.get("data")
        return d if isinstance(d, list) else []
    return []


async def _whop_get_user_id_by_email(email: str, whop_key: str, company_id: str) -> tuple[str | None, str | None]:
    """
    Returns (whop_user_id, api_error). Use whop_user_id for memberships list (user_ids param).
    """
    if not email or not whop_key or not company_id:
        return (None, None)
    import httpx
    headers = {"Authorization": f"Bearer {whop_key}"}
    email_lower = email.strip().lower()
    user_id_for_memberships: str | None = None
    api_error: str | None = None
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://api.whop.com/api/v1/members",
                params={"company_id": company_id, "first": 100},
                headers=headers,
                timeout=15.0,
            )
        if r.status_code == 401:
            api_error = "whop_unauthorized"
            return (None, api_error)
        if r.status_code == 403:
            api_error = "whop_forbidden"
            return (None, api_error)
        if r.status_code >= 400:
            return (None, None)
        data = r.json()
        members = _extract_members_list(data, "v1")
        for m in members:
            if not isinstance(m, dict):
                continue
            u = m.get("user") or m.get("user_id")
            if isinstance(u, dict):
                em = (u.get("email") or "").strip().lower()
            else:
                em = (m.get("email") or "").strip().lower()
            if em == email_lower:
                u_obj = m.get("user")
                user_id_for_memberships = (u_obj.get("id") if isinstance(u_obj, dict) else None) or m.get("user_id")
                break
        return (user_id_for_memberships, None)
    except Exception as e:
        logger.warning("Whop get user_id by email: %s", e)
        return (None, None)


async def _whop_get_current_membership(
    email: str, whop_key: str, company_id: str
) -> tuple[str | None, str | None, str | None, str | None]:
    """
    Stratégie recommandée Whop : récupérer l'abonnement actuel = le plus récent actif/trialing.
    GET /memberships avec statuses=["active", "trialing"], order="created_at", direction="desc", first=1.
    Returns (app_plan, membership_id, subscription_ends_at, api_error).
    """
    if not email or not whop_key or not company_id:
        return (None, None, None, None)
    user_id_whop, api_error = await _whop_get_user_id_by_email(email, whop_key, company_id)
    if api_error:
        return (None, None, None, api_error)
    if not user_id_whop:
        logger.info("Whop: no user found for email %s*** (cannot list memberships)", (email or "")[:4])
        return (None, None, None, None)
    import httpx
    headers = {"Authorization": f"Bearer {whop_key}"}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://api.whop.com/api/v1/memberships",
                params={
                    "company_id": company_id,
                    "user_ids": [user_id_whop],
                    "statuses": ["active", "trialing"],
                    "order": "created_at",
                    "direction": "desc",
                    "first": 1,
                },
                headers=headers,
                timeout=15.0,
            )
        if r.status_code >= 400:
            logger.warning("Whop list memberships (current): HTTP %s", r.status_code)
            return (None, None, None, None)
        data = r.json()
        list_ms = data.get("data") if isinstance(data.get("data"), list) else data.get("memberships") or []
        if not list_ms or not isinstance(list_ms[0], dict):
            return (None, None, None, None)
        ms = list_ms[0]
        membership_id = ms.get("id") or ms.get("membership_id")
        plan_id = ms.get("plan_id") or (ms.get("plan") or {}).get("id") if isinstance(ms.get("plan"), dict) else None
        if not membership_id:
            return (None, None, None, None)
        # Get details to know cancel_at_period_end and period_end
        _, period_end_iso, is_canceled = await _whop_get_membership_details(membership_id, whop_key)
        app_plan = (WHOP_PLAN_TO_APP.get((plan_id or "").strip()) if plan_id else "starter") or "starter"
        subscription_ends_at = period_end_iso if is_canceled else None
        return (app_plan, membership_id, subscription_ends_at, None)
    except Exception as e:
        logger.warning("Whop get current membership: %s", e)
        return (None, None, None, None)


async def _whop_get_plan_for_email(email: str, whop_key: str, company_id: str) -> tuple[str | None, str | None, str | None]:
    """
    Trouve le membre Whop par email et son membership actif.
    Retourne (app_plan, membership_id, api_error).
    api_error = "whop_unauthorized" (401) ou "whop_forbidden" (403) si l'API Whop refuse la requête.
    """
    if not email or not whop_key or not company_id:
        return (None, None, None)
    import httpx
    headers = {"Authorization": f"Bearer {whop_key}"}
    email_lower = email.strip().lower()
    member_id = None
    user_id_for_memberships: str | None = None  # v1 list memberships filters by user_ids
    api_error: str | None = None
    # Company API keys must use v1 only; v5/v2 /company/* routes are for App API keys (401 otherwise)
    # https://docs.whop.com/developer/api/getting-started
    endpoints: list[tuple[str, str, dict]] = [
        ("https://api.whop.com/api/v1", "/members", {"company_id": company_id, "first": 100}),
    ]
    for base, path, base_params in endpoints:
        page = 1
        after_cursor: str | None = None
        while page <= 5:
            try:
                params = dict(base_params)
                if "page" in params:
                    params["page"] = page
                if after_cursor and "first" in params:
                    params["after"] = after_cursor
                async with httpx.AsyncClient() as client:
                    r = await client.get(
                        f"{base}{path}",
                        params=params,
                        headers=headers,
                        timeout=15.0,
                    )
                if r.status_code == 401:
                    try:
                        body = (r.text or "")[:500]
                        logger.warning(
                            "Whop API: 401 (use Company API key with member:basic:read, member:email:read, member:phone:read). Response: %s",
                            body or "(empty)",
                        )
                    except Exception:
                        logger.warning("Whop API: 401 Unauthorized (check WHOP_API_KEY)")
                    api_error = "whop_unauthorized"
                    break
                if r.status_code == 403:
                    logger.warning("Whop API: 403 Forbidden (check company_id or API scope)")
                    api_error = "whop_forbidden"
                    break
                if r.status_code >= 400:
                    break
                data = r.json()
                members = _extract_members_list(data, base)
                if not members and page == 1:
                    logger.info("Whop: company members list empty (company_id=%s)", company_id[:12] + "...")
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
                        u_obj = m.get("user")
                        user_id_for_memberships = (u_obj.get("id") if isinstance(u_obj, dict) else None) or m.get("user_id")
                        break
                if member_id:
                    break
                # Cursor-based (v1): use next page cursor if present
                if "first" in params:
                    next_cursor = (data.get("has_next_page") and data.get("end_cursor")) or data.get("next_cursor")
                    if next_cursor and len(members) >= 100:
                        after_cursor = next_cursor
                        page += 1
                        continue
                # Page-based: stop if less than full page
                if len(members) < 100:
                    break
                page += 1
            except Exception as e:
                logger.warning("Whop list members %s%s page %s: %s", base, path, page, e)
                break
        if member_id or api_error:
            break
    if api_error:
        return (None, None, api_error)
    if not member_id:
        logger.info("Whop: no member found for email %s (v1 members)", email_lower[:3] + "***")
        return (None, None, None)

    membership_id = None
    plan_id = None
    # Company API keys: v1 only; v1 list memberships uses statuses[] and user_ids[] (not member_id)
    for base, path in [
        ("https://api.whop.com/api/v1", "/memberships"),
    ]:
        try:
            params: dict = {"company_id": company_id, "first": 50}
            if user_id_for_memberships:
                params["user_ids"] = [user_id_for_memberships]
            params["statuses"] = ["active"]
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{base}{path}",
                    params=params,
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
        return (None, None, None)
    app_plan = WHOP_PLAN_TO_APP.get((plan_id or "").strip()) if plan_id else "starter"
    return (app_plan or "starter", membership_id, None)


async def _whop_get_best_membership_for_user(
    email: str, whop_key: str, company_id: str
) -> tuple[str | None, str | None, str | None, str | None]:
    """
    Liste tous les memberships actifs de l'user, choisit le plus pertinent.
    - Préfère un membership qui RENEW (pas cancel_at_period_end) = dernier plan actif.
    - Si tous sont en "cancels in..." → on prend le plus récent et on renvoie subscription_ends_at.
    Returns (app_plan, membership_id, subscription_ends_at, api_error).
    """
    result = await _whop_get_plan_for_email(email, whop_key, company_id)
    plan_from_list, single_membership_id, api_error = result
    if api_error:
        return (None, None, None, api_error)
    if not single_membership_id:
        return (None, None, None, None)
    # We currently get only the first membership from list. We need ALL. So we need to change
    # _whop_get_plan_for_email to return all membership ids, or add a new internal function.
    # Simpler: list memberships again and collect all ids, then fetch details for each.
    import httpx
    headers = {"Authorization": f"Bearer {whop_key}"}
    # Get user_id_for_memberships again (we need it to list memberships)
    email_lower = (email or "").strip().lower()
    member_id = None
    user_id_for_memberships = None
    for base, path, base_params in [
        ("https://api.whop.com/api/v1", "/members", {"company_id": company_id, "first": 100}),
    ]:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{base}{path}",
                    params=base_params,
                    headers=headers,
                    timeout=15.0,
                )
            if r.status_code >= 400:
                continue
            data = r.json()
            members = _extract_members_list(data, base)
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
                    u_obj = m.get("user")
                    user_id_for_memberships = (u_obj.get("id") if isinstance(u_obj, dict) else None) or m.get("user_id")
                    break
            if member_id:
                break
        except Exception as e:
            logger.debug("Whop list members for best membership: %s", e)
            return (None, None, None, None)
    if not user_id_for_memberships:
        return (None, None, None, None)
    # List all active memberships
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://api.whop.com/api/v1/memberships",
                params={"company_id": company_id, "user_ids": [user_id_for_memberships], "first": 50, "statuses": ["active"]},
                headers=headers,
                timeout=15.0,
            )
        if r.status_code >= 400:
            return (plan_from_list, single_membership_id, None, None)
        data = r.json()
        list_ms = data.get("data") if isinstance(data.get("data"), list) else data.get("memberships") or []
        if not isinstance(list_ms, list):
            list_ms = []
    except Exception as e:
        logger.debug("Whop list memberships for best: %s", e)
        return (plan_from_list, single_membership_id, None, None)
    # Collect (membership_id, plan_id) from list
    candidates: list[tuple[str, str | None]] = []
    for ms in list_ms:
        if not isinstance(ms, dict):
            continue
        mid = ms.get("id") or ms.get("membership_id")
        pid = ms.get("plan_id") or (ms.get("plan") or {}).get("id") if isinstance(ms.get("plan"), dict) else None
        if mid:
            candidates.append((str(mid).strip(), pid))
    if not candidates:
        return (None, None, None, None)
    # Fetch details for each to get is_canceled and period_end
    renewing: list[tuple[str, str, int]] = []  # (membership_id, app_plan, tier)
    cancelling: list[tuple[str, str, str | None, int]] = []  # (membership_id, app_plan, period_end, tier)
    for mid, list_plan_id in candidates:
        plan_id, period_end, is_canceled = await _whop_get_membership_details(mid, whop_key)
        plan_id = plan_id or list_plan_id
        app_plan = (WHOP_PLAN_TO_APP.get((plan_id or "").strip()) if plan_id else "starter") or "starter"
        tier = _whop_plan_tier(app_plan)
        if is_canceled:
            cancelling.append((mid, app_plan, period_end, tier))
        else:
            renewing.append((mid, app_plan, tier))
    # Prefer renewing (last active plan); best tier first
    if renewing:
        renewing.sort(key=lambda x: -x[2])
        best_id, best_plan, _ = renewing[0]
        return (best_plan, best_id, None, None)
    # All cancelling: pick best tier, then latest period_end (so "last" cancelling membership)
    if cancelling:
        cancelling.sort(key=lambda x: (x[3], x[2] or ""), reverse=True)
        best_id, best_plan, period_end, _ = cancelling[0]
        return (best_plan, best_id, period_end or None, None)
    return (None, None, None, None)


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
    app_plan, membership_id, subscription_ends_at, whop_error = await _whop_get_best_membership_for_user(email, whop_key, company_id)
    if whop_error:
        return {"ok": False, "plan": "free", "updated": False, "reason": "whop_api_error"}
    if not app_plan or not membership_id:
        return {"ok": True, "plan": "free", "updated": False, "reason": "no_active_membership"}
    try:
        admin.table("profiles").upsert(
            {"id": user_id, "plan": app_plan, "whop_membership_id": membership_id, "subscription_ends_at": subscription_ends_at},
            on_conflict="id",
        ).execute()
        logger.info("Sync plan: user %s updated to %s (membership_id=%s) subscription_ends_at=%s", user_id, app_plan, membership_id[:12] + "...", subscription_ends_at[:10] if subscription_ends_at else None)
        return {"ok": True, "plan": app_plan, "updated": True, "subscription_ends_at": subscription_ends_at}
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
        r = admin.table("profiles").select("plan, whop_membership_id, subscription_ends_at").eq("id", user_id).execute()
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

    period_end_iso: str | None = None
    if membership_id and whop_key:
        cancelled_via_whop, period_end_iso = await _whop_cancel_membership(membership_id, whop_key)
        if cancelled_via_whop:
            logger.info("Cancel subscription: user %s cancelled via Whop API (membership_id)", user_id)
    elif not membership_id and whop_key and company_id:
        email = _get_user_email_from_supabase(admin, user_id)
        if email:
            cancelled_via_whop, period_end_iso = await _whop_find_and_cancel_by_email(email, whop_key, company_id)
            if cancelled_via_whop:
                logger.info("Cancel subscription: user %s cancelled via Whop API (by email)", user_id)

    current_plan = (row.get("plan") or "free").strip() or "free"
    # Annulation réussie : on stocke la date de fin (at_period_end), on ne passe PAS le plan en free tout de suite
    if cancelled_via_whop:
        admin.table("profiles").update(
            {"subscription_ends_at": period_end_iso}
        ).eq("id", user_id).execute()
        logger.info("Cancel subscription: user %s subscription_ends_at=%s (plan unchanged: %s)", user_id, period_end_iso, current_plan)
        return {"ok": True, "plan": current_plan, "cancelled_via_whop": True, "subscription_ends_at": period_end_iso}
    logger.info("Cancel subscription: user %s — Whop cancel not done, plan unchanged", user_id)
    return {"ok": True, "plan": current_plan, "cancelled_via_whop": False}


@router.post("/me/renew-subscription")
async def renew_subscription(x_user_id: str | None = Header(None, alias="X-User-Id")):
    """
    Reverse the cancellation of the user's plan (Whop uncancel). Clears subscription_ends_at
    so the subscription will renew again at the end of the period.
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
        if "whop_membership_id" in msg or "does not exist" in msg:
            raise HTTPException(status_code=503, detail="Database migration required")
        raise

    if not r.data or len(r.data) == 0:
        raise HTTPException(status_code=404, detail="Profile not found")
    row = r.data[0]
    membership_id = (row.get("whop_membership_id") or "").strip()
    current_plan = (row.get("plan") or "free").strip() or "free"

    if not membership_id:
        raise HTTPException(status_code=400, detail="No subscription to renew")

    settings = get_settings()
    whop_key = (settings.whop_api_key or "").strip()
    if not whop_key:
        raise HTTPException(status_code=503, detail="Whop not configured")

    renewed = await _whop_uncancel_membership(membership_id, whop_key)
    if not renewed:
        raise HTTPException(status_code=400, detail="Could not renew subscription. It may already be active.")

    try:
        admin.table("profiles").update({"subscription_ends_at": None}).eq("id", user_id).execute()
    except Exception as e:
        logger.warning("renew-subscription: failed to clear subscription_ends_at for user %s: %s", user_id, e)

    logger.info("Renew subscription: user %s plan=%s subscription_ends_at cleared", user_id, current_plan)
    return {"ok": True, "plan": current_plan, "renewed": True, "subscription_ends_at": None}


@router.post("/me/notify-offer-claim")
async def notify_offer_claim(x_user_id: str | None = Header(None, alias="X-User-Id")):
    """
    Appelé quand l'utilisateur clique sur "Claim 50% offer". Envoie un email à notify_offer_email
    (anto.delbos@gmail.com) si RESEND_API_KEY est configuré. Sinon, log uniquement.
    """
    user_id = (x_user_id or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User-Id required")

    settings = get_settings()
    to_email = (settings.notify_offer_email or "anto.delbos@gmail.com").strip()
    api_key = (settings.resend_api_key or "").strip()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    body_text = f"Un utilisateur a cliqué sur « Claim 50% offer ».\n\nUser ID: {user_id}\nDate: {now}"
    from_addr = (settings.notify_from_email or "DeepFoot <onboarding@resend.dev>").strip()
    payload = {
        "from": from_addr,
        "to": [to_email],
        "subject": "DeepFoot: Claim 50% offer",
        "text": body_text,
    }

    if api_key:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=10.0,
                )
                if r.status_code in (200, 201):
                    logger.info("notify-offer-claim: email sent to %s for user %s", to_email[:10] + "...", _mask_user_id(user_id))
                else:
                    logger.warning("notify-offer-claim: Resend returned %s %s", r.status_code, r.text[:200])
        except Exception as e:
            logger.warning("notify-offer-claim: failed to send email: %s", e)
    else:
        logger.info("notify-offer-claim: RESEND_API_KEY not set, skip send (user_id=%s)", _mask_user_id(user_id))

    return {"ok": True}
