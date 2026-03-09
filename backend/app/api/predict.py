# backend/app/api/predict.py
import json
import logging
import queue
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, HTTPException, Query, Header
from fastapi.responses import StreamingResponse

from app.schemas.predict import (
    PredictRequest,
    PredictResponse,
    TranslateRequest,
    ChatRequest,
    OverUnderItem,
    ExactScoreItem,
    MostLikelyScoreItem,
    AsianHandicapItem,
)
from app.services.data_loader import load_match_context
from app.ml.poisson import predict_all
from app.services.openai_summary import build_prompt_context, generate_ai_analysis, generate_ai_analysis_sportmonks, translate_analysis, chat_ai_reply
from app.services.news_fetcher import fetch_football_news
from app.services.news_scraper import fetch_news_multi_source, format_news_for_prompt
from app.services.motivation_analysis import run_motivation_analysis
from app.services.api_football import get_predictions as api_get_predictions
from app.services.subscription import can_analyze, consume_analysis, can_use_chat_ai, consume_chat_ai

router = APIRouter(prefix="/predict", tags=["predict"])


def _save_analysis_news(
    home_team: str,
    away_team: str,
    league: Optional[str],
    scraped_items: list,
    motivation_text: str,
) -> None:
    """Persist scraped news and motivation analysis to Supabase (analysis_news + analysis_motivation tables)."""
    try:
        from app.core.config import get_settings
        from app.core.supabase_client import get_supabase
        s = get_settings()
        if not (s.supabase_url and s.supabase_key):
            return
        supabase = get_supabase()
        for it in scraped_items:
            supabase.table("analysis_news").insert({
                "home_team": home_team,
                "away_team": away_team,
                "league": league or "",
                "source": it.get("source") or "",
                "title": (it.get("title") or "")[:500],
                "snippet": (it.get("snippet") or "")[:2000],
                "url": (it.get("url") or "")[:1000],
                "keywords_found": it.get("keywords_found") or [],
            }).execute()
        if motivation_text and motivation_text.strip():
            supabase.table("analysis_motivation").insert({
                "home_team": home_team,
                "away_team": away_team,
                "league": league or "",
                "analysis_text": motivation_text.strip()[:15000],
            }).execute()
    except Exception:
        pass


def _parse_pct(s: str) -> float:
    if not s:
        return 0.0
    s = str(s).strip().rstrip("%")
    try:
        return round(float(s), 1)
    except ValueError:
        return 0.0


def _implied_odds(p: float) -> float:
    return round(100 / max(p, 0.5), 2) if p else 0.0


def _is_two_legged_league(league: Optional[str]) -> bool:
    """True if competition uses two-legged ties (LDC, Europa, Conference League)."""
    if not league or not isinstance(league, str):
        return False
    name = league.strip().lower()
    return (
        "champions league" in name
        or "europa league" in name
        or "europa conference" in name
        or "conference league" in name
    )


def _apply_two_legged_draw_zero(
    out: dict,
    league: Optional[str],
    first_leg_home_goals: Optional[int],
    first_leg_away_goals: Optional[int],
) -> None:
    """
    If league is two-legged and first leg was a draw, set prob_draw to 0 and
    renormalize prob_home / prob_away (départage obligatoire en match retour).
    """
    if not _is_two_legged_league(league):
        return
    if first_leg_home_goals is None or first_leg_away_goals is None:
        return
    if first_leg_home_goals != first_leg_away_goals:
        return
    p1 = float(out.get("prob_home") or 0)
    p2 = float(out.get("prob_away") or 0)
    px = float(out.get("prob_draw") or 0)
    if px <= 0:
        return
    total_win = p1 + p2
    if total_win <= 0:
        return
    out["prob_home"] = round(100 * p1 / total_win, 1)
    out["prob_draw"] = 0.0
    out["prob_away"] = round(100 * p2 / total_win, 1)
    out["implied_odds_home"] = _implied_odds(out["prob_home"])
    out["implied_odds_draw"] = None
    out["implied_odds_away"] = _implied_odds(out["prob_away"])
    out["double_chance_1x"] = round(out["prob_home"], 1)
    out["double_chance_x2"] = round(out["prob_away"], 1)
    out["double_chance_12"] = round(out["prob_home"] + out["prob_away"], 1)
    out["upset_probability"] = round(min(out["prob_home"], out["prob_away"]), 1)


