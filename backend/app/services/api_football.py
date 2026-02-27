# backend/app/services/api_football.py
"""
Client pour API-Football (api-sports.io) v3.
Documentation: https://www.api-football.com/documentation-v3
Base: https://v3.football.api-sports.io/
"""
from typing import Any, Optional
import time
import httpx
from app.core.config import get_settings
from app.core.leagues import LEAGUE_IDS, current_season

# Cache global: équipes (id -> {id, name, logo})
_teams_cache: dict[int, dict] = {}
_teams_cache_filled = False


def _use_api() -> bool:
    return bool(get_settings().api_football_key)


def _headers() -> dict[str, str]:
    return {
        "x-apisports-key": get_settings().api_football_key,
        "Accept": "application/json",
    }


def _url(path: str) -> str:
    base = (get_settings().api_football_base_url or "https://v3.football.api-sports.io").rstrip("/")
    return f"{base}{path}" if path.startswith("/") else f"{base}/{path}"


def _get(path: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """GET sur API-Football. Réponse standard: { "response": [...], "errors": {} }."""
    if not _use_api():
        return {}
    with httpx.Client(timeout=15.0) as client:
        r = client.get(_url(path), headers=_headers(), params=params or {})
        r.raise_for_status()
        data = r.json() or {}
        if data.get("errors") and not data.get("response"):
            return {}
        return data


def get_teams_by_league(league_id: int, season: Optional[int] = None) -> list[dict]:
    """Équipes d'une ligue. Chaque item: { "team": { "id", "name", "logo" } }."""
    season = season or current_season()
    data = _get("/teams", params={"league": league_id, "season": season})
    raw = data.get("response") or []
    return raw


def get_teams_search(search: str, min_chars: int = 2) -> list[dict]:
    """Recherche d'équipes via API (une requête). Retourne liste avec team.id, name, logo."""
    if not search or len(search.strip()) < min_chars:
        return []
    data = _get("/teams", params={"search": search.strip()})
    return data.get("response") or []


def get_countries() -> list[dict]:
    """
    Liste des pays disponibles (API-Football).
    Chaque item: { "name": "France", "code": "FR" } (noms utilisables pour GET /teams?country=...).
    """
    data = _get("/countries")
    raw = data.get("response") or []
    out = []
    for c in raw:
        name = (c.get("name") or "").strip()
        if name:
            out.append({"name": name, "code": (c.get("code") or "").strip() or None})
    return out


def get_teams_by_country(country_name: str) -> list[dict]:
    """
    Toutes les équipes (clubs + sélections) d'un pays.
    Méthode 1 par pays: GET /teams?country={CountryName}
    Chaque item: { "team": { "id", "name", "logo" }, ... } (format standard API).
    """
    if not (country_name or "").strip():
        return []
    data = _get("/teams", params={"country": country_name.strip()})
    return data.get("response") or []


def get_players_by_team(team_id: int, season: Optional[int] = None) -> list[dict]:
    """
    Joueurs d'une équipe pour une saison. GET /players?team=ID&season=YEAR.
    Chaque item: { "player": { "id", "name", "age", "nationality", "photo" }, "statistics": [ { "games": { "position" } } ] }.
    """
    season = season or current_season()
    data = _get("/players", params={"team": team_id, "season": season})
    return data.get("response") or []


def _fill_teams_cache() -> None:
    """Remplit le cache avec les équipes de toutes les ligues configurées."""
    global _teams_cache, _teams_cache_filled
    if _teams_cache_filled or not _use_api():
        return
    season = current_season()
    for league_id in LEAGUE_IDS:
        try:
            for item in get_teams_by_league(league_id, season):
                t = item.get("team") or item
                tid = t.get("id")
                if tid is not None:
                    _teams_cache[int(tid)] = {
                        "id": int(tid),
                        "name": (t.get("name") or "").strip(),
                        "shortName": (t.get("name") or "").strip(),
                        "crest": (t.get("logo") or "").strip() or None,
                    }
        except Exception:
            continue
    _teams_cache_filled = True


def _normalize_for_search(s: str) -> str:
    import unicodedata
    if not s:
        return ""
    n = unicodedata.normalize("NFD", s)
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    return n.lower().strip()


# Alias de recherche : ce que l'utilisateur tape -> terme pour trouver l'équipe (nom ou mot-clé)
# Permet aja → Auxerre, psg → Paris SG même avec beaucoup d'équipes en base.
TEAM_SEARCH_ALIASES: dict[str, list[str]] = {
    "psg": ["paris saint germain", "paris sg", "psg", "paris"],
    "psj": ["paris saint germain", "paris sg", "psg", "paris"],
    "paris sg": ["paris saint germain", "paris sg", "psg", "paris"],
    "aja": ["auxerre"],
    "auxerre": ["auxerre"],
    "om": ["marseille"],
    "ol": ["lyon"],
    "lyon": ["lyon"],
    "ogc": ["nice"],
    "nice": ["nice"],
    "rcs": ["strasbourg"],
    "strasbourg": ["strasbourg"],
    "scc": ["lens"],
    "lens": ["lens"],
    "losc": ["lille"],
    "lille": ["lille"],
    "asmonaco": ["monaco"],
    "monaco": ["monaco"],
    "stade rennais": ["rennes"],
    "rennes": ["rennes"],
    "reims": ["reims"],
    "montpellier": ["montpellier"],
    "tfc": ["toulouse"],
    "toulouse": ["toulouse"],
    "eh": ["havre"],
    "havre": ["havre"],
    "brest": ["brest"],
    "nantes": ["nantes"],
    "lorient": ["lorient"],
    "clermont": ["clermont"],
    "cf63": ["clermont"],
    "real": ["real madrid"],
    "barca": ["barcelona"],
    "barcelona": ["barcelona"],
    "bayern": ["bayern"],
    "juve": ["juventus"],
    "juventus": ["juventus"],
    "inter": ["inter"],
    "man u": ["manchester united"],
    "man utd": ["manchester united"],
    "united": ["manchester united"],
    "city": ["manchester city"],
    "liverpool": ["liverpool"],
    "arsenal": ["arsenal"],
    "chelsea": ["chelsea"],
    "spurs": ["tottenham"],
    "tottenham": ["tottenham"],
    "france": ["france"],
    "espagne": ["spain"],
    "spain": ["spain"],
    "italie": ["italy"],
    "angleterre": ["england"],
    "england": ["england"],
    "allemagne": ["germany"],
    "germany": ["germany"],
    "bresil": ["brazil"],
    "brazil": ["brazil"],
    "argentine": ["argentina"],
    "argentina": ["argentina"],
    "portugal": ["portugal"],
    "belgique": ["belgium"],
    "belgium": ["belgium"],
    "pays-bas": ["netherlands"],
    "netherlands": ["netherlands"],
}

# Priorité d'affichage pour les clubs principaux (plus petit = plus prioritaire)
TOP_CLUB_PRIORITY: dict[str, int] = {
    "real madrid": 1,
    "barcelona": 2,
    "paris saint-germain": 3,
    "olympique de marseille": 4,
    "olympique lyonnais": 5,
    "aj auxerre": 6,
    "manchester city": 7,
    "manchester united": 8,
    "liverpool": 9,
    "arsenal": 10,
    "chelsea": 11,
    "tottenham": 12,
    "bayern munich": 13,
    "borussia dortmund": 14,
    "juventus": 15,
    "inter": 16,
    "ac milan": 17,
    "napoli": 18,
    "atletico madrid": 19,
    "ajax": 20,
    "psv": 21,
    "feyenoord": 22,
    "benfica": 23,
    "porto": 24,
    "sporting cp": 25,
}

_SUPABASE_AUTOCOMPLETE_TTL_SECONDS = 600
_supabase_teams_cache: list[dict] = []
_supabase_teams_cache_ts: float = 0.0


def _priority_for_name(n: str) -> int:
    direct = TOP_CLUB_PRIORITY.get(n)
    if direct is not None:
        return direct
    if "paris" in n and ("saint germain" in n or "sg" in n or n.endswith("psg")):
        return 3
    if "marseille" in n:
        return 4
    if "lyon" in n and "olympique" in n:
        return 5
    if "auxerre" in n:
        return 6
    if "real madrid" in n:
        return 1
    if "barcelona" in n:
        return 2
    return 9999


def _is_non_primary_team_name(name: str) -> bool:
    """Filtre équipes de jeunes/réserve/féminines qui polluent l'autocomplete principal."""
    n = _normalize_for_search(name)
    bad_tokens = (" u17", " u18", " u19", " u20", " u21", " u23", " women", " feminino", " feminine", " fem")
    if any(tok in n for tok in bad_tokens):
        return True
    if n.endswith(" ii") or n.endswith(" iii") or n.endswith(" b"):
        return True
    return False


def _refresh_supabase_teams_cache_if_needed() -> Optional[list[dict]]:
    """Charge les équipes Supabase en mémoire (TTL) pour un autocomplete instantané."""
    global _supabase_teams_cache, _supabase_teams_cache_ts
    from app.core.config import get_settings
    s = get_settings()
    if not (s.supabase_url and s.supabase_key):
        return None
    now = time.time()
    if _supabase_teams_cache and (now - _supabase_teams_cache_ts) < _SUPABASE_AUTOCOMPLETE_TTL_SECONDS:
        return _supabase_teams_cache
    try:
        from app.core.supabase_client import get_supabase
        supabase = get_supabase()
        all_rows: list[dict] = []
        start = 0
        page_size = 1000
        while True:
            end = start + page_size - 1
            r = (
                supabase.table("teams")
                .select("slug, name, logo_url, country")
                .order("name")
                .range(start, end)
                .execute()
            )
            chunk = r.data or []
            if not chunk:
                break
            all_rows.extend(chunk)
            if len(chunk) < page_size:
                break
            start += page_size
        _supabase_teams_cache = all_rows
        _supabase_teams_cache_ts = now
        return _supabase_teams_cache
    except Exception:
        # Keep previous cache if available; otherwise fallback to caller behavior.
        return _supabase_teams_cache or None


def _team_relevance_score(name: str, q_normalized: str) -> tuple[int, int, str]:
    """Score de tri: exact/alias > début nom > début mot > priorité top clubs."""
    n = _normalize_for_search(name)
    if not q_normalized:
        return (3, _priority_for_name(n), n)
    aliases = TEAM_SEARCH_ALIASES.get(q_normalized, [])
    words = n.split()
    if n == q_normalized:
        return (0, _priority_for_name(n), n)
    if any(n == a for a in aliases):
        return (0, _priority_for_name(n), n)
    if n.startswith(q_normalized):
        return (1, _priority_for_name(n), n)
    if any(w.startswith(q_normalized) for w in words):
        return (2, _priority_for_name(n), n)
    if any(n.startswith(a) for a in aliases):
        return (1, _priority_for_name(n), n)
    if any(any(w.startswith(a) for w in words) for a in aliases):
        return (2, _priority_for_name(n), n)
    return (4, _priority_for_name(n), n)


def get_teams_from_supabase(q: Optional[str] = None, limit: int = 80) -> Optional[list[dict]]:
    """
    Liste d'équipes depuis Supabase. Suggestion intelligente :
    - Alias (aja, psg, om...) : on cherche l'équipe dont le nom correspond à l'alias (ex. aja → Auxerre).
    - Sinon : uniquement les équipes dont le nom (ou un mot du nom) COMMENCE par les lettres tapées.
    """
    from app.core.config import get_settings
    s = get_settings()
    if not (s.supabase_url and s.supabase_key):
        return None
    try:
        data = _refresh_supabase_teams_cache_if_needed()
        if data is None:
            return None
        q_clean = (q or "").strip()
        teams = [
            {
                "id": row.get("slug"),
                "name": (row.get("name") or "").strip() or row.get("slug"),
                "crest": row.get("logo_url"),
                "country": (row.get("country") or "").strip() or None,
            }
            for row in data
            if row.get("logo_url")
        ]
        if q_clean:
            teams = [
                t
                for t in teams
                if not _is_non_primary_team_name(t.get("name") or "")
                and _team_matches_query({"name": t.get("name") or "", "shortName": ""}, q_normalized)
            ]
            teams.sort(key=lambda t: _team_relevance_score(t.get("name") or "", q_normalized))
        else:
            teams.sort(key=lambda t: ((t.get("name") or "").lower()))
        return teams[:limit]
    except Exception:
        return None


def _team_matches_query(team: dict, q_normalized: str) -> bool:
    """True si l'équipe correspond à la requête : alias (aja→Auxerre) ou nom/mot qui COMMENCE par la requête."""
    name = (team.get("name") or "").strip()
    short = (team.get("shortName") or "").strip()
    if not q_normalized:
        return True
    n_norm = _normalize_for_search(name)
    s_norm = _normalize_for_search(short)
    combined = n_norm + " " + s_norm
    # Alias : "aja" -> Auxerre, "psg" -> Paris, etc.
    if q_normalized in TEAM_SEARCH_ALIASES:
        for part in TEAM_SEARCH_ALIASES[q_normalized]:
            if part in combined or n_norm.startswith(part) or s_norm.startswith(part):
                return True
        return False
    # Sans alias : uniquement "commence par" (nom entier ou un mot)
    if n_norm.startswith(q_normalized) or s_norm.startswith(q_normalized):
        return True
    for word in (name + " " + short).split():
        if _normalize_for_search(word).startswith(q_normalized):
            return True
    return False


def get_teams_for_autocomplete(q: Optional[str] = None, limit: int = 80) -> list[dict]:
    """
    Liste d'équipes pour l'autocomplete (id, name, crest).
    - Alias connus (aja, psg, om, etc.) : on utilise le cache pour résoudre (ex: aja → Auxerre).
    - Sinon recherche API en une requête (rapide), puis fallback cache si vide.
    """
    q_clean = (q or "").strip()
    q_normalized = _normalize_for_search(q_clean) if q_clean else ""
    # Alias (aja, psg, om, …) : passer par le cache pour avoir la bonne équipe
    if q_normalized and q_normalized in TEAM_SEARCH_ALIASES:
        _fill_teams_cache()
        teams_list = [t for t in _teams_cache.values() if t.get("name") and _team_matches_query(t, q_normalized)]
        teams_list.sort(key=lambda t: (t.get("name") or "").lower())
        result = []
        seen_names: set[str] = set()
        for t in teams_list:
            name = t.get("name") or t.get("shortName") or ""
            if name in seen_names:
                continue
            seen_names.add(name)
            result.append({"id": t.get("id"), "name": name, "crest": t.get("crest"), "country": None})
            if len(result) >= limit:
                break
        return result
    if q_clean and len(q_clean) >= 2:
        raw = get_teams_search(q_clean, min_chars=2)
        if raw:
            result = []
            seen_names: set[str] = set()
            for item in raw:
                t = item.get("team") or item
                name = (t.get("name") or "").strip()
                if not name or name in seen_names:
                    continue
                # Même règle "commence par" : ne garder que si le nom (ou un mot) commence par la requête
                team_dict = {"name": name, "shortName": name}
                if not _team_matches_query(team_dict, q_normalized):
                    continue
                seen_names.add(name)
                logo = t.get("logo")
                crest = (logo or "").strip() or None
                result.append({"id": t.get("id"), "name": name, "crest": crest, "country": None})
                if len(result) >= limit:
                    break
            return result
    _fill_teams_cache()
    teams_list = [t for t in _teams_cache.values() if t.get("name")]
    if q_clean:
        ql = _normalize_for_search(q_clean)
        teams_list = [t for t in teams_list if _team_matches_query(t, ql)]
    teams_list.sort(key=lambda t: (t.get("name") or "").lower())
    result = []
    seen_names = set()
    for t in teams_list:
        name = t.get("name") or t.get("shortName") or ""
        if name in seen_names:
            continue
        seen_names.add(name)
        result.append({"id": t.get("id"), "name": name, "crest": t.get("crest"), "country": None})
        if len(result) >= limit:
            break
    return result


def get_team_fixtures(team_id: int, season: Optional[int] = None, last_n: int = 10) -> list[dict]:
    """Derniers matchs d'une équipe (fixtures terminés). Chaque item a teams.home, teams.away, goals."""
    season = season or current_season()
    data = _get("/fixtures", params={"team": team_id, "season": season, "status": "FT"})
    raw = data.get("response") or []
    # Trier par date décroissante et prendre les last_n
    raw.sort(key=lambda x: (x.get("fixture") or {}).get("date") or "", reverse=True)
    return raw[:last_n]


def get_team_upcoming_fixtures(team_id: int, next_n: int = 10) -> list[dict]:
    """Prochains matchs d'une équipe. Chaque item a fixture.date, teams.home, teams.away."""
    if not _use_api():
        return []
    data = _get("/fixtures", params={"team": team_id, "next": next_n})
    raw = data.get("response") or []
    raw.sort(key=lambda x: (x.get("fixture") or {}).get("date") or "")
    return raw[:next_n]


def get_team_by_id(team_id: int) -> Optional[dict]:
    """Infos d'une équipe (id, name, logo, venue/stadium). 1 requête par équipe."""
    if not _use_api():
        return None
    data = _get("/teams", params={"id": team_id})
    raw = data.get("response") or []
    if not raw:
        return None
    item = raw[0]
    team = item.get("team") or item
    venue = (item.get("venue") or {}) if isinstance(item.get("venue"), dict) else {}
    return {
        "id": int(team.get("id") or 0),
        "name": (team.get("name") or "").strip(),
        "logo": (team.get("logo") or "").strip() or None,
        "stadium": (venue.get("name") or "").strip() or None,
    }


def get_fixtures_headtohead(team1_id: int, team2_id: int, last_n: int = 15) -> list[dict]:
    """Historique des confrontations directes (H2H). 1 requête = tout l'historique (limité par l'API)."""
    if not _use_api():
        return []
    h2h_param = f"{min(team1_id, team2_id)}-{max(team1_id, team2_id)}"
    data = _get("/fixtures/headtohead", params={"h2h": h2h_param})
    raw = data.get("response") or []
    raw.sort(key=lambda x: (x.get("fixture") or {}).get("date") or "", reverse=True)
    return raw[:last_n]


def _season_from_fixture_date(date_str: str, current: int) -> int:
    """Saison API (année de début) à partir de la date du match. Ex: 2022-08-27 -> 2022, 2023-01-15 -> 2022."""
    if not date_str or len(date_str) < 7:
        return current
    try:
        y = int(date_str[:4])
        m = int(date_str[5:7]) if len(date_str) >= 7 else 8
        return y if m >= 8 else y - 1
    except (ValueError, TypeError):
        return current


# Poids par ancienneté : saison courante = 1.0, -1 = 0.8, -2 = 0.6, -3 = 0.4, -4 = 0.2 (5 dernières saisons)
H2H_SEASON_WEIGHTS: tuple[float, ...] = (1.0, 0.8, 0.6, 0.4, 0.2)


def get_fixtures_headtohead_multi_season(
    home_id: int,
    away_id: int,
    ideal_seasons: int = 5,
    max_seasons: int = 5,
) -> list[dict]:
    """
    Tous les matchs H2H entre home_id et away_id sur les 5 dernières saisons.
    Pour chaque saison on interroge les deux équipes (team=home_id et team=away_id) puis on fusionne
    pour ne manquer aucun match (limite éventuelle de l'API par requête).
    """
    if not _use_api():
        return []
    pair = {home_id, away_id}
    seen_ids: set[int] = set()
    out: list[dict] = []
    season = current_season()
    seasons_to_try = list(range(season, season - max_seasons, -1))
    for s in seasons_to_try:
        for team_id in (home_id, away_id):
            raw = _get("/fixtures", params={"team": team_id, "season": s, "status": "FT"})
            for f in (raw.get("response") or []):
                teams = f.get("teams") or {}
                hid = (teams.get("home") or {}).get("id")
                aid = (teams.get("away") or {}).get("id")
                if not hid or not aid or {hid, aid} != pair:
                    continue
                fid = (f.get("fixture") or {}).get("id")
                if fid is not None and fid in seen_ids:
                    continue
                seen_ids.add(fid)
                out.append(f)
    out.sort(key=lambda x: (x.get("fixture") or {}).get("date") or "", reverse=True)
    return out


def get_weighted_h2h_home_pct(
    home_team_id: int,
    away_team_id: int,
    fixtures: list[dict],
    current: Optional[int] = None,
) -> Optional[float]:
    """
    Pourcentage pondéré domicile pour le H2H (0–100).
    Poids par ancienneté : saison la plus récente 1.0, puis 0.8, 0.6, 0.4, 0.2.
    Si aucun match, retourne None.
    """
    if not fixtures:
        return None
    cur = current if current is not None else current_season()
    seasons_index: dict[int, int] = {}
    for i, s in enumerate(range(cur, cur - 5, -1)):
        seasons_index[s] = i
    weighted_home = 0.0
    weighted_draw = 0.0
    weighted_away = 0.0
    pair = {home_team_id, away_team_id}
    for f in fixtures:
        teams = f.get("teams") or {}
        home_id = (teams.get("home") or {}).get("id")
        away_id = (teams.get("away") or {}).get("id")
        if not home_id or not away_id or {home_id, away_id} != pair:
            continue
        date_str = (f.get("fixture") or {}).get("date") or ""
        season = _season_from_fixture_date(date_str, cur)
        idx = seasons_index.get(season, 4)
        w = H2H_SEASON_WEIGHTS[idx] if idx < len(H2H_SEASON_WEIGHTS) else 0.2
        goals = f.get("goals") or {}
        hg = int(goals.get("home") if goals.get("home") is not None else 0)
        ag = int(goals.get("away") if goals.get("away") is not None else 0)
        if home_id == home_team_id:
            if hg > ag:
                weighted_home += w
            elif hg < ag:
                weighted_away += w
            else:
                weighted_draw += w
        else:
            if ag > hg:
                weighted_home += w
            elif ag < hg:
                weighted_away += w
            else:
                weighted_draw += w
    total = weighted_home + weighted_draw + weighted_away
    if total <= 0:
        return None
    return (weighted_home + 0.5 * weighted_draw) / total * 100


def get_standings(league_id: int, season: Optional[int] = None) -> list[dict]:
    """Classement d'une ligue/saison. 1 requête = toutes les équipes. Retourne liste de lignes (position, team, points, etc.)."""
    season = season or current_season()
    data = _get("/standings", params={"league": league_id, "season": season})
    raw = data.get("response") or []
    if not raw:
        return []
    if isinstance(raw[0], dict) and "league" in raw[0]:
        standings = (raw[0].get("league") or {}).get("standings") or []
        if not isinstance(standings, list):
            return []
        # Une ligue peut avoir plusieurs groupes (ex: poules); on renvoie le premier groupe ou concatène
        if standings and isinstance(standings[0], list):
            out: list[dict] = []
            for group in standings:
                out.extend(group)
            return out
        return standings
    return raw


def get_fixtures_by_league(league_id: int, season: Optional[int] = None, status: str = "FT") -> list[dict]:
    """Matchs d'une ligue (terminés). status=FT pour finished."""
    season = season or current_season()
    data = _get("/fixtures", params={"league": league_id, "season": season, "status": status})
    return data.get("response") or []


def get_fixtures_by_date(date: str) -> list[dict]:
    """Matchs d'une date (YYYY-MM-DD)."""
    data = _get("/fixtures", params={"date": date})
    return data.get("response") or []


def resolve_team_name_to_id(team_name: str, _league_id: Optional[int] = None) -> Optional[int]:
    """Résout un nom d'équipe en ID API-Football (recherche dans le cache multi-ligues)."""
    if not _use_api() or not (team_name or "").strip():
        return None
    name_lower = team_name.strip().lower()
    _fill_teams_cache()
    for t in _teams_cache.values():
        n = (t.get("name") or "").strip().lower()
        sn = (t.get("shortName") or "").strip().lower()
        if name_lower == n or name_lower == sn or name_lower in n or name_lower in sn or n in name_lower or sn in name_lower:
            return int(t["id"])
    return None


def _fixture_to_goals_and_form(team_id: int, fixtures: list[dict], last_n: int = 5) -> tuple[list[int], list[int], list[str]]:
    """À partir des fixtures API-Football, retourne (goals_for, goals_against, form)."""
    goals_for: list[int] = []
    goals_against: list[int] = []
    form: list[str] = []
    for f in fixtures[:last_n]:
        teams = f.get("teams") or {}
        goals = f.get("goals") or {}
        home = teams.get("home") or {}
        away = teams.get("away") or {}
        hid = home.get("id")
        hg = int(goals.get("home") is not None and goals.get("home") or 0)
        ag = int(goals.get("away") is not None and goals.get("away") or 0)
        is_home = hid == team_id
        if is_home:
            goals_for.append(hg)
            goals_against.append(ag)
            form.append("W" if hg > ag else ("D" if hg == ag else "L"))
        else:
            goals_for.append(ag)
            goals_against.append(hg)
            form.append("W" if ag > hg else ("D" if ag == hg else "L"))
    return (goals_for, goals_against, form)


def get_h2h_from_fixtures(home_team_id: int, away_team_id: int, fixtures: list[dict]) -> tuple[int, int, int]:
    """H2H (home_wins, draws, away_wins) à partir d'une liste de fixtures."""
    h_wins = d = a_wins = 0
    pair = {home_team_id, away_team_id}
    for f in fixtures:
        teams = f.get("teams") or {}
        home = (teams.get("home") or {}).get("id")
        away = (teams.get("away") or {}).get("id")
        if not home or not away or {home, away} != pair:
            continue
        goals = f.get("goals") or {}
        hg = int(goals.get("home") if goals.get("home") is not None else 0)
        ag = int(goals.get("away") if goals.get("away") is not None else 0)
        if home == home_team_id:
            if hg > ag:
                h_wins += 1
            elif hg < ag:
                a_wins += 1
            else:
                d += 1
        else:
            if ag > hg:
                h_wins += 1
            elif ag < hg:
                a_wins += 1
            else:
                d += 1
    return (h_wins, d, a_wins)


def fixture_for_ingest(f: dict) -> Optional[tuple[str, str, str, int, int, str]]:
    """Extrait (hid, aid, hname, aname, hg, ag, date, league) d'une fixture pour l'ingest Supabase."""
    try:
        teams = f.get("teams") or {}
        goals = f.get("goals") or {}
        home = teams.get("home") or {}
        away = teams.get("away") or {}
        hid = str(home.get("id") or "")
        aid = str(away.get("id") or "")
        hname = (home.get("name") or "").strip()
        aname = (away.get("name") or "").strip()
        hg = goals.get("home")
        ag = goals.get("away")
        if hg is None or ag is None:
            return None
        fix = f.get("fixture") or {}
        date_str = (fix.get("date") or "")[:10]
        league = (f.get("league") or {}).get("name") or ""
        if not hid or not aid or not date_str:
            return None
        return (hid, aid, hname, aname, int(hg), int(ag), date_str, league)
    except Exception:
        return None
