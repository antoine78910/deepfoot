# backend/app/services/openai_summary.py
"""
Génération du résumé rapide, scénarios et key forces via OpenAI (un seul appel structuré).
+ Analyse professionnelle Sportmonks (8 sections) quand les données viennent de Sportmonks.
"""
import json
from typing import Any, Optional

from openai import OpenAI
from app.core.config import get_settings

SPORTMONKS_ANALYST_SYSTEM = """You are a professional football match analyst.

Your task is to analyze a football match using Sportmonks prediction data and contextual match information.

INPUT DATA:
You will receive a JSON object containing:
- Match information (teams, league, date)
- Win probability predictions (home_win %, draw %, away_win %)
- Goal probabilities (Over/Under 2.5)
- BTTS probabilities
- Expected goals (xG)
- Team form (if available)
- Injuries or suspensions (if available)
- Additional context if available

ANALYSIS REQUIREMENTS:

1. MATCH OVERVIEW
   Explain the general context: competition, teams involved, importance of the match.

2. WIN PROBABILITY ANALYSIS
   Interpret home win %, draw %, away win %. Explain which team is favored and why.

3. GOAL EXPECTATION ANALYSIS
   Analyze expected goals, over/under probabilities, attacking potential. Defensive or open match.

4. BOTH TEAMS TO SCORE (BTTS)
   Analyze BTTS probabilities and whether both teams are likely to score.

5. TEAM STRENGTH & FORM
   Analyze recent form and performance indicators. Which team appears stronger.

6. INJURY / ABSENCE IMPACT
   If injuries are provided, explain how they may affect the match outcome.

7. KEY MATCH DYNAMICS
   Tempo of the match, possible tactical scenario, likely match pattern.

8. FINAL MATCH INSIGHT
   Summarize: which team has the edge, likely score range, level of match balance.

STYLE: Professional sports analysis. Clear and concise. Do not invent information. Use probabilities to support conclusions. Avoid overly long explanations.

OUTPUT: Return a JSON object with exactly these keys (each a string, 1-3 short paragraphs):
- match_overview
- win_probability_analysis
- goal_expectation_analysis
- btts_analysis
- team_strength_form
- injury_absence_impact
- key_match_dynamics
- final_match_insight
- key_forces_home (array of 2-4 short bullet points)
- key_forces_away (array of 2-4 short bullet points)
Return only valid JSON, no markdown."""


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
    motivation_analysis: str | None = None,
    scraped_news_formatted: str | None = None,
) -> str:
    """Contexte texte pour le LLM (stats + optionnel: analyse motivation et news scrapées)."""
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
    base = " ".join(parts)
    if motivation_analysis and motivation_analysis.strip():
        base = "MOTIVATION AND CONTEXT ANALYSIS (use this to enrich summary and scenarios):\n" + motivation_analysis.strip() + "\n\n" + base
    if scraped_news_formatted and scraped_news_formatted.strip():
        base = scraped_news_formatted.strip() + "\n\n" + base
    return base


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


