"""
Endpoints internes (cron, polling). Protégés par X-Admin-Key si admin_api_key est défini.
"""
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.supabase_client import get_supabase, get_supabase_admin
from app.services.fixture_polling import run_poll_finished_fixtures
from app.services.prediction_costs import (
    cost_from_result,
    economics_payload,
    estimated_cost_eur,
    revenue_for_plan,
)
from app.services.subscription import _normalize_plan, get_analysis_limit

router = APIRouter(prefix="/internal", tags=["internal"])


def _fetch_auth_emails_via_http() -> dict[str, str]:
    """
    Récupère tous les emails Supabase Auth via l'API REST admin (auth/v1/admin/users).
    Retourne un dict user_id -> email. Vide si pas de config ou erreur.
    """
    s = get_settings()
    url_base = (s.supabase_url or "").strip().rstrip("/")
    key = (s.supabase_service_role_key or "").strip()
    if not url_base or not key:
        return {}
    uid_to_email: dict[str, str] = {}
    try:
        import httpx
        auth_url = f"{url_base}/auth/v1/admin/users"
        headers = {"Authorization": f"Bearer {key}", "apikey": key}
        page = 1
        per_page = 1000
        while True:
            with httpx.Client(timeout=30.0) as client:
                r = client.get(auth_url, params={"per_page": per_page, "page": page}, headers=headers)
            if r.status_code >= 400:
                break
            data = r.json()
            users = data.get("users") if isinstance(data.get("users"), list) else []
            for u in users:
                if not isinstance(u, dict):
                    continue
                uid = (u.get("id") or "").strip()
                em = (u.get("email") or "").strip()
                if uid and em:
                    uid_to_email[uid] = em
            if len(users) < per_page:
                break
            page += 1
    except Exception:
        pass
    return uid_to_email


def dashboard_admin_emails() -> set[str]:
    raw = (get_settings().admin_emails or "anto.delbos@gmail.com")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def is_dashboard_admin_email(email: str | None) -> bool:
    em = (email or "").strip().lower()
    return bool(em) and em in dashboard_admin_emails()


def _email_for_user_id(user_id: str) -> str | None:
    uid = (user_id or "").strip()
    if not uid:
        return None
    admin = get_supabase_admin()
    if admin:
        try:
            r = admin.auth.admin.get_user_by_id(uid)
            user_obj = getattr(r, "user", None)
            if user_obj is not None:
                em = getattr(user_obj, "email", None) or (user_obj.get("email") if isinstance(user_obj, dict) else None)
                if em:
                    return str(em).strip()
        except Exception:
            pass
    s = get_settings()
    url_base = (s.supabase_url or "").strip().rstrip("/")
    key = (s.supabase_service_role_key or "").strip()
    if not url_base or not key:
        return None
    try:
        import httpx

        r = httpx.get(
            f"{url_base}/auth/v1/admin/users/{uid}",
            headers={"Authorization": f"Bearer {key}", "apikey": key},
            timeout=20.0,
        )
        if r.status_code < 400:
            data = r.json() if r.content else {}
            em = (data.get("email") or "").strip() if isinstance(data, dict) else ""
            if em:
                return em
    except Exception:
        pass
    return None


def _check_admin(x_admin_key: str | None) -> None:
    key = get_settings().admin_api_key
    if not key:
        return
    if x_admin_key != key:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Admin-Key")


def _check_dashboard_admin(
    x_user_id: str | None = None,
    x_user_email: str | None = None,
) -> None:
    uid = (x_user_id or "").strip()
    looked_up = _email_for_user_id(uid)
    if is_dashboard_admin_email(looked_up):
        return
    # Fallback when Auth admin lookup is unavailable: signed-in owner session.
    if uid and is_dashboard_admin_email(x_user_email):
        return
    raise HTTPException(status_code=403, detail="Admin access required")


_ADMIN_HISTORY_SELECT = (
    "id, created_at, user_id, home_team, away_team, home_logo, away_logo, league, "
    "result->prob_home, result->prob_draw, result->prob_away, "
    "result->internal_prob_home, result->internal_prob_draw, result->internal_prob_away, "
    "result->xg_home, result->xg_away, result->most_likely_score, result->quick_summary, "
    "result->recalculated_from_form, result->data_source, result->llm_usage, "
    "result->analysis_recap->placeholder_form, result->analysis_recap->data_source"
)


