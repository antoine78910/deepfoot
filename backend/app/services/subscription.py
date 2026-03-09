# backend/app/services/subscription.py
"""
Limites d'analyses par plan : free (3/jour à 15% flouté), starter (1 complète/jour), pro/lifetime (illimité).
Sans Supabase configuré, on autorise toujours (mode démo).
"""
from datetime import date, datetime, timezone
from app.core.config import get_settings
from app.core.supabase_client import get_supabase, get_supabase_admin

# Plans reconnus : free, starter, pro, lifetime (premium mappé sur pro)
PLAN_FREE = "free"
PLAN_STARTER = "starter"
PLAN_PRO = "pro"
PLAN_LIFETIME = "lifetime"


def _use_supabase() -> bool:
    s = get_settings()
    return bool(s.supabase_url and s.supabase_key)


def _normalize_plan(plan: str) -> str:
    p = (plan or "free").lower().strip()
    if p in (PLAN_PRO, "premium"):
        return PLAN_PRO
    if p == PLAN_STARTER:
        return PLAN_STARTER
    if p == PLAN_LIFETIME:
        return PLAN_LIFETIME
    return PLAN_FREE


def get_plan_and_usage(user_id: str) -> tuple[str, int, date | None, str | None, str | None]:
    """
    Récupère plan normalisé, usage du jour, last_*_date, subscription_ends_at, whop_membership_id.
    Pour free : analyses_used_today / last_analysis_date (analyses partielles).
    Pour starter/pro/lifetime : full_analyses_used_today / last_full_analysis_date (analyses complètes).
    """
    if not user_id or not _use_supabase():
        return (PLAN_FREE, 0, None, None, None)
    supabase = get_supabase_admin() or get_supabase()
    r = supabase.table("profiles").select(
        "plan, analyses_used_today, last_analysis_date, full_analyses_used_today, last_full_analysis_date, subscription_ends_at, whop_membership_id"
    ).eq("id", user_id).execute()
    if not r.data or len(r.data) == 0:
        return (PLAN_FREE, 0, None, None, None)
    row = r.data[0]
    plan = _normalize_plan(str(row.get("plan") or "free"))
    if plan in (PLAN_STARTER, PLAN_PRO, PLAN_LIFETIME):
        used = int(row.get("full_analyses_used_today") or 0)
        last_raw = row.get("last_full_analysis_date")
    else:
        used = int(row.get("analyses_used_today") or 0)
        last_raw = row.get("last_analysis_date")
    last = None
    if last_raw:
        try:
            last = date.fromisoformat(str(last_raw)[:10])
        except Exception:
            last = None
    ends_at = row.get("subscription_ends_at")
    if ends_at is not None and ends_at != "":
        ends_at = str(ends_at).strip()
    else:
        ends_at = None
    membership_id = (row.get("whop_membership_id") or "").strip() or None
    return (plan, used, last, ends_at, membership_id)


def reset_if_new_day(used: int, last: date | None, today: date) -> int:
    """Si last < today, remet used à 0."""
    if last is None or last < today:
        return 0
    return used


def get_analysis_limit(plan: str) -> tuple[int | None, bool]:
    """
    Retourne (limite_par_jour, full_analysis).
    None = illimité. full_analysis = True si l'analyse est complète (pas de flou).
    Free : 3 analyses/jour à 15% (contenu partiel + flou). Starter : 1 complète/jour.
    """
    if plan in (PLAN_PRO, PLAN_LIFETIME):
        return (None, True)
    if plan == PLAN_STARTER:
        return (1, True)  # 1 analyse complète par jour
    # free : 3 analyses par jour, full_analysis = False (affichage partiel à 15% + flou)
    return (3, False)


def can_analyze(user_id: str) -> tuple[bool, str, bool, str | None]:
    """
    Retourne (autorisé, message_erreur, full_analysis, limit_reason).
    limit_reason = "free" | "starter" quand limite atteinte (pour afficher le bon popup côté front).
    """
    if not _use_supabase():
        return (True, "", True, None)
    today = datetime.now(timezone.utc).date()
    plan, used, last, _, _ = get_plan_and_usage(user_id)
    used = reset_if_new_day(used, last, today)
    limit, full_analysis = get_analysis_limit(plan)

    if limit is None:
        return (True, "", full_analysis, None)
    if used >= limit:
        msg = "Limite atteinte. Passez à un plan payant pour effectuer des analyses."
        return (False, msg, full_analysis, plan)
    return (True, "", full_analysis, None)


