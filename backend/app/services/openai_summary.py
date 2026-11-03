# backend/app/services/openai_summary.py
"""
Génération du résumé rapide, scénarios et key forces via OpenAI (un seul appel structuré).
+ Analyse professionnelle Sportmonks (8 sections) quand les données viennent de Sportmonks.
"""
import json
import logging
import re
from typing import Any, Optional

from openai import OpenAI
from app.core.config import get_settings
from app.services.prediction_costs import usage_from_openai

logger = logging.getLogger(__name__)

CHAT_UNAVAILABLE_MSG = "The AI chat is temporarily unavailable. Please try again later."


class ChatAIError(Exception):
    """OpenAI chat failed; do not consume the user's daily quota."""

    def __init__(self, user_message: str = CHAT_UNAVAILABLE_MSG):
        super().__init__(user_message)
        self.user_message = user_message

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
   One paragraph describing the single most likely way the match will unfold on the pitch. Narrative focus: who will control the game, how the opening 20–30 minutes might go, pressure and transitions. Use data to inform but describe what will happen (e.g. "Team X will likely establish early control through patient possession..."). Do not just list context or stats.

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
   Describe what will happen on the pitch in an alternative scenario: tempo, tactical pattern, how the game might unfold. Narrative, not a list of data.

8. FINAL MATCH INSIGHT
   Summarize: which team has the edge and level of match balance. Do NOT include score ranges or specific score predictions (e.g. no "1-0 or 2-1", "likely score range").

STYLE: Professional sports analysis. Clear and concise. Do not invent information. Use probabilities to support conclusions. Avoid overly long explanations. Do not include score ranges or specific score predictions (e.g. no "1-0 or 2-1", "likely score range") in match_overview or final_match_insight.

If the input includes "match_context_summary" and "motivation" (home_motivation_label, away_motivation_label), you MUST use them:
- The quick_summary (and match_overview) must be a credible news-style summary: mention league position, points gap, matches remaining, and stakes (title race, relegation battle, european qualification). Example: "Team A sit 2nd but cannot catch the leader with 2 games left. Team B are 1 point above the relegation zone, making this crucial for survival."
- Reflect Match Importance: home motivation (e.g. medium/high/very high), away motivation.
If the input includes recent commentaries/news from past matches, include at least one concrete form fact in the summary (team + opponent + result), e.g. "Lens arrive with confidence after beating Reims 2-1."

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


def _shorten_to_sentences(text: str, max_sentences: int = 3, max_chars: int = 360) -> str:
    s = (text or "").strip()
    if not s:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", s)
    clipped = " ".join([p.strip() for p in parts if p.strip()][:max_sentences]).strip()
    if len(clipped) > max_chars:
        clipped = clipped[: max_chars - 1].rstrip() + "…"
    return clipped


def _is_generic_scenario_title(title: str) -> bool:
    t = (title or "").strip().lower()
    if not t:
        return True
    generic_tokens = {
        "win probability",
        "goals & btts",
        "match dynamics",
        "btts and goals",
        "scenario",
    }
    return t in generic_tokens or t.startswith("scenario ")


def _descriptive_title_from_body(body: str, fallback: str = "Likely Match Pattern") -> str:
    b = _shorten_to_sentences(body, max_sentences=1, max_chars=90)
    if not b:
        return fallback
    first = re.split(r"[,:;.!?]", b)[0].strip()
    words = [w for w in first.split() if w]
    if not words:
        return fallback
    title = " ".join(words[:7]).strip()
    return title[:70] if title else fallback


def _normalize_scenarios_payload(data: dict, default: dict) -> dict:
    for key in ("scenario_2", "scenario_3", "scenario_4"):
        if key in data and not isinstance(data[key], dict):
            data[key] = {"title": str(data[key])[:80], "body": "", "probability_pct": None}
        data.setdefault(key, default[key])
        if isinstance(data.get(key), dict):
            body = _shorten_to_sentences(str(data[key].get("body") or ""), max_sentences=3, max_chars=360)
            title = str(data[key].get("title") or "").strip()
            if _is_generic_scenario_title(title):
                title = _descriptive_title_from_body(body, fallback="Likely Match Pattern")
            data[key] = {
                **data[key],
                "title": title[:70],
                "body": body,
            }
    return data


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
                {"role": "system", "content": "You are a football analysis assistant. Write a short, neutral summary (2-3 sentences) for a match prediction. Mention teams, form, and main takeaway. Do NOT include score ranges or specific score predictions (e.g. no '1-0 or 2-1', 'likely score range'). Write in the same language as the user's team names (e.g. French if teams are French)."},
                {"role": "user", "content": context},
            ],
            max_tokens=200,
        )
        return (r.choices[0].message.content or "").strip()
    except Exception:
        return "Summary based on stats and form."


