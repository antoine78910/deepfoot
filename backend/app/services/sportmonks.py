"""
Client Sportmonks Football API v3 — données matchs, prédictions, équipes (blasons).
Documentation: https://docs.sportmonks.com/v3/
Remplace API-Football pour le flux d'analyse quand SPORTMONKS_API_TOKEN est configuré.
"""
from __future__ import annotations

from typing import Any, Optional

import httpx

from app.core.config import get_settings

BASE_URL = "https://api.sportmonks.com/v3/football"


def _token() -> str:
    return (get_settings().sportmonks_api_token or "").strip()


def _use_sportmonks() -> bool:
    return bool(_token())


def _get(path: str, params: Optional[dict[str, Any]] = None, include: Optional[str] = None) -> dict[str, Any]:
    """GET Sportmonks. Réponse: { "data": ... } ou { "data": [], "pagination": ... }."""
    if not _use_sportmonks():
        return {}
    url = f"{BASE_URL.rstrip('/')}{path}" if path.startswith("/") else f"{BASE_URL}/{path}"
    p = dict(params or {})
    p["api_token"] = _token()
    if include:
        p["include"] = include
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(url, params=p)
            data = r.json() if r.content else {}
            n = len(data.get("data") or []) if isinstance(data.get("data"), list) else ("obj" if data.get("data") else 0)
            print(f"[sportmonks] GET {path[:50]}... -> {r.status_code} data_len={n}")
            r.raise_for_status()
            return data or {}
    except Exception as e:
        print(f"[sportmonks] GET {path[:50]}... ERREUR: {e}")
        return {}


def teams_search(
    name: str, limit: int = 5, include: Optional[str] = None
) -> list[dict[str, Any]] | dict[str, Any]:
    """
    GET /teams/search/{name}. Retourne liste de { id, name, short_code, image_path, country_id, ... }.
    Si include est fourni (ex. "country"), retourne la réponse complète { "data": [...], "country": [...] }.
    """
    name_clean = (name or "").strip()
    if not name_clean:
        return [] if not include else {}
    import urllib.parse
    q = urllib.parse.quote(name_clean)
    data = _get(f"/teams/search/{q}", params={"per_page": limit}, include=include)
    if include:
        return data
    return data.get("data") or []


# Alias pour la suggestion intelligente (même logique qu'API-Football) : aja→Auxerre, psg→Paris SG, etc.
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


def _normalize_for_search(s: str) -> str:
    import unicodedata
    n = (s or "").strip().lower()
    n = unicodedata.normalize("NFD", n)
    return "".join(c for c in n if unicodedata.category(c) != "Mn")


def _team_crest(team: dict) -> Optional[str]:
    """URL du blason depuis un objet team Sportmonks (image_path)."""
    img = team.get("image_path") or team.get("logo_path")
    if not img:
        return None
    s = str(img).strip()
    if s.startswith("http"):
        return s
    return f"https://cdn.sportmonks.com/images/soccer/teams/{s}" if s else None


def _team_matches_query_sportmonks(team: dict, q_normalized: str) -> bool:
    """True si l'équipe correspond à la requête (alias ou nom/short_code commence par)."""
    if not q_normalized:
        return True
    name = (team.get("name") or "").strip()
    short = (team.get("short_code") or "").strip()
    n_norm = _normalize_for_search(name)
    s_norm = _normalize_for_search(short)
    combined = n_norm + " " + s_norm
    if q_normalized in TEAM_SEARCH_ALIASES:
        for part in TEAM_SEARCH_ALIASES[q_normalized]:
            if part in combined or n_norm.startswith(part) or s_norm.startswith(part):
                return True
        return False
    if n_norm.startswith(q_normalized) or s_norm.startswith(q_normalized):
        return True
    for word in (name + " " + short).split():
        if _normalize_for_search(word).startswith(q_normalized):
            return True
    return False


def _team_country_allowed(country_name: Optional[str]) -> bool:
    """True si le pays fait partie des pays autorisés (Europe + 27 ligues)."""
    from app.core.leagues import ALLOWED_COUNTRIES_FOR_SUGGESTIONS
    c = (country_name or "").strip()
    if not c:
        return False
    return c in ALLOWED_COUNTRIES_FOR_SUGGESTIONS


