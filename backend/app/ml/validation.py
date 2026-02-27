"""
Backtest du modèle Poisson sur des matchs passés (point-in-time).
Métriques : précision 1X2, score exact dans le top 5, Over/Under 2.5.
"""
from __future__ import annotations

import time
from typing import Any, Optional

from app.ml.features import compute_goals_avg, compute_lambda_home_away
from app.ml.poisson import predict_all, exact_score_probs, prob_over_under, poisson_score_grid


def _to_jsonable(obj: Any) -> Any:
    """Convertit les types numpy en types Python pour la sérialisation JSON (FastAPI)."""
    try:
        import numpy as np
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
    except ImportError:
        pass
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    return obj


def get_team_results_before_date(
    supabase: Any,
    team_id: str,
    before_date: str,
    as_home: bool,
    last_n: int = 5,
) -> tuple[list[int], list[int]]:
    """Derniers matchs d'une équipe avant une date (point-in-time). (goals_for, goals_against)."""
    team_col = "home_team_id" if as_home else "away_team_id"
    goals_for_col = "home_goals" if as_home else "away_goals"
    goals_against_col = "away_goals" if as_home else "home_goals"
    r = (
        supabase.table("results")
        .select("date," + goals_for_col + "," + goals_against_col)
        .eq(team_col, team_id)
        .lt("date", before_date)
        .order("date", desc=True)
        .limit(last_n)
        .execute()
    )
    if not r.data:
        default = [1, 2, 1, 0, 2] if as_home else [0, 1, 1, 2, 0]
        default_a = [1, 0, 2, 1, 1] if as_home else [2, 1, 0, 1, 2]
        return (default, default_a)
    goals_for = [int(row.get(goals_for_col, 1)) for row in r.data]
    goals_against = [int(row.get(goals_against_col, 1)) for row in r.data]
    return (goals_for, goals_against)


def get_h2h_before_date(
    supabase: Any,
    home_id: str,
    away_id: str,
    before_date: str,
) -> tuple[int, int, int]:
    """H2H (home_wins, draws, away_wins) avant une date, dérivé de results."""
    r = (
        supabase.table("results")
        .select("home_team_id, home_goals, away_goals")
        .eq("home_team_id", home_id)
        .eq("away_team_id", away_id)
        .lt("date", before_date)
        .execute()
    )
    h_wins = d = a_wins = 0
    for row in r.data or []:
        hg = int(row.get("home_goals", 0))
        ag = int(row.get("away_goals", 0))
        if hg > ag:
            h_wins += 1
        elif hg < ag:
            a_wins += 1
        else:
            d += 1
    r2 = (
        supabase.table("results")
        .select("home_team_id, home_goals, away_goals")
        .eq("home_team_id", away_id)
        .eq("away_team_id", home_id)
        .lt("date", before_date)
        .execute()
    )
    for row in r2.data or []:
        hg = int(row.get("home_goals", 0))
        ag = int(row.get("away_goals", 0))
        if hg > ag:
            a_wins += 1
        elif hg < ag:
            h_wins += 1
        else:
            d += 1
    return (h_wins, d, a_wins)


def compute_lambdas_point_in_time(
    supabase: Any,
    home_id: str,
    away_id: str,
    before_date: str,
    last_n: int = 5,
) -> tuple[float, float]:
    """Calcule lambda_home, lambda_away en n'utilisant que les résultats avant before_date."""
    home_for_h, home_ag_h = get_team_results_before_date(supabase, home_id, before_date, as_home=True, last_n=last_n)
    home_for_a, home_ag_a = get_team_results_before_date(supabase, home_id, before_date, as_home=False, last_n=last_n)
    away_for_h, away_ag_h = get_team_results_before_date(supabase, away_id, before_date, as_home=True, last_n=last_n)
    away_for_a, away_ag_a = get_team_results_before_date(supabase, away_id, before_date, as_home=False, last_n=last_n)
    home_goals_for = home_for_h + home_for_a
    home_goals_against = home_ag_h + home_ag_a
    away_goals_for = away_for_h + away_for_a
    away_goals_against = away_ag_h + away_ag_a
    if not home_goals_for and not home_goals_against:
        home_goals_for, home_goals_against = [1, 2, 1, 0, 2], [1, 0, 2, 1, 1]
    if not away_goals_for and not away_goals_against:
        away_goals_for, away_goals_against = [0, 1, 1, 2, 0], [2, 1, 0, 1, 2]
    return compute_lambda_home_away(
        home_goals_for, home_goals_against,
        away_goals_for, away_goals_against,
    )