def get_chat_limit(plan: str) -> int | None:
    """
    Retourne la limite de requêtes chat IA par jour.
    Pro: 1/jour. Lifetime: None (illimité). Free/Starter: 0 (non autorisé).
    """
    if plan == PLAN_LIFETIME:
        return None
    if plan == PLAN_PRO:
        return 1
    return 0


def get_chat_usage(user_id: str) -> tuple[int, date | None]:
    """Récupère chat_requests_used_today et last_chat_date pour l'utilisateur."""
    if not user_id or not _use_supabase():
        return (0, None)
    supabase = get_supabase_admin() or get_supabase()
    try:
        r = supabase.table("profiles").select("chat_requests_used_today, last_chat_date").eq("id", user_id).execute()
        if not r.data or len(r.data) == 0:
            return (0, None)
        row = r.data[0]
        used = int(row.get("chat_requests_used_today") or 0)
        last = row.get("last_chat_date")
        if last:
            try:
                last = date.fromisoformat(str(last)[:10])
            except Exception:
                last = None
        return (used, last)
    except Exception:
        return (0, None)


def can_use_chat_ai(user_id: str) -> tuple[bool, int | None, str]:
    """
    Retourne (autorisé, remaining, message).
    remaining = None si illimité (Lifetime), sinon nombre de questions restantes aujourd'hui.
    """
    if not _use_supabase():
        return (True, None, "")
    plan, _, _, _, _ = get_plan_and_usage(user_id)
    limit = get_chat_limit(plan)
    if limit == 0:
        return (False, 0, "Chat IA réservé aux abonnés Pro et Lifetime.")
    today = datetime.now(timezone.utc).date()
    used, last = get_chat_usage(user_id)
    used = reset_if_new_day(used, last, today)
    if limit is None:
        return (True, None, "")
    remaining = max(0, limit - used)
    if remaining == 0:
        return (False, 0, "Limite atteinte : 1 question par jour pour le plan Pro. Réessayez demain ou passez à Lifetime pour des questions illimitées.")
    return (True, remaining, "")


def consume_chat_ai(user_id: str) -> None:
    """Incrémente chat_requests_used_today et met à jour last_chat_date."""
    if not user_id or not _use_supabase():
        return
    today = datetime.now(timezone.utc).date()
    used, last = get_chat_usage(user_id)
    used = reset_if_new_day(used, last, today)
    new_used = used + 1
    supabase = get_supabase_admin() or get_supabase()
    supabase.table("profiles").upsert(
        {
            "id": user_id,
            "chat_requests_used_today": new_used,
            "last_chat_date": today.isoformat(),
        },
        on_conflict="id",
    ).execute()


def consume_analysis(user_id: str, home_team: str | None = None, away_team: str | None = None) -> None:
    """
    Compte une analyse : free → analyses_used_today/last_analysis_date ;
    starter/pro/lifetime → full_analyses_used_today/last_full_analysis_date.
    Incrémente aussi analyses_total et journalise l'événement.
    """
    if not user_id or not _use_supabase():
        return
    today = datetime.now(timezone.utc).date()
    plan, used, last, _, _ = get_plan_and_usage(user_id)
    used = reset_if_new_day(used, last, today)
    new_used = used + 1

    supabase = get_supabase_admin() or get_supabase()
    analyses_total = 0
    try:
        r = supabase.table("profiles").select("analyses_total").eq("id", user_id).execute()
        if r.data and len(r.data) > 0:
            analyses_total = int((r.data[0] or {}).get("analyses_total") or 0)
    except Exception:
        analyses_total = 0

    if plan in (PLAN_STARTER, PLAN_PRO, PLAN_LIFETIME):
        payload = {
            "id": user_id,
            "full_analyses_used_today": new_used,
            "last_full_analysis_date": today.isoformat(),
            "analyses_total": analyses_total + 1,
        }
    else:
        payload = {
            "id": user_id,
            "analyses_used_today": new_used,
            "last_analysis_date": today.isoformat(),
            "analyses_total": analyses_total + 1,
        }
    supabase.table("profiles").upsert(payload, on_conflict="id").execute()
    try:
        supabase.table("analysis_events").insert(
            {
                "user_id": user_id,
                "home_team": (home_team or "").strip() or None,
                "away_team": (away_team or "").strip() or None,
                "source": "predict",
            }
        ).execute()
    except Exception:
        # table absente / RLS / autre : on ne bloque pas l'analyse
        pass