def _apply_motivation_to_1x2(out: dict, ctx: dict) -> None:
    """
    Ajuste prob_home / prob_draw / prob_away selon la motivation des équipes
    (home_motivation_score, away_motivation_score dans ctx). Renormalise à 100%.
    Applique le même ajustement aux internal_prob_* pour que l'affichage "Model win probabilities" reflète la motivation.
    """
    home_score = ctx.get("home_motivation_score")
    away_score = ctx.get("away_motivation_score")
    if home_score is None and away_score is None:
        return
    try:
        h = float(home_score) if home_score is not None else 0.0
        a = float(away_score) if away_score is not None else 0.0
    except (TypeError, ValueError):
        return
    diff = h - a
    if diff == 0:
        return
    # Shift at most 6% toward the more motivated team (2% per point of difference, cap 3 points)
    shift = max(-6.0, min(6.0, diff * 2.0))
    p1 = float(out.get("prob_home") or 0)
    px = float(out.get("prob_draw") or 0)
    p2 = float(out.get("prob_away") or 0)
    p1 += shift
    p2 -= shift
    total = p1 + px + p2
    if total <= 0:
        return
    out["prob_home"] = round(100 * p1 / total, 1)
    out["prob_draw"] = round(100 * px / total, 1)
    out["prob_away"] = round(100 * p2 / total, 1)
    out["implied_odds_home"] = _implied_odds(out["prob_home"])
    out["implied_odds_draw"] = _implied_odds(out["prob_draw"])
    out["implied_odds_away"] = _implied_odds(out["prob_away"])
    out["double_chance_1x"] = round(out["prob_home"] + out["prob_draw"], 1)
    out["double_chance_x2"] = round(out["prob_draw"] + out["prob_away"], 1)
    out["double_chance_12"] = round(out["prob_home"] + out["prob_away"], 1)
    out["upset_probability"] = round(min(out["prob_home"], out["prob_away"]), 1)
    # Appliquer le même shift aux internal_prob_* (affichées dans "Model win probabilities") pour cohérence avec la motivation
    i1 = out.get("internal_prob_home")
    ix = out.get("internal_prob_draw")
    i2 = out.get("internal_prob_away")
    if i1 is not None and ix is not None and i2 is not None:
        i1 = float(i1) + shift
        i2 = float(i2) - shift
        itotal = i1 + ix + i2
        if itotal > 0:
            out["internal_prob_home"] = round(100 * i1 / itotal, 1)
            out["internal_prob_draw"] = round(100 * float(ix) / itotal, 1)
            out["internal_prob_away"] = round(100 * i2 / itotal, 1)


def _apply_recent_performance_to_internal(out: dict, ctx: dict) -> None:
    """
    Blend recent performance (overall bar: attack/defense/form/h2h/goals) into Model win probabilities.
    Soft shift: if overall_home_pct > 50, shift a few % from away to home (and vice versa). Draw unchanged proportionally.
    """
    pcts = ctx.get("comparison_pcts") or {}
    overall_home = pcts.get("overall_home_pct")
    if overall_home is None:
        return
    try:
        oh = float(overall_home)
    except (TypeError, ValueError):
        return
    # shift in [-4, +4] from (overall_home - 50) * 0.1
    shift = max(-4.0, min(4.0, (oh - 50.0) * 0.1))
    if shift == 0:
        return
    i1 = out.get("internal_prob_home")
    ix = out.get("internal_prob_draw")
    i2 = out.get("internal_prob_away")
    if i1 is None or ix is None or i2 is None:
        return
    i1 = float(i1) + shift
    i2 = float(i2) - shift
    itotal = i1 + ix + i2
    if itotal <= 0:
        return
    out["internal_prob_home"] = round(100 * i1 / itotal, 1)
    out["internal_prob_draw"] = round(100 * float(ix) / itotal, 1)
    out["internal_prob_away"] = round(100 * i2 / itotal, 1)


def _out_from_sportmonks(ctx: dict) -> dict:
    """
    Construit l'objet `out` à partir du contexte Sportmonks (data_recap.sportmonks_predictions).
    Utilise UNIQUEMENT les données de l'API Sportmonks, pas de valeurs approximées.
    Les champs non disponibles dans l'API sont retournés comme None ou listes vides.
    """
    recap = ctx.get("data_recap") or {}
    sp = recap.get("sportmonks_predictions") or {}

    # Données de l'API Sportmonks uniquement
    prob_home = round(float(sp.get("home_win") or 0), 1)
    prob_draw = round(float(sp.get("draw") or 0), 1)
    prob_away = round(float(sp.get("away_win") or 0), 1)
    xg_home = round(float(sp.get("xg_home") or 0), 2)
    xg_away = round(float(sp.get("xg_away") or 0), 2)
    xg_total = round(xg_home + xg_away, 2)

    # Over/Under : lignes disponibles de l'API (0.5/1.5/2.5/3.5...), fallback sur 2.5
    over_25 = float(sp.get("over_2_5") or 0)
    under_25 = float(sp.get("under_2_5") or 0)
    over_under_raw = sp.get("over_under_lines")
    over_under: list[dict] = []
    if isinstance(over_under_raw, list):
        for row in over_under_raw:
            if not isinstance(row, dict):
                continue
            line = str(row.get("line") or "").strip()
            try:
                over_pct = float(row.get("over_pct") or 0)
                under_pct = float(row.get("under_pct") or 0)
            except Exception:
                continue
            if line:
                over_under.append({"line": line, "over_pct": round(over_pct, 2), "under_pct": round(under_pct, 2)})
    if not over_under:
        over_under = [{"line": "2.5", "over_pct": over_25, "under_pct": under_25}]
    over_under.sort(key=lambda x: float(x["line"]) if str(x.get("line", "")).replace(".", "", 1).isdigit() else 99.0)

    # BTTS de l'API
    btts_yes = float(sp.get("btts_yes") or 0)
    btts_no = float(sp.get("btts_no") or 0)

    exact_scores = sp.get("exact_scores") if isinstance(sp.get("exact_scores"), list) else []
    most_likely_score = exact_scores[0] if exact_scores else None

    return {
        "xg_home": xg_home,
        "xg_away": xg_away,
        "xg_total": xg_total,
        "prob_home": prob_home,
        "prob_draw": prob_draw,
        "prob_away": prob_away,
        "implied_odds_home": _implied_odds(prob_home) if prob_home > 0 else None,
        "implied_odds_draw": _implied_odds(prob_draw) if prob_draw > 0 else None,
        "implied_odds_away": _implied_odds(prob_away) if prob_away > 0 else None,
        "btts_yes_pct": btts_yes,
        "btts_no_pct": btts_no,
        "over_under": over_under,
        "exact_scores": exact_scores,
        "most_likely_score": most_likely_score,
        "total_goals_distribution": None,
        "goal_difference_dist": None,
        "double_chance_1x": round(prob_home + prob_draw, 1),
        "double_chance_x2": round(prob_draw + prob_away, 1),
        "double_chance_12": round(prob_home + prob_away, 1),
        "asian_handicap": None,
        "upset_probability": round(min(prob_home, prob_away), 1),
        "api_advice": None,
    }