def get_teams_for_autocomplete_sportmonks(q: Optional[str] = None, limit: int = 80) -> list[dict[str, Any]]:
    """
    Liste d'équipes pour l'autocomplete (id, name, crest, country).
    Suggestion intelligente : alias (psg→Paris SG, aja→Auxerre) + recherche Sportmonks.
    Ne garde que les équipes dont le pays est en Europe ou dans les 27 ligues.
    """
    if not _use_sportmonks():
        print("[sportmonks] token non configuré -> []")
        return []
    q_clean = (q or "").strip()
    q_normalized = _normalize_for_search(q_clean) if q_clean else ""
    if not q_clean or len(q_clean) < 2:
        print(f"[sportmonks] q trop court: {q_clean!r} -> []")
        return []

    # Alias : lancer une recherche par terme étendu pour avoir les bonnes équipes
    search_terms: list[str] = []
    if q_normalized in TEAM_SEARCH_ALIASES:
        search_terms = TEAM_SEARCH_ALIASES[q_normalized][:3]  # max 3 termes pour limiter les appels
        print(f"[sportmonks] alias {q_normalized!r} -> search_terms {search_terms}")
    else:
        search_terms = [q_clean]

    seen_ids: set[int] = set()
    result: list[dict[str, Any]] = []
    per_search = max(limit // len(search_terms), 10)

    for term in search_terms:
        raw_response = teams_search(term, limit=per_search, include="country")
        if isinstance(raw_response, dict):
            raw = raw_response.get("data") or []
            # Map country_id -> name (Sportmonks renvoie country/countries en liste ou objet)
            country_list = raw_response.get("country") or raw_response.get("countries")
            if isinstance(country_list, dict):
                country_list = [country_list] if country_list.get("id") is not None else []
            elif not isinstance(country_list, list):
                country_list = []
            country_by_id: dict[int, str] = {}
            for co in country_list:
                if isinstance(co, dict) and co.get("id") is not None:
                    country_by_id[int(co["id"])] = (co.get("name") or "").strip()
        else:
            raw = raw_response or []
            country_by_id = {}

        print(f"[sportmonks] teams_search({term!r}, {per_search}) -> {len(raw)} résultats")
        for t in raw:
            tid = t.get("id")
            if tid is None:
                continue
            try:
                tid_int = int(tid)
            except (ValueError, TypeError):
                continue
            if tid_int in seen_ids:
                continue
            name = (t.get("name") or "").strip()
            if not name:
                continue
            if q_normalized and not _team_matches_query_sportmonks(t, q_normalized):
                continue
            cid = t.get("country_id")
            country_name = country_by_id.get(int(cid)) if cid is not None and country_by_id else None
            if not _team_country_allowed(country_name):
                continue
            seen_ids.add(tid_int)
            result.append({
                "id": tid_int,
                "name": name,
                "crest": _team_crest(t),
                "country": country_name,
            })
            if len(result) >= limit:
                break
        if len(result) >= limit:
            break

    # Tri par pertinence : alias exact en premier, puis ordre alphabétique
    def sort_key(item: dict) -> tuple[int, str]:
        name = (item.get("name") or "").lower()
        if q_normalized in TEAM_SEARCH_ALIASES:
            for i, part in enumerate(TEAM_SEARCH_ALIASES[q_normalized]):
                if part in _normalize_for_search(name):
                    return (i, name)
        return (len(TEAM_SEARCH_ALIASES), name)

    result.sort(key=sort_key)
    print(f"[sportmonks] total -> {len(result)} teams (Europe + 27 ligues)")
    return result[:limit]


def fixtures_search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """GET /fixtures/search/{query}. Retourne fixtures (name, starting_at, id, etc.)."""
    q = (query or "").strip()
    if not q:
        return []
    import urllib.parse
    enc = urllib.parse.quote(q)
    data = _get(f"/fixtures/search/{enc}", params={"per_page": limit})
    return data.get("data") or []


def team_past_fixtures(
    team_id: int,
    last_n: int = 5,
) -> tuple[list[int], list[int], list[str]]:
    """
    Derniers matchs terminés d'une équipe (Sportmonks).
    Retourne (goals_for_list, goals_against_list, form_list W/D/L).
    """
    if not _use_sportmonks() or not team_id:
        return ([], [], [])
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    end_date = now.strftime("%Y-%m-%d")
    start_date = (now - timedelta(days=120)).strftime("%Y-%m-%d")
    path = f"/fixtures/between/{start_date}/{end_date}/{team_id}"
    params: dict[str, Any] = {"per_page": 30}
    try:
        data = _get(path, params=params, include="participants;scores")
    except Exception:
        return ([], [], [])
    raw = data.get("data")
    if isinstance(raw, dict):
        raw = raw.get("data") if isinstance(raw.get("data"), list) else []
    if not isinstance(raw, list):
        raw = []
    raw.sort(key=lambda x: (x.get("starting_at") or ""), reverse=True)
    participants_by_fid: dict[int, list] = {}
    for p in (data.get("participants") or []):
        if isinstance(p, dict):
            fid = p.get("fixture_id")
            if fid is not None:
                participants_by_fid.setdefault(int(fid), []).append(p)
    scores_by_fid: dict[int, list] = {}
    for s in (data.get("scores") or []):
        if isinstance(s, dict):
            fid = s.get("fixture_id")
            if fid is not None:
                scores_by_fid.setdefault(int(fid), []).append(s)
    goals_for_list: list[int] = []
    goals_against_list: list[int] = []
    form_list: list[str] = []
    seen = 0
    for f in raw:
        if seen >= last_n:
            break
        fid = f.get("id")
        if fid is None:
            continue
        sat = f.get("starting_at") or ""
        try:
            if sat:
                dt_str = sat.replace("T", " ")[:19].strip()
                fixture_dt = datetime.fromisoformat(dt_str.replace(" ", "T").replace("Z", "+00:00"))
                if fixture_dt.tzinfo is None:
                    fixture_dt = fixture_dt.replace(tzinfo=timezone.utc)
                if fixture_dt >= now:
                    continue
        except Exception:
            pass
        participants = f.get("participants") or participants_by_fid.get(int(fid), [])
        scores = f.get("scores") or scores_by_fid.get(int(fid), [])
        if not participants or not scores:
            continue
        home_goals = sum(
            int((s.get("score") or {}).get("goals", 0) or 0)
            for s in scores
            if (s.get("score") or {}).get("participant") == "home"
        )
        away_goals = sum(
            int((s.get("score") or {}).get("goals", 0) or 0)
            for s in scores
            if (s.get("score") or {}).get("participant") == "away"
        )
        home_p, away_p = None, None
        for p in participants:
            meta = p.get("meta") or {}
            loc = (meta.get("location") or "").lower()
            if loc == "home":
                home_p = p
            elif loc == "away":
                away_p = p
        if not home_p or not away_p and len(participants) >= 2:
            home_p = participants[0] if participants else None
            away_p = participants[1] if len(participants) > 1 else None
        def _team_id_from_p(p: Optional[dict]) -> Optional[int]:
            if not p:
                return None
            v = p.get("team_id") or p.get("id")
            return int(v) if v is not None else None
        pid_home = _team_id_from_p(home_p)
        pid_away = _team_id_from_p(away_p)
        tid = int(team_id)
        is_home = pid_home is not None and pid_home == tid
        is_away = pid_away is not None and pid_away == tid
        if not is_home and not is_away:
            if not _fixture_involves_team(f, team_id):
                continue
            is_home = _team_id_from_p(participants[0] if participants else None) == tid
            is_away = not is_home and len(participants) > 1
        if not (is_home or is_away):
            continue
        gf = home_goals if is_home else away_goals
        ga = away_goals if is_home else home_goals
        if home_goals > away_goals:
            res = "W" if is_home else "L"
        elif home_goals < away_goals:
            res = "L" if is_home else "W"
        else:
            res = "D"
        goals_for_list.append(gf)
        goals_against_list.append(ga)
        form_list.append(res)
        seen += 1
    return (goals_for_list, goals_against_list, form_list)


def team_upcoming_fixtures(team_id: int, limit: int = 10) -> list[dict[str, Any]]:
    """
    Prochains matchs de l'équipe (Sportmonks).
    1) GET /fixtures?filters=team_id:{id};starting_after:{date}&include=participants;league
    2) Si vide ou erreur, fallback GET /fixtures/between/{today}/{today+90j}/{team_id}
    """
    if not _use_sportmonks() or not team_id:
        return []
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    start_date = now.strftime("%Y-%m-%d")
    end_date_future = (now + timedelta(days=90)).strftime("%Y-%m-%d")
    raw: list = []
    data: dict = {}
    filters = f"team_id:{team_id};starting_after:{start_date}"
    data = _get(
        "/fixtures",
        params={"per_page": min(limit * 2, 50), "filters": filters},
        include="participants;league",
    )
    raw = data.get("data")
    if isinstance(raw, dict):
        raw = raw.get("data") if isinstance(raw.get("data"), list) else []
    if not isinstance(raw, list):
        raw = []
    # Fallback: endpoint between (dates futures) si filtre vide ou 400
    if not raw:
        path_between = f"/fixtures/between/{start_date}/{end_date_future}/{team_id}"
        data = _get(path_between, params={"per_page": min(limit * 2, 50)}, include="participants;league")
        raw = data.get("data")
        if isinstance(raw, dict):
            raw = raw.get("data") if isinstance(raw.get("data"), list) else []
        if not isinstance(raw, list):
            raw = []
    # Inclure les participants à la racine (format list endpoint Sportmonks) dans chaque fixture
    if raw and (not raw[0] or "participants" not in raw[0]) and isinstance(data.get("participants"), list):
        by_fid: dict[int, list] = {}
        for p in data.get("participants", []):
            if isinstance(p, dict):
                fid = p.get("fixture_id")
                if fid is not None:
                    by_fid.setdefault(int(fid), []).append(p)
        for f in raw:
            if "participants" not in f or not f.get("participants"):
                fid = f.get("id")
                if fid is not None:
                    f["participants"] = by_fid.get(int(fid), [])
    # Garder uniquement les matchs futurs où l'équipe demandée joue bien (filtrer Super Lig etc. si mauvais team_id)
    upcoming = []
    for f in raw:
        if not _fixture_involves_team(f, team_id):
            continue
        sat = f.get("starting_at") or ""
        try:
            if sat:
                dt_str = sat.replace("T", " ")[:19].strip()
                fixture_dt = datetime.fromisoformat(dt_str.replace(" ", "T").replace("Z", "+00:00"))
                if fixture_dt.tzinfo is None:
                    fixture_dt = fixture_dt.replace(tzinfo=timezone.utc)
                if fixture_dt >= now:
                    upcoming.append(f)
            else:
                upcoming.append(f)
        except Exception:
            upcoming.append(f)
    upcoming.sort(key=lambda x: (x.get("starting_at") or ""))
    return upcoming[:limit]


def fixture_by_id(
    fixture_id: int, include: str = "participants;league;venue;predictions;metadata;h2h"
) -> Optional[dict[str, Any]]:
    """GET /fixtures/{id} avec participants, league, venue, predictions, metadata (predictable) et h2h."""
    data = _get(f"/fixtures/{fixture_id}", include=include)
    inner = data.get("data") if isinstance(data.get("data"), dict) else None
    if not inner:
        return None
    # Sportmonks v3 can put includes in root (e.g. participants) or inside data
    if "participants" not in inner and data.get("participants"):
        inner = {**inner, "participants": data.get("participants")}
    if "league" not in inner and data.get("league"):
        inner = {**inner, "league": data.get("league")}
    if "venue" not in inner and data.get("venue"):
        inner = {**inner, "venue": data.get("venue")}
    if "predictions" not in inner and data.get("predictions"):
        inner = {**inner, "predictions": data.get("predictions")}
    if "metadata" not in inner and data.get("metadata"):
        inner = {**inner, "metadata": data.get("metadata")}
    if "h2h" not in inner and data.get("h2h"):
        inner = {**inner, "h2h": data.get("h2h")}
    return inner


def predictions_fixture(fixture_id: int) -> Optional[dict[str, Any]]:
    """
    GET /predictions/fixtures/{fixture_id} — endpoint principal prédictions.
    Retourne { fixture_id, predictions: { home_win, draw, away_win }, winner, expected_goals? }.
    """
    data = _get(f"/predictions/fixtures/{fixture_id}")
    raw = data.get("data")
    if raw is None or not isinstance(raw, dict):
        return None
    return raw


def predictions_probabilities_by_fixture(
    fixture_id: int, include_type: bool = True
) -> Optional[list[dict[str, Any]]]:
    """
    GET /predictions/probabilities/fixtures/{id}.
    Retourne la liste des prédictions (chaque item: id, fixture_id, predictions, type_id, type si include_type).
    Doc: https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/odds-and-predictions/predictions/probabilities
    """
    data = _get(
        f"/predictions/probabilities/fixtures/{fixture_id}",
        include="type" if include_type else None,
    )
    raw = data.get("data")
    if raw is None:
        return None
    if not isinstance(raw, list):
        return [raw] if isinstance(raw, dict) else None
    # Si l'API renvoie type au niveau racine (liste d'objets type), attacher par type_id
    type_list = data.get("type")
    if isinstance(type_list, dict):
        type_list = [type_list] if type_list.get("id") is not None else []
    elif not isinstance(type_list, list):
        type_list = []
    type_by_id = {int(t["id"]): t for t in type_list if isinstance(t, dict) and t.get("id") is not None}
    if type_by_id:
        for p in raw:
            if isinstance(p, dict) and p.get("type_id") is not None and "type" not in p:
                tid = int(p.get("type_id"))
                if tid in type_by_id:
                    p["type"] = type_by_id[tid]
    return raw


def value_bets_by_fixture(
    fixture_id: int, include_type: bool = True
) -> Optional[list[dict[str, Any]]]:
    """
    GET /predictions/value-bets/fixtures/{id}.
    Retourne la liste des value bets (bookmaker, odd, fair_odd, stake, bet, is_value, type_id [+ type si include).
    Doc: https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/predictions/get-value-bets-by-fixture-id
    """
    data = _get(
        f"/predictions/value-bets/fixtures/{fixture_id}",
        include="type" if include_type else None,
    )
    raw = data.get("data")
    if raw is None:
        return None
    if not isinstance(raw, list):
        return [raw] if isinstance(raw, dict) else None
    type_list = data.get("type")
    if isinstance(type_list, dict):
        type_list = [type_list] if type_list.get("id") is not None else []
    elif not isinstance(type_list, list):
        type_list = []
    type_by_id = {int(t["id"]): t for t in type_list if isinstance(t, dict) and t.get("id") is not None}
    if type_by_id:
        for v in raw:
            if isinstance(v, dict) and v.get("type_id") is not None and "type" not in v:
                tid = int(v.get("type_id"))
                if tid in type_by_id:
                    v["type"] = type_by_id[tid]
    return raw


def resolve_fixture_and_teams(home_team: str, away_team: str) -> Optional[dict[str, Any]]:
    """
    Trouve un prochain match entre les deux équipes et retourne fixture + infos équipes (logos).
    Retourne None si pas trouvé ou API non configurée.
    """
    if not _use_sportmonks():
        return None
    query = f"{home_team} vs {away_team}"
    fixtures = fixtures_search(query, limit=15)
    for f in fixtures:
        name = (f.get("name") or "").strip()
        if not name:
            continue
        # Vérifier que les deux noms d'équipes apparaissent
        h = (home_team or "").lower()
        a = (away_team or "").lower()
        n = name.lower()
        if h in n and a in n:
            fid = f.get("id")
            if fid:
                full = fixture_by_id(int(fid))
                if full:
                    return full
    return None


def _fixture_involves_team(fixture_data: dict, team_id: int) -> bool:
    """True si l'équipe team_id est bien un des participants du match (évite mauvais résultats API)."""
    inc = fixture_data.get("participants") or fixture_data.get("participant")
    if not inc:
        return True  # pas d'info → on garde
    participants = inc if isinstance(inc, list) else [inc.get("home"), inc.get("away")] if isinstance(inc, dict) else []
    tid = int(team_id)
    for p in participants:
        if not isinstance(p, dict):
            continue
        pid = p.get("id") or p.get("team_id")
        if pid is not None and int(pid) == tid:
            return True
    return False


def _extract_participants(fixture_data: dict) -> tuple[Optional[dict], Optional[dict]]:
    """Extrait home et away participant (équipe) depuis la réponse fixture avec include=participants."""
    inc = fixture_data.get("participants") or fixture_data.get("participant")
    if isinstance(inc, list):
        home_p, away_p = None, None
        for p in inc:
            meta = p.get("meta") or {}
            loc = (meta.get("location") or "").lower()
            if loc == "home":
                home_p = p
            elif loc == "away":
                away_p = p
        if home_p is not None or away_p is not None:
            return (home_p, away_p)
        if len(inc) >= 2:
            return (inc[0], inc[1])
        return (inc[0] if inc else None, None)
    if isinstance(inc, dict):
        return (inc.get("home"), inc.get("away"))
    return (None, None)


def _team_logo(participant: Optional[dict]) -> Optional[str]:
    """Image URL du blason depuis un participant (team). Sportmonks: image_path peut être relatif."""
    if not participant:
        return None
    img = participant.get("image_path") or participant.get("logo_path")
    if not img:
        return None
    s = str(img).strip()
    if s.startswith("http"):
        return s
    return f"https://cdn.sportmonks.com/images/soccer/teams/{s}" if s else None


def _parse_sportmonks_predictions_array(predictions_list: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Parse le tableau predictions de l'API Sportmonks (Fulltime Result, Over/Under 2.5, BTTS, Correct Score).
    Retourne dict avec home_win, draw, away_win, over_2_5, under_2_5, btts_yes, btts_no, xg_home, xg_away (optionnel).
    """
    out: dict[str, Any] = {
        "home_win": 33.33,
        "draw": 33.33,
        "away_win": 33.33,
        "over_2_5": 50.0,
        "under_2_5": 50.0,
        "btts_yes": 50.0,
        "btts_no": 50.0,
        "xg_home": 1.2,
        "xg_away": 1.2,
    }
    if not predictions_list or not isinstance(predictions_list, list):
        return out
    for p in predictions_list:
        if not isinstance(p, dict):
            continue
        pred_vals = p.get("predictions")
        if not isinstance(pred_vals, dict):
            continue
        type_obj = p.get("type")
        code = (type_obj.get("code") or "").lower() if isinstance(type_obj, dict) else ""
        dev_name = (type_obj.get("developer_name") or "").lower() if isinstance(type_obj, dict) else ""
        type_id = p.get("type_id")

        if type_id == 237 or "fulltime" in code or "fulltime_result" in dev_name:
            if "home" in pred_vals and "draw" in pred_vals and "away" in pred_vals:
                out["home_win"] = float(pred_vals.get("home") or 33.33)
                out["draw"] = float(pred_vals.get("draw") or 33.33)
                out["away_win"] = float(pred_vals.get("away") or 33.33)
        elif type_id == 235 or ("over" in code and "2" in code and "5" in code):
            if "yes" in pred_vals and "no" in pred_vals:
                out["over_2_5"] = float(pred_vals.get("yes") or 50)
                out["under_2_5"] = float(pred_vals.get("no") or 50)
        elif type_id == 231 or "btts" in code or "both" in code:
            if "yes" in pred_vals and "no" in pred_vals:
                out["btts_yes"] = float(pred_vals.get("yes") or 50)
                out["btts_no"] = float(pred_vals.get("no") or 50)
        elif type_id == 240 or "correct" in code or "correct_score" in dev_name:
            scores = pred_vals.get("scores")
            if isinstance(scores, dict):
                xg_h = 0.0
                xg_a = 0.0
                total_p = 0.0
                for key, prob in scores.items():
                    if key.startswith("Other") or not isinstance(prob, (int, float)):
                        continue
                    parts = str(key).split("-")
                    if len(parts) != 2:
                        continue
                    try:
                        i, j = int(parts[0]), int(parts[1])
                    except (ValueError, TypeError):
                        continue
                    pct = float(prob) / 100.0
                    xg_h += i * pct
                    xg_a += j * pct
                    total_p += pct
                if total_p > 0:
                    out["xg_home"] = round(xg_h, 2)
                    out["xg_away"] = round(xg_a, 2)
    return out


def load_match_context_sportmonks(
    home_team: str,
    away_team: str,
    progress_callback: Optional[Any] = None,
) -> Optional[dict[str, Any]]:
    """
    Charge le contexte match depuis Sportmonks: fixture, prédictions, forme (derniers matchs), équipes avec blasons.
    Retourne le même format que _load_match_context_api_football pour compatibilité predict.
    Quand les prédictions API sont vides, on utilise la forme et les buts (Poisson) depuis les matchs passés Sportmonks.
    """
    if not _use_sportmonks():
        return None

    def report(step: str, percent: int) -> None:
        if progress_callback:
            progress_callback(step, percent)

    report("Loading Sportmonks fixture…", 10)
    fixture_data = resolve_fixture_and_teams(home_team, away_team)
    if not fixture_data:
        return None

    home_participant, away_participant = _extract_participants(fixture_data)
    home_name = (home_participant.get("name") if home_participant else None) or home_team
    away_name = (away_participant.get("name") if away_participant else None) or away_team
    home_logo = _team_logo(home_participant)
    away_logo = _team_logo(away_participant)
    home_team_id = (home_participant.get("id") or home_participant.get("team_id")) if home_participant else None
    away_team_id = (away_participant.get("id") or away_participant.get("team_id")) if away_participant else None

    league_obj = fixture_data.get("league") or {}
    league_name = league_obj.get("name") if isinstance(league_obj, dict) else None
    if not league_name and isinstance(league_obj, dict):
        league_name = league_obj.get("short_name")
    venue_obj = fixture_data.get("venue") or {}
    venue_name = venue_obj.get("name") if isinstance(venue_obj, dict) else None
    starting_at = fixture_data.get("starting_at")
    match_date_iso = starting_at
    match_date = starting_at
    fixture_id = fixture_data.get("id")

    report("Loading Sportmonks predictions…", 25)
    # 1) Prédictions via include sur le fixture (souvent disponible quand l’endpoint dédié renvoie vide)
    probs_list: Optional[list[dict[str, Any]]] = None
    predictions_fixture_data: Optional[dict[str, Any]] = None
    if fixture_id:
        predictions_fixture_data = predictions_fixture(int(fixture_id))
        if predictions_fixture_data:
            pred_obj = predictions_fixture_data.get("predictions")
            if isinstance(pred_obj, dict) and (
                pred_obj.get("home_win") is not None
                or pred_obj.get("draw") is not None
                or pred_obj.get("win_probability_home") is not None
            ):
                print(f"[sportmonks] predictions from GET /predictions/fixtures/{fixture_id} -> home_win/draw/away_win")
            else:
                predictions_fixture_data = None
    if not predictions_fixture_data and fixture_data.get("predictions") and isinstance(fixture_data["predictions"], list):
        probs_list = fixture_data["predictions"]
        print(f"[sportmonks] predictions from fixture include -> {len(probs_list)} items")
    if not probs_list and not predictions_fixture_data and fixture_id:
        probs_list = predictions_probabilities_by_fixture(int(fixture_id))
        if probs_list:
            print(f"[sportmonks] predictions from probabilities endpoint -> {len(probs_list)} items")
        else:
            print(f"[sportmonks] no predictions for fixture {fixture_id} (Predictions add-on or fixture not predictable). Using Poisson from form.")

    home_win = draw = away_win = 33.33
    over_25 = under_25 = 50.0
    btts_yes = btts_no = 50.0
    xg_home = xg_away = 1.2
    if predictions_fixture_data:
        pred_obj = predictions_fixture_data.get("predictions") or {}
        if isinstance(pred_obj, dict):
            home_win = float(pred_obj.get("home_win") or pred_obj.get("home") or pred_obj.get("win_probability_home") or 33.33)
            draw = float(pred_obj.get("draw") or pred_obj.get("win_probability_draw") or 33.33)
            away_win = float(pred_obj.get("away_win") or pred_obj.get("away") or pred_obj.get("win_probability_away") or 33.33)
        eg = predictions_fixture_data.get("expected_goals")
        if isinstance(eg, dict):
            xg_home = float(eg.get("home") or eg.get("home_goals") or 1.2)
            xg_away = float(eg.get("away") or eg.get("away_goals") or 1.2)
        elif isinstance(eg, (list, tuple)) and len(eg) >= 2:
            xg_home = float(eg[0]) if eg[0] is not None else 1.2
            xg_away = float(eg[1]) if eg[1] is not None else 1.2
    elif probs_list and isinstance(probs_list, list):
        parsed = _parse_sportmonks_predictions_array(probs_list)
        home_win = parsed["home_win"]
        draw = parsed["draw"]
        away_win = parsed["away_win"]
        over_25 = parsed["over_2_5"]
        under_25 = parsed["under_2_5"]
        btts_yes = parsed["btts_yes"]
        btts_no = parsed["btts_no"]
        xg_home = parsed["xg_home"]
        xg_away = parsed["xg_away"]

    home_goals_for: list[int] = []
    home_goals_against: list[int] = []
    away_goals_for: list[int] = []
    away_goals_against: list[int] = []
    home_form: list[str] = []
    away_form: list[str] = []
    hw, hd, hl = 0, 0, 0
    aw, ad, al = 0, 0, 0
    h2h_hw, h2h_hd, h2h_ha = 0, 0, 0
    h2h_list = fixture_data.get("h2h")
    if isinstance(h2h_list, list):
        for m in h2h_list:
            if not isinstance(m, dict):
                continue
            res = (m.get("result") or "").strip().lower()
            if res == "home":
                h2h_hw += 1
            elif res == "draw":
                h2h_hd += 1
            elif res == "away":
                h2h_ha += 1
        if h2h_hw or h2h_hd or h2h_ha:
            print(f"[sportmonks] H2H from fixture include: home_wins={h2h_hw}, draws={h2h_hd}, away_wins={h2h_ha}")
    lambda_home_calc = xg_home
    lambda_away_calc = xg_away
    comparison_pcts: Optional[dict[str, float]] = None
    pipeline_steps: list[dict] = []

    def _form_to_label(wins: int, draws: int, losses: int) -> str:
        total = wins + draws + losses or 1
        pts = wins * 3 + draws
        ratio = pts / (total * 3)
        if ratio >= 0.6:
            return "Great form"
        if ratio >= 0.4:
            return "Average form"
        return "Poor form"

    if home_team_id and away_team_id:
        report("Loading team form (last 5)…", 30)
        try:
            from app.ml.features import (
                compute_goals_avg,
                compute_lambda_home_away,
                form_to_wdl,
                build_comparison_pcts,
            )
            home_goals_for, home_goals_against, home_form = team_past_fixtures(int(home_team_id), last_n=5)
            away_goals_for, away_goals_against, away_form = team_past_fixtures(int(away_team_id), last_n=5)
            hw = sum(1 for x in home_form if x == "W")
            hd = sum(1 for x in home_form if x == "D")
            hl = sum(1 for x in home_form if x == "L")
            aw = sum(1 for x in away_form if x == "W")
            ad = sum(1 for x in away_form if x == "D")
            al = sum(1 for x in away_form if x == "L")
            h_for_avg, h_against_avg = compute_goals_avg(home_goals_for, home_goals_against)
            a_for_avg, a_against_avg = compute_goals_avg(away_goals_for, away_goals_against)
            lambda_home_calc, lambda_away_calc = compute_lambda_home_away(
                home_goals_for, home_goals_against, away_goals_for, away_goals_against,
            )
            comparison_pcts = build_comparison_pcts(
                hw, hd, hl, aw, ad, al,
                h_for_avg, a_for_avg, h_against_avg, a_against_avg,
                h2h_hw, h2h_hd, h2h_ha,
            )
            pipeline_steps = [
                {"order": 1, "title_key": "recap.step.data_source_sportmonks", "detail": "Data source: Sportmonks (fixture + predictions + team past fixtures for form)."},
                {"order": 2, "title_key": "recap.step.form", "detail": f"Team results (Sportmonks last 5): home goals_for/against avg {h_for_avg:.2f}/{h_against_avg:.2f}, away {a_for_avg:.2f}/{a_against_avg:.2f}. Form W-D-L."},
                {"order": 3, "title_key": "recap.step.features", "detail": f"Feature engineering: lambda_home={lambda_home_calc:.2f}, lambda_away={lambda_away_calc:.2f}. Comparison percentages."},
            ]
            if h2h_hw or h2h_hd or h2h_ha:
                pipeline_steps.append({
                    "order": 4,
                    "title_key": "recap.step.h2h",
                    "detail": f"H2H from fixture include: home_wins={h2h_hw}, draws={h2h_hd}, away_wins={h2h_ha}.",
                })
        except Exception:
            pass

    use_api_probs = bool(probs_list or predictions_fixture_data)
    # Selon la doc Sportmonks : si metadata.predictable === false, les prédictions ne sont pas dispo.
    # On pose une erreur pour que l'API renvoie 503 au lieu de fallback Poisson.
    # https://docs.sportmonks.com/v3/tutorials-and-guides/tutorials/odds-and-predictions/predictions
    _sportmonks_predictions_unavailable_error: Optional[str] = None
    if not use_api_probs:
        xg_home = lambda_home_calc
        xg_away = lambda_away_calc
        pipeline_steps.append({
            "order": 4,
            "title_key": "recap.step.sportmonks_no_predictions",
            "detail": "No Sportmonks predictions for this fixture (Predictions add-on required, or fixture not predictable). Probabilities from Poisson model using form data.",
        })
        meta = fixture_data.get("metadata")
        if isinstance(meta, list) and meta:
            meta = meta[0] if isinstance(meta[0], dict) else {}
        elif not isinstance(meta, dict):
            meta = {}
        predictable = meta.get("predictable") if isinstance(meta, dict) else None
        if predictable is False:
            _sportmonks_predictions_unavailable_error = (
                "Predictions not available for this fixture (predictable: false — insufficient data for the model)."
            )
        else:
            _sportmonks_predictions_unavailable_error = (
                "Predictions not available for this fixture (Predictions add-on required, or fixture not predictable)."
            )

    # Format fixture + predictions pour la réponse API (endpoint principal ou Probabilities)
    sportmonks_fixture_with_predictions: Optional[dict[str, Any]] = None
    if fixture_id and fixture_data:
        fixture_flat = {k: v for k, v in fixture_data.items() if k not in ("participants", "league", "venue")}
        if predictions_fixture_data:
            # GET /predictions/fixtures/{id} : home_win, draw, away_win, winner, expected_goals
            sportmonks_fixture_with_predictions = {"data": {**fixture_flat, **predictions_fixture_data}}
        elif probs_list:
            sportmonks_fixture_with_predictions = {"data": {**fixture_flat, "predictions": probs_list}}

    # Value Bets : uniquement quand on a des prédictions (évite de bloquer le flux 503)
    sportmonks_value_bets: Optional[list[dict[str, Any]]] = None
    if fixture_id and use_api_probs:
        report("Loading Sportmonks value bets…", 28)
        sportmonks_value_bets = value_bets_by_fixture(int(fixture_id))
        if sportmonks_value_bets:
            print(f"[sportmonks] value_bets_by_fixture({fixture_id}) -> {len(sportmonks_value_bets)} items")

    data_recap: dict[str, Any] = {
        "data_source": "Sportmonks",
        "pipeline_steps": pipeline_steps,
        "sportmonks_predictions_unavailable_reason": None if use_api_probs else "Predictions add-on or fixture not predictable",
        "sportmonks_fixture_with_predictions": sportmonks_fixture_with_predictions,
        "sportmonks_value_bets": sportmonks_value_bets,
        "sportmonks_predictions": {
            "home_win": home_win,
            "draw": draw,
            "away_win": away_win,
            "over_2_5": over_25,
            "under_2_5": under_25,
            "btts_yes": btts_yes,
            "btts_no": btts_no,
            "xg_home": xg_home,
            "xg_away": xg_away,
        },
        "raw_home_goals_for": home_goals_for,
        "raw_home_goals_against": home_goals_against,
        "raw_away_goals_for": away_goals_for,
        "raw_away_goals_against": away_goals_against,
        "raw_home_form": home_form,
        "raw_away_form": away_form,
        "form_home_matches": len(home_goals_for),
        "form_away_matches": len(away_goals_for),
        "home_goals_for_avg": round(sum(home_goals_for) / len(home_goals_for), 2) if home_goals_for else None,
        "home_goals_against_avg": round(sum(home_goals_against) / len(home_goals_against), 2) if home_goals_against else None,
        "away_goals_for_avg": round(sum(away_goals_for) / len(away_goals_for), 2) if away_goals_for else None,
        "away_goals_against_avg": round(sum(away_goals_against) / len(away_goals_against), 2) if away_goals_against else None,
        "h2h_matches_count": h2h_hw + h2h_hd + h2h_ha,
        "h2h_home_wins": h2h_hw,
        "h2h_draws": h2h_hd,
        "h2h_away_wins": h2h_ha,
    }

    return {
        "home_team": home_name,
        "away_team": away_name,
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "home_team_logo": home_logo,
        "away_team_logo": away_logo,
        "league": league_name,
        "match_date": match_date,
        "match_date_iso": match_date_iso,
        "venue": venue_name,
        "fixture_id": fixture_id,
        "lambda_home": xg_home,
        "lambda_away": xg_away,
        "home_form": home_form or None,
        "away_form": away_form or None,
        "home_wdl": f"{hw}-{hd}-{hl}" if home_form else None,
        "away_wdl": f"{aw}-{ad}-{al}" if away_form else None,
        "home_form_label": _form_to_label(hw, hd, hl) if home_form else None,
        "away_form_label": _form_to_label(aw, ad, al) if away_form else None,
        "comparison_pcts": comparison_pcts,
        "match_over": False,
        "final_score_home": None,
        "final_score_away": None,
        "match_statistics": None,
        "data_recap": data_recap,
        "_sportmonks_raw_probs": probs_list,
        "_sportmonks_use_predictions": use_api_probs,
        "_sportmonks_predictions_unavailable_error": _sportmonks_predictions_unavailable_error,
    }
