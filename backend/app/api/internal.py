"""
Endpoints internes (cron, polling). Protégés par X-Admin-Key si admin_api_key est défini.
"""
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.supabase_client import get_supabase, get_supabase_admin
from app.services.fixture_polling import run_poll_finished_fixtures

router = APIRouter(prefix="/internal", tags=["internal"])


def _check_admin(x_admin_key: str | None) -> None:
    key = get_settings().admin_api_key
    if not key:
        return
    if x_admin_key != key:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Admin-Key")


def _check_dashboard_admin(x_admin_key: str | None) -> None:
    s = get_settings()
    expected = (s.admin_dashboard_token or s.admin_api_key or "").strip()
    if not expected:
        return
    if (x_admin_key or "").strip() != expected:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Admin-Key")


class FeedbackPayload(BaseModel):
    message: str
    user_id: str | None = None
    home_team: str | None = None
    away_team: str | None = None
    page: str | None = None
    email: str | None = None


@router.get("/poll-finished-fixtures")
def poll_finished_fixtures(x_admin_key: str | None = Header(None, alias="X-Admin-Key")):
    """
    Une itération du polling Option A : matchs du jour, si status=FT et pas encore traité
    → récupère les stats et marque comme traité.
    À appeler toutes les 10 s (test) puis toutes les 1 h (cron).
    """
    _check_admin(x_admin_key)
    result = run_poll_finished_fixtures()
    return result


@router.post("/feedback")
def create_feedback(payload: FeedbackPayload):
    msg = (payload.message or "").strip()
    if len(msg) < 4:
        raise HTTPException(status_code=400, detail="Feedback too short")
    supabase = get_supabase_admin() or get_supabase()
    row = {
        "message": msg[:2000],
        "user_id": (payload.user_id or "").strip() or None,
        "home_team": (payload.home_team or "").strip() or None,
        "away_team": (payload.away_team or "").strip() or None,
        "page": (payload.page or "").strip() or "analysis",
        "email": (payload.email or "").strip() or None,
    }
    try:
        supabase.table("analysis_feedback").insert(row).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save feedback: {e}") from e
    return {"ok": True}