def _out_from_api_predictions(api_pred: dict) -> dict:
    """
    Construit l'objet `out` UNIQUEMENT à partir de la réponse API-Football Predictions.
    Aucune donnée de notre modèle Poisson : pas d'interférence.
    Les champs que l'API ne fournit pas (BTTS, exact_scores, grille over/under complète)
    sont mis en valeurs neutres (50/50, liste vide) pour garder le schéma de réponse valide.
    """
    pred = api_pred.get("predictions") or {}
    pct = pred.get("percent") or {}
    prob_home = _parse_pct(pct.get("home"))
    prob_draw = _parse_pct(pct.get("draw"))
    prob_away = _parse_pct(pct.get("away"))

    # xG : l'API peut avoir teams.home.last_5.goals.for.average (string "0.6")
    teams = api_pred.get("teams") or {}
    home_team_data = teams.get("home") or {}
    away_team_data = teams.get("away") or {}
    home_goals = home_team_data.get("last_5") or {}
    away_goals = away_team_data.get("last_5") or {}
    h_for = (home_goals.get("goals") or {}).get("for") or {}
    h_against = (home_goals.get("goals") or {}).get("against") or {}
    a_for = (away_goals.get("goals") or {}).get("for") or {}
    a_against = (away_goals.get("goals") or {}).get("against") or {}

    def _avg(d: dict, key: str) -> float:
        v = d.get(key) if isinstance(d, dict) else None
        if v is None:
            return 0.0
        try:
            return round(float(str(v).replace(",", ".")), 2)
        except ValueError:
            return 0.0

    xg_home = _avg(h_for, "average") or 0.0
    xg_away = _avg(a_for, "average") or 0.0
    if xg_home == 0.0 and xg_away == 0.0:
        xg_home = 1.0
        xg_away = 1.0
    xg_total = round(xg_home + xg_away, 2)

    # Over/Under : l'API donne une seule ligne (ex. "-3.5" = under 3.5, "+2.5" = over 2.5). Les autres lignes en 50/50
    under_over_raw = (pred.get("under_over") or "").strip()
    api_line = under_over_raw.lstrip("+-").strip() if under_over_raw else None
    over_under = []
    for line in ["0.5", "1.5", "2.5", "3.5"]:
        if api_line == line and under_over_raw.startswith("-"):
            over_under.append({"line": line, "over_pct": 30.0, "under_pct": 70.0})
        elif api_line == line and under_over_raw.startswith("+"):
            over_under.append({"line": line, "over_pct": 70.0, "under_pct": 30.0})
        else:
            over_under.append({"line": line, "over_pct": 50.0, "under_pct": 50.0})

    # Double chance dérivées uniquement du 1X2 API
    double_chance_1x = round(prob_home + prob_draw, 1)
    double_chance_x2 = round(prob_draw + prob_away, 1)
    double_chance_12 = round(prob_home + prob_away, 1)
    upset = round(min(prob_home, prob_away), 1)

    return {
        "xg_home": round(xg_home, 2),
        "xg_away": round(xg_away, 2),
        "xg_total": xg_total,
        "prob_home": prob_home,
        "prob_draw": prob_draw,
        "prob_away": prob_away,
        "implied_odds_home": _implied_odds(prob_home),
        "implied_odds_draw": _implied_odds(prob_draw),
        "implied_odds_away": _implied_odds(prob_away),
        "btts_yes_pct": 50.0,
        "btts_no_pct": 50.0,
        "over_under": over_under,
        "exact_scores": [],
        "most_likely_score": {"home": 0, "away": 0, "probability": 0.0},
        "total_goals_distribution": {"0": 25.0, "1": 25.0, "2": 25.0, "3+": 25.0},
        "goal_difference_dist": {"1": 34.0, "2": 33.0, "3+": 33.0},
        "double_chance_1x": double_chance_1x,
        "double_chance_x2": double_chance_x2,
        "double_chance_12": double_chance_12,
        "asian_handicap": {
            "home_neg1_pct": 50.0,
            "home_plus1_pct": 50.0,
            "away_neg1_pct": 50.0,
            "away_plus1_pct": 50.0,
        },
        "upset_probability": upset,
        "api_advice": (pred.get("advice") or "").strip() or None,
    }


