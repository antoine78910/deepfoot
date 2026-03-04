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


def generate_ai_analysis(
    context: str, home_team: str, away_team: str, language: str | None = None
) -> dict:
    """
    Single OpenAI call returning JSON: quick_summary, scenario_1, scenario_2, scenario_3, scenario_4,
    key_forces_home, key_forces_away. Speeds up analysis vs multiple calls.
    language: "fr" or "en" to force output language; if None, infer from team names.
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
    lang_instruction = (
        " Write the ENTIRE response (quick_summary, scenario_1, scenario_2, scenario_3, scenario_4, key_forces_home, key_forces_away) in French."
        if (language or "").strip().lower() == "fr"
        else (
            " Write the ENTIRE response in Spanish."
            if (language or "").strip().lower() == "es"
            else (
                " Write the ENTIRE response in English."
                if (language or "").strip().lower() == "en"
                else " Use the same language as the team names (e.g. French if teams are French)."
            )
        )
    )
    system = """You are a football analysis assistant. Based on the match context, return a JSON object with exactly these keys."""
    system += lang_instruction
    system += """
- quick_summary: 2-3 sentences. Always use the REAL team names, league name, and venue from the context (e.g. "Monaco hosts Angers in a Ligue 1 match at Stade Louis II") — never output placeholder text like [Home], [Away], [League] or [Venue]. If "Latest football news" is provided in the context, add: "Our AI, connected to the latest football news, takes into account the latest info: " then briefly mention relevant news for each side. Otherwise give a neutral summary based on teams, form, and main takeaway.
- scenario_1: One paragraph describing how the match might unfold (who dominates, when goals might come).
- scenario_2: Object with title (short), body (2 sentences + optional "Professional tip: ..."), probability_pct (number or null).
- scenario_3: Same structure as scenario_2 (e.g. offensive duel, goals galore, over 2.5).
- scenario_4: Same structure (e.g. offensive inefficiency, BTTS No).
- key_forces_home: Array of 2-4 short bullet points. You may derive from news if provided.
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


# Keys we translate when user changes language (AI-generated text only).
TRANSLATE_KEYS = ("quick_summary", "scenario_1", "scenario_2", "scenario_3", "scenario_4", "key_forces_home", "key_forces_away")


def translate_analysis(analysis: dict, target_lang: str) -> dict:
    """
    Returns a copy of `analysis` with AI text fields translated to target_lang.
    target_lang: "en", "fr", or "es".
    """
    lang_names = {"en": "English", "fr": "French", "es": "Spanish"}
    lang_name = lang_names.get((target_lang or "en").strip().lower(), "English")
    out = dict(analysis)
    subset = {}
    for key in TRANSLATE_KEYS:
        if key not in out:
            continue
        v = out[key]
        if v is None:
            continue
        if key in ("scenario_2", "scenario_3", "scenario_4") and isinstance(v, dict):
            subset[key] = {"title": v.get("title") or "", "body": v.get("body") or ""}
        elif key in ("key_forces_home", "key_forces_away") and isinstance(v, list):
            subset[key] = v
        elif isinstance(v, str):
            subset[key] = v
    if not subset:
        return out
    client = _client()
    if not client:
        return out
    try:
        payload = json.dumps(subset, ensure_ascii=False)
        system = f"Translate the following JSON into {lang_name}. Preserve the exact structure and keys. Translate only string values and each string in arrays. Return only valid JSON, no markdown."
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": payload},
            ],
            max_tokens=2000,
            response_format={"type": "json_object"},
        )
        raw = (r.choices[0].message.content or "").strip()
        if not raw:
            return out
        translated = json.loads(raw)
        for key in TRANSLATE_KEYS:
            if key not in translated:
                continue
            if key in ("scenario_2", "scenario_3", "scenario_4") and isinstance(out.get(key), dict) and isinstance(translated.get(key), dict):
                out[key] = {**out[key], "title": translated[key].get("title") or out[key].get("title"), "body": translated[key].get("body") or out[key].get("body")}
            else:
                out[key] = translated[key]
        return out
    except Exception:
        return out