def outcome_1x2(home_goals: int, away_goals: int) -> str:
    """Retourne '1', 'X' ou '2'."""
    if home_goals > away_goals:
        return "1"
    if home_goals < away_goals:
        return "2"
    return "X"


def run_backtest(
    supabase: Any,
    *,
    league: Optional[str] = None,
    date_min: Optional[str] = None,
    date_max: Optional[str] = None,
    max_matches: Optional[int] = 500,
) -> dict[str, Any]:
    """
    Backtest point-in-time sur les résultats Supabase.
    - Filtre optionnel : league, date_min, date_max.
    - Pour chaque match : calcule les lambdas avec uniquement les résultats avant la date du match,
      prédit 1X2 / top 5 scores / Over 2.5, compare au résultat réel.
    Retourne : n_matches, accuracy_1x2, accuracy_exact_top5, accuracy_over25, details, duration_seconds.
    """
    t0 = time.perf_counter()
    league = (league or "").strip() or None
    date_min = (date_min or "").strip() or None
    date_max = (date_max or "").strip() or None
    limit = max_matches or 2000
    q = supabase.table("results").select("home_team_id, away_team_id, home_goals, away_goals, date, league").order("date", desc=False).limit(limit)
    if league:
        q = q.eq("league", league)
    if date_min:
        q = q.gte("date", date_min)
    if date_max:
        q = q.lte("date", date_max)
    r = q.execute()
    rows = r.data or []
    total_in_db = _count_results(supabase)
    if max_matches and len(rows) > max_matches:
        rows = rows[: max_matches]
    if not rows:
        if total_in_db == 0:
            error_msg = (
                "Aucun match en base. Lancez le script d'ingest pour remplir Supabase : "
                "cd backend && python scripts/ingest_matches.py (avec API_FOOTBALL_KEY et Supabase configurés)."
            )
        else:
            error_msg = (
                f"Aucun match trouvé pour les filtres (ligue, dates). Il y a {total_in_db} match(s) au total en base. "
                "Essayez sans filtre ou avec des plages plus larges."
            )
        return {
            "n_matches": 0,
            "accuracy_1x2": 0.0,
            "accuracy_exact_top5": 0.0,
            "accuracy_over25": 0.0,
            "details": [],
            "error": error_msg,
            "total_results_in_db": total_in_db,
            "duration_seconds": round(time.perf_counter() - t0, 2),
        }
    correct_1x2 = 0
    correct_exact_top5 = 0
    correct_over25 = 0
    details: list[dict] = []
    for row in rows:
        home_id = str(row.get("home_team_id") or "")
        away_id = str(row.get("away_team_id") or "")
        hg = int(row.get("home_goals", 0))
        ag = int(row.get("away_goals", 0))
        date_val = (row.get("date") or "")[:10]
        if not home_id or not away_id or not date_val:
            continue
        try:
            lambda_home, lambda_away = compute_lambdas_point_in_time(supabase, home_id, away_id, date_val)
        except Exception:
            continue
        out = predict_all(lambda_home, lambda_away)
        actual_outcome = outcome_1x2(hg, ag)
        pred_1 = out.get("prob_home") or 0
        pred_x = out.get("prob_draw") or 0
        pred_2 = out.get("prob_away") or 0
        pred_outcome = "1" if pred_1 >= pred_x and pred_1 >= pred_2 else ("X" if pred_x >= pred_2 else "2")
        if pred_outcome == actual_outcome:
            correct_1x2 += 1
        top5 = exact_score_probs(lambda_home, lambda_away, top_n=5)
        exact_hit = any((i, j) == (hg, ag) for i, j, _ in top5)
        if exact_hit:
            correct_exact_top5 += 1
        grid = poisson_score_grid(lambda_home, lambda_away)
        over_p, _ = prob_over_under(2.5, grid)
        pred_over = over_p >= 0.5
        actual_over = (hg + ag) > 2.5
        if pred_over == actual_over:
            correct_over25 += 1
        if len(details) < 30:
            home_name = _resolve_team_name_supabase(supabase, home_id) or f"Équipe {home_id}"
            away_name = _resolve_team_name_supabase(supabase, away_id) or f"Équipe {away_id}"
            details.append({
                "date": date_val,
                "home_id": home_id,
                "away_id": away_id,
                "home_name": home_name,
                "away_name": away_name,
                "score": f"{hg}-{ag}",
                "actual_1x2": actual_outcome,
                "pred_1x2": pred_outcome,
                "prob_1": round(float(pred_1), 1),
                "prob_x": round(float(pred_x), 1),
                "prob_2": round(float(pred_2), 1),
                "exact_top5": exact_hit,
                "over25_ok": pred_over == actual_over,
            })
    n = len(rows)
    duration_seconds = round(time.perf_counter() - t0, 2)
    return _to_jsonable({
        "n_matches": n,
        "accuracy_1x2": round(100.0 * correct_1x2 / n, 1) if n else 0.0,
        "accuracy_exact_top5": round(100.0 * correct_exact_top5 / n, 1) if n else 0.0,
        "accuracy_over25": round(100.0 * correct_over25 / n, 1) if n else 0.0,
        "correct_1x2": correct_1x2,
        "correct_exact_top5": correct_exact_top5,
        "correct_over25": correct_over25,
        "details": details,
        "duration_seconds": duration_seconds,
        "total_results_in_db": total_in_db,
    })


