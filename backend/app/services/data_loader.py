# backend/app/services/data_loader.py
"""
Charge les données équipes/matchs pour le feature engineering.
Priorité: 1) API football-data.org (v4) si token configuré, 2) Supabase, 3) démo.
"""
from typing import Any
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


def _use_football_data() -> bool:
    return bool(get_settings().football_data_api_token)


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


def _load_match_context_football_data(home_team: str, away_team: str) -> dict[str, Any] | None:
    """
    Charge le contexte match via l'API football-data.org (v4).
    Retourne None si token absent ou équipes non résolues.
    """
    from app.services.football_data import (
        resolve_team_name_to_id,
        get_team_matches,
        team_matches_to_goals_and_form,
        get_h2h_from_matches,
    )
    home_id = resolve_team_name_to_id(home_team)
    away_id = resolve_team_name_to_id(away_team)
    if home_id is None or away_id is None:
        return None
    home_matches = get_team_matches(home_id, status="FINISHED", limit=10)
    away_matches = get_team_matches(away_id, status="FINISHED", limit=10)
    home_goals_for, home_goals_against, home_form = team_matches_to_goals_and_form(
        home_id, home_matches, last_n=5
    )
    away_goals_for, away_goals_against, away_form = team_matches_to_goals_and_form(
        away_id, away_matches, last_n=5
    )
    if not home_goals_for and not home_goals_against:
        home_goals_for, home_goals_against = [1, 2, 1, 0, 2], [1, 0, 2, 1, 1]
    if not away_goals_for and not away_goals_against:
        away_goals_for, away_goals_against = [0, 1, 1, 2, 0], [2, 1, 0, 1, 2]
    if not home_form:
        home_form = ["W", "D", "L", "W", "W"]
    if not away_form:
        away_form = ["W", "D", "L", "W", "W"]
    h2h_matches = [m for m in home_matches if (m.get("awayTeam") or {}).get("id") == away_id or (m.get("homeTeam") or {}).get("id") == away_id]
    h2h_h, h2h_d, h2h_a = get_h2h_from_matches(home_id, away_id, h2h_matches)
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
    )
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
    }


def load_match_context(home_team: str, away_team: str) -> dict[str, Any]:
    """
    Charge tout le contexte pour un match : form, goals for/against home/away, H2H.
    Priorité: football-data.org (v4) si token → Supabase → démo.
    """
    if _use_football_data():
        ctx = _load_match_context_football_data(home_team, away_team)
        if ctx is not None:
            return ctx

    h = normalize_team_name(home_team)
    a = normalize_team_name(away_team)

    home_goals_for, home_goals_against = get_team_results(h, is_home=True)
    away_goals_for, away_goals_against = get_team_results(a, is_home=False)

    home_form, hw, hd, hl = get_team_form(h)
    away_form, aw, ad, al = get_team_form(a)

    h2h_h, h2h_d, h2h_a = get_h2h(h, a)

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
    }
