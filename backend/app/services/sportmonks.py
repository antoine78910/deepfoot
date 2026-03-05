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


def teams_search(name: str, limit: int = 5) -> list[dict[str, Any]]:
    """GET /teams/search/{name}. Retourne liste de { id, name, short_code, image_path, ... }."""
    name_clean = (name or "").strip()
    if not name_clean:
        return []
    # API: search by name (encode the query)
    import urllib.parse
    q = urllib.parse.quote(name_clean)
    data = _get(f"/teams/search/{q}", params={"per_page": limit})
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


def get_teams_for_autocomplete_sportmonks(q: Optional[str] = None, limit: int = 80) -> list[dict[str, Any]]:
    """
    Liste d'équipes pour l'autocomplete (id, name, crest, country).
    Suggestion intelligente : alias (psg→Paris SG, aja→Auxerre) + recherche Sportmonks.
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
        raw = teams_search(term, limit=per_search)
        print(f"[sportmonks] teams_search({term!r}, {per_search}) -> {len(raw or [])} résultats")
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
            seen_ids.add(tid_int)
            result.append({
                "id": tid_int,
                "name": name,
                "crest": _team_crest(t),
                "country": None,  # Sportmonks team peut avoir country_id; on ne charge pas l'include ici
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
    print(f"[sportmonks] total -> {len(result)} teams")
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


def team_upcoming_fixtures(team_id: int, limit: int = 10) -> list[dict[str, Any]]:
    """
    Prochains matchs de l'équipe (Sportmonks).
    Utilise l'endpoint dédié: GET /fixtures/between/{start_date}/{end_date}/{team_id}
    """
    if not _use_sportmonks() or not team_id:
        return []
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    start_date = now.strftime("%Y-%m-%d")
    end_date = (now + timedelta(days=90)).strftime("%Y-%m-%d")
    path = f"/fixtures/between/{start_date}/{end_date}/{team_id}"
    data = _get(path, params={"per_page": min(limit, 50)}, include="participants;league")
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


def fixture_by_id(fixture_id: int, include: str = "participants;league;venue") -> Optional[dict[str, Any]]:
    """GET /fixtures/{id} avec participants (équipes + image_path pour blasons), league, venue."""
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
    return inner


def predictions_probabilities_by_fixture(fixture_id: int) -> Optional[dict[str, Any]]:
    """GET /predictions/probabilities/fixtures/{id}. Retourne probas (structure dépend de l'API)."""
    data = _get(f"/predictions/probabilities/fixtures/{fixture_id}")
    return data.get("data") if data.get("data") is not None else None


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


def load_match_context_sportmonks(
    home_team: str,
    away_team: str,
    progress_callback: Optional[Any] = None,
) -> Optional[dict[str, Any]]:
    """
    Charge le contexte match depuis Sportmonks: fixture, prédictions, équipes avec blasons.
    Retourne le même format que _load_match_context_api_football pour compatibilité predict.
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

    league_obj = fixture_data.get("league") or {}
    league_name = league_obj.get("name") if isinstance(league_obj, dict) else None
    if not league_name and isinstance(league_obj, dict):
        league_name = league_obj.get("short_name")
    venue_obj = fixture_data.get("venue") or {}
    venue_name = venue_obj.get("name") if isinstance(venue_obj, dict) else None
    starting_at = fixture_data.get("starting_at")
    match_date_iso = starting_at
    match_date = starting_at  # peut formater en "4 March 2026 at 20:00" si besoin
    fixture_id = fixture_data.get("id")

    report("Loading Sportmonks predictions…", 30)
    probs = predictions_probabilities_by_fixture(int(fixture_id)) if fixture_id else None

    # Mapper les probas Sportmonks vers notre format (noms de champs peuvent varier selon l'API)
    home_win = draw = away_win = 33.33
    over_25 = under_25 = 50.0
    btts_yes = btts_no = 50.0
    xg_home = xg_away = 1.2
    if probs:
        if isinstance(probs, list):
            for p in probs:
                pred_type = (p.get("type") or p.get("prediction_type") or "").lower()
                if "1x2" in pred_type or "winner" in pred_type or "match" in pred_type:
                    v = p.get("predictions") or p.get("values") or p
                    if isinstance(v, dict):
                        home_win = float(v.get("home") or v.get("1") or 33.33)
                        draw = float(v.get("draw") or v.get("X") or 33.33)
                        away_win = float(v.get("away") or v.get("2") or 33.33)
                elif "over" in pred_type or "total" in pred_type:
                    v = p.get("predictions") or p.get("values") or p
                    if isinstance(v, dict):
                        over_25 = float(v.get("over") or v.get("over_2_5") or 50)
                        under_25 = float(v.get("under") or v.get("under_2_5") or 50)
                elif "btts" in pred_type or "both_teams" in pred_type:
                    v = p.get("predictions") or p.get("values") or p
                    if isinstance(v, dict):
                        btts_yes = float(v.get("yes") or v.get("btts_yes") or 50)
                        btts_no = float(v.get("no") or v.get("btts_no") or 50)
        elif isinstance(probs, dict):
            home_win = float(probs.get("home_win") or probs.get("home") or 33.33)
            draw = float(probs.get("draw") or 33.33)
            away_win = float(probs.get("away_win") or probs.get("away") or 33.33)
            over_25 = float(probs.get("over_2_5") or probs.get("over_2.5") or 50)
            under_25 = float(probs.get("under_2_5") or probs.get("under_2.5") or 50)
            btts_yes = float(probs.get("btts_yes") or probs.get("btts_yes") or 50)
            btts_no = float(probs.get("btts_no") or probs.get("btts_no") or 50)
            xg_home = float(probs.get("expected_goals_home") or probs.get("xg_home") or 1.2)
            xg_away = float(probs.get("expected_goals_away") or probs.get("xg_away") or 1.2)

    # Construire le contexte au format attendu par predict (comme API-Football)
    return {
        "home_team": home_name,
        "away_team": away_name,
        "home_team_id": home_participant.get("id") if home_participant else None,
        "away_team_id": away_participant.get("id") if away_participant else None,
        "home_team_logo": home_logo,
        "away_team_logo": away_logo,
        "league": league_name,
        "match_date": match_date,
        "match_date_iso": match_date_iso,
        "venue": venue_name,
        "fixture_id": fixture_id,
        "lambda_home": xg_home,
        "lambda_away": xg_away,
        "home_form": None,
        "away_form": None,
        "home_wdl": None,
        "away_wdl": None,
        "home_form_label": None,
        "away_form_label": None,
        "comparison_pcts": None,
        "match_over": False,
        "final_score_home": None,
        "final_score_away": None,
        "match_statistics": None,
        "data_recap": {
            "data_source": "Sportmonks",
            "pipeline_steps": [],
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
        },
        "_sportmonks_raw_probs": probs,
        "_sportmonks_use_predictions": bool(probs),
    }
