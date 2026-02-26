# backend/app/services/subscription.py
"""
Vérification limite d'analyses : 1/jour (free) vs illimité (premium).
Sans Supabase configuré, on autorise toujours (mode démo).
"""
from datetime import date, timezone
from app.core.config import get_settings
from app.core.supabase_client import get_supabase


def _use_supabase() -> bool:
    s = get_settings()
    return bool(s.supabase_url and s.supabase_key)


def get_plan_and_usage(user_id: str) -> tuple[str, int, date | None]:
    """
    Récupère plan ('free' | 'premium'), analyses_used_today, last_analysis_date.
    Si pas de ligne profile, considère free avec 0 usage.
    """
    if not _use_supabase():
        return ("free", 0, None)
    supabase = get_supabase()
    r = supabase.table("profiles").select("plan, analyses_used_today, last_analysis_date").eq("id", user_id).execute()
    if not r.data or len(r.data) == 0:
        return ("free", 0, None)
    row = r.data[0]
    plan = row.get("plan") or "free"
    used = int(row.get("analyses_used_today") or 0)
    last = row.get("last_analysis_date")
    if last:
        try:
            last = date.fromisoformat(str(last)[:10])
        except Exception:
            last = None
    return (plan, used, last)


def reset_if_new_day(used: int, last: date | None, today: date) -> int:
    """Si last < today, remet used à 0."""
    if last is None or last < today:
        return 0
    return used


def can_analyze(user_id: str) -> tuple[bool, str]:
    """
    Retourne (True, "") si l'utilisateur peut faire une analyse, sinon (False, message).
    """
    if not _use_supabase():
        return (True, "")
    today = date.today(timezone.utc)
    plan, used, last = get_plan_and_usage(user_id)
    used = reset_if_new_day(used, last, today)

    if plan == "premium":
        return (True, "")

    limit = get_settings().free_analyses_per_day
    if used >= limit:
        return (False, f"Limite atteinte : {limit} analyse(s) gratuite(s) par jour.")
    return (True, "")


def consume_analysis(user_id: str) -> None:
    """Incrémente analyses_used_today et met à jour last_analysis_date."""
    if not _use_supabase():
        return
    today = date.today(timezone.utc).isoformat()
    supabase = get_supabase()
    plan, used, last = get_plan_and_usage(user_id)
    used = reset_if_new_day(used, last, date.today(timezone.utc))
    new_used = used + 1

    supabase.table("profiles").upsert({
        "id": user_id,
        "analyses_used_today": new_used,
        "last_analysis_date": today,
    }, on_conflict="id").execute()
