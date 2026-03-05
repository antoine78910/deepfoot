# backend/app/api/teams.py
from fastapi import APIRouter
from typing import Optional

router = APIRouter(prefix="/teams", tags=["teams"])


def _dedupe_teams_prefer_country(teams: list) -> list:
    """Supprime les doublons (même nom normalisé), garde une seule entrée par équipe en préférant celle avec country."""
    if not teams:
        return teams
    seen: dict[str, dict] = {}
    for t in teams:
        name = (t.get("name") or "").strip()
        key = name.lower()
        if not key:
            continue
        existing = seen.get(key)
        has_country = bool((t.get("country") or "").strip())
        if existing is None:
            seen[key] = t
        elif has_country and not (existing.get("country") or "").strip():
            seen[key] = t
    return list(seen.values())


def _only_teams_with_country(teams: list) -> list:
    """Ne garde que les équipes avec pays (clubs qu'on a bien dans notre base Sportmonks/Supabase)."""
    return [t for t in teams if (t.get("country") or "").strip()]


@router.get("")
def list_teams(q: Optional[str] = None, limit: int = 80):
    """
    Liste des équipes pour autocomplete (id, name, crest).
    Avec Sportmonks: uniquement Supabase (clubs synchronisés) ou API Sportmonks, pas API-Football.
    Doublons supprimés en gardant l'entrée avec country.
    """
    from app.services.sportmonks import _use_sportmonks, get_teams_for_autocomplete_sportmonks
    from app.services.api_football import (
        get_teams_from_supabase,
        get_teams_from_supabase_direct,
        _use_api,
        get_teams_for_autocomplete,
    )
    from app.core.leagues import LEAGUES

    q_clean = (q or "").strip()
    print(f"[teams] GET /teams q={q_clean!r} limit={limit}")

    # 1) Sportmonks configuré : uniquement Supabase (nos clubs) ou API Sportmonks, jamais API-Football
    use_sm = _use_sportmonks()
    print(f"[teams] _use_sportmonks() = {use_sm}")
    if use_sm:
        if q_clean:
            teams_sb = get_teams_from_supabase_direct(q_clean, limit=limit * 2)
            if teams_sb:
                teams_sb = _only_teams_with_country(teams_sb)
                teams_sb = _dedupe_teams_prefer_country(teams_sb)[:limit]
                if teams_sb:
                    print(f"[teams] Supabase direct -> {len(teams_sb)} teams")
                    return {"teams": teams_sb, "leagues": LEAGUES}
        teams_sb = get_teams_from_supabase(q=q, limit=limit * 2, allow_fetch=True)
        sb_count = len(teams_sb) if teams_sb is not None else -1
        print(f"[teams] Supabase cache -> {'ok' if teams_sb else 'None/empty'} (count={sb_count})")
        if teams_sb:
            teams_sb = _only_teams_with_country(teams_sb)
            teams_sb = _dedupe_teams_prefer_country(teams_sb)[:limit]
            if teams_sb:
                return {"teams": teams_sb, "leagues": LEAGUES}
        teams_sm = get_teams_for_autocomplete_sportmonks(q=q, limit=limit)
        if teams_sm:
            teams_sm = _dedupe_teams_prefer_country(teams_sm)[:limit]
            print(f"[teams] Sportmonks API -> {len(teams_sm)} teams")
            return {"teams": teams_sm, "leagues": LEAGUES}
        return {"teams": [], "leagues": LEAGUES}

    print("[teams] Sportmonks inactif -> Supabase / API-Football")
    # 2) Sans Sportmonks : Supabase puis API-Football
    teams_sb = get_teams_from_supabase(q=q, limit=limit)
    if teams_sb is not None:
        if teams_sb:
            teams_sb = _dedupe_teams_prefer_country(teams_sb)[:limit]
            return {"teams": teams_sb, "leagues": LEAGUES}
        if _use_api():
            teams = get_teams_for_autocomplete(q=q, limit=limit)
            teams = _dedupe_teams_prefer_country(teams)[:limit]
            return {"teams": teams, "leagues": LEAGUES}
        return {"teams": [], "leagues": LEAGUES}

    # 3) Fallback API-Football
    if _use_api():
        teams = get_teams_for_autocomplete(q=q, limit=limit)
        teams = _dedupe_teams_prefer_country(teams)[:limit]
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
    from app.services.api_football import _country_allowed_for_suggestions
    supabase = get_supabase()
    r = supabase.table("teams").select("slug, name, logo_url, country").ilike("name", f"{q_clean}%").limit(limit * 2).execute()
    raw = [
        {"id": x.get("slug"), "name": (x.get("name") or x.get("slug")).strip(), "crest": x.get("logo_url"), "country": (x.get("country") or "").strip() or None}
        for x in (r.data or [])
        if x.get("logo_url") and _country_allowed_for_suggestions(x.get("country"))
    ]
    raw = _dedupe_teams_prefer_country(raw)[:limit]
    return {"teams": raw, "leagues": LEAGUES}


