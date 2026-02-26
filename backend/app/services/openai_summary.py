# backend/app/services/openai_summary.py
"""
Génération du résumé rapide et du scénario #1 via OpenAI.
"""
from openai import OpenAI
from app.core.config import get_settings


def _client() -> OpenAI | None:
    key = get_settings().openai_api_key
    if not key:
        return None
    return OpenAI(api_key=key)


def build_prompt_context(
    home_team: str,
    away_team: str,
    xg_home: float,
    xg_away: float,
    prob_home: float,
    prob_draw: float,
    prob_away: float,
    home_form_label: str | None,
    away_form_label: str | None,
    league: str | None = None,
    venue: str | None = None,
) -> str:
    """Contexte texte pour le LLM."""
    parts = [
        f"Match: {home_team} vs {away_team}.",
        f"Expected goals: {home_team} {xg_home}, {away_team} {xg_away}.",
        f"Probabilities 1X2: Home {prob_home}%, Draw {prob_draw}%, Away {prob_away}%.",
    ]
    if home_form_label:
        parts.append(f"{home_team} form: {home_form_label}.")
    if away_form_label:
        parts.append(f"{away_team} form: {away_form_label}.")
    if league:
        parts.append(f"League: {league}.")
    if venue:
        parts.append(f"Venue: {venue}.")
    return " ".join(parts)


def generate_quick_summary(context: str) -> str:
    """2-3 phrases de résumé style Visifoot."""
    client = _client()
    if not client:
        return "Summary based on stats and form (AI summary unavailable)."
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a football analysis assistant. Write a short, neutral summary (2-3 sentences) for a match prediction. Mention teams, form, and main takeaway. Write in the same language as the user's team names (e.g. French if teams are French)."},
                {"role": "user", "content": context},
            ],
            max_tokens=200,
        )
        return (r.choices[0].message.content or "").strip()
    except Exception:
        return "Summary based on stats and form."


def generate_scenario_1(context: str) -> str:
    """Un paragraphe décrivant un scénario probable du match."""
    client = _client()
    if not client:
        return "Scenario based on expected goals and form (AI scenario unavailable)."
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a football analyst. In one paragraph, describe how the match might unfold: who dominates, when goals might come, tactical balance. Be concrete but neutral. Use the same language as the team names (e.g. French for French teams)."},
                {"role": "user", "content": context},
            ],
            max_tokens=400,
        )
        return (r.choices[0].message.content or "").strip()
    except Exception:
        return "Scenario based on expected goals and recent form."
