# backend/app/services/fetch_match_data.py
"""
Récupère toutes les données nécessaires pour une analyse de match (équipes, derniers matchs,
H2H, classement), les stocke dans Supabase et applique un cache 24h pour minimiser les appels API.
Entrée: home_team_name, away_team_name, league_id.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from app.core.config import get_settings
from app.core.leagues import current_season
from app.services import api_football

CACHE_HOURS = 24


def _use_api() -> bool:
    return bool(get_settings().api_football_key)


def _use_supabase() -> bool:
    s = get_settings()
    return bool(s.supabase_url and s.supabase_key)


def _cache_cutoff() -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=CACHE_HOURS)


def _is_fresh(row: dict, key: str = "last_updated") -> bool:
    val = row.get(key)
    if not val:
        return False
    if isinstance(val, datetime):
        return val >= _cache_cutoff()
    try:
        s = val.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(s)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed >= _cache_cutoff()
    except Exception:
        return False


def _ensure_teams(
    supabase: Any,
    home_id: int,
    away_id: int,
    force_refresh: bool = False,
) -> None:
    """Met à jour les lignes teams pour les deux équipes si absentes ou > 24h."""
    if not _use_api():
        return
    now = datetime.now(timezone.utc).isoformat()
    for team_id in (home_id, away_id):
        slug = str(team_id)
        if not force_refresh and _use_supabase():
            r = supabase.table("teams").select("slug, last_updated").eq("slug", slug).execute()
            if r.data and _is_fresh(r.data[0]):
                continue
        info = api_football.get_team_by_id(team_id)
        if not info:
            continue
        row = {
            "name": (info.get("name") or "").strip() or slug,
            "slug": slug,
            "logo_url": info.get("logo"),
            "stadium": info.get("stadium"),
            "last_updated": now,
        }
        supabase.table("teams").upsert([row], on_conflict="slug").execute()


def _upsert_results(supabase: Any, fixtures: list[dict]) -> None:
    """Insère les matchs dans results (évite doublons par home_team_id, away_team_id, date)."""
    for f in fixtures:
        row = api_football.fixture_for_ingest(f)
        if not row:
            continue
        hid, aid, hname, aname, hg, ag, date_str, league = row
        utc_date = date_str
        existing = (
            supabase.table("results")
            .select("id")
            .eq("home_team_id", hid)
            .eq("away_team_id", aid)
            .eq("date", utc_date)
            .execute()
        )
        if existing.data:
            continue
        supabase.table("results").insert(
            {
                "home_team_id": hid,
                "away_team_id": aid,
                "home_goals": hg,
                "away_goals": ag,
                "date": utc_date,
                "league": league or None,
            }
        ).execute()


def _ensure_h2h(
    supabase: Any,
    home_id: int,
    away_id: int,
    force_refresh: bool = False,
) -> tuple[int, int, int]:
    """Met à jour H2H si absent ou > 24h. Retourne (home_wins, draws, away_wins)."""
    hid_s, aid_s = str(home_id), str(away_id)
    if _use_supabase() and not force_refresh:
        r = (
            supabase.table("h2h")
            .select("home_wins, draws, away_wins, last_updated")
            .eq("home_team_id", hid_s)
            .eq("away_team_id", aid_s)
            .execute()
        )
        if r.data and _is_fresh(r.data[0]):
            row = r.data[0]
            return (int(row.get("home_wins", 0)), int(row.get("draws", 0)), int(row.get("away_wins", 0)))
    if not _use_api():
        return (0, 0, 0)
    fixtures = api_football.get_fixtures_headtohead_multi_season(home_id, away_id, ideal_seasons=5, max_seasons=5)
    h_wins, d, a_wins = api_football.get_h2h_from_fixtures(home_id, away_id, fixtures)
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("h2h").upsert(
        {
            "home_team_id": hid_s,
            "away_team_id": aid_s,
            "home_wins": h_wins,
            "draws": d,
            "away_wins": a_wins,
            "last_updated": now,
        },
        on_conflict="home_team_id,away_team_id",
    ).execute()
    return (h_wins, d, a_wins)


def _ensure_standings(
    supabase: Any,
    league_id: int,
    season: Optional[int] = None,
    force_refresh: bool = False,
) -> list[dict]:
    """Met à jour le classement si absent ou > 24h. Retourne la liste des lignes (position, team, points, etc.)."""
    season = season or current_season()
    if _use_supabase() and not force_refresh:
        r = (
            supabase.table("standings")
            .select("data, last_updated")
            .eq("league_id", league_id)
            .eq("season", season)
            .execute()
        )
        if r.data and _is_fresh(r.data[0]):
            return r.data[0].get("data") or []
    if not _use_api():
        return []
    rows = api_football.get_standings(league_id, season)
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("standings").upsert(
        {
            "league_id": league_id,
            "season": season,
            "data": rows,
            "last_updated": now,
        },
        on_conflict="league_id,season",
    ).execute()
    return rows


def fetch_and_store(
    home_team_name: str,
    away_team_name: str,
    league_id: int,
    *,
    season: Optional[int] = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """
    Récupère et stocke en base toutes les données pour l'analyse du match.
    Réutilise le cache Supabase si < 24h.
    Retourne un dict avec: home_team_id, away_team_id, teams (infos), last_5_home, last_5_away,
    h2h (home_wins, draws, away_wins), standings (liste).
    """
    if not _use_api():
        return {
            "home_team_id": None,
            "away_team_id": None,
            "teams": {},
            "last_5_home": [],
            "last_5_away": [],
            "h2h": (0, 0, 0),
            "standings": [],
            "error": "API-Football non configurée",
        }
    home_id = api_football.resolve_team_name_to_id(home_team_name)
    away_id = api_football.resolve_team_name_to_id(away_team_name)
    if not home_id or not away_id:
        return {
            "home_team_id": home_id,
            "away_team_id": away_id,
            "teams": {},
            "last_5_home": [],
            "last_5_away": [],
            "h2h": (0, 0, 0),
            "standings": [],
            "error": "Équipe(s) introuvable(s)",
        }
    season = season or current_season()
    supabase = None
    if _use_supabase():
        from app.core.supabase_client import get_supabase
        supabase = get_supabase()

    if supabase:
        _ensure_teams(supabase, home_id, away_id, force_refresh=force_refresh)

    last_5_home = api_football.get_team_fixtures(home_id, season=season, last_n=5)
    last_5_away = api_football.get_team_fixtures(away_id, season=season, last_n=5)
    if supabase:
        _upsert_results(supabase, last_5_home)
        _upsert_results(supabase, last_5_away)

    h2h_tuple = (0, 0, 0)
    if supabase:
        h2h_tuple = _ensure_h2h(supabase, home_id, away_id, force_refresh=force_refresh)
    else:
        if _use_api():
            fixtures = api_football.get_fixtures_headtohead_multi_season(home_id, away_id, ideal_seasons=5, max_seasons=5)
            h2h_tuple = api_football.get_h2h_from_fixtures(home_id, away_id, fixtures)

    standings_list: list[dict] = []
    if supabase:
        standings_list = _ensure_standings(supabase, league_id, season, force_refresh=force_refresh)
    else:
        if _use_api():
            standings_list = api_football.get_standings(league_id, season)

    teams_info: dict[str, dict] = {}
    if supabase:
        r = supabase.table("teams").select("slug, name, logo_url, stadium").in_("slug", [str(home_id), str(away_id)]).execute()
        for row in r.data or []:
            slug = row.get("slug")
            if slug == str(home_id):
                teams_info["home"] = {"id": home_id, "name": row.get("name") or "", "logo": row.get("logo_url"), "stadium": row.get("stadium")}
            elif slug == str(away_id):
                teams_info["away"] = {"id": away_id, "name": row.get("name") or "", "logo": row.get("logo_url"), "stadium": row.get("stadium")}
    for label, tid in [("home", home_id), ("away", away_id)]:
        if label not in teams_info:
            t = api_football.get_team_by_id(tid) if _use_api() else None
            teams_info[label] = t or {"id": tid, "name": "", "logo": None, "stadium": None}

    return {
        "home_team_id": home_id,
        "away_team_id": away_id,
        "teams": teams_info,
        "last_5_home": last_5_home,
        "last_5_away": last_5_away,
        "h2h": h2h_tuple,
        "standings": standings_list,
        "season": season,
        "league_id": league_id,
    }
