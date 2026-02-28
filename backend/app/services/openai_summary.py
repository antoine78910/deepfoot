# backend/app/services/openai_summary.py
"""
Génération du résumé rapide, scénarios et key forces via OpenAI (un seul appel structuré).
"""
import json
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


def generate_ai_analysis(context: str, home_team: str, away_team: str) -> dict:
    """
    Single OpenAI call returning JSON: quick_summary, scenario_1, scenario_2, scenario_3, scenario_4,
    key_forces_home, key_forces_away. Speeds up analysis vs multiple calls.
    """
    default = {
        "quick_summary": "Summary based on stats and form.",
        "scenario_1": "Scenario based on expected goals and recent form.",
        "scenario_2": {"title": "", "body": "", "probability_pct": None},
        "scenario_3": {"title": "", "body": "", "probability_pct": None},
        "scenario_4": {"title": "", "body": "", "probability_pct": None},
        "key_forces_home": [],
        "key_forces_away": [],
    }
    client = _client()
    if not client:
        return default
    system = """You are a football analysis assistant. Based on the match context, return a JSON object with exactly these keys (use the same language as the team names, e.g. French if teams are French):
- quick_summary: 2-3 sentences. Always use the REAL team names, league name, and venue from the context (e.g. "Monaco hosts Angers in a Ligue 1 match at Stade Louis II") — never output placeholder text like [Home], [Away], [League] or [Venue]. If "Latest football news" is provided in the context, add: "Our AI, connected to the latest football news, takes into account the latest info: " then briefly mention relevant news for each side. Otherwise give a neutral summary based on teams, form, and main takeaway.
- scenario_1: One paragraph describing how the match might unfold (who dominates, when goals might come).
- scenario_2: Object with title (short, e.g. "Home win"), body (2 sentences + optional "Professional tip: ..."), probability_pct (number or null).
- scenario_3: Same structure as scenario_2 (e.g. "Offensive duel", "Goals galore", over 2.5).
- scenario_4: Same structure (e.g. "Offensive inefficiency", BTTS No).
- key_forces_home: Array of 2-4 short bullet points (e.g. "Good recent form", "Powerful attack"). You may derive from news if provided.
- key_forces_away: Array of 2-4 short bullet points for the away team.
Return only valid JSON, no markdown."""
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": context},
            ],
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
        raw = (r.choices[0].message.content or "").strip()
        if not raw:
            return default
        data = json.loads(raw)
        for key in ("scenario_2", "scenario_3", "scenario_4"):
            if key in data and not isinstance(data[key], dict):
                data[key] = {"title": str(data[key])[:80], "body": "", "probability_pct": None}
            data.setdefault(key, default[key])
        data.setdefault("quick_summary", default["quick_summary"])
        data.setdefault("scenario_1", default["scenario_1"])
        data.setdefault("key_forces_home", default["key_forces_home"])
        data.setdefault("key_forces_away", default["key_forces_away"])
        return data
    except Exception:
        return default