def get_data_stats(supabase: Any) -> dict[str, Any]:
    """Retourne le nombre total de matchs en base et la plage de dates (min/max)."""
    total = _count_results(supabase)
    if total == 0:
        return {"total_results": 0, "date_min": None, "date_max": None}
    try:
        r_min = supabase.table("results").select("date").order("date", desc=False).limit(1).execute()
        r_max = supabase.table("results").select("date").order("date", desc=True).limit(1).execute()
        date_min = (r_min.data or [{}])[0].get("date") if r_min.data else None
        date_max = (r_max.data or [{}])[0].get("date") if r_max.data else None
        if date_min and len(str(date_min)) > 10:
            date_min = str(date_min)[:10]
        if date_max and len(str(date_max)) > 10:
            date_max = str(date_max)[:10]
        return {"total_results": total, "date_min": date_min, "date_max": date_max}
    except Exception:
        return {"total_results": total, "date_min": None, "date_max": None}


def _count_results(supabase: Any) -> int:
    """Compte le nombre de lignes dans results (sans filtre)."""
    try:
        r = supabase.table("results").select("*", count="exact").limit(0).execute()
        if hasattr(r, "count") and r.count is not None:
            return int(r.count)
        # Fallback: fetch a batch to see if table has data
        r2 = supabase.table("results").select("id").limit(5000).execute()
        return len(r2.data or [])
    except Exception:
        return 0


