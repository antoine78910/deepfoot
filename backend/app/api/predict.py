# backend/app/api/predict.py
import json
import queue
import threading
from typing import Callable, Optional

from fastapi import APIRouter, HTTPException, Query, Header
from fastapi.responses import StreamingResponse

from app.schemas.predict import (
    PredictRequest,
    PredictResponse,
    TranslateRequest,
    OverUnderItem,
    ExactScoreItem,
    MostLikelyScoreItem,
    AsianHandicapItem,
)
from app.services.data_loader import load_match_context
from app.ml.poisson import predict_all
from app.services.openai_summary import build_prompt_context, generate_ai_analysis, translate_analysis
from app.services.news_fetcher import fetch_football_news
from app.services.api_football import get_predictions as api_get_predictions
from app.services.subscription import can_analyze, consume_analysis

router = APIRouter(prefix="/predict", tags=["predict"])


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


def _build_response(
    ctx: dict,
    out: dict,
    ai: dict,
) -> dict:
    pcts = ctx.get("comparison_pcts") or {}
    return {
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
    }


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
    report("Computing probabilities…", 62)

    # Mode API : uniquement les données API-Football Predictions, aucune donnée de notre modèle
    if payload.use_api_predictions and ctx.get("fixture_id"):
        api_pred = api_get_predictions(ctx["fixture_id"])
        if api_pred:
            out = _out_from_api_predictions(api_pred)
        else:
            out = predict_all(ctx["lambda_home"], ctx["lambda_away"])
    else:
        out = predict_all(ctx["lambda_home"], ctx["lambda_away"])

    ai: dict = {}
    report("Generating AI summary…", 75)
    try:
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
        )
        news_text = fetch_football_news(
            ctx["home_team"],
            ctx["away_team"],
            ctx.get("league"),
        )
        if news_text:
            prompt_ctx = prompt_ctx + "\n\n" + news_text
        ai = generate_ai_analysis(
            prompt_ctx,
            ctx["home_team"],
            ctx["away_team"],
            language=payload.language,
        )
    except Exception:
        ai = {"quick_summary": None, "scenario_1": None}

    report("Done", 100)
    return _build_response(ctx, out, ai)


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
        consume_analysis(user_id)
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
                consume_analysis(user_id)
            progress_queue.put({"type": "result", "data": result})
        except Exception as e:  # noqa: BLE001
            progress_queue.put({"type": "error", "message": str(e)})

    thread = threading.Thread(target=run)
    thread.start()

    def generate():
        while True:
            item = progress_queue.get()
            yield json.dumps(item, ensure_ascii=False) + "\n"
            if item.get("type") in ("result", "error"):
                break

    return StreamingResponse(generate(), media_type="application/x-ndjson")
