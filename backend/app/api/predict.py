# backend/app/api/predict.py
import json
import queue
import threading
from typing import Callable, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.predict import (
    PredictRequest,
    PredictResponse,
    OverUnderItem,
    ExactScoreItem,
    MostLikelyScoreItem,
    AsianHandicapItem,
)
from app.services.data_loader import load_match_context
from app.ml.poisson import predict_all
from app.services.openai_summary import build_prompt_context, generate_ai_analysis
from app.services.news_fetcher import fetch_football_news
from app.services.api_football import get_predictions as api_get_predictions

router = APIRouter(prefix="/predict", tags=["predict"])


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
    out = predict_all(ctx["lambda_home"], ctx["lambda_away"])

    # Option: remplacer 1X2 par les prédictions API-Football si fixture trouvée
    if payload.use_api_predictions and ctx.get("fixture_id"):
        api_pred = api_get_predictions(ctx["fixture_id"])
        if api_pred:
            pred = api_pred.get("predictions") or {}
            pct = pred.get("percent") or {}
            def _pct(s: str) -> float:
                if not s:
                    return 0.0
                s = str(s).strip().rstrip("%")
                try:
                    return round(float(s), 1)
                except ValueError:
                    return 0.0
            out["prob_home"] = _pct(pct.get("home"))
            out["prob_draw"] = _pct(pct.get("draw"))
            out["prob_away"] = _pct(pct.get("away"))
            # Cotes implicites cohérentes avec les nouveaux 1X2
            def _impl(p: float) -> float:
                return round(100 / max(p, 0.5), 2) if p else 0.0
            out["implied_odds_home"] = _impl(out["prob_home"])
            out["implied_odds_draw"] = _impl(out["prob_draw"])
            out["implied_odds_away"] = _impl(out["prob_away"])
            if pred.get("advice"):
                out["api_advice"] = pred.get("advice")

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
        ai = generate_ai_analysis(prompt_ctx, ctx["home_team"], ctx["away_team"])
    except Exception:
        ai = {"quick_summary": None, "scenario_1": None}

    report("Done", 100)
    return _build_response(ctx, out, ai)


@router.post("", response_model=PredictResponse)
def predict(payload: PredictRequest):
    """
    Analyse un match : probabilités 1X2, Over/Under, BTTS, xG, score exact.
    Optionnel : résumé et scénario #1 via OpenAI.
    """
    data = run_predict_with_progress(payload, progress_callback=None)
    return PredictResponse(**data)


@router.post("/stream")
def predict_stream(payload: PredictRequest):
    """
    Same as POST /predict but streams NDJSON: progress events { "type": "progress", "step": "...", "percent": n }
    then a final { "type": "result", "data": { ... } } or { "type": "error", "message": "..." }.
    """
    progress_queue: queue.Queue = queue.Queue()

    def on_progress(step: str, percent: int) -> None:
        progress_queue.put({"type": "progress", "step": step, "percent": percent})

    def run() -> None:
        try:
            result = run_predict_with_progress(payload, progress_callback=on_progress)
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