def generate_scenario_1(context: str) -> str:
    """One paragraph describing the single most likely way the match will unfold on the pitch (narrative)."""
    client = _client()
    if not client:
        return "Scenario based on expected goals and form (AI scenario unavailable)."
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a football analyst. In one paragraph, describe the single most likely way the match will unfold on the pitch: who will control the game, how the opening 20–30 minutes might go, how pressure and transitions will play out. Write as a match narrative (e.g. 'Team X will likely establish early control through patient possession...'). Use the data to inform the story but do not list stats; describe what will happen. Use the same language as the team names (e.g. French for French teams)."},
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
    news_context: Optional[str] = None,
) -> dict:
    """
    Analyse professionnelle à partir des données Sportmonks (prédictions + contexte + news).
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
    if ctx.get("match_context_summary") or ctx.get("home_motivation_label"):
        input_json["match_context_summary"] = ctx.get("match_context_summary") or ""
        input_json["motivation"] = {
            "home": ctx.get("home_motivation_label") or "medium",
            "away": ctx.get("away_motivation_label") or "medium",
        }
    # Add news context if available
    if news_context and news_context.strip():
        input_json["news"] = news_context.strip()
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
        llm_usage = usage_from_openai(r)
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
        result = {
            "quick_summary": data.get("final_match_insight") or data.get("match_overview") or default["quick_summary"],
            "scenario_1": data.get("match_overview") or "",
            "scenario_2": {"title": "", "body": data.get("win_probability_analysis") or "", "probability_pct": out.get("prob_home")},
            "scenario_3": {"title": "", "body": (data.get("goal_expectation_analysis") or "") + " " + (data.get("btts_analysis") or ""), "probability_pct": out.get("btts_yes_pct")},
            "scenario_4": {"title": "", "body": data.get("key_match_dynamics") or "", "probability_pct": None},
            "key_forces_home": data.get("key_forces_home") or [],
            "key_forces_away": data.get("key_forces_away") or [],
            "professional_analysis": professional_analysis,
        }
        result = _normalize_scenarios_payload(result, default)
        if llm_usage:
            result["llm_usage"] = llm_usage
        return result
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
- quick_summary: 2-3 sentences. Always use the REAL team names, league name, and venue from the context (e.g. "Monaco hosts Angers in a Ligue 1 match at Stade Louis II") — never output placeholder text like [Home], [Away], [League] or [Venue]. If "MOTIVATION AND CONTEXT ANALYSIS" or "SCRAPED NEWS" is provided in the context, you MUST use it: mention motivation factors, injuries/rotation, stakes (relegation, derby, must-win), and key news that could impact the match. If recent match commentaries/news include concrete results, include at least one factual sentence with opponent + result (e.g. "Lens come in confident after beating Reims 2-1"). Do NOT include score ranges or specific score predictions (e.g. no "1-0 or 2-1", "likely score range", "could end 2-1").
- scenario_1: One paragraph describing the single most likely way the match will unfold on the pitch. Focus on narrative: who will control the game, how the first 20–30 minutes might go, how pressure and transitions will play out. Use the data (xG, form, motivation) to inform the story but write as a match narrative. Do not list stats; describe what will happen.
- scenario_2: Object with title (short, descriptive of what happens in this scenario — e.g. "Home side grinds out a narrow win" or "Both teams score in an open game"; NOT generic labels like "Win probability" or "BTTS and goals"), body (2-3 sentences max, short and concise, describing what will happen on the pitch in this scenario), probability_pct (number or null).
- scenario_3: Same structure as scenario_2: descriptive title + short concise body (2-3 sentences).
- scenario_4: Same structure as scenario_2: descriptive title + short concise body (2-3 sentences).
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
        data = _normalize_scenarios_payload(data, default)
        data.setdefault("quick_summary", default["quick_summary"])
        data.setdefault("scenario_1", default["scenario_1"])
        data.setdefault("key_forces_home", default["key_forces_home"])
        data.setdefault("key_forces_away", default["key_forces_away"])
        llm_usage = usage_from_openai(r)
        if llm_usage:
            data["llm_usage"] = llm_usage
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


CHAT_AI_SYSTEM = """You are Deepfoot's match assistant. Your job is to answer the user's actual question, not to recap every market.

