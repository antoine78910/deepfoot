"""
Routes pour les compétitions : classement, matchs récents, équipes.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/competitions", tags=["competitions"])


def _season_year(season: Optional[int]) -> int:
    from app.core.leagues import current_season
    return season or current_season()


@router.get("/{league_id}/standings")
def league_standings(league_id: int, season: Optional[int] = None):
    """Classement d'une ligue/saison."""
    from app.services.api_football import _use_api, get_standings
    if not _use_api():
        return {"standings": []}
    s = _season_year(season)
    rows = get_standings(league_id, season=s)
    return {"standings": rows, "season": s}


@router.get("/{league_id}/fixtures")
def league_fixtures(
    league_id: int,
    season: Optional[int] = None,
    status: str = "FT",
    limit: int = 20,
):
    """Matchs d'une ligue (FT = terminés). Récent en premier."""
    from app.services.api_football import _use_api, get_fixtures_by_league
    if not _use_api():
        return {"fixtures": []}
    s = _season_year(season)
    raw = get_fixtures_by_league(league_id, season=s, status=status)
    raw.sort(key=lambda x: (x.get("fixture") or {}).get("date") or "", reverse=True)
    fixtures = []
    for f in raw[:limit]:
        fix = f.get("fixture") or {}
        teams = f.get("teams") or {}
        goals = f.get("goals") or {}
        home = teams.get("home") or {}
        away = teams.get("away") or {}
        date_str = (fix.get("date") or "")[:10]
        fixtures.append({
            "date": date_str,
            "time": (fix.get("date") or "")[11:16] if len(fix.get("date") or "") >= 16 else "",
            "home_team": home.get("name") or "",
            "away_team": away.get("name") or "",
            "home_logo": (home.get("logo") or "").strip() or None,
            "away_logo": (away.get("logo") or "").strip() or None,
            "home_goals": goals.get("home") if goals.get("home") is not None else None,
            "away_goals": goals.get("away") if goals.get("away") is not None else None,
        })
    return {"fixtures": fixtures, "season": s}


@router.get("/{league_id}/teams")
def league_teams(league_id: int, season: Optional[int] = None):
    """Liste des équipes d'une ligue/saison."""
    from app.services.api_football import _use_api, get_teams_by_league
    if not _use_api():
        return {"teams": []}
    s = _season_year(season)
    raw = get_teams_by_league(league_id, season=s)
    teams = []
    for item in raw:
        t = item.get("team") or item
        tid = t.get("id")
        name = (t.get("name") or "").strip()
        logo = (t.get("logo") or "").strip() or None
        if tid is not None and name:
            teams.append({"id": tid, "name": name, "logo": logo})
    return {"teams": teams, "season": s}