def _build_analysis_recap(
    ctx: dict,
    out: dict,
    prob_source: str,
    news_included: bool,
) -> dict:
    """Build a detailed recap of all data used for this analysis (per match): steps + data from API."""
    recap = ctx.get("data_recap") or {}
    steps = list(recap.get("pipeline_steps") or [])
    # Append steps done in predict pipeline (probabilities, AI)
    xg_h = out.get("xg_home")
    xg_a = out.get("xg_away")
    ph = out.get("prob_home")
    pd_ = out.get("prob_draw")
    pa = out.get("prob_away")
    ph_s = f"{round(ph, 1)}" if isinstance(ph, (int, float)) else "—"
    pd_s = f"{round(pd_, 1)}" if isinstance(pd_, (int, float)) else "—"
    pa_s = f"{round(pa, 1)}" if isinstance(pa, (int, float)) else "—"
    steps.append({
        "order": 10,
        "title_key": "recap.step.probabilities",
        "detail": f"Model: {prob_source}. Input: lambda_home={ctx.get('lambda_home')}, lambda_away={ctx.get('lambda_away')}. "
        f"Output: xG {xg_h}–{xg_a}, 1X2 (Home {ph_s}% / Draw {pd_s}% / Away {pa_s}%), "
        "BTTS, Over/Under 0.5–3.5, exact scores, double chance, Asian handicap.",
    })
    steps.append({
        "order": 11,
        "title_key": "recap.step.ai_context",
        "detail": "Context built for AI: match names, xG, 1X2 probabilities, form labels, league, venue.",
    })
    if news_included:
        steps.append({
            "order": 12,
            "title_key": "recap.step.news",
            "detail": "NewsAPI + Google News RSS (team, injury, lineup, rotation). Twitter insiders via Nitter RSS (league-based: Ornstein, Romano, Laurens, etc.) for lineup/injury/rotation leaks. Snippets + keyword detection added to context.",
        })
    steps.append({
        "order": 13,
        "title_key": "recap.step.openai",
        "detail": "1 request: OpenAI chat.completions (gpt-4o-mini). Response: quick_summary, scenario_1–4, key_forces_home, key_forces_away.",
    })
    steps.sort(key=lambda s: (s["order"], s.get("title_key", "")))
    pcts = ctx.get("comparison_pcts") or {}

    # Period for all form-based stats (Attack, Defense, Goals, Form)
    stats_period = (
        "Attack, Defense, Goals: last 30 matches per team (recency-weighted, decay 0.95). Form bar: last 5 (W-D-L). "
        "H2H: all head-to-head matches found over up to 5 seasons (recency weighted with weight = 0.6^years_ago). "
        "Poisson lambdas use the same 30-match weighted goals. Model win probabilities blend xG, motivation and recent performance (overall bar)."
    )
    # How we compute each comparison bar
    how_bars_work = {
        "attack": "Home % = 100 × (home weighted avg goals scored) / (home + away). Last 30 matches, recency-weighted.",
        "defense": "Home % = 100 × (1 / home weighted avg goals conceded) / (1/home + 1/away). Last 30 matches, recency-weighted.",
        "goals": "Same formula as Attack: share of total goals scored (last 30 each, recency-weighted).",
        "form": "Home % = 100 × (home points) / (home + away points), with points = 3×W + 1×D + 0×L over last 5.",
        "h2h": "Home % = (home wins + 0.5×draws) / total H2H × 100, weighted by recency with weight = 0.6^years_ago.",
        "overall": "Average of the 5 bars above (attack, defense, form, h2h, goals), each with weight 1/5.",
    }
    # How we predict the score
    how_score_prediction_works = (
        "Poisson model. Base λ_home = (home_goals_for_avg × away_goals_against_avg) / (league_avg/2), "
        "base λ_away = (away_goals_for_avg × home_goals_against_avg) / (league_avg/2). league_avg = 2.7. "
        "Then blend with home/away split (home-at-home vs away-away), apply fatigue multiplier "
        "(matches in last 7 days + rest days), and blend recent xG when available. Lambdas clamped 0.2 to 4.0. "
        "P(score i–j) = Poisson(i | λ_home) × Poisson(j | λ_away). "
        "1X2: P(Home)=sum i>j, P(Draw)=sum i=j, P(Away)=sum i<j. "
        "BTTS Yes = sum P(i,j) for i≥1, j≥1. Over/Under = sum P(i,j) for i+j > line. "
        "Exact scores = grid sorted by probability; most likely = highest P(i,j)."
    )
    # All raw data we have from API + computed values (so user sees every number used)
    raw_data = {
        "home_goals_for_last5": recap.get("raw_home_goals_for") or [],
        "home_goals_against_last5": recap.get("raw_home_goals_against") or [],
        "away_goals_for_last5": recap.get("raw_away_goals_for") or [],
        "away_goals_against_last5": recap.get("raw_away_goals_against") or [],
        "home_form_last5": recap.get("raw_home_form") or [],
        "away_form_last5": recap.get("raw_away_form") or [],
        "averages": {
            "home_goals_for": recap.get("home_goals_for_avg"),
            "home_goals_against": recap.get("home_goals_against_avg"),
            "away_goals_for": recap.get("away_goals_for_avg"),
            "away_goals_against": recap.get("away_goals_against_avg"),
        },
        "lambdas": {
            "lambda_home": ctx.get("lambda_home"),
            "lambda_away": ctx.get("lambda_away"),
        },
        "advanced_metrics": {
            "home": recap.get("home_advanced_metrics") or {},
            "away": recap.get("away_advanced_metrics") or {},
        },
        "comparison_pcts": {
            "attack_home_pct": pcts.get("attack_home_pct"),
            "defense_home_pct": pcts.get("defense_home_pct"),
            "form_home_pct": pcts.get("form_home_pct"),
            "h2h_home_pct": pcts.get("h2h_home_pct"),
            "goals_home_pct": pcts.get("goals_home_pct"),
            "overall_home_pct": pcts.get("overall_home_pct"),
        },
        "h2h": {
            "home_wins": recap.get("h2h_home_wins"),
            "draws": recap.get("h2h_draws"),
            "away_wins": recap.get("h2h_away_wins"),
            "matches_count": recap.get("h2h_matches_count"),
            "raw_home_wins": recap.get("h2h_raw_home_wins"),
            "raw_draws": recap.get("h2h_raw_draws"),
            "raw_away_wins": recap.get("h2h_raw_away_wins"),
            "raw_matches_count": recap.get("h2h_raw_matches_count"),
            "season_breakdown": recap.get("h2h_season_breakdown") or [],
            "weighting": recap.get("h2h_weighting") or [],
        },
    }
    return {
        "data_source": recap.get("data_source", "Unknown"),
        "stats_period": stats_period,
        "how_bars_work": how_bars_work,
        "how_score_prediction_works": how_score_prediction_works,
        "raw_data": raw_data,
        "form": {
            "home_matches_used": recap.get("form_home_matches"),
            "away_matches_used": recap.get("form_away_matches"),
            "home_goals_for_avg": recap.get("home_goals_for_avg"),
            "home_goals_against_avg": recap.get("home_goals_against_avg"),
            "away_goals_for_avg": recap.get("away_goals_for_avg"),
            "away_goals_against_avg": recap.get("away_goals_against_avg"),
            "home_wdl": recap.get("home_wdl"),
            "away_wdl": recap.get("away_wdl"),
        },
        "h2h": {
            "matches_count": recap.get("h2h_matches_count"),
            "home_wins": recap.get("h2h_home_wins"),
            "draws": recap.get("h2h_draws"),
            "away_wins": recap.get("h2h_away_wins"),
            "seasons_used": recap.get("h2h_seasons_used"),
            "raw_matches_count": recap.get("h2h_raw_matches_count"),
            "raw_home_wins": recap.get("h2h_raw_home_wins"),
            "raw_draws": recap.get("h2h_raw_draws"),
            "raw_away_wins": recap.get("h2h_raw_away_wins"),
            "season_breakdown": recap.get("h2h_season_breakdown") or [],
            "weighting": recap.get("h2h_weighting") or [],
        },
        "probabilities": {
            "model": prob_source,
            "lambda_home": ctx.get("lambda_home"),
            "lambda_away": ctx.get("lambda_away"),
            "xg_home": xg_h,
            "xg_away": xg_a,
            "sportmonks_unavailable_reason": recap.get("sportmonks_predictions_unavailable_reason"),
        },
        "match_info": {
            "fixture_id": recap.get("fixture_id"),
            "has_upcoming_match": recap.get("has_upcoming_match"),
            "league": recap.get("league") or ctx.get("league"),
            "venue": recap.get("venue") or ctx.get("venue"),
        },
        "motivation": {
            "match_context_summary": recap.get("match_context_summary") or ctx.get("match_context_summary"),
            "home_motivation_score": recap.get("home_motivation_score") or ctx.get("home_motivation_score"),
            "away_motivation_score": recap.get("away_motivation_score") or ctx.get("away_motivation_score"),
            "home_motivation_label": recap.get("home_motivation_label") or ctx.get("home_motivation_label"),
            "away_motivation_label": recap.get("away_motivation_label") or ctx.get("away_motivation_label"),
        },
        "ai_summary": {
            "news_included": news_included,
            "context_used": "stats + form + H2H" + (" + football news" if news_included else ""),
        },
        "api_requests_estimate": "~17–21 requests (API-Football)" if recap.get("data_source") == "API-Football" else None,
        "pipeline_steps": steps,
        "sportmonks_fixture_with_predictions": recap.get("sportmonks_fixture_with_predictions"),
        "sportmonks_value_bets": recap.get("sportmonks_value_bets"),
    }