def _resolve_team_name_supabase(supabase: Any, team_id: str) -> Optional[str]:
    """Résout un team_id (slug ou id API) en nom d'équipe : Supabase teams puis API-Football."""
    if not team_id:
        return None
    try:
        r = supabase.table("teams").select("name").eq("slug", team_id).limit(1).execute()
        if r.data and len(r.data) > 0 and r.data[0].get("name"):
            return str(r.data[0]["name"]).strip()
    except Exception:
        pass
    try:
        from app.services.api_football import get_team_by_id, _use_api
        if _use_api():
            info = get_team_by_id(int(team_id))
            if info and info.get("name"):
                return str(info["name"]).strip()
    except (ValueError, TypeError):
        pass
    return None


def _fixtures_to_rows(fixtures: list[dict]) -> list[dict]:
    """Convertit les fixtures API-Football en liste de {home_team_id, away_team_id, home_name, away_name, home_goals, away_goals, date}."""
    rows = []
    for f in fixtures:
        teams = f.get("teams") or {}
        goals = f.get("goals") or {}
        home = teams.get("home") or {}
        away = teams.get("away") or {}
        hid = str(home.get("id") or "")
        aid = str(away.get("id") or "")
        hg = goals.get("home")
        ag = goals.get("away")
        if hg is None or ag is None or not hid or not aid:
            continue
        fix = f.get("fixture") or {}
        date_val = (fix.get("date") or "")[:10]
        if not date_val:
            continue
        rows.append({
            "home_team_id": hid,
            "away_team_id": aid,
            "home_name": (home.get("name") or "").strip() or f"Équipe {hid}",
            "away_name": (away.get("name") or "").strip() or f"Équipe {aid}",
            "home_goals": int(hg),
            "away_goals": int(ag),
            "date": date_val,
        })
    return rows


def _team_goals_from_rows(rows: list[dict], team_id: str, before_date: str, last_n: int = 5) -> tuple[list[int], list[int]]:
    """À partir d'une liste de matchs triée par date, retourne (goals_for, goals_against) pour team_id avant before_date."""
    goals_for: list[int] = []
    goals_against: list[int] = []
    for r in reversed(rows):
        if (r.get("date") or "") >= before_date:
            continue
        hid = str(r.get("home_team_id") or "")
        aid = str(r.get("away_team_id") or "")
        hg = int(r.get("home_goals", 0))
        ag = int(r.get("away_goals", 0))
        if hid == team_id:
            goals_for.append(hg)
            goals_against.append(ag)
        elif aid == team_id:
            goals_for.append(ag)
            goals_against.append(hg)
        else:
            continue
        if len(goals_for) >= last_n:
            break
    if not goals_for:
        return ([1, 2, 1, 0, 2], [1, 0, 2, 1, 1])
    return (goals_for, goals_against)