@router.get("/admin/summary")
def admin_summary(
    days: int = 30,
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
):
    _check_dashboard_admin(x_admin_key)
    supabase = get_supabase_admin() or get_supabase()
    days = max(1, min(int(days or 30), 365))

    # Feedback récents
    feedback_rows = []
    try:
        r_fb = (
            supabase.table("analysis_feedback")
            .select("id, created_at, user_id, home_team, away_team, page, message, email")
            .order("created_at", desc=True)
            .limit(300)
            .execute()
        )
        feedback_rows = r_fb.data or []
    except Exception:
        feedback_rows = []

    # Profils (snapshot)
    profiles_rows = []
    try:
        r_prof = (
            supabase.table("profiles")
            .select("id, plan, analyses_used_today, last_analysis_date, analyses_total")
            .limit(5000)
            .execute()
        )
        profiles_rows = r_prof.data or []
    except Exception:
        profiles_rows = []

    # Evénements analyses (historique pour agrégations)
    events_rows = []
    try:
        from datetime import datetime, timezone, timedelta

        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        r_ev = (
            supabase.table("analysis_events")
            .select("created_at, user_id, home_team, away_team")
            .gte("created_at", since)
            .order("created_at", desc=True)
            .limit(20000)
            .execute()
        )
        events_rows = r_ev.data or []
    except Exception:
        events_rows = []

    # Agrégations
    per_user: dict[str, dict] = {}
    match_counts: dict[str, int] = {}
    for ev in events_rows:
        if not isinstance(ev, dict):
            continue
        uid = (ev.get("user_id") or "").strip() or "anonymous"
        row = per_user.setdefault(uid, {"user_id": uid, "analyses_window": 0, "matches": []})
        row["analyses_window"] += 1
        h = (ev.get("home_team") or "").strip()
        a = (ev.get("away_team") or "").strip()
        if h and a:
            m = f"{h} vs {a}"
            row["matches"].append(m)
            match_counts[m] = match_counts.get(m, 0) + 1

    profile_map = {str((p or {}).get("id") or ""): p for p in profiles_rows if isinstance(p, dict)}
    users = []
    for uid, r in per_user.items():
        p = profile_map.get(uid) or {}
        users.append(
            {
                "user_id": uid,
                "plan": (p.get("plan") or "free"),
                "analyses_today": int(p.get("analyses_used_today") or 0),
                "analyses_total": int(p.get("analyses_total") or 0),
                "analyses_last_days": int(r.get("analyses_window") or 0),
                "last_analysis_date": p.get("last_analysis_date"),
                "recent_matches": (r.get("matches") or [])[:10],
            }
        )
    # utilisateurs visibles même sans évènement fenêtre
    for p in profiles_rows:
        if not isinstance(p, dict):
            continue
        uid = str(p.get("id") or "")
        if not uid or any(u["user_id"] == uid for u in users):
            continue
        users.append(
            {
                "user_id": uid,
                "plan": (p.get("plan") or "free"),
                "analyses_today": int(p.get("analyses_used_today") or 0),
                "analyses_total": int(p.get("analyses_total") or 0),
                "analyses_last_days": 0,
                "last_analysis_date": p.get("last_analysis_date"),
                "recent_matches": [],
            }
        )

    users.sort(key=lambda x: (x.get("analyses_total") or 0), reverse=True)
    top_matches = sorted(
        [{"match": k, "count": v} for k, v in match_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:30]

    # Resolve Supabase Auth email for each user_id (app login email)
    uid_to_email: dict[str, str] = {}
    admin_client = get_supabase_admin()
    try:
        if admin_client:
            page = 1
            per_page = 1000
            while True:
                r = admin_client.auth.admin.list_users(page=page, per_page=per_page)
                auth_users = None
                if isinstance(r, list):
                    auth_users = r
                elif hasattr(r, "users"):
                    auth_users = getattr(r, "users", None)
                elif hasattr(r, "data"):
                    auth_users = getattr(r, "data", None)
                elif hasattr(r, "model_dump"):
                    d = r.model_dump() if callable(getattr(r, "model_dump")) else {}
                    auth_users = d.get("users") if isinstance(d, dict) else None
                elif isinstance(r, dict):
                    auth_users = r.get("users")
                if not isinstance(auth_users, list):
                    break
                for u in auth_users:
                    uid = None
                    em = None
                    if isinstance(u, dict):
                        uid, em = u.get("id"), u.get("email")
                    else:
                        uid, em = getattr(u, "id", None), getattr(u, "email", None)
                    if uid and em:
                        uid_to_email[str(uid)] = str(em).strip()
                if len(auth_users) < per_page:
                    break
                page += 1
    except Exception:
        uid_to_email = {}

    # Fallback: resolve email one-by-one for users we return (if still missing), max 150 to avoid rate limits
    fallback_count = 0
    for u in users:
        uid = u.get("user_id")
        u["email"] = uid_to_email.get(uid)
        if not u["email"] and uid and admin_client and uid != "anonymous" and fallback_count < 150:
            try:
                fallback_count += 1
                r = admin_client.auth.admin.get_user_by_id(uid)
                user_obj = getattr(r, "user", None)
                if user_obj is not None:
                    em = getattr(user_obj, "email", None) or (user_obj.get("email") if isinstance(user_obj, dict) else None)
                    if em:
                        u["email"] = str(em).strip()
            except Exception:
                pass

    return {
        "window_days": days,
        "feedback_count": len(feedback_rows),
        "feedback": feedback_rows[:200],
        "users_count": len(users),
        "users": users[:500],
        "top_requested_matches": top_matches,
    }
