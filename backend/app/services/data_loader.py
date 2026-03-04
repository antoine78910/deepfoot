# backend/app/services/data_loader.py
"""
Charge les données équipes/matchs pour le feature engineering.
Priorité: 1) API-Football (api-sports.io) si clé configurée, 2) Supabase, 3) démo.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Optional
from app.core.config import get_settings
from app.ml.features import (
    compute_goals_avg,
    compute_lambda_home_away,
    form_to_wdl,
    form_to_label,
    build_comparison_pcts,
)


def normalize_team_name(name: str) -> str:
    return name.strip().lower().replace(" ", "_") if name else ""


def _use_api_football() -> bool:
    return bool(get_settings().api_football_key)


def _use_supabase() -> bool:
    s = get_settings()
    return bool(s.supabase_url and s.supabase_key)


def get_team_results(team_slug: str, is_home: bool, last_n: int = 5) -> tuple[list[int], list[int]]:
    """
    Récupère les N derniers matchs (goals_for, goals_against) pour une équipe en home ou away.
    Retourne (goals_for_list, goals_against_list).
    """
    if not _use_supabase():
        return ([1, 2, 1, 0, 2], [1, 0, 2, 1, 1]) if is_home else ([0, 1, 1, 2, 0], [2, 1, 0, 1, 2])
    from app.core.supabase_client import get_supabase
    supabase = get_supabase()
    team_col = "home_team_id" if is_home else "away_team_id"
    goals_for_col = "home_goals" if is_home else "away_goals"
    goals_against_col = "away_goals" if is_home else "home_goals"
    r = supabase.table("results").select("*").eq(team_col, team_slug).order("date", desc=True).limit(last_n).execute()
    if not r.data:
        return ([1, 2, 1, 0, 2], [1, 0, 2, 1, 1]) if is_home else ([0, 1, 1, 2, 0], [2, 1, 0, 1, 2])
    goals_for = [int(row.get(goals_for_col, 1)) for row in r.data]
    goals_against = [int(row.get(goals_against_col, 1)) for row in r.data]
    return (goals_for, goals_against)


def get_team_form(team_slug: str, last_n: int = 5) -> tuple[list[str], int, int, int]:
    """Form = liste ['W','D','L',...], puis W, D, L counts."""
    if not _use_supabase():
        form = ["W", "D", "L", "W", "W"]
        return (form, 3, 1, 1)
    from app.core.supabase_client import get_supabase
    supabase = get_supabase()
    r = supabase.table("results").select("home_team_id, away_team_id, home_goals, away_goals").eq("home_team_id", team_slug).order("date", desc=True).limit(last_n).execute()
    if not r.data:
        r = supabase.table("results").select("home_team_id, away_team_id, home_goals, away_goals").eq("away_team_id", team_slug).order("date", desc=True).limit(last_n).execute()
    form = []
    if not r.data:
        form = ["W", "D", "L", "W", "W"]
    else:
        for row in r.data:
            is_home = row.get("home_team_id") == team_slug
            hg = int(row.get("home_goals", 0))
            ag = int(row.get("away_goals", 0))
            if hg > ag:
                form.append("W" if is_home else "L")
            elif hg < ag:
                form.append("L" if is_home else "W")
            else:
                form.append("D")
    w = sum(1 for x in form if x == "W")
    d = sum(1 for x in form if x == "D")
    l = sum(1 for x in form if x == "L")
    return (form, w, d, l)


def get_h2h(home_slug: str, away_slug: str) -> tuple[int, int, int]:
    """Nombre de victoires home, draw, away en H2H."""
    if not _use_supabase():
        return (1, 1, 1)
    from app.core.supabase_client import get_supabase
    supabase = get_supabase()
    r = supabase.table("h2h").select("home_wins, draws, away_wins").eq("home_team_id", home_slug).eq("away_team_id", away_slug).execute()
    if not r.data:
        return (0, 0, 0)
    row = r.data[0]
    return (int(row.get("home_wins", 0)), int(row.get("draws", 0)), int(row.get("away_wins", 0)))


def _load_match_context_api_football(
    home_team: str,
    away_team: str,
    progress_callback: Optional[Callable[[str, int], None]] = None,
    home_team_id: Optional[int] = None,
    away_team_id: Optional[int] = None,
) -> dict[str, Any] | None:
    """
    Charge le contexte match via API-Football (api-sports.io) v3.
    Si home_team_id/away_team_id sont fournis (ex: depuis l'autocomplete), on les utilise
    directement pour éviter toute mauvaise résolution (ex: Angers vs Rangers).
    Retourne None si clé absente ou équipes non résolues.
    """
    def report(step: str, percent: int) -> None:
        if progress_callback:
            progress_callback(step, percent)

    from app.services.api_football import (
        resolve_team_name_to_id,
        get_team_fixtures,
        get_team_upcoming_fixtures,
        get_team_by_id,
        _fixture_to_goals_and_form,
        get_h2h_from_fixtures,
        get_fixtures_headtohead_multi_season,
        get_weighted_h2h_home_pct,
        guess_common_league_name,
        get_fixture_by_id,
        get_fixture_statistics,
    )
    report("Resolving teams…", 5)
    home_id = home_team_id if home_team_id is not None else resolve_team_name_to_id(home_team)
    away_id = away_team_id if away_team_id is not None else resolve_team_name_to_id(away_team)
    if home_id is None or away_id is None:
        return None

    report("Fetching team info…", 15)
    league: Any = None
    match_date: Any = None
    match_date_iso: Any = None
    venue: Any = None
    fixture_id: Any = None
    home_team_logo: Any = None
    away_team_logo: Any = None
    try:
        with ThreadPoolExecutor(max_workers=2) as ex:
            fut_h = ex.submit(get_team_by_id, home_id)
            fut_a = ex.submit(get_team_by_id, away_id)
            home_info = fut_h.result()
            away_info = fut_a.result()
        if home_info:
            home_team_logo = home_info.get("logo")
            if (home_info.get("name") or "").strip():
                home_team = (home_info.get("name") or "").strip()
        if away_info:
            away_team_logo = away_info.get("logo")
            if (away_info.get("name") or "").strip():
                away_team = (away_info.get("name") or "").strip()
        upcoming = get_team_upcoming_fixtures(home_id, next_n=15)
        for f in upcoming:
            teams = f.get("teams") or {}
            f_home_id = (teams.get("home") or {}).get("id")
            f_away_id = (teams.get("away") or {}).get("id")
            # Accept both orientations; users may enter teams in either order.
            if {f_home_id, f_away_id} == {home_id, away_id}:
                fix = f.get("fixture") or {}
                fixture_id = fix.get("id")
                # Date : format "2 March 2026 at 00:15"
                date_val = fix.get("date") or ""
                if date_val:
                    from datetime import datetime
                    match_date_iso = date_val
                    try:
                        dt = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
                        match_date = f"{dt.day} {dt.strftime('%B %Y')} at {dt.strftime('%H:%M')}"
                        match_date_iso = dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
                    except Exception:
                        match_date = date_val[:16] if len(date_val) >= 16 else date_val
                league = (f.get("league") or {}).get("name")
                # Lieu : depuis la fixture (stade du match), sinon stade de l'équipe à domicile
                fix_venue = fix.get("venue") if isinstance(fix.get("venue"), dict) else {}
                if fix_venue:
                    v_name = (fix_venue.get("name") or "").strip()
                    v_city = (fix_venue.get("city") or "").strip()
                    if v_name and v_city:
                        venue = f"{v_name} - {v_city}"
                    elif v_name:
                        venue = v_name
                if not venue and home_info:
                    venue = home_info.get("stadium")
                break
        if not venue and home_info:
            venue = home_info.get("stadium")
    except Exception:
        pass

    report("Fetching team form…", 28)
    with ThreadPoolExecutor(max_workers=2) as ex:
        fut_h = ex.submit(get_team_fixtures, home_id, None, 10)
        fut_a = ex.submit(get_team_fixtures, away_id, None, 10)
        home_fixtures = fut_h.result()
        away_fixtures = fut_a.result()
    home_goals_for, home_goals_against, home_form = _fixture_to_goals_and_form(
        home_id, home_fixtures, last_n=5
    )
    away_goals_for, away_goals_against, away_form = _fixture_to_goals_and_form(
        away_id, away_fixtures, last_n=5
    )
    report("Fetching head-to-head…", 52)
    if not home_goals_for and not home_goals_against:
        home_goals_for, home_goals_against = [1, 2, 1, 0, 2], [1, 0, 2, 1, 1]
    if not away_goals_for and not away_goals_against:
        away_goals_for, away_goals_against = [0, 1, 1, 2, 0], [2, 1, 0, 1, 2]
    if not home_form:
        home_form = ["W", "D", "L", "W", "W"]
    if not away_form:
        away_form = ["W", "D", "L", "W", "W"]
    h2h_fixtures = get_fixtures_headtohead_multi_season(home_id, away_id, ideal_seasons=5, max_seasons=5)
    h2h_h, h2h_d, h2h_a = get_h2h_from_fixtures(home_id, away_id, h2h_fixtures)
    h2h_weighted_pct = get_weighted_h2h_home_pct(home_id, away_id, h2h_fixtures)

    # Si on n'a pas réussi à trouver la ligue / date / stade via un prochain match,
    # on essaie de les déduire du dernier H2H disponible sur les 5 dernières saisons.
    if (league is None or match_date is None or venue is None) and h2h_fixtures:
        last = h2h_fixtures[0]
        if league is None:
            league = (last.get("league") or {}).get("name") or league
        fix_last = last.get("fixture") or {}
        date_val = fix_last.get("date") or ""
        if match_date is None and date_val:
            from datetime import datetime
            match_date_iso = date_val
            try:
                dt = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
                match_date = f"{dt.day} {dt.strftime('%B %Y')} at {dt.strftime('%H:%M')}"
                match_date_iso = dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
            except Exception:
                match_date = date_val[:16] if len(date_val) >= 16 else date_val
        elif match_date_iso is None and date_val:
            match_date_iso = date_val
        if venue is None:
            fix_venue = fix_last.get("venue") if isinstance(fix_last.get("venue"), dict) else {}
            if fix_venue:
                v_name = (fix_venue.get("name") or "").strip()
                v_city = (fix_venue.get("city") or "").strip()
                if v_name and v_city:
                    venue = f"{v_name} - {v_city}"
                elif v_name:
                    venue = v_name
            if venue is None and home_info:
                venue = home_info.get("stadium")

    # If league is still missing, infer from the common league both teams play in (major + secondary).
    if league is None:
        league = guess_common_league_name(home_id, away_id)
    report("Computing features…", 58)
    hw = sum(1 for x in home_form if x == "W")
    hd = sum(1 for x in home_form if x == "D")
    hl = sum(1 for x in home_form if x == "L")
    aw = sum(1 for x in away_form if x == "W")
    ad = sum(1 for x in away_form if x == "D")
    al = sum(1 for x in away_form if x == "L")
    h_for_avg, h_against_avg = compute_goals_avg(home_goals_for, home_goals_against)
    a_for_avg, a_against_avg = compute_goals_avg(away_goals_for, away_goals_against)
    lambda_home, lambda_away = compute_lambda_home_away(
        home_goals_for, home_goals_against, away_goals_for, away_goals_against
    )
    pcts = build_comparison_pcts(
        hw, hd, hl, aw, ad, al,
        h_for_avg, a_for_avg, h_against_avg, a_against_avg,
        h2h_h, h2h_d, h2h_a,
        h2h_home_pct_override=h2h_weighted_pct,
    )

    # Si pas de prochain match : récupérer le dernier H2H via GET /fixtures?id= ; si status=FT → score + GET /fixtures/statistics
    match_over = False
    final_score_home: Any = None
    final_score_away: Any = None
    match_statistics: Any = None
    if fixture_id is None and h2h_fixtures:
        last_h2h = h2h_fixtures[0]
        fix_last = last_h2h.get("fixture") or {}
        last_fid = fix_last.get("id")
        if last_fid:
            # 1) GET /fixtures?id={fixture_id} — résultat officiel (status, goals)
            fixture_result = get_fixture_by_id(last_fid)
            if fixture_result and (fixture_result.get("status_short") or "").strip() == "FT":
                match_over = True
                f_home_id = fixture_result.get("home_team_id")
                f_away_id = fixture_result.get("away_team_id")
                try:
                    g_h = fixture_result.get("goals_home")
                    g_a = fixture_result.get("goals_away")
                    g_h = int(g_h) if g_h is not None else None
                    g_a = int(g_a) if g_a is not None else None
                except (TypeError, ValueError):
                    g_h, g_a = None, None
                if home_id == f_home_id:
                    final_score_home = g_h
                    final_score_away = g_a
                else:
                    final_score_home = g_a
                    final_score_away = g_h
                # 2) GET /fixtures/statistics?fixture={fixture_id} — stats du match
                if f_home_id is not None and f_away_id is not None:
                    stats_raw = get_fixture_statistics(last_fid, f_home_id, f_away_id)
                    if stats_raw and home_id != f_home_id:
                        match_statistics = [
                            {"type": s["type"], "home_value": s["away_value"], "away_value": s["home_value"]}
                            for s in stats_raw
                        ]
                    else:
                        match_statistics = stats_raw

    data_recap = {
        "data_source": "API-Football",
        "form_home_matches": len(home_goals_for),
        "form_away_matches": len(away_goals_for),
        "home_goals_for_avg": round(h_for_avg, 2),
        "home_goals_against_avg": round(h_against_avg, 2),
        "away_goals_for_avg": round(a_for_avg, 2),
        "away_goals_against_avg": round(a_against_avg, 2),
        "home_wdl": form_to_wdl(home_form),
        "away_wdl": form_to_wdl(away_form),
        "h2h_matches_count": len(h2h_fixtures),
        "h2h_home_wins": h2h_h,
        "h2h_draws": h2h_d,
        "h2h_away_wins": h2h_a,
        "h2h_seasons_used": 5,
        "fixture_id": fixture_id,
        "has_upcoming_match": fixture_id is not None,
        "league": league,
        "venue": venue,
    }
    return {
        "home_team": home_team,
        "away_team": away_team,
        "home_team_id": home_id,
        "away_team_id": away_id,
        "lambda_home": lambda_home,
        "lambda_away": lambda_away,
        "home_form": home_form,
        "away_form": away_form,
        "home_wdl": form_to_wdl(home_form),
        "away_wdl": form_to_wdl(away_form),
        "home_form_label": form_to_label(hw, hd, hl),
        "away_form_label": form_to_label(aw, ad, al),
        "comparison_pcts": pcts,
        "league": league,
        "match_date": match_date,
        "match_date_iso": match_date_iso,
        "venue": venue,
        "fixture_id": fixture_id,
        "home_team_logo": home_team_logo,
        "away_team_logo": away_team_logo,
        "match_over": match_over,
        "final_score_home": final_score_home,
        "final_score_away": final_score_away,
        "match_statistics": match_statistics,
        "data_recap": data_recap,
    }


def load_match_context(
    home_team: str,
    away_team: str,
    progress_callback: Optional[Callable[[str, int], None]] = None,
    home_team_id: Optional[int] = None,
    away_team_id: Optional[int] = None,
) -> dict[str, Any]:
    """
    Charge tout le contexte pour un match : form, goals for/against home/away, H2H.
    Priorité: API-Football si clé → Supabase → démo.
    Si home_team_id/away_team_id sont fournis (sélection autocomplete), ils sont utilisés en priorité.
    """
    def report(step: str, percent: int) -> None:
        if progress_callback:
            progress_callback(step, percent)

    if _use_api_football():
        ctx = _load_match_context_api_football(
            home_team,
            away_team,
            progress_callback=progress_callback,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
        )
        if ctx is not None:
            return ctx

    report("Loading match data…", 10)
    h = normalize_team_name(home_team)
    a = normalize_team_name(away_team)

    report("Fetching results…", 22)
    home_goals_for, home_goals_against = get_team_results(h, is_home=True)
    away_goals_for, away_goals_against = get_team_results(a, is_home=False)

    report("Fetching form…", 38)
    home_form, hw, hd, hl = get_team_form(h)
    away_form, aw, ad, al = get_team_form(a)

    report("Fetching head-to-head…", 50)
    h2h_h, h2h_d, h2h_a = get_h2h(h, a)
    report("Computing features…", 58)

    h_for_avg, h_against_avg = compute_goals_avg(home_goals_for, home_goals_against)
    a_for_avg, a_against_avg = compute_goals_avg(away_goals_for, away_goals_against)
    lambda_home, lambda_away = compute_lambda_home_away(
        home_goals_for, home_goals_against, away_goals_for, away_goals_against
    )

    pcts = build_comparison_pcts(
        hw, hd, hl, aw, ad, al,
        h_for_avg, a_for_avg, h_against_avg, a_against_avg,
        h2h_h, h2h_d, h2h_a,
    )
    h2h_total = h2h_h + h2h_d + h2h_a
    data_recap = {
        "data_source": "Supabase",
        "form_home_matches": len(home_goals_for),
        "form_away_matches": len(away_goals_for),
        "home_goals_for_avg": round(h_for_avg, 2),
        "home_goals_against_avg": round(h_against_avg, 2),
        "away_goals_for_avg": round(a_for_avg, 2),
        "away_goals_against_avg": round(a_against_avg, 2),
        "home_wdl": form_to_wdl(home_form),
        "away_wdl": form_to_wdl(away_form),
        "h2h_matches_count": h2h_total,
        "h2h_home_wins": h2h_h,
        "h2h_draws": h2h_d,
        "h2h_away_wins": h2h_a,
        "h2h_seasons_used": None,
        "fixture_id": None,
        "has_upcoming_match": False,
        "league": None,
        "venue": None,
    }
    return {
        "home_team": home_team,
        "away_team": away_team,
        "lambda_home": lambda_home,
        "lambda_away": lambda_away,
        "home_form": home_form,
        "away_form": away_form,
        "home_wdl": form_to_wdl(home_form),
        "away_wdl": form_to_wdl(away_form),
        "home_form_label": form_to_label(hw, hd, hl),
        "away_form_label": form_to_label(aw, ad, al),
        "comparison_pcts": pcts,
        "data_recap": data_recap,
    }
