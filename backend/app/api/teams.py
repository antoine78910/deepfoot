# backend/app/api/teams.py
from fastapi import APIRouter
from typing import Optional

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("")
def list_teams(q: Optional[str] = None, limit: int = 20):
    """
    Liste des équipes pour autocomplete (avec id, name, crest pour les logos).
    Priorité: football-data.org (v4) sur toutes les ligues → Supabase → démo.
    """
    from app.services.football_data import _use_api, get_teams_for_autocomplete
    from app.core.leagues import LEAGUES

    if _use_api():
        teams = get_teams_for_autocomplete(q=q, limit=limit)
        return {"teams": teams, "leagues": LEAGUES}

    from app.core.config import get_settings
    s = get_settings()
    if not (s.supabase_url and s.supabase_key):
        demo = ["Lorient", "Auxerre", "Paris SG", "Marseille", "Lyon", "Lille", "Monaco", "Rennes", "Nice", "Lens"]
        if q:
            ql = q.strip().lower()
            demo = [t for t in demo if ql in t.lower()][:limit]
        return {"teams": [{"id": None, "name": n, "crest": None} for n in demo], "leagues": []}
    from app.core.supabase_client import get_supabase
    supabase = get_supabase()
    r = supabase.table("teams").select("id, name, slug").ilike("name", f"%{q or ''}%").limit(limit).execute()
    return {
        "teams": [{"id": x.get("slug"), "name": x.get("name") or x.get("slug"), "crest": None} for x in (r.data or [])],
        "leagues": [],
    }


@router.get("/leagues")
def list_leagues():
    """Liste des ligues supportées (code + nom)."""
    from app.core.leagues import LEAGUES
    return {"leagues": LEAGUES}
