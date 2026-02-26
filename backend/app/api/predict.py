# backend/app/api/predict.py
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.predict import PredictRequest, PredictResponse, OverUnderItem, ExactScoreItem
from app.services.data_loader import load_match_context
from app.ml.poisson import predict_all
from app.services.openai_summary import build_prompt_context, generate_quick_summary, generate_scenario_1
from typing import Optional

router = APIRouter(prefix="/predict", tags=["predict"])


@router.post("", response_model=PredictResponse)
def predict(payload: PredictRequest):
    """
    Analyse un match : probabilités 1X2, Over/Under, BTTS, xG, score exact.
    Optionnel : résumé et scénario #1 via OpenAI.
    """
    ctx = load_match_context(payload.home_team, payload.away_team)
    out = predict_all(ctx["lambda_home"], ctx["lambda_away"])

    quick_summary = None
    scenario_1 = None
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
        )
        quick_summary = generate_quick_summary(prompt_ctx)
        scenario_1 = generate_scenario_1(prompt_ctx)
    except Exception:
        pass

    pcts = ctx.get("comparison_pcts") or {}

    return PredictResponse(
        home_team=ctx["home_team"],
        away_team=ctx["away_team"],
        league=None,
        match_date=None,
        venue=None,
        xg_home=out["xg_home"],
        xg_away=out["xg_away"],
        xg_total=out["xg_total"],
        prob_home=out["prob_home"],
        prob_draw=out["prob_draw"],
        prob_away=out["prob_away"],
        btts_yes_pct=out["btts_yes_pct"],
        btts_no_pct=out["btts_no_pct"],
        over_under=[OverUnderItem(**x) for x in out["over_under"]],
        exact_scores=[ExactScoreItem(**x) for x in out["exact_scores"]],
        home_form=ctx.get("home_form"),
        away_form=ctx.get("away_form"),
        home_wdl=ctx.get("home_wdl"),
        away_wdl=ctx.get("away_wdl"),
        home_form_label=ctx.get("home_form_label"),
        away_form_label=ctx.get("away_form_label"),
        quick_summary=quick_summary,
        scenario_1=scenario_1,
        ai_confidence="Very high",
        attack_home_pct=pcts.get("attack_home_pct"),
        defense_home_pct=pcts.get("defense_home_pct"),
        form_home_pct=pcts.get("form_home_pct"),
        h2h_home_pct=pcts.get("h2h_home_pct"),
        goals_home_pct=pcts.get("goals_home_pct"),
        overall_home_pct=pcts.get("overall_home_pct"),
    )
