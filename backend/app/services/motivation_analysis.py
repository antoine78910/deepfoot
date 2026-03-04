"""
Football match motivation analysis via OpenAI: analyzes scraped news + context
and returns structured insight (stakes, injuries, rotation, motivation scores) for
summary and scenarios.
"""
from __future__ import annotations

from typing import Any, Optional

from openai import OpenAI

from app.core.config import get_settings


MOTIVATION_SYSTEM_PROMPT = """You are a football analyst specialized in match context analysis.

Your task is to analyze news, context and information about two football teams before a match and determine their motivation level.

INPUT:
You will receive:
- News articles about both teams
- Context information (league position, injuries, upcoming matches)
- Any relevant media reports

GOAL:
Generate a structured analysis about:
1. Team motivation
2. Current situation
3. Key factors impacting performance

ANALYSIS CRITERIA:
Evaluate motivation based on:

1. Competition stakes
- Title race
- European qualification
- Relegation battle
- End of season with no objective

2. Match importance
- Derby / rivalry
- Must-win match
- Knockout competition

3. Schedule pressure
- Champions League or European games soon
- Congested schedule
- Possible squad rotation

4. Squad situation
- Injuries
- Suspensions
- Key players missing
- Expected lineup rotation

5. Psychological context
- New coach
- Winning/losing streak
- Media pressure
- Internal problems

6. Public statements
- Coach press conferences
- Player interviews
- Club communication

OUTPUT FORMAT:

MATCH CONTEXT
Short summary explaining the importance of the match.

TEAM 1 ANALYSIS
Team name:
Current situation:
Motivation factors:
Injuries / suspensions:
Expected rotation:
Recent form:
Motivation score: (0-100)
Short explanation:

TEAM 2 ANALYSIS
Team name:
Current situation:
Motivation factors:
Injuries / suspensions:
Expected rotation:
Recent form:
Motivation score: (0-100)
Short explanation:

MOTIVATION COMPARISON
Which team is more motivated and why.

KEY NEWS SUMMARY
Summarize the most important news impacting the match.

FINAL CONTEXT INSIGHT
Explain how motivation could influence the match result.

Important: 
Be concise, factual and avoid speculation not supported by the news."""


def _client() -> OpenAI | None:
    key = get_settings().openai_api_key
    if not key:
        return None
    return OpenAI(api_key=key)


def run_motivation_analysis(
    news_text: str,
    home_team: str,
    away_team: str,
    league: Optional[str] = None,
    home_form_label: Optional[str] = None,
    away_form_label: Optional[str] = None,
    venue: Optional[str] = None,
    language: Optional[str] = None,
) -> str:
    """
    Run GPT with the motivation-analysis prompt. Returns the full structured text
    (MATCH CONTEXT, TEAM 1/2 ANALYSIS, MOTIVATION COMPARISON, etc.) to be included
    in the main summary/scenarios prompt.
    """
    client = _client()
    if not client:
        return ""

    context_parts = [
        f"Teams: {home_team} (Team 1 / Home) vs {away_team} (Team 2 / Away).",
    ]
    if league:
        context_parts.append(f"League: {league}.")
    if venue:
        context_parts.append(f"Venue: {venue}.")
    if home_form_label:
        context_parts.append(f"{home_team} recent form: {home_form_label}.")
    if away_form_label:
        context_parts.append(f"{away_team} recent form: {away_form_label}.")
    context_parts.append("")
    context_parts.append(news_text)

    user_content = "\n".join(context_parts)
    lang_instruction = ""
    if (language or "").strip().lower() == "fr":
        lang_instruction = " Write the entire analysis in French."
    elif (language or "").strip().lower() == "es":
        lang_instruction = " Write the entire analysis in Spanish."
    else:
        lang_instruction = " Write the entire analysis in English."

    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": MOTIVATION_SYSTEM_PROMPT + lang_instruction},
                {"role": "user", "content": user_content},
            ],
            max_tokens=1500,
        )
        raw = (r.choices[0].message.content or "").strip()
        return raw
    except Exception:
        return ""