def _resolve_team_id_fast(team_name: str):
    """Résout le nom en ID (Supabase). Préfère la ligne dont le nom correspond (ex. Olympique Marseille pas Antalyaspor)."""
    from app.core.config import get_settings
    s = get_settings()
    if s.supabase_url and s.supabase_key and (team_name or "").strip():
        try:
            from app.core.supabase_client import get_supabase
            supabase = get_supabase()
            name = team_name.strip()
            r = supabase.table("teams").select("slug, name, country").ilike("search_terms", f"%{name}%").limit(15).execute()
            rows = list(r.data or [])
            if not rows:
                return None
            name_lower = name.lower()
            name_words = set(name_lower.split())

            def score(row):
                row_name = (row.get("name") or "").strip().lower()
                if not row_name:
                    return (2, 0)
                has_country = 1 if (row.get("country") or "").strip() else 0
                if row_name == name_lower:
                    return (0, has_country)
                if name_lower in row_name or row_name in name_lower:
                    return (1, has_country)
                row_words = set(row_name.split())
                if name_words & row_words:
                    return (2, has_country)
                return (3, has_country)

            rows.sort(key=lambda row: score(row))
            for row in rows:
                slug = row.get("slug")
                if slug is not None:
                    try:
                        return int(slug)
                    except (ValueError, TypeError):
                        pass
        except Exception:
            pass
    from app.services.api_football import resolve_team_name_to_id
    return resolve_team_name_to_id(team_name)


def _format_sportmonks_fixture_for_upcoming(f: dict) -> Optional[dict]:
    """Convertit une fixture Sportmonks (avec participants) vers le format attendu par le front."""
    from app.services.sportmonks import _extract_participants, _team_logo
    from datetime import datetime
    starting_at = f.get("starting_at") or ""
    try:
        dt = datetime.fromisoformat(starting_at.replace("Z", "+00:00")) if starting_at else None
    except Exception:
        dt = None
    day = dt.strftime("%d/%m") if dt else ""
    time = dt.strftime("%H:%M") if dt else ""
    league_obj = f.get("league") or {}
    league_name = (league_obj.get("name") or "").strip() or None if isinstance(league_obj, dict) else None
    home_p, away_p = _extract_participants(f)
    home_name = (home_p.get("name") or "").strip() if home_p else ""
    away_name = (away_p.get("name") or "").strip() if away_p else ""
    home_logo = _team_logo(home_p) if home_p else None
    away_logo = _team_logo(away_p) if away_p else None
    return {
        "date": day,
        "time": time,
        "league": {"name": league_name},
        "home": {"name": home_name, "logo": home_logo},
        "away": {"name": away_name, "logo": away_logo},
    }


def _short_name_fallback(team_name: str) -> list[str]:
    """Pour recherche Sportmonks: si le nom complet ne matche pas, essayer des variantes (ex. FC Basel 1893 -> Basel)."""
    s = (team_name or "").strip()
    if not s:
        return []
    parts = s.split()
    out = []
    # Ignorer préfixes courants et années (4 chiffres)
    skip = {"fc", "ac", "sc", "ssv", "fk", "cf", "cf", "ogc", "as", "rc", "us", "nk", "fk", "fc"}
    main_words = [p for p in parts if p.lower() not in skip and not (len(p) == 4 and p.isdigit())]
    if main_words:
        out.append(main_words[0].strip())
    if len(main_words) >= 2:
        out.append(" ".join(main_words[:2]).strip())
    return out[:3]