def _build_response(
    ctx: dict,
    out: dict,
    ai: dict,
    analysis_recap: Optional[dict] = None,
) -> dict:
    pcts = ctx.get("comparison_pcts") or {}
    resp = {
        "home_team": ctx["home_team"],
        "away_team": ctx["away_team"],
        "league": ctx.get("league"),
        "match_date": ctx.get("match_date"),
        "match_date_iso": ctx.get("match_date_iso"),
        "venue": ctx.get("venue"),
        "home_team_logo": ctx.get("home_team_logo"),
        "away_team_logo": ctx.get("away_team_logo"),
        "xg_home": out["xg_home"],
        "xg_away": out["xg_away"],
        "xg_total": out["xg_total"],
        "prob_home": out["prob_home"],
        "prob_draw": out["prob_draw"],
        "prob_away": out["prob_away"],
        "implied_odds_home": out.get("implied_odds_home"),
        "implied_odds_draw": out.get("implied_odds_draw"),
        "implied_odds_away": out.get("implied_odds_away"),
        "internal_prob_home": out.get("internal_prob_home"),
        "internal_prob_draw": out.get("internal_prob_draw"),
        "internal_prob_away": out.get("internal_prob_away"),
        "most_likely_score": out.get("most_likely_score"),
        "total_goals_distribution": out.get("total_goals_distribution"),
        "goal_difference_dist": out.get("goal_difference_dist"),
        "double_chance_1x": out.get("double_chance_1x"),
        "double_chance_x2": out.get("double_chance_x2"),
        "double_chance_12": out.get("double_chance_12"),
        "asian_handicap": out.get("asian_handicap"),
        "upset_probability": out.get("upset_probability"),
        "btts_yes_pct": out["btts_yes_pct"],
        "btts_no_pct": out["btts_no_pct"],
        "over_under": out["over_under"],
        "exact_scores": out["exact_scores"],
        "home_form": ctx.get("home_form"),
        "away_form": ctx.get("away_form"),
        "home_wdl": ctx.get("home_wdl"),
        "away_wdl": ctx.get("away_wdl"),
        "home_form_label": ctx.get("home_form_label"),
        "away_form_label": ctx.get("away_form_label"),
        "quick_summary": ai.get("quick_summary"),
        "scenario_1": ai.get("scenario_1"),
        "scenario_2": ai.get("scenario_2"),
        "scenario_3": ai.get("scenario_3"),
        "scenario_4": ai.get("scenario_4"),
        "key_forces_home": ai.get("key_forces_home") or [],
        "key_forces_away": ai.get("key_forces_away") or [],
        "professional_analysis": ai.get("professional_analysis"),
        "api_advice": out.get("api_advice"),
        "ai_confidence": "Very high",
        "attack_home_pct": pcts.get("attack_home_pct"),
        "defense_home_pct": pcts.get("defense_home_pct"),
        "form_home_pct": pcts.get("form_home_pct"),
        "h2h_home_pct": pcts.get("h2h_home_pct"),
        "goals_home_pct": pcts.get("goals_home_pct"),
        "overall_home_pct": pcts.get("overall_home_pct"),
        "match_over": ctx.get("match_over"),
        "final_score_home": ctx.get("final_score_home"),
        "final_score_away": ctx.get("final_score_away"),
        "match_statistics": ctx.get("match_statistics"),
        "home_team_id": ctx.get("home_team_id"),
        "away_team_id": ctx.get("away_team_id"),
        "match_context_summary": ctx.get("match_context_summary"),
        "home_motivation_score": ctx.get("home_motivation_score"),
        "away_motivation_score": ctx.get("away_motivation_score"),
        "home_motivation_label": ctx.get("home_motivation_label"),
        "away_motivation_label": ctx.get("away_motivation_label"),
    }
    if analysis_recap is not None:
        resp["analysis_recap"] = analysis_recap
    # Format Sportmonks (fixture + predictions avec type) pour affichage / réutilisation
    sportmonks_fixture = (ctx.get("data_recap") or {}).get("sportmonks_fixture_with_predictions")
    if sportmonks_fixture is not None:
        resp["sportmonks_fixture_with_predictions"] = sportmonks_fixture
    # Value bets (bookmaker, odd, fair_odd, stake, bet, is_value) — Sportmonks Predictions add-on
    value_bets = (ctx.get("data_recap") or {}).get("sportmonks_value_bets")
    if value_bets is not None:
        resp["value_bets"] = value_bets
    return resp