def _history_row_for_card(row: dict) -> dict:
    """Accept either nested `result` or flattened PostgREST jsonb columns."""
    if isinstance(row.get("result"), dict):
        return row
    recap = {
        "placeholder_form": row.get("placeholder_form"),
        "recalculated_from_form": row.get("recalculated_from_form"),
        "data_source": row.get("data_source"),
    }
    result = {
        "prob_home": row.get("prob_home"),
        "prob_draw": row.get("prob_draw"),
        "prob_away": row.get("prob_away"),
        "internal_prob_home": row.get("internal_prob_home"),
        "internal_prob_draw": row.get("internal_prob_draw"),
        "internal_prob_away": row.get("internal_prob_away"),
        "xg_home": row.get("xg_home"),
        "xg_away": row.get("xg_away"),
        "most_likely_score": row.get("most_likely_score"),
        "quick_summary": row.get("quick_summary"),
        "recalculated_from_form": row.get("recalculated_from_form"),
        "data_source": row.get("data_source"),
        "llm_usage": row.get("llm_usage"),
        "analysis_recap": recap,
    }
    return {**row, "result": result}


def _fetch_history_prediction_rows(supabase, *, user_id: str | None = None, limit: int) -> list[dict]:
    query = (
        supabase.table("analysis_history")
        .select(_ADMIN_HISTORY_SELECT)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if user_id:
        query = query.eq("user_id", user_id)
    r = query.execute()
    return [row for row in (r.data or []) if isinstance(row, dict)]


def _prediction_summary(row: dict) -> dict:
    """Compact prediction card for the admin dashboard (no full analysis blob)."""
    row = _history_row_for_card(row)
    result = row.get("result") if isinstance(row.get("result"), dict) else {}
    mls = result.get("most_likely_score") if isinstance(result.get("most_likely_score"), dict) else {}
    home = (row.get("home_team") or result.get("home_team") or "").strip() or None
    away = (row.get("away_team") or result.get("away_team") or "").strip() or None
    score = None
    if mls.get("home") is not None and mls.get("away") is not None:
        score = f"{mls.get('home')}-{mls.get('away')}"
    cost_eur, cost_estimated = cost_from_result(result)
    recap = result.get("analysis_recap") if isinstance(result.get("analysis_recap"), dict) else {}
    placeholder_form = bool(recap.get("placeholder_form"))
    if recap.get("recalculated_from_form") or result.get("recalculated_from_form"):
        placeholder_form = False
    elif not placeholder_form:
        steps_blob = " ".join(
            str(s.get("detail") or "") for s in (recap.get("pipeline_steps") or []) if isinstance(s, dict)
        )
        if "goals_for=[1, 2, 1, 0, 2]" in steps_blob and "goals_for=[0, 1, 1, 2, 0]" in steps_blob:
            placeholder_form = True
        else:
            try:
                if (
                    round(float(result.get("xg_home")), 2) == 1.07
                    and round(float(result.get("xg_away")), 2) == 0.59
                    and round(float(result.get("prob_home")), 1) == 46.7
                ):
                    placeholder_form = True
            except (TypeError, ValueError):
                pass
    return {
        "id": row.get("id"),
        "user_id": row.get("user_id"),
        "created_at": row.get("created_at"),
        "home_team": home,
        "away_team": away,
        "league": row.get("league") or result.get("league"),
        "home_logo": row.get("home_logo") or result.get("home_team_logo"),
        "away_logo": row.get("away_logo") or result.get("away_team_logo"),
        "prob_home": result.get("internal_prob_home")
        if result.get("internal_prob_home") is not None
        else result.get("prob_home"),
        "prob_draw": result.get("internal_prob_draw")
        if result.get("internal_prob_draw") is not None
        else result.get("prob_draw"),
        "prob_away": result.get("internal_prob_away")
        if result.get("internal_prob_away") is not None
        else result.get("prob_away"),
        "most_likely_score": score,
        "most_likely_score_pct": mls.get("probability"),
        "quick_summary": result.get("quick_summary"),
        "source": row.get("source") or "history",
        "cost_eur": cost_eur,
        "cost_estimated": cost_estimated,
        "data_source": recap.get("data_source") or result.get("data_source"),
        "placeholder_form": placeholder_form,
        "xg_home": result.get("xg_home"),
        "xg_away": result.get("xg_away"),
    }


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


@router.get("/admin/session")
def admin_session(
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    x_user_email: str | None = Header(None, alias="X-User-Email"),
):
    uid = (x_user_id or "").strip()
    email = _email_for_user_id(uid)
    if not is_dashboard_admin_email(email) and uid and is_dashboard_admin_email(x_user_email):
        email = (x_user_email or "").strip()
    return {"admin": is_dashboard_admin_email(email), "email": email}


@router.get("/admin/summary")
def admin_summary(
    days: int = 30,
    q: str | None = None,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    x_user_email: str | None = Header(None, alias="X-User-Email"),
):
    _check_dashboard_admin(x_user_id, x_user_email)
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

    # Evénements analyses (historique pour agrégations) — all-time, then window in Python
    events_rows = []
    try:
        from datetime import datetime, timezone, timedelta

        r_ev = (
            supabase.table("analysis_events")
            .select("created_at, user_id, home_team, away_team")
            .order("created_at", desc=True)
            .limit(50000)
            .execute()
        )
        events_rows = r_ev.data or []
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    except Exception:
        events_rows = []
        since = ""

    history_counts: dict[str, int] = {}
    try:
        r_hist = supabase.table("analysis_history").select("user_id").limit(20000).execute()
        for hrow in r_hist.data or []:
            if not isinstance(hrow, dict):
                continue
            hid = str(hrow.get("user_id") or "").strip()
            if hid:
                history_counts[hid] = history_counts.get(hid, 0) + 1
    except Exception:
        history_counts = {}

    # Agrégations
    per_user: dict[str, dict] = {}
    match_counts: dict[str, int] = {}
    for ev in events_rows:
        if not isinstance(ev, dict):
            continue
        uid = (ev.get("user_id") or "").strip() or "anonymous"
        row = per_user.setdefault(uid, {"user_id": uid, "analyses_window": 0, "analyses_all_time": 0, "matches": []})
        row["analyses_all_time"] += 1
        created = str(ev.get("created_at") or "")
        if not since or created >= since:
            row["analyses_window"] += 1
        h = (ev.get("home_team") or "").strip()
        a = (ev.get("away_team") or "").strip()
        if h and a:
            m = f"{h} vs {a}"
            row["matches"].append(m)
            match_counts[m] = match_counts.get(m, 0) + 1

    profile_map = {str((p or {}).get("id") or ""): p for p in profiles_rows if isinstance(p, dict)}
    users = []
    all_uids = set(per_user.keys()) | set(profile_map.keys()) | set(history_counts.keys())
    for uid in all_uids:
        if not uid or uid == "anonymous":
            continue
        p = profile_map.get(uid) or {}
        r = per_user.get(uid) or {}
        from_profile = int(p.get("analyses_total") or 0)
        from_events = int(r.get("analyses_all_time") or 0)
        from_history = int(history_counts.get(uid) or 0)
        users.append(
            {
                "user_id": uid,
                "plan": (p.get("plan") or "free"),
                "analyses_today": int(p.get("analyses_used_today") or 0),
                "analyses_total": max(from_profile, from_events, from_history),
                "analyses_last_days": int(r.get("analyses_window") or 0),
                "last_analysis_date": p.get("last_analysis_date"),
                "recent_matches": (r.get("matches") or [])[:12],
            }
        )
    if "anonymous" in per_user:
        r = per_user["anonymous"]
        users.append(
            {
                "user_id": "anonymous",
                "plan": "free",
                "analyses_today": 0,
                "analyses_total": int(r.get("analyses_all_time") or 0),
                "analyses_last_days": int(r.get("analyses_window") or 0),
                "last_analysis_date": None,
                "recent_matches": (r.get("matches") or [])[:12],
            }
        )

    unit_cost = estimated_cost_eur()
    plan_counts = {"starter": 0, "pro": 0, "lifetime": 0, "free": 0}
    for u in users:
        total = int(u.get("analyses_total") or 0)
        window_n = int(u.get("analyses_last_days") or 0)
        u["cost_eur"] = round(total * unit_cost, 4)
        u["cost_last_days_eur"] = round(window_n * unit_cost, 4)
        u["revenue_eur"] = revenue_for_plan(u.get("plan"))
        if u.get("user_id") == "anonymous":
            continue
        plan = str(u.get("plan") or "free").strip().lower()
        if plan not in plan_counts:
            plan = "free"
        plan_counts[plan] += 1

    users.sort(key=lambda x: (x.get("analyses_total") or 0), reverse=True)
    top_matches = sorted(
        [{"match": k, "count": v} for k, v in match_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:30]

    # Resolve Supabase Auth email for each user_id (Users analytics = emails instead of UIDs)
    uid_to_email: dict[str, str] = _fetch_auth_emails_via_http()
    admin_client = get_supabase_admin()
    if not uid_to_email and admin_client:
        try:
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
            pass

    fallback_count = 0
    for u in users:
        uid = u.get("user_id")
        u["email"] = uid_to_email.get(uid)
        if not u["email"] and uid and admin_client and uid != "anonymous" and fallback_count < 200:
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

    predictions_all_time = sum(int(u.get("analyses_total") or 0) for u in users)
    predictions_window = sum(int(u.get("analyses_last_days") or 0) for u in users)
    economics = economics_payload(
        predictions_all_time=predictions_all_time,
        predictions_window=predictions_window,
        window_days=days,
        plan_counts=plan_counts,
    )

    q_norm = (q or "").strip().lower()
    if q_norm:
        users = [
            u
            for u in users
            if q_norm in (u.get("email") or "").lower()
            or q_norm in (u.get("plan") or "").lower()
            or q_norm in (u.get("user_id") or "").lower()
            or any(q_norm in (m or "").lower() for m in (u.get("recent_matches") or []))
        ]

    return {
        "window_days": days,
        "feedback_count": len(feedback_rows),
        "feedback": feedback_rows[:200],
        "users_count": len(users),
        "users": users[:500],
        "top_requested_matches": top_matches,
        "economics": economics,
    }


@router.get("/admin/predictions")
def admin_recent_predictions(
    limit: int = 200,
    q: str | None = None,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    x_user_email: str | None = Header(None, alias="X-User-Email"),
):
    """Latest predictions across all users for the admin console."""
    _check_dashboard_admin(x_user_id, x_user_email)
    limit = max(1, min(int(limit or 200), 400))
    supabase = get_supabase_admin() or get_supabase()
    rows: list[dict] = []
    try:
        rows = _fetch_history_prediction_rows(supabase, limit=limit)
    except Exception as exc:
        print(f"[admin] compact history fetch failed: {exc}")
        try:
            r = (
                supabase.table("analysis_history")
                .select("id, created_at, user_id, home_team, away_team, home_logo, away_logo, league, result")
                .order("created_at", desc=True)
                .limit(min(limit, 80))
                .execute()
            )
            rows = [row for row in (r.data or []) if isinstance(row, dict)]
        except Exception as exc2:
            print(f"[admin] full history fetch failed: {exc2}")
            rows = []
    uid_to_email = _fetch_auth_emails_via_http()
    q_norm = (q or "").strip().lower()
    predictions: list[dict] = []
    for row in rows:
        try:
            card = _prediction_summary({**row, "source": "history"})
        except Exception as exc:
            print(f"[admin] skip prediction card {row.get('id')}: {exc}")
            continue
        uid = str(row.get("user_id") or "").strip()
        card["email"] = uid_to_email.get(uid)
        if q_norm:
            hay = " ".join(
                [
                    str(card.get("email") or ""),
                    str(card.get("home_team") or ""),
                    str(card.get("away_team") or ""),
                    str(card.get("league") or ""),
                    uid,
                ]
            ).lower()
            if q_norm not in hay:
                continue
        predictions.append(card)
    return {"predictions_count": len(predictions), "predictions": predictions}


def _plan_view_for_user(supabase, user_id: str | None) -> tuple[str, bool]:
    """Current subscription plan and whether that plan sees the full analysis."""
    uid = (user_id or "").strip()
    plan = "free"
    if uid and uid != "anonymous" and supabase:
        try:
            pr = supabase.table("profiles").select("plan").eq("id", uid).limit(1).execute()
            if pr.data:
                plan = _normalize_plan(str((pr.data[0] or {}).get("plan") or "free"))
        except Exception:
            plan = "free"
    _, full = get_analysis_limit(plan)
    return plan, full


@router.get("/admin/predictions/{prediction_id}")
def admin_prediction_detail(
    prediction_id: str,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    x_user_email: str | None = Header(None, alias="X-User-Email"),
):
    """Full stored analysis, rendered as that user's current plan (free = blurred)."""
    _check_dashboard_admin(x_user_id, x_user_email)
    pid = (prediction_id or "").strip()
    if not pid:
        raise HTTPException(status_code=400, detail="prediction_id required")
    supabase = get_supabase_admin() or get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        r = supabase.table("analysis_history").select("*").eq("id", pid).limit(1).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Could not load prediction") from exc
    if not r.data:
        raise HTTPException(status_code=404, detail="Prediction not found")
    row = r.data[0] if isinstance(r.data[0], dict) else {}
    result = row.get("result") if isinstance(row.get("result"), dict) else {}
    uid = str(row.get("user_id") or "").strip() or None
    plan, full = _plan_view_for_user(supabase, uid)
    out = {
        **result,
        "home_team": row.get("home_team") or result.get("home_team"),
        "away_team": row.get("away_team") or result.get("away_team"),
        "league": row.get("league") or result.get("league"),
        "home_team_logo": row.get("home_logo") or result.get("home_team_logo"),
        "away_team_logo": row.get("away_logo") or result.get("away_team_logo"),
        "full_analysis": full,
    }
    return {
        "id": row.get("id"),
        "user_id": uid,
        "email": _email_for_user_id(uid) if uid else None,
        "plan": plan,
        "full_analysis": full,
        "created_at": row.get("created_at"),
        "result": out,
    }


@router.get("/admin/users/{user_id}/predictions")
def admin_user_predictions(
    user_id: str,
    limit: int = 100,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    x_user_email: str | None = Header(None, alias="X-User-Email"),
):
    """All saved predictions for one user (history first, events as fallback)."""
    _check_dashboard_admin(x_user_id, x_user_email)
    uid = (user_id or "").strip()
    if not uid or uid == "anonymous":
        raise HTTPException(status_code=400, detail="user_id required")
    limit = max(1, min(int(limit or 100), 300))
    supabase = get_supabase_admin() or get_supabase()
    predictions: list[dict] = []
    try:
        for row in _fetch_history_prediction_rows(supabase, user_id=uid, limit=limit):
            try:
                predictions.append(_prediction_summary({**row, "source": "history"}))
            except Exception as exc:
                print(f"[admin] skip user prediction card {row.get('id')}: {exc}")
    except Exception as exc:
        print(f"[admin] user history fetch failed: {exc}")
        predictions = []

    seen_keys = {
        f"{(p.get('created_at') or '')[:19]}|{(p.get('home_team') or '').lower()}|{(p.get('away_team') or '').lower()}"
        for p in predictions
    }
    if len(predictions) < limit:
        try:
            r_ev = (
                supabase.table("analysis_events")
                .select("id, created_at, user_id, home_team, away_team")
                .eq("user_id", uid)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            for row in r_ev.data or []:
                if not isinstance(row, dict):
                    continue
                key = f"{str(row.get('created_at') or '')[:19]}|{(row.get('home_team') or '').lower()}|{(row.get('away_team') or '').lower()}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                predictions.append(_prediction_summary({**row, "source": "event", "result": {}}))
                if len(predictions) >= limit:
                    break
        except Exception:
            pass

    predictions.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    email = _email_for_user_id(uid)
    plan = "free"
    analyses_total = len(predictions)
    try:
        pr = supabase.table("profiles").select("plan, analyses_total").eq("id", uid).limit(1).execute()
        if pr.data:
            plan = (pr.data[0] or {}).get("plan") or "free"
            analyses_total = max(int((pr.data[0] or {}).get("analyses_total") or 0), len(predictions))
    except Exception:
        pass
    try:
        ev = supabase.table("analysis_events").select("id").eq("user_id", uid).limit(20000).execute()
        analyses_total = max(analyses_total, len(ev.data or []))
    except Exception:
        pass
    return {
        "user_id": uid,
        "email": email,
        "plan": plan,
        "predictions_count": analyses_total,
        "predictions": predictions[:limit],
    }
