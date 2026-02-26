# backend/app/services/football_data.py
"""
Client pour l'API football-data.org (v4).
Documentation: https://www.football-data.org/documentation/quickstart
Une requête GET https://api.football-data.org/v4/matches suffit pour récupérer les matchs du jour.
"""
from typing import Any, Optional
import httpx
from app.core.config import get_settings
from app.core.leagues import LEAGUE_CODES

# Cache global: équipes de toutes les ligues (id -> {id, name, shortName, crest})
_teams_cache: dict[int, dict] = {}
_teams_cache_filled = False


def _use_api() -> bool:
    return bool(get_settings().football_data_api_token)


def _headers() -> dict[str, str]:
    return {"X-Auth-Token": get_settings().football_data_api_token}


def _url(path: str) -> str:
    base = get_settings().football_data_base_url.rstrip("/")
    return f"{base}{path}" if path.startswith("/") else f"{base}/{path}"


def _get(path: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """GET sur l'API football-data.org. Retourne le JSON ou {} en cas d'erreur."""
    if not _use_api():
        return {}
    with httpx.Client(timeout=15.0) as client:
        r = client.get(_url(path), headers=_headers(), params=params or {})
        r.raise_for_status()
        return r.json() or {}


def get_matches(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: str = "FINISHED",
    limit: int = 100,
) -> list[dict]:
    """
    Liste des matchs. Filtres: dateFrom, dateTo, status.
    Ex: GET /v4/matches?status=FINISHED&limit=50
    """
    params: dict[str, Any] = {"status": status, "limit": limit}
    if date_from:
        params["dateFrom"] = date_from
    if date_to:
        params["dateTo"] = date_to
    data = _get("/matches", params=params)
    matches = data.get("matches")
    if isinstance(matches, list):
        return matches
    return []


def get_competitions() -> list[dict]:
    """Liste des compétitions disponibles."""
    data = _get("/competitions")
    return data.get("competitions", []) if isinstance(data.get("competitions"), list) else []


def get_competition_teams(competition_code_or_id: str | int) -> list[dict]:
    """
    Équipes d'une compétition (ex: FL1 pour Ligue 1).
    Retourne une liste de {id, name, shortName, tla, crest, ...}.
    """
    data = _get(f"/competitions/{competition_code_or_id}/teams")
    return data.get("teams", []) if isinstance(data.get("teams"), list) else []


def _fill_teams_cache() -> None:
    """Remplit le cache avec les équipes de toutes les ligues configurées."""
    global _teams_cache, _teams_cache_filled
    if _teams_cache_filled or not _use_api():
        return
    for code in LEAGUE_CODES:
        try:
            teams = get_competition_teams(code)
            for t in teams:
                tid = t.get("id")
                if tid is not None and isinstance(tid, int):
                    _teams_cache[tid] = {
                        "id": tid,
                        "name": (t.get("name") or "").strip(),
                        "shortName": (t.get("shortName") or "").strip(),
                        "crest": (t.get("crest") or "").strip() or None,
                    }
        except Exception:
            continue
    _teams_cache_filled = True


def get_teams_for_autocomplete(q: Optional[str] = None, limit: int = 20) -> list[dict]:
    """
    Liste d'équipes pour l'autocomplete, avec logo (crest).
    Retourne [{ id, name, crest }, ...]. Recherche dans toutes les ligues.
    """
    _fill_teams_cache()
    teams_list = list(_teams_cache.values())
    teams_list = [t for t in teams_list if t.get("name")]
    if q and q.strip():
        ql = q.strip().lower()
        teams_list = [
            t for t in teams_list
            if ql in (t.get("name") or "").lower() or ql in (t.get("shortName") or "").lower()
        ]
    result = []
    seen_names: set[str] = set()
    for t in teams_list[: limit * 2]:
        name = t.get("name") or t.get("shortName") or ""
        if name in seen_names:
            continue
        seen_names.add(name)
        result.append({
            "id": t.get("id"),
            "name": name,
            "crest": t.get("crest"),
        })
        if len(result) >= limit:
            break
    return result


def get_team_matches(
    team_id: int,
    status: str = "FINISHED",
    limit: int = 10,
    venue: Optional[str] = None,
) -> list[dict]:
    """
    Derniers matchs d'une équipe. status=FINISHED pour avoir les scores.
    Chaque match a homeTeam, awayTeam, score.fullTime.homeTeam, score.fullTime.awayTeam.
    """
    params: dict[str, Any] = {"status": status, "limit": limit}
    if venue:
        params["venue"] = venue
    data = _get(f"/teams/{team_id}/matches", params=params)
    return data.get("matches", []) if isinstance(data.get("matches"), list) else []


def get_match(match_id: int) -> dict:
    """Un match par ID (détails complets, head2head si dispo)."""
    return _get(f"/matches/{match_id}")


def resolve_team_name_to_id(team_name: str, competition_code: Optional[str] = None) -> Optional[int]:
    """
    Résout un nom d'équipe (ex: "Lorient", "AJA") en ID football-data.org
    en cherchant dans les équipes de toutes les ligues configurées (ou une seule si competition_code fourni).
    """
    if not _use_api() or not team_name or not team_name.strip():
        return None
    name_lower = team_name.strip().lower()
    if competition_code:
        teams = get_competition_teams(competition_code)
        for t in teams:
            n = (t.get("name") or "").strip().lower()
            sn = (t.get("shortName") or "").strip().lower()
            if name_lower in n or name_lower in sn or n in name_lower or sn in name_lower:
                return int(t["id"]) if t.get("id") is not None else None
        return None
    _fill_teams_cache()
    for t in _teams_cache.values():
        n = (t.get("name") or "").strip().lower()
        sn = (t.get("shortName") or "").strip().lower()
        if name_lower == n or name_lower == sn or name_lower in n or name_lower in sn or n in name_lower or sn in name_lower:
            return int(t["id"]) if t.get("id") is not None else None
    return None


def team_matches_to_goals_and_form(
    team_id: int,
    matches: list[dict],
    last_n: int = 5,
) -> tuple[list[int], list[int], list[str]]:
    """
    À partir de la liste de matchs d'une équipe (déjà FINISHED),
    retourne (goals_for_list, goals_against_list, form_list ['W'|'D'|'L']).
    """
    goals_for: list[int] = []
    goals_against: list[int] = []
    form: list[str] = []
    for m in matches[:last_n]:
        score = m.get("score") or {}
        ft = score.get("fullTime") or {}
        ht = int(ft.get("homeTeam") if ft.get("homeTeam") is not None else 0)
        at = int(ft.get("awayTeam") if ft.get("awayTeam") is not None else 0)
        home = m.get("homeTeam") or {}
        away = m.get("awayTeam") or {}
        home_id = home.get("id")
        is_home = home_id == team_id
        if is_home:
            goals_for.append(ht)
            goals_against.append(at)
            form.append("W" if ht > at else ("D" if ht == at else "L"))
        else:
            goals_for.append(at)
            goals_against.append(ht)
            form.append("W" if at > ht else ("D" if at == ht else "L"))
    return (goals_for, goals_against, form)


def get_h2h_from_matches(
    home_team_id: int,
    away_team_id: int,
    matches: list[dict],
) -> tuple[int, int, int]:
    """
    Calcule H2H (home_wins, draws, away_wins) à partir d'une liste de matchs
    où les deux équipes ont joué (ex: matchs d'une équipe filtrés par adversaire).
    """
    h_wins = d = a_wins = 0
    pair = {home_team_id, away_team_id}
    for m in matches:
        home = (m.get("homeTeam") or {}).get("id")
        away = (m.get("awayTeam") or {}).get("id")
        if not home or not away or {home, away} != pair:
            continue
        score = m.get("score") or {}
        ft = score.get("fullTime") or {}
        ht = int(ft.get("homeTeam") if ft.get("homeTeam") is not None else 0)
        at = int(ft.get("awayTeam") if ft.get("awayTeam") is not None else 0)
        if home == home_team_id:
            if ht > at:
                h_wins += 1
            elif ht < at:
                a_wins += 1
            else:
                d += 1
        else:
            if at > ht:
                h_wins += 1
            elif at < ht:
                a_wins += 1
            else:
                d += 1
    return (h_wins, d, a_wins)