def run_backtest_from_api(
    league_id: int,
    season: int,
    max_matches: Optional[int] = 500,
) -> dict[str, Any]:
    """
    Backtest en récupérant les matchs via l'API (une requête par ligue/saison).
    Point-in-time : pour chaque match, les lambdas sont calculés à partir des matchs précédents dans la même réponse.
    """
    from app.services.api_football import get_fixtures_by_league, _use_api

    t0 = time.perf_counter()
    if not _use_api():
        return {
            "n_matches": 0,
            "accuracy_1x2": 0.0,
            "accuracy_exact_top5": 0.0,
            "accuracy_over25": 0.0,
            "details": [],
            "error": "API-Football non configurée (API_FOOTBALL_KEY).",
            "duration_seconds": 0,
            "source": "api",
        }
    fixtures = get_fixtures_by_league(league_id, season=season, status="FT")
    rows = _fixtures_to_rows(fixtures)
    rows.sort(key=lambda x: x.get("date") or "")
    if max_matches and len(rows) > max_matches:
        rows = rows[:max_matches]
    if not rows:
        return {
            "n_matches": 0,
            "accuracy_1x2": 0.0,
            "accuracy_exact_top5": 0.0,
            "accuracy_over25": 0.0,
            "details": [],
            "error": f"Aucun match trouvé pour la ligue {league_id} et la saison {season}.",
            "duration_seconds": round(time.perf_counter() - t0, 2),
            "source": "api",
        }
    correct_1x2 = 0
    correct_exact_top5 = 0
    correct_over25 = 0
    details: list[dict] = []
    for row in rows:
        home_id = str(row.get("home_team_id") or "")
        away_id = str(row.get("away_team_id") or "")
        hg = int(row.get("home_goals", 0))
        ag = int(row.get("away_goals", 0))
        date_val = (row.get("date") or "")[:10]
        if not home_id or not away_id or not date_val:
            continue
        try:
            home_for_h, home_ag_h = _team_goals_from_rows(rows, home_id, date_val, 5)
            home_for_a, home_ag_a = _team_goals_from_rows(rows, home_id, date_val, 5)
            away_for_h, away_ag_h = _team_goals_from_rows(rows, away_id, date_val, 5)
            away_for_a, away_ag_a = _team_goals_from_rows(rows, away_id, date_val, 5)
            home_goals_for = home_for_h + home_for_a
            home_goals_against = home_ag_h + home_ag_a
            away_goals_for = away_for_h + away_for_a
            away_goals_against = away_ag_h + away_ag_a
            if not home_goals_for and not home_goals_against:
                home_goals_for, home_goals_against = [1, 2, 1, 0, 2], [1, 0, 2, 1, 1]
            if not away_goals_for and not away_goals_against:
                away_goals_for, away_goals_against = [0, 1, 1, 2, 0], [2, 1, 0, 1, 2]
            lambda_home, lambda_away = compute_lambda_home_away(
                home_goals_for, home_goals_against,
                away_goals_for, away_goals_against,
            )
        except Exception:
            continue
        out = predict_all(lambda_home, lambda_away)
        actual_outcome = outcome_1x2(hg, ag)
        pred_1 = out.get("prob_home") or 0
        pred_x = out.get("prob_draw") or 0
        pred_2 = out.get("prob_away") or 0
        pred_outcome = "1" if pred_1 >= pred_x and pred_1 >= pred_2 else ("X" if pred_x >= pred_2 else "2")
        if pred_outcome == actual_outcome:
            correct_1x2 += 1
        top5 = exact_score_probs(lambda_home, lambda_away, top_n=5)
        exact_hit = any((i, j) == (hg, ag) for i, j, _ in top5)
        if exact_hit:
            correct_exact_top5 += 1
        grid = poisson_score_grid(lambda_home, lambda_away)
        over_p, _ = prob_over_under(2.5, grid)
        pred_over = over_p >= 0.5
        actual_over = (hg + ag) > 2.5
        if pred_over == actual_over:
            correct_over25 += 1
        if len(details) < 30:
            details.append({
                "date": date_val,
                "home_id": home_id,
                "away_id": away_id,
                "home_name": (row.get("home_name") or "").strip() or f"Équipe {home_id}",
                "away_name": (row.get("away_name") or "").strip() or f"Équipe {away_id}",
                "score": f"{hg}-{ag}",
                "actual_1x2": actual_outcome,
                "pred_1x2": pred_outcome,
                "prob_1": round(float(pred_1), 1),
                "prob_x": round(float(pred_x), 1),
                "prob_2": round(float(pred_2), 1),
                "exact_top5": exact_hit,
                "over25_ok": pred_over == actual_over,
            })
    n = len(rows)
    duration_seconds = round(time.perf_counter() - t0, 2)
    return _to_jsonable({
        "n_matches": n,
        "accuracy_1x2": round(100.0 * correct_1x2 / n, 1) if n else 0.0,
        "accuracy_exact_top5": round(100.0 * correct_exact_top5 / n, 1) if n else 0.0,
        "accuracy_over25": round(100.0 * correct_over25 / n, 1) if n else 0.0,
        "correct_1x2": correct_1x2,
        "correct_exact_top5": correct_exact_top5,
        "correct_over25": correct_over25,
        "details": details,
        "duration_seconds": duration_seconds,
        "source": "api",
    })
