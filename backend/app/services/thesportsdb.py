"""TheSportsDB (free) — next fixtures for a named club. Cached on disk, no API-Football quota."""
from __future__ import annotations

import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "thesportsdb"
_CACHE_DIR = _DATA_DIR / "cache"
_BASE = "https://www.thesportsdb.com/api/v1/json/123"
_SEARCH_TTL = 7 * 24 * 3600
_EVENTS_TTL = 6 * 3600
_ROUND_TTL = 12 * 3600

_SEARCH_ALIASES: dict[str, str] = {
    "paris saint germain": "Paris Saint Germain",
    "bayern munchen": "Bayern Munich",
    "bayern munich": "Bayern Munich",
    "internazionale": "Inter",
    "atletico madrid": "Atletico Madrid",
    "olympique marseille": "Marseille",
    "olympique lyon": "Lyon",
}


def _normalize(s: str) -> str:
    import unicodedata

    n = unicodedata.normalize("NFD", (s or "").strip().lower())
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    n = n.replace("-", " ").replace(".", " ")
    return " ".join(n.split())


def _ensure_cache_dir() -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(kind: str, key: str) -> Path:
    digest = hashlib.sha256(f"{kind}:{key}".encode("utf-8")).hexdigest()
    return _CACHE_DIR / f"{digest}.json"


def _read_cache(kind: str, key: str, ttl: int) -> Optional[Any]:
    fp = _cache_path(kind, key)
    if not fp.exists():
        return None
    try:
        payload = json.loads(fp.read_text(encoding="utf-8"))
        stored_at = float(payload.get("stored_at") or 0)
        if time.time() - stored_at > ttl:
            return None
        return payload.get("data")
    except (OSError, ValueError, TypeError):
        return None


def _write_cache(kind: str, key: str, data: Any) -> None:
    try:
        _ensure_cache_dir()
        fp = _cache_path(kind, key)
        fp.write_text(
            json.dumps({"stored_at": time.time(), "data": data}, default=str),
            encoding="utf-8",
        )
    except OSError:
        pass


def _http_get(path: str, params: dict[str, str]) -> dict[str, Any]:
    url = f"{_BASE}{path}" if path.startswith("/") else f"{_BASE}/{path}"
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(url, params=params)
        r.raise_for_status()
        return r.json() or {}
    except Exception as exc:
        print(f"[thesportsdb] GET {path} error: {exc}")
        return {}


def format_event_for_upcoming(ev: dict) -> Optional[dict]:
    """Convert one TheSportsDB event to the LP upcoming card shape. None if not playable."""
    if not isinstance(ev, dict):
        return None
    status = (ev.get("strStatus") or "").strip().upper()
    if status in ("FT", "MATCH FINISHED", "AET", "PEN", "AWARDED", "POSTP"):
        return None
    ts = (ev.get("strTimestamp") or "").strip()
    date_event = (ev.get("dateEvent") or "")[:10]
    time_raw = (ev.get("strTime") or "").strip()
    dt = None
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except ValueError:
            dt = None
    if dt is None and date_event:
        try:
            hhmm = time_raw[:8] if time_raw and time_raw[0].isdigit() else "00:00:00"
            dt = datetime.fromisoformat(f"{date_event}T{hhmm}").replace(tzinfo=timezone.utc)
        except ValueError:
            dt = None
    if dt is not None and dt < datetime.now(timezone.utc):
        return None
    home = (ev.get("strHomeTeam") or "").strip()
    away = (ev.get("strAwayTeam") or "").strip()
    if not home or not away:
        return None
    return {
        "date": dt.strftime("%d/%m") if dt else "",
        "time": dt.strftime("%H:%M") if dt else "",
        "league": {"name": (ev.get("strLeague") or "").strip() or None},
        "home": {"name": home, "logo": (ev.get("strHomeTeamBadge") or "").strip() or None},
        "away": {"name": away, "logo": (ev.get("strAwayTeamBadge") or "").strip() or None},
        "sort_at": dt.isoformat() if dt else "",
    }


def _current_soccer_season() -> str:
    now = datetime.now(timezone.utc)
    year = now.year
    if now.month >= 7:
        return f"{year}-{year + 1}"
    return f"{year - 1}-{year}"


def event_involves_team(ev: dict, team_id: Optional[str] = None, team_name: Optional[str] = None) -> bool:
    if not isinstance(ev, dict):
        return False
    if team_id:
        tid = str(team_id)
        if tid and tid in (str(ev.get("idHomeTeam") or ""), str(ev.get("idAwayTeam") or "")):
            return True
    qn = _normalize(team_name or "")
    if not qn:
        return False
    home = _normalize(ev.get("strHomeTeam") or "")
    away = _normalize(ev.get("strAwayTeam") or "")
    return qn == home or qn == away or qn in home or qn in away