def generate_ai_analysis_sportmonks(
    ctx: dict,
    out: dict,
    language: Optional[str] = None,
) -> dict:
    """
    Analyse professionnelle à partir des données Sportmonks (prédictions + contexte).
    Retourne quick_summary, professional_analysis (8 sections), scenario_1–4, key_forces_home/away.
    """
    default = {
        "quick_summary": "Analysis based on Sportmonks prediction data.",
        "scenario_1": "",
        "scenario_2": {"title": "", "body": "", "probability_pct": None},
        "scenario_3": {"title": "", "body": "", "probability_pct": None},
        "scenario_4": {"title": "", "body": "", "probability_pct": None},
        "key_forces_home": [],
        "key_forces_away": [],
        "professional_analysis": "",
    }
    client = _client()
    if not client:
        return default
    lang_instruction = " Write the ENTIRE response in French." if (language or "").strip().lower() == "fr" else (
        " Write the ENTIRE response in Spanish." if (language or "").strip().lower() == "es" else
        " Write the ENTIRE response in English."
    )
    input_json = {
        "match": f"{ctx.get('home_team', '')} vs {ctx.get('away_team', '')}",
        "league": ctx.get("league"),
        "venue": ctx.get("venue"),
        "predictions": {
            "home_win": out.get("prob_home"),
            "draw": out.get("prob_draw"),
            "away_win": out.get("prob_away"),
            "over_2_5": next((x.get("over_pct") for x in (out.get("over_under") or []) if x.get("line") == "2.5"), 50),
            "under_2_5": next((x.get("under_pct") for x in (out.get("over_under") or []) if x.get("line") == "2.5"), 50),
            "btts_yes": out.get("btts_yes_pct"),
            "btts_no": out.get("btts_no_pct"),
        },
        "expected_goals": {"home": out.get("xg_home"), "away": out.get("xg_away")},
        "form": {"home": ctx.get("home_form_label"), "away": ctx.get("away_form_label")},
    }
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SPORTMONKS_ANALYST_SYSTEM + lang_instruction},
                {"role": "user", "content": json.dumps(input_json, ensure_ascii=False)},
            ],
            max_tokens=1800,
            response_format={"type": "json_object"},
        )
        raw = (r.choices[0].message.content or "").strip()
        if not raw:
            return default
        data = json.loads(raw)
        sections = [
            ("1. MATCH OVERVIEW", data.get("match_overview")),
            ("2. WIN PROBABILITY ANALYSIS", data.get("win_probability_analysis")),
            ("3. GOAL EXPECTATION ANALYSIS", data.get("goal_expectation_analysis")),
            ("4. BOTH TEAMS TO SCORE (BTTS)", data.get("btts_analysis")),
            ("5. TEAM STRENGTH & FORM", data.get("team_strength_form")),
            ("6. INJURY / ABSENCE IMPACT", data.get("injury_absence_impact")),
            ("7. KEY MATCH DYNAMICS", data.get("key_match_dynamics")),
            ("8. FINAL MATCH INSIGHT", data.get("final_match_insight")),
        ]
        professional_analysis = "\n\n".join(
            f"{title}\n{text}" for title, text in sections if text
        )
        return {
            "quick_summary": data.get("final_match_insight") or data.get("match_overview") or default["quick_summary"],
            "scenario_1": data.get("match_overview") or "",
            "scenario_2": {"title": "Win probability", "body": data.get("win_probability_analysis") or "", "probability_pct": out.get("prob_home")},
            "scenario_3": {"title": "Goals & BTTS", "body": (data.get("goal_expectation_analysis") or "") + " " + (data.get("btts_analysis") or ""), "probability_pct": out.get("btts_yes_pct")},
            "scenario_4": {"title": "Match dynamics", "body": data.get("key_match_dynamics") or "", "probability_pct": None},
            "key_forces_home": data.get("key_forces_home") or [],
            "key_forces_away": data.get("key_forces_away") or [],
            "professional_analysis": professional_analysis,
        }
    except Exception:
        return default


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
- quick_summary: 2-3 sentences. Always use the REAL team names, league name, and venue from the context (e.g. "Monaco hosts Angers in a Ligue 1 match at Stade Louis II") — never output placeholder text like [Home], [Away], [League] or [Venue]. If "MOTIVATION AND CONTEXT ANALYSIS" or "SCRAPED NEWS" is provided in the context, you MUST use it: mention motivation factors, injuries/rotation, stakes (relegation, derby, must-win), and key news that could impact the match. E.g. "Our AI has analyzed news and context: [team] is in a relegation battle / has rotation concerns / key injury...". This makes the predictor more reliable.
- scenario_1: One paragraph describing how the match might unfold. If motivation analysis is provided, reflect it (e.g. more motivated team, rotation, pressure).
- scenario_2: Object with title (short), body (2 sentences + optional "Professional tip: ..."), probability_pct (number or null). Use news/motivation when relevant.
- scenario_3: Same structure as scenario_2 (e.g. offensive duel, goals galore, over 2.5).
- scenario_4: Same structure (e.g. offensive inefficiency, BTTS No).
- key_forces_home: Array of 2-4 short bullet points. Derive from MOTIVATION AND CONTEXT ANALYSIS and SCRAPED NEWS when provided (injuries, rotation, form, stakes).
- key_forces_away: Array of 2-4 short bullet points for the away team. Same: use motivation and news when provided.
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
