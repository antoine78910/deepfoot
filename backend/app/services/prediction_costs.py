"""OpenAI cost of a DeepFoot match prediction (gpt-4o-mini).

Published gpt-4o-mini rates (USD / 1M tokens). Historical rows without
token usage use the typical Sportmonks analysis call size.
"""
from __future__ import annotations

from typing import Any

GPT_4O_MINI_INPUT_USD_PER_1M = 0.15
GPT_4O_MINI_OUTPUT_USD_PER_1M = 0.60
USD_TO_EUR = 0.92
MODEL_NAME = "gpt-4o-mini"

# Long system prompt + match JSON/news in, 8-section JSON out.
EST_PROMPT_TOKENS = 2500
EST_COMPLETION_TOKENS = 1100

PLAN_PRICE_EUR = {
    "starter": 9.0,
    "pro": 19.0,
    "lifetime": 99.0,
}


def cost_usd(prompt_tokens: int, completion_tokens: int) -> float:
    prompt = max(0, int(prompt_tokens or 0))
    completion = max(0, int(completion_tokens or 0))
    return (
        prompt * GPT_4O_MINI_INPUT_USD_PER_1M + completion * GPT_4O_MINI_OUTPUT_USD_PER_1M
    ) / 1_000_000


def cost_eur(prompt_tokens: int, completion_tokens: int) -> float:
    return cost_usd(prompt_tokens, completion_tokens) * USD_TO_EUR


def estimated_cost_eur() -> float:
    return round(cost_eur(EST_PROMPT_TOKENS, EST_COMPLETION_TOKENS), 6)


def estimated_cost_usd() -> float:
    return round(cost_usd(EST_PROMPT_TOKENS, EST_COMPLETION_TOKENS), 6)


def usage_from_openai(response: Any, model: str = MODEL_NAME) -> dict[str, Any] | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion = int(getattr(usage, "completion_tokens", 0) or 0)
    total = int(getattr(usage, "total_tokens", 0) or (prompt + completion))
    if prompt <= 0 and completion <= 0:
        return None
    return {
        "model": model,
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
        "cost_usd": round(cost_usd(prompt, completion), 6),
        "cost_eur": round(cost_eur(prompt, completion), 6),
    }


def cost_from_result(result: dict | None) -> tuple[float, bool]:
    """Return (cost_eur, estimated)."""
    if isinstance(result, dict):
        usage = result.get("llm_usage")
        if isinstance(usage, dict):
            raw_eur = usage.get("cost_eur")
            if raw_eur is not None:
                try:
                    return float(raw_eur), False
                except (TypeError, ValueError):
                    pass
            try:
                prompt = int(usage.get("prompt_tokens") or 0)
                completion = int(usage.get("completion_tokens") or 0)
            except (TypeError, ValueError):
                prompt, completion = 0, 0
            if prompt or completion:
                return round(cost_eur(prompt, completion), 6), False
    return estimated_cost_eur(), True


def revenue_for_plan(plan: str | None) -> float:
    return PLAN_PRICE_EUR.get((plan or "").strip().lower(), 0.0)


def economics_payload(
    *,
    predictions_all_time: int,
    predictions_window: int,
    window_days: int,
    plan_counts: dict[str, int],
) -> dict[str, Any]:
    unit = estimated_cost_eur()
    cost_all_time = round(predictions_all_time * unit, 4)
    cost_window = round(predictions_window * unit, 4)
    starter = int(plan_counts.get("starter") or 0)
    pro = int(plan_counts.get("pro") or 0)
    lifetime = int(plan_counts.get("lifetime") or 0)
    free = int(plan_counts.get("free") or 0)
    mrr = round(starter * PLAN_PRICE_EUR["starter"] + pro * PLAN_PRICE_EUR["pro"], 2)
    lifetime_revenue = round(lifetime * PLAN_PRICE_EUR["lifetime"], 2)
    days = max(1, int(window_days or 30))
    revenue_window = round(mrr * (days / 30.0), 2)
    profit_window = round(revenue_window - cost_window, 2)
    profit_all_time = round(mrr + lifetime_revenue - cost_all_time, 2)
    return {
        "currency": "EUR",
        "model": MODEL_NAME,
        "cost_per_prediction_eur": unit,
        "cost_per_prediction_usd": estimated_cost_usd(),
        "cost_estimated": True,
        "cost_note": (
            "OpenAI gpt-4o-mini only (typical 2500 input / 1100 output tokens). "
            "Sportmonks, Railway and Vercel monthly fees are not included."
        ),
        "predictions_all_time": predictions_all_time,
        "predictions_window": predictions_window,
        "cost_all_time_eur": cost_all_time,
        "cost_window_eur": cost_window,
        "paid": {"starter": starter, "pro": pro, "lifetime": lifetime, "free": free},
        "mrr_eur": mrr,
        "lifetime_revenue_eur": lifetime_revenue,
        "revenue_window_eur": revenue_window,
        "profit_window_eur": profit_window,
        "profit_all_time_eur": profit_all_time,
        "profitable_window": profit_window >= 0,
    }
