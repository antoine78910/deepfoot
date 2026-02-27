# backend/app/api/teams.py
from fastapi import APIRouter
from typing import Optional

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("")
def list_teams(q: Optional[str] = None, limit: int = 80):
    """
    Liste des équipes pour autocomplete (id, name, crest).
    Priorité: Supabase (recherche rapide avec alias) → API-Football → démo.
    Pour une recherche instantanée, lancer une fois: python scripts/sync_teams_to_supabase.py
    """
    from app.services.api_football import get_teams_from_supabase, _use_api, get_teams_for_autocomplete
    from app.core.leagues import LEAGUES

    q_clean = (q or "").strip()

    # 1) Supabase en premier : pas d'appel API, recherche + alias + blasons
    teams_sb = get_teams_from_supabase(q=q, limit=limit)
    # Si Supabase est configuré, on renvoie directement sa réponse (même vide)
    # pour éviter la latence API et garder un comportement strict/prévisible.
    if teams_sb is not None:
        return {"teams": teams_sb, "leagues": LEAGUES}

    # 2) Pas de Supabase disponible: fallback API/caches
    if _use_api():
        teams = get_teams_for_autocomplete(q=q, limit=limit)
        return {"teams": teams, "leagues": LEAGUES}

    from app.core.config import get_settings
    s = get_settings()
    if not (s.supabase_url and s.supabase_key):
        demo = ["Lorient", "Auxerre", "Paris SG", "Marseille", "Lyon", "Lille", "Monaco", "Rennes", "Nice", "Lens"]
        if q_clean:
            ql = q_clean.lower()
            demo = [t for t in demo if t.lower().startswith(ql) or any(w.startswith(ql) for w in t.lower().split())][:limit]
        return {"teams": [{"id": None, "name": n, "crest": None} for n in demo], "leagues": []}
    from app.core.supabase_client import get_supabase
    supabase = get_supabase()
    r = supabase.table("teams").select("slug, name, logo_url, country").ilike("name", f"{q_clean}%").limit(limit).execute()
    return {
        "teams": [
            {
                "id": x.get("slug"),
                "name": x.get("name") or x.get("slug"),
                "crest": x.get("logo_url"),
                "country": (x.get("country") or "").strip() or None,
            }
            for x in (r.data or [])
            if x.get("logo_url")
        ],
        "leagues": LEAGUES,
    }


def _resolve_team_id_fast(team_name: str):
    """Résout le nom en ID sans remplir le cache (Supabase d'abord, puis API resolve)."""
    from app.core.config import get_settings
    s = get_settings()
    if s.supabase_url and s.supabase_key and (team_name or "").strip():
        try:
            from app.core.supabase_client import get_supabase
            supabase = get_supabase()
            name = team_name.strip()
            r = supabase.table("teams").select("slug").ilike("search_terms", f"%{name}%").limit(1).execute()
            if r.data and len(r.data) > 0:
                slug = r.data[0].get("slug")
                if slug is not None:
                    try:
                        return int(slug)
                    except (ValueError, TypeError):
                        return None
        except Exception:
            pass
    from app.services.api_football import resolve_team_name_to_id
    return resolve_team_name_to_id(team_name)


@router.get("/upcoming")
def upcoming_fixtures(team: Optional[str] = None, team_id: Optional[int] = None, limit: int = 10):
    """Prochains matchs de l'équipe. Donner team_id (depuis l'autocomplete) pour un chargement rapide ; sinon team (nom)."""
    from app.services.api_football import _use_api, get_team_upcoming_fixtures

    if not _use_api():
        return {"fixtures": []}
    tid = team_id
    if tid is None and (team or "").strip():
        tid = _resolve_team_id_fast(team.strip())
    if not tid:
        return {"fixtures": []}
    raw = get_team_upcoming_fixtures(int(tid), next_n=limit)
    fixtures = []
    for f in raw:
        fix = f.get("fixture") or {}
        teams = f.get("teams") or {}
        home = teams.get("home") or {}
        away = teams.get("away") or {}
        date_str = (fix.get("date") or "")[:19]
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else None
        except Exception:
            dt = None
        day = dt.strftime("%d/%m") if dt else ""
        time = dt.strftime("%H:%M") if dt else ""
        fixtures.append({
            "date": day,
            "time": time,
            "home": {"name": home.get("name") or "", "logo": home.get("logo") or None},
            "away": {"name": away.get("name") or "", "logo": away.get("logo") or None},
        })
    return {"fixtures": fixtures}