def fixtures_for_team_from_events(
    events: list[dict],
    team_id: Optional[str] = None,
    team_name: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """Keep upcoming fixtures that involve the selected club, in source order."""
    out: list[dict] = []
    seen: set[tuple] = set()
    for ev in events:
        if not event_involves_team(ev, team_id=team_id, team_name=team_name):
            continue
        row = format_event_for_upcoming(ev)
        if not row:
            continue
        key = (row["date"], row["time"], row["home"]["name"], row["away"]["name"])
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
        if len(out) >= limit:
            break
    return out


def _pick_team(rows: list[dict], query: str) -> Optional[dict]:
    qn = _normalize(query)
    scored: list[tuple[int, dict]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = (row.get("strTeam") or "").strip()
        if not name:
            continue
        sport = (row.get("strSport") or "").strip().lower()
        if sport and sport not in ("soccer", "association football", ""):
            continue
        nn = _normalize(name)
        league = _normalize(row.get("strLeague") or "")
        if any(tok in nn for tok in ("talon", "esport", " u19", " u21", " women", " wfc")):
            continue
        if nn == qn:
            score = 0
        elif qn in nn or nn in qn:
            score = 1
        else:
            continue
        if "esports" in league or "mobile" in league:
            continue
        scored.append((score, row))
    scored.sort(key=lambda x: (x[0], x[1].get("strTeam") or ""))
    return scored[0][1] if scored else None


def resolve_team(team_name: str) -> Optional[dict]:
    name = (team_name or "").strip()
    if not name:
        return None
    key = _normalize(name)
    cached = _read_cache("teaminfo", key, _SEARCH_TTL)
    if isinstance(cached, dict) and cached.get("idTeam"):
        return cached
    search = _SEARCH_ALIASES.get(key) or name
    data = _http_get("/searchteams.php", {"t": search})
    rows = data.get("teams") or []
    if not isinstance(rows, list):
        rows = []
    picked = _pick_team(rows, search)
    if not picked:
        return None
    tid = str(picked.get("idTeam") or "").strip()
    if not tid:
        return None
    info = {
        "idTeam": tid,
        "strTeam": (picked.get("strTeam") or name).strip(),
        "idLeague": str(picked.get("idLeague") or "").strip() or None,
        "strLeague": (picked.get("strLeague") or "").strip() or None,
        "strTeamBadge": (picked.get("strTeamBadge") or "").strip() or None,
    }
    _write_cache("teaminfo", key, info)
    _write_cache("team", key, tid)
    return info


def resolve_team_id(team_name: str) -> Optional[str]:
    info = resolve_team(team_name)
    if not info:
        return None
    return str(info.get("idTeam") or "") or None


def _events_next(team_id: str) -> list[dict]:
    cached = _read_cache("events", team_id, _EVENTS_TTL)
    if isinstance(cached, list):
        return [e for e in cached if isinstance(e, dict)]
    data = _http_get("/eventsnext.php", {"id": team_id})
    raw = data.get("events") or []
    events = [e for e in raw if isinstance(e, dict)]
    _write_cache("events", team_id, events)
    return events


def fetch_round_events(league_id: str, season: str, rnd: int) -> list[dict]:
    key = f"{league_id}:{season}:{rnd}"
    cached = _read_cache("round", key, _ROUND_TTL)
    if isinstance(cached, list):
        return [e for e in cached if isinstance(e, dict)]
    data = _http_get("/eventsround.php", {"id": str(league_id), "r": str(rnd), "s": season})
    raw = data.get("events") or []
    events = [e for e in raw if isinstance(e, dict)]
    if events:
        _write_cache("round", key, events)
    return events


def _fetch_rounds(league_id: str, season: str, rounds: list[int]) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = {}
    missing: list[int] = []
    for rnd in rounds:
        key = f"{league_id}:{season}:{rnd}"
        cached = _read_cache("round", key, _ROUND_TTL)
        if isinstance(cached, list):
            out[rnd] = [e for e in cached if isinstance(e, dict)]
        else:
            missing.append(rnd)
    if not missing:
        return out
    with ThreadPoolExecutor(max_workers=5) as pool:
        futs = {pool.submit(fetch_round_events, league_id, season, rnd): rnd for rnd in missing}
        for fut in as_completed(futs):
            rnd = futs[fut]
            try:
                out[rnd] = fut.result()
            except Exception:
                out[rnd] = []
    return out


def get_upcoming_for_team(team_name: str, limit: int = 10) -> list[dict]:
    """Next league fixtures for a club (cached rounds). Aims for `limit` matches, not just the next one."""
    info = resolve_team(team_name)
    if not info:
        return []
    tid = str(info.get("idTeam") or "")
    league_id = (info.get("idLeague") or "").strip() or None
    display_name = (info.get("strTeam") or team_name).strip()
    next_events = _events_next(tid) if tid else []
    if next_events and not league_id:
        league_id = str(next_events[0].get("idLeague") or "").strip() or None
    season = (next_events[0].get("strSeason") if next_events else None) or _current_soccer_season()
    start_round = 1
    for ev in next_events:
        raw_round = ev.get("intRound")
        try:
            start_round = max(1, int(raw_round))
            break
        except (TypeError, ValueError):
            continue

    collected: list[dict] = []
    if league_id:
        round_ids = list(range(start_round, start_round + 10))
        by_round = _fetch_rounds(league_id, season, round_ids)
        empty_streak = 0
        for rnd in round_ids:
            events = by_round.get(rnd) or []
            if not events:
                empty_streak += 1
                if empty_streak >= 3:
                    break
                continue
            empty_streak = 0
            collected.extend(
                fixtures_for_team_from_events(
                    events, team_id=tid, team_name=display_name, limit=limit
                )
            )
            if len(collected) >= limit:
                break

    if len(collected) < limit and next_events:
        extra = fixtures_for_team_from_events(
            next_events, team_id=tid, team_name=display_name, limit=limit
        )
        seen = {(r["date"], r["time"], r["home"]["name"], r["away"]["name"]) for r in collected}
        for row in extra:
            key = (row["date"], row["time"], row["home"]["name"], row["away"]["name"])
            if key in seen:
                continue
            seen.add(key)
            collected.append(row)
            if len(collected) >= limit:
                break

    return collected[:limit]
