"""Recompute stored 1X2 from real recent form (TheSportsDB + Poisson). No demo scores, no OpenAI."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.ml.poisson import predict_all
from app.services.data_loader import apply_thesportsdb_form_if_missing


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if isinstance(value, float):
        return float(value)
    return value


def match_cache_key(home_team: str, away_team: str) -> str:
    return f"{(home_team or '').strip().lower()}||{(away_team or '').strip().lower()}"


def recompute_match_model(home_team: str, away_team: str) -> Optional[dict[str, Any]]:
    """Return Poisson fields from real form, or None if form is still missing."""
    home = (home_team or "").strip()
    away = (away_team or "").strip()
    if not home or not away:
        return None
    ctx = apply_thesportsdb_form_if_missing(
        {
            "home_team": home,
            "away_team": away,
            "lambda_home": 1.2,
            "lambda_away": 1.2,
            "data_recap": {},
        },
        home,
        away,
    )
    recap = ctx.get("data_recap") if isinstance(ctx.get("data_recap"), dict) else {}
    if recap.get("placeholder_form") or not ctx.get("lambda_home") or not ctx.get("lambda_away"):
        return None
    if not recap.get("raw_home_goals_for") or not recap.get("raw_away_goals_for"):
        return None
    out = predict_all(float(ctx["lambda_home"]), float(ctx["lambda_away"]))
    pcts = ctx.get("comparison_pcts") or {}
    mls = out.get("most_likely_score") if isinstance(out.get("most_likely_score"), dict) else {}
    return _jsonable(
        {
            "xg_home": out.get("xg_home"),
            "xg_away": out.get("xg_away"),
            "xg_total": out.get("xg_total"),
            "prob_home": out.get("prob_home"),
            "prob_draw": out.get("prob_draw"),
            "prob_away": out.get("prob_away"),
            "internal_prob_home": out.get("prob_home"),
            "internal_prob_draw": out.get("prob_draw"),
            "internal_prob_away": out.get("prob_away"),
            "implied_odds_home": out.get("implied_odds_home"),
            "implied_odds_draw": out.get("implied_odds_draw"),
            "implied_odds_away": out.get("implied_odds_away"),
            "btts_yes_pct": out.get("btts_yes_pct"),
            "btts_no_pct": out.get("btts_no_pct"),
            "over_under": out.get("over_under"),
            "exact_scores": out.get("exact_scores"),
            "most_likely_score": {
                "home": mls.get("home"),
                "away": mls.get("away"),
                "probability": mls.get("probability"),
            },
            "total_goals_distribution": out.get("total_goals_distribution"),
            "double_chance_1x": out.get("double_chance_1x"),
            "double_chance_x2": out.get("double_chance_x2"),
            "double_chance_12": out.get("double_chance_12"),
            "asian_handicap": out.get("asian_handicap"),
            "goal_difference_dist": out.get("goal_difference_dist"),
            "home_form": ctx.get("home_form"),
            "away_form": ctx.get("away_form"),
            "home_wdl": ctx.get("home_wdl"),
            "away_wdl": ctx.get("away_wdl"),
            "home_form_label": ctx.get("home_form_label"),
            "away_form_label": ctx.get("away_form_label"),
            "attack_home_pct": pcts.get("attack_home_pct"),
            "defense_home_pct": pcts.get("defense_home_pct"),
            "form_home_pct": pcts.get("form_home_pct"),
            "h2h_home_pct": pcts.get("h2h_home_pct"),
            "goals_home_pct": pcts.get("goals_home_pct"),
            "overall_home_pct": pcts.get("overall_home_pct"),
            "form_source": "TheSportsDB",
            "recalculated_from_form": True,
            "recalculated_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def apply_recomputed_probs(result: dict[str, Any], computed: dict[str, Any]) -> dict[str, Any]:
    """Merge recomputed Poisson fields into a stored analysis blob. Keep AI copy."""
    merged = dict(result or {})
    skip = {"form_source", "recalculated_from_form", "recalculated_at"}
    for key, value in computed.items():
        if key in skip:
            continue
        merged[key] = value
    recap = dict(merged.get("analysis_recap") or {}) if isinstance(merged.get("analysis_recap"), dict) else {}
    recap["placeholder_form"] = False
    recap["recalculated_from_form"] = True
    recap["form_source"] = computed.get("form_source") or "TheSportsDB"
    recap["recalculated_at"] = computed.get("recalculated_at")
    steps = recap.get("pipeline_steps")
    if isinstance(steps, list):
        cleaned = []
        for step in steps:
            if not isinstance(step, dict):
                cleaned.append(step)
                continue
            detail = str(step.get("detail") or "")
            if "goals_for=[1, 2, 1, 0, 2]" in detail and "goals_for=[0, 1, 1, 2, 0]" in detail:
                cleaned.append({**step, "detail": "Form rebuilt from TheSportsDB last results."})
            else:
                cleaned.append(step)
        recap["pipeline_steps"] = cleaned
    merged["analysis_recap"] = recap
    merged["recalculated_from_form"] = True
    return merged


def prob_signature(result: dict[str, Any] | None) -> str:
    result = result if isinstance(result, dict) else {}
    return "|".join(
        str(result.get(k) if result.get(k) is not None else result.get(f"internal_{k}"))
        for k in ("prob_home", "prob_draw", "prob_away")
    )