You will receive match predictions (1X2, xG, BTTS, over/under, form, summary) plus optional news.

ANSWER SHAPE (always):
1. First sentence: a direct answer to the question.
2. Blank line.
3. Then 1–3 short blocks. Each block starts with a **bold title** on its own line, then 1–3 bullets.
4. Use markdown: blank lines between blocks, **bold** only for the pick and the fair odds, "- " bullets.
5. Keep it under 160 words. No wall of text. No numbered dump of every market.

IF they ask what to bet / which odds are interesting:
- Choose ONE primary angle (the clearest edge). Optionally one backup. Skip the rest.
- Explain WHY in football language (form, xG, news, how close the match is) — do not restack every percentage.
- Fair decimal odds = 100 / model probability %. A book price is interesting only if it is STRICTLY HIGHER than that fair odds.
- Use the fair_odds values from the data. Do not invent bookmaker prices.
- If 1X2 is tight (favorite under ~45%, or home/away gap under ~8 points), say 1X2 is low-edge and prefer BTTS or Over/Under instead of forcing a winner.
- Do not recommend exact-score bets unless asked (they are longshots).
- Close with one line: probabilities, not certainties; never stake more than you can afford to lose.

OTHER questions: answer first, then only the 1–2 stats that support it.
Never invent injuries, news, scores, or odds. If data is missing, say so.
Reply in the requested language."""


def _brief_num(val: Any) -> float | None:
    if val is None or val == "":
        return None
    try:
        return round(float(val), 1)
    except (TypeError, ValueError):
        return None


def _fair_decimal_odds(pct: float | None) -> float | None:
    """Book odds are interesting only if strictly higher than 100 / model %."""
    if pct is None or pct <= 0:
        return None
    return round(100.0 / float(pct), 2)


def _value_row(pct: float | None) -> dict[str, Any] | None:
    fair = _fair_decimal_odds(pct)
    if pct is None or fair is None:
        return None
    return {"prob_pct": pct, "fair_decimal_odds": fair}


def _brief_scenario(val: Any) -> Any:
    if isinstance(val, str) and val.strip():
        return val.strip()[:400]
    if isinstance(val, dict):
        body = str(val.get("body") or "").strip()
        title = str(val.get("title") or "").strip()
        out: dict[str, Any] = {}
        if title:
            out["title"] = title[:120]
        if body:
            out["body"] = body[:400]
        pct = _brief_num(val.get("probability_pct"))
        if pct is not None:
            out["probability_pct"] = pct
        return out or None
    return None


def build_chat_prediction_brief(analysis: dict[str, Any] | None) -> dict[str, Any]:
    """Compact prediction payload for the AI chat (1X2, xG, form, news-ready fields)."""
    if not isinstance(analysis, dict) or not analysis:
        return {}

    def pick(*keys: str) -> Any:
        for key in keys:
            val = analysis.get(key)
            if val is not None and val != "":
                return val
        return None

    home = str(pick("home_team") or "Home")
    away = str(pick("away_team") or "Away")
    mls = analysis.get("most_likely_score") if isinstance(analysis.get("most_likely_score"), dict) else {}
    over_under_out: list[dict[str, Any]] = []
    raw_ou = analysis.get("over_under")
    if isinstance(raw_ou, list):
        for item in raw_ou[:4]:
            if not isinstance(item, dict):
                continue
            over_under_out.append(
                {
                    "line": str(item.get("line") or ""),
                    "over_pct": _brief_num(item.get("over_pct")),
                    "under_pct": _brief_num(item.get("under_pct")),
                }
            )

    brief: dict[str, Any] = {
        "match": f"{home} vs {away}",
        "league": pick("league"),
        "kickoff": pick("match_date", "match_date_iso", "date"),
        "venue": pick("venue"),
        "probabilities_1x2_pct": {
            "home": _brief_num(pick("internal_prob_home", "prob_home")),
            "draw": _brief_num(pick("internal_prob_draw", "prob_draw")),
            "away": _brief_num(pick("internal_prob_away", "prob_away")),
        },
        "xg": {
            "home": _brief_num(pick("xg_home")),
            "away": _brief_num(pick("xg_away")),
            "total": _brief_num(pick("xg_total")),
        },
        "most_likely_score": None,
        "btts_yes_pct": _brief_num(pick("btts_yes_pct")),
        "btts_no_pct": _brief_num(pick("btts_no_pct")),
        "over_under": over_under_out,
        "home_form": pick("home_form"),
        "away_form": pick("away_form"),
        "home_form_label": pick("home_form_label"),
        "away_form_label": pick("away_form_label"),
        "quick_summary": (str(pick("quick_summary") or "").strip()[:800] or None),
        "match_overview": (str(pick("match_overview", "match_context_summary") or "").strip()[:600] or None),
        "motivation": {
            "home": pick("home_motivation_label"),
            "away": pick("away_motivation_label"),
        },
        "key_forces_home": pick("key_forces_home"),
        "key_forces_away": pick("key_forces_away"),
    }
    if mls:
        brief["most_likely_score"] = {
            "home": mls.get("home"),
            "away": mls.get("away"),
            "probability_pct": _brief_num(mls.get("probability")),
        }
    for key in ("scenario_1", "scenario_2", "scenario_3"):
        sc = _brief_scenario(analysis.get(key))
        if sc:
            brief[key] = sc
    injuries = pick("injuries", "injury_absence_impact")
    if injuries:
        brief["injuries"] = str(injuries)[:500]

    p1x2 = brief.get("probabilities_1x2_pct") if isinstance(brief.get("probabilities_1x2_pct"), dict) else {}
    over_25 = next((x for x in over_under_out if str(x.get("line")) == "2.5"), None)
    value_guide: dict[str, Any] = {
        "rule": "A book price is interesting only if it is strictly higher than fair_decimal_odds (100 / model %).",
        "1x2_home": _value_row(p1x2.get("home") if isinstance(p1x2, dict) else None),
        "1x2_draw": _value_row(p1x2.get("draw") if isinstance(p1x2, dict) else None),
        "1x2_away": _value_row(p1x2.get("away") if isinstance(p1x2, dict) else None),
        "btts_yes": _value_row(brief.get("btts_yes_pct") if isinstance(brief.get("btts_yes_pct"), (int, float)) else None),
        "over_2_5": _value_row(over_25.get("over_pct") if isinstance(over_25, dict) else None),
    }
    brief["value_guide"] = {k: v for k, v in value_guide.items() if v}
    return {k: v for k, v in brief.items() if v not in (None, "", [], {})}


def chat_ai_reply(
    analysis_context: dict,
    user_message: str,
    language: str = "en",
    news_context: str = "",
) -> str:
    """
    Generates a single GPT reply for the AI chat, based on the match analysis and optional news.
    analysis_context: full analysis object (quick_summary, scenarios, key_forces, etc.).
    user_message: the user's question.
    language: "en", "fr", or "es" for response language.
    news_context: optional pre-formatted news text to include.
    """
    client = _client()
    if not client:
        raise ChatAIError()
    if not (user_message or "").strip():
        return "Please ask a specific question about the match analysis."
    lang_names = {"en": "English", "fr": "French", "es": "Spanish"}
    lang_name = lang_names.get((language or "en").strip().lower(), "English")
    try:
        brief = build_chat_prediction_brief(analysis_context if isinstance(analysis_context, dict) else {})
        question = (user_message or "").strip()
        context_parts = [
            f"User question (answer this directly, do not dump every market):\n{question}",
            "Match data:",
            json.dumps(brief or {"note": "No compact prediction was available."}, ensure_ascii=False, indent=2)[:8000],
        ]
        if (news_context or "").strip():
            context_parts.append("Recent news (use only if it changes the answer):")
            context_parts.append((news_context or "").strip()[:4000])
        system = CHAT_AI_SYSTEM + f"\n\nRespond in {lang_name}."
        user_content = "\n\n".join(context_parts)
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            max_tokens=700,
        )
        raw = (r.choices[0].message.content or "").strip()
        return raw or "I couldn't generate a reply. Please try again."
    except ChatAIError:
        raise
    except Exception as e:
        logger.exception("chat_ai_reply failed: %s", e)
        raise ChatAIError() from e
