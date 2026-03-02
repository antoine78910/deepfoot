# backend/app/services/subscription.py
"""
Limites d'analyses par plan : free (1/jour, partielle), starter (1 complète/jour), pro/lifetime (illimité).
Sans Supabase configuré, on autorise toujours (mode démo).
"""
from datetime import date, timezone
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


def get_plan_and_usage(user_id: str) -> tuple[str, int, date | None]:
    """
    Récupère plan normalisé (free|starter|pro|lifetime), analyses_used_today, last_analysis_date.
    Si pas de ligne profile ou user_id vide, considère free avec 0 usage.
    Utilise le client service_role si dispo (RLS bloque la clé anon sans JWT).
    """
    if not user_id or not _use_supabase():
        return (PLAN_FREE, 0, None)
    supabase = get_supabase_admin() or get_supabase()
    r = supabase.table("profiles").select("plan, analyses_used_today, last_analysis_date").eq("id", user_id).execute()
    if not r.data or len(r.data) == 0:
        return (PLAN_FREE, 0, None)
    row = r.data[0]
    plan = _normalize_plan(str(row.get("plan") or "free"))
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


def get_analysis_limit(plan: str) -> tuple[int | None, bool]:
    """
    Retourne (limite_par_jour, full_analysis).
    None = illimité. full_analysis = True si l'analyse est complète (pas de flou).
    Free : analyses illimitées mais contenu partiel (début visible, reste flouté).
    """
    if plan in (PLAN_PRO, PLAN_LIFETIME):
        return (None, True)
    if plan == PLAN_STARTER:
        return (1, True)  # 1 analyse complète par jour
    # free : analyses illimitées, full_analysis = False (affichage partiel + flou)
    return (None, False)


def can_analyze(user_id: str) -> tuple[bool, str, bool]:
    """
    Retourne (autorisé, message_erreur, full_analysis).
    full_analysis = True si la prochaine analyse sera complète (non floutée).
    """
    if not _use_supabase():
        return (True, "", True)
    today = date.today(timezone.utc)
    plan, used, last = get_plan_and_usage(user_id)
    used = reset_if_new_day(used, last, today)
    limit, full_analysis = get_analysis_limit(plan)

    if limit is None:
        return (True, "", full_analysis)
    if used >= limit:
        return (False, "Limite atteinte. Passez à un plan payant pour effectuer des analyses.", full_analysis)
    return (True, "", full_analysis)


def consume_analysis(user_id: str) -> None:
    """Incrémente analyses_used_today et met à jour last_analysis_date."""
    if not user_id or not _use_supabase():
        return
    today = date.today(timezone.utc).isoformat()
    plan, used, last = get_plan_and_usage(user_id)
    used = reset_if_new_day(used, last, date.today(timezone.utc))
    new_used = used + 1

    supabase = get_supabase_admin() or get_supabase()
    supabase.table("profiles").upsert({
        "id": user_id,
        "analyses_used_today": new_used,
        "last_analysis_date": today,
    }, on_conflict="id").execute()