def _resolve_team_id_sportmonks(team_name: str):
    """Résout le nom en Sportmonks ID via l'API Sportmonks (évite mélange avec anciens ids API-Football)."""
    from app.services.sportmonks import _use_sportmonks, teams_search, TEAM_SEARCH_ALIASES
    if not _use_sportmonks() or not (team_name or "").strip():
        return None
    name = team_name.strip().lower()
    search_term = name
    if name in TEAM_SEARCH_ALIASES:
        search_term = TEAM_SEARCH_ALIASES[name][0]
    query = search_term if search_term != name else team_name.strip()
    results = teams_search(query, limit=10)
    if not results:
        results = teams_search(team_name.strip(), limit=10)
    # Fallback: nom court (ex. "Basel" pour "FC Basel 1893") pour ligue suisse etc.
    if not results:
        for short in _short_name_fallback(team_name):
            if not short or short.lower() == name:
                continue
            results = teams_search(short, limit=10)
            if results:
                break
    if not results:
        return None
    name_norm = name.replace("é", "e").replace("è", "e")
    for t in results:
        tname = (t.get("name") or "").strip().lower()
        tname_norm = tname.replace("é", "e").replace("è", "e")
        if tname == name or tname_norm == name_norm:
            try:
                return int(t.get("id"))
            except (TypeError, ValueError):
                pass
        if name in tname or name_norm in tname_norm:
            if "women" not in tname and " u1" not in tname and " u2" not in tname:
                try:
                    return int(t.get("id"))
                except (TypeError, ValueError):
                    pass
    try:
        return int(results[0].get("id"))
    except (TypeError, ValueError):
        return None


def _format_api_football_fixture_for_upcoming(f: dict) -> dict:
    """Format one API-Football fixture for the upcoming list (same shape as Sportmonks format)."""
    fix = f.get("fixture") or {}
    league = f.get("league") or {}
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
    return {
        "date": day,
        "time": time,
        "league": {"name": (league.get("name") or "").strip() or None},
        "home": {"name": home.get("name") or "", "logo": home.get("logo") or None},
        "away": {"name": away.get("name") or "", "logo": away.get("logo") or None},
    }


@router.get("/upcoming")
def upcoming_fixtures(team: Optional[str] = None, team_id: Optional[int] = None, limit: int = 10):
    """Prochains matchs de l'équipe. Sportmonks d'abord, puis fallback API-Football si vide (ex. PSG, ligue suisse)."""
    from app.services.sportmonks import _use_sportmonks, team_upcoming_fixtures
    from app.services.api_football import _use_api, get_team_upcoming_fixtures, resolve_team_name_to_id

    tid = None
    team_name_clean = (team or "").strip()

    if _use_sportmonks():
        if team_name_clean:
            tid = _resolve_team_id_sportmonks(team_name_clean)
        if tid is None and team_id is not None:
            tid = int(team_id)
    else:
        tid = team_id
        if tid is None and team_name_clean:
            tid = _resolve_team_id_fast(team_name_clean)
        if tid is None and team_name_clean:
            tid = resolve_team_name_to_id(team_name_clean) if _use_api() else None

    if not tid:
        return {"fixtures": []}

    fixtures: list = []

    if _use_sportmonks():
        raw = team_upcoming_fixtures(int(tid), limit=limit * 2)
        team_norm = team_name_clean.lower() if team_name_clean else ""
        team_words = [w for w in team_norm.replace("é", "e").replace("è", "e").split() if len(w) > 2]
        for f in raw:
            row = _format_sportmonks_fixture_for_upcoming(f)
            if not row:
                continue
            if team_norm:
                home_n = ((row.get("home") or {}).get("name") or "").lower().replace("é", "e").replace("è", "e")
                away_n = ((row.get("away") or {}).get("name") or "").lower().replace("é", "e").replace("è", "e")
                if team_norm not in home_n and team_norm not in away_n:
                    if not team_words or not any(w in home_n or w in away_n for w in team_words):
                        continue
            fixtures.append(row)
        fixtures = fixtures[:limit]

    # Fallback API-Football si Sportmonks ne renvoie rien (ex. PSG, clubs ligue suisse)
    if not fixtures and _use_api():
        api_tid = None
        if team_name_clean:
            api_tid = resolve_team_name_to_id(team_name_clean)
        if api_tid is None and team_id is not None:
            api_tid = int(team_id)
        if api_tid is not None:
            raw = get_team_upcoming_fixtures(int(api_tid), next_n=limit)
            for f in raw:
                fixtures.append(_format_api_football_fixture_for_upcoming(f))
    elif not fixtures and _use_api() and not _use_sportmonks() and tid:
        raw = get_team_upcoming_fixtures(int(tid), next_n=limit)
        for f in raw:
            fixtures.append(_format_api_football_fixture_for_upcoming(f))

    if fixtures:
        return {"fixtures": fixtures}

    return {"fixtures": []}