def run_predict_with_progress(
    payload: PredictRequest,
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> dict:
    """Run full prediction and call progress_callback(step: str, percent: int) along the way."""
    def report(step: str, percent: int) -> None:
        if progress_callback:
            progress_callback(step, percent)

    report("Initializing…", 0)
    ctx = load_match_context(
        payload.home_team,
        payload.away_team,
        progress_callback=progress_callback,
        home_team_id=payload.home_team_id,
        away_team_id=payload.away_team_id,
    )
    if not ctx:
        raise HTTPException(status_code=404, detail="No fixture found for this match.")
    # On ne bloque plus en 503 si prédictions API absentes : on continue avec Poisson (form + xG) et on affiche l'analyse
    report("Computing probabilities…", 62)

    used_api_predictions = False
    if ctx.get("_sportmonks_use_predictions"):
        out = _out_from_sportmonks(ctx)
    elif payload.use_api_predictions and ctx.get("fixture_id"):
        api_pred = api_get_predictions(ctx["fixture_id"])
        if api_pred:
            out = _out_from_api_predictions(api_pred)
            used_api_predictions = True
        else:
            out = predict_all(ctx["lambda_home"], ctx["lambda_away"])
    else:
        out = predict_all(ctx["lambda_home"], ctx["lambda_away"])

    # Toujours calculer notre modèle interne pour comparer avec Sportmonks / API.
    internal_out = predict_all(ctx["lambda_home"], ctx["lambda_away"])
    out["internal_prob_home"] = round(float(internal_out.get("prob_home") or 0), 1)
    out["internal_prob_draw"] = round(float(internal_out.get("prob_draw") or 0), 1)
    out["internal_prob_away"] = round(float(internal_out.get("prob_away") or 0), 1)
    # Toujours utiliser le modèle Poisson interne pour over/under (plus fiable que les prédictions Sportmonks qui renvoient 50/50).
    out["over_under"] = internal_out["over_under"]

    # LDC / Europa / Conference : si match aller nul → proba nul = 0 % (départage obligatoire).
    _apply_two_legged_draw_zero(
        out,
        ctx.get("league"),
        payload.first_leg_home_goals,
        payload.first_leg_away_goals,
    )
    # Ajuster 1X2 selon la motivation des équipes.
    _apply_motivation_to_1x2(out, ctx)
    # Mélanger les barres "recent performance" (overall) dans les Model win probabilities (internal_prob_*).
    _apply_recent_performance_to_internal(out, ctx)

    ai: dict = {}
    news_included = False
    scraped_items: list = []
    motivation_text = ""

    # Scrape news for context
    report("Fetching news…", 68)
    try:
        # Essayer d'abord les news externes (NewsAPI, Google News, etc.)
        scraped_items = fetch_news_multi_source(
            ctx.get("home_team", ""),
            ctx.get("away_team", ""),
            ctx.get("league"),
        )

        # Si Sportmonks activé, ajouter les commentaires de match
        if ctx.get("_sportmonks_use_predictions"):
            from app.services.sportmonks import get_match_news_and_comments
            sportmonks_news = get_match_news_and_comments(
                fixture_id=ctx.get("fixture_id"),
                home_team_id=ctx.get("home_team_id"),
                away_team_id=ctx.get("away_team_id"),
                match_date=ctx.get("match_date_iso"),
            )
            if sportmonks_news:
                scraped_items.extend(sportmonks_news)
                print(f"[predict] Added {len(sportmonks_news)} Sportmonks commentary items")

        if scraped_items:
            news_included = True
            print(f"[predict] Total news items: {len(scraped_items)}")
    except Exception as e:
        print(f"[predict] News scraping failed: {e}")

    # Generate AI summary with news context
    report("Generating AI summary…", 75)
    try:
        if ctx.get("_sportmonks_use_predictions"):
            # Build news context for Sportmonks
            scraped_news_formatted = format_news_for_prompt(scraped_items) if news_included else None

            # Generate AI analysis (we'll need to modify generate_ai_analysis_sportmonks to accept news)
            ai = generate_ai_analysis_sportmonks(ctx, out, language=payload.language, news_context=scraped_news_formatted)

            # Put news-style match context at the top of quick_summary (avoid duplicating Match Importance block shown below)
            top_parts = []
            if ctx.get("match_context_summary"):
                top_parts.append(ctx["match_context_summary"].strip())
            if top_parts:
                block = "\n\n".join(top_parts)
                ai["quick_summary"] = (block + "\n\n" + (ai.get("quick_summary") or "").strip()).strip()
        else:
            prompt_ctx = build_prompt_context(
                ctx["home_team"],
                ctx["away_team"],
                out["xg_home"],
                out["xg_away"],
                out["prob_home"],
                out["prob_draw"],
                out["prob_away"],
                ctx.get("home_form_label"),
                ctx.get("away_form_label"),
                ctx.get("league"),
                ctx.get("venue"),
                motivation_analysis=None,
                scraped_news_formatted=None,
            )
            ai = generate_ai_analysis(
                prompt_ctx,
                ctx["home_team"],
                ctx["away_team"],
                language=payload.language,
            )
    except Exception:
        ai = {"quick_summary": None, "scenario_1": None}

    prob_source = "Sportmonks" if ctx.get("_sportmonks_use_predictions") else ("API-Football Predictions" if used_api_predictions else "Poisson")
    analysis_recap = _build_analysis_recap(ctx, out, prob_source, news_included)
    if analysis_recap:
        analysis_recap["scraped_news_count"] = len(scraped_items)
        analysis_recap["motivation_analysis_used"] = bool(motivation_text and motivation_text.strip())
    report("Done", 100)
    resp = _build_response(ctx, out, ai, analysis_recap)
    resp["scraped_news_count"] = len(scraped_items)
    resp["motivation_analysis"] = (motivation_text[:8000] if motivation_text else None) or None
    return resp


@router.get("/match-result")
def get_match_result(
    home_team: str = Query(..., min_length=1),
    away_team: str = Query(..., min_length=1),
    home_team_id: Optional[int] = Query(None),
    away_team_id: Optional[int] = Query(None),
):
    """
    Returns match_over, final_score_*, match_statistics for the last H2H if the match is over.
    Used to enrich displayed analysis (e.g. when opening from history) so score and stats show.
    """
    try:
        ctx = load_match_context(
            home_team.strip(),
            away_team.strip(),
            home_team_id=home_team_id,
            away_team_id=away_team_id,
        )
        return {
            "match_over": ctx.get("match_over"),
            "final_score_home": ctx.get("final_score_home"),
            "final_score_away": ctx.get("final_score_away"),
            "match_statistics": ctx.get("match_statistics"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/chat")
def predict_chat(
    payload: ChatRequest,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    """
    Chat IA: answer one user question about the current match analysis. Pro: 1 request/day, Lifetime: unlimited.
    Requires X-User-Id. Body: message, analysis_context (optional), language (optional).
    """
    user_id = (x_user_id or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required to use the AI chat.")
    allowed, remaining, msg = can_use_chat_ai(user_id)
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=msg or "Chat IA is not available for your plan.",
        )
    analysis_context = payload.analysis_context or {}
    home_team = (analysis_context.get("home_team") or "").strip() or ""
    away_team = (analysis_context.get("away_team") or "").strip() or ""
    league = (analysis_context.get("league") or "").strip() or None
    news_context = ""
    if home_team and away_team:
        try:
            scraped_items = fetch_news_multi_source(
                home_team=home_team,
                away_team=away_team,
                league=league,
                max_items_total=12,
                max_age_days=5,
            )
            news_context = format_news_for_prompt(scraped_items) if scraped_items else ""
        except Exception:
            news_context = ""
    reply = chat_ai_reply(
        analysis_context=analysis_context,
        user_message=payload.message or "",
        language=payload.language or "en",
        news_context=news_context,
    )
    consume_chat_ai(user_id)
    _, remaining_after, _ = can_use_chat_ai(user_id)
    return {"answer": reply, "chat_remaining": remaining_after}


@router.post("/translate")
def translate_predict(payload: TranslateRequest):
    """
    Translate the AI-generated text fields of an analysis to the target language (en, fr, es).
    Returns the same analysis object with quick_summary, scenario_1–4, key_forces translated.
    """
    try:
        translated = translate_analysis(payload.analysis, payload.target_lang or "en")
        return translated
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("", response_model=PredictResponse)
def predict(
    payload: PredictRequest,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    """
    Analyse un match : probabilités 1X2, Over/Under, BTTS, xG, score exact.
    X-User-Id optionnel : si fourni, applique les limites du plan (free/starter/pro/lifetime).
    """
    user_id = (x_user_id or "").strip()
    allowed, msg, full_analysis, limit_reason = can_analyze(user_id)
    if not allowed:
        raise HTTPException(status_code=403, detail=limit_reason or msg)
    data = run_predict_with_progress(payload, progress_callback=None)
    data["full_analysis"] = full_analysis
    if user_id:
        consume_analysis(user_id, home_team=payload.home_team, away_team=payload.away_team)
    return PredictResponse(**data)


@router.post("/stream")
def predict_stream(
    payload: PredictRequest,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    """
    Same as POST /predict but streams NDJSON: progress events { "type": "progress", "step": "...", "percent": n }
    then a final { "type": "result", "data": { ... } } or { "type": "error", "message": "..." }.
    X-User-Id optionnel : applique les limites du plan et ajoute full_analysis dans data.
    """
    user_id = (x_user_id or "").strip()
    allowed, msg, full_analysis, limit_reason = can_analyze(user_id)
    logger.info(
        "predict/stream: user_id=%s allowed=%s full_analysis=%s",
        (user_id[:8] + "...") if len(user_id) > 8 else (user_id or "(none)"),
        allowed,
        full_analysis,
    )
    if not allowed:
        def error_stream():
            yield json.dumps({"type": "error", "message": msg, "code": limit_reason or "limit"}, ensure_ascii=False) + "\n"
        return StreamingResponse(error_stream(), media_type="application/x-ndjson")

    progress_queue: queue.Queue = queue.Queue()

    def on_progress(step: str, percent: int) -> None:
        progress_queue.put({"type": "progress", "step": step, "percent": percent})

    def run() -> None:
        try:
            result = run_predict_with_progress(payload, progress_callback=on_progress)
            result["full_analysis"] = full_analysis
            if user_id:
                consume_analysis(user_id, home_team=payload.home_team, away_team=payload.away_team)
            progress_queue.put({"type": "result", "data": result})
        except HTTPException as e:
            detail = e.detail if isinstance(e.detail, str) else (str(e.detail) if e.detail else str(e))
            progress_queue.put({"type": "error", "message": detail or "Service unavailable.", "code": "predictions_unavailable" if e.status_code == 503 else None})
        except Exception as e:  # noqa: BLE001
            progress_queue.put({"type": "error", "message": str(e) or "Analysis failed.", "code": None})

    thread = threading.Thread(target=run)
    thread.start()

    def generate():
        while True:
            item = progress_queue.get()
            yield json.dumps(item, ensure_ascii=False) + "\n"
            if item.get("type") in ("result", "error"):
                break

    return StreamingResponse(generate(), media_type="application/x-ndjson")
