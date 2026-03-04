"""
Multi-source news scraping for match analysis: RSS (Google News), NewsAPI, Twitter via Nitter.
- Google News RSS: team + injury/lineup/rotation queries.
- NewsAPI: articles per team + league.
- Twitter insiders: Nitter instances (e.g. nitter.privacydev.net) expose user RSS; we scrape
  league-relevant insiders (Ornstein, Romano, Julien Laurens, etc.) for lineup/injury/rotation
  leaks (often 30–60 min before bookmakers).
Detects motivation keywords (rotation, injury, "miss the match", "expected lineup", etc.) and
returns structured items for motivation analysis and summary enrichment.
"""
from __future__ import annotations

import re
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import httpx
import feedparser

from app.core.config import get_settings


# Keywords used by NLP to flag motivation/context (injury, rotation, pressure, etc.)
# Includes Twitter insider phrases: "miss the match", "expected lineup", "rotate squad"
MOTIVATION_KEYWORDS = [
    "rotation",
    "rest",
    "injury",
    "injuries",
    "blessure",
    "blessé",
    "must win",
    "pressure",
    "derby",
    "fight for survival",
    "relegation",
    "relégation",
    "title race",
    "european",
    "europa",
    "champions league",
    "suspension",
    "suspended",
    "lineup",
    "compos",
    "press conference",
    "conférence",
    "streak",
    "série",
    "rested",
    "key player",
    "absent",
    "doubt",
    "out",
    "miss the match",
    "will miss",
    "likely to rotate",
    "rotate squad",
    "expected lineup",
    "expected xi",
]

# Twitter insiders by league (Nitter handle → display name). Scraped via Nitter RSS.
# Ref: list of reliable insiders analysts follow (Fabrizio Romano, Ornstein, etc.)
TWITTER_INSIDERS_BY_LEAGUE: dict[str, list[tuple[str, str]]] = {
    "Ligue 1": [
        ("FabrizioRomano", "Fabrizio Romano"),
        ("julienlaurens", "Julien Laurens"),
        ("LoicTanzi", "Loïc Tanzi"),
        ("BenjaminQuarez", "Benjamin Quarez"),
        ("FlorentGermain", "Florent Germain"),
        ("sachatavolieri", "Sacha Tavolieri"),
        ("HugoGuillemet", "Hugo Guillemet"),
    ],
    "Premier League": [
        ("David_Ornstein", "David Ornstein"),
        ("Matt_Law_DT", "Matt Law"),
        ("JamesBenge", "James Benge"),
        ("NizaarKinsella", "Nizaar Kinsella"),
        ("SamuelLuckhurst", "Samuel Luckhurst"),
        ("SamLee__", "Sam Lee"),
        ("Paul_Joyce", "Paul Joyce"),
    ],
    "La Liga": [
        ("GuillemBalague", "Guillem Balague"),
        ("MarioCortegana", "Mario Cortegana"),
        ("gerardromero", "Gerard Romero"),
    ],
    "Serie A": [
        ("FabrizioRomano", "Fabrizio Romano"),
        ("DiMarzio", "Gianluca Di Marzio"),
        ("AntonioVitiello", "Antonio Vitiello"),
        ("RomeoAgresti", "Romeo Agresti"),
    ],
    "Bundesliga": [
        ("honigstein", "Raphael Honigstein"),
        ("Plettigoal", "Florian Plettenberg"),
        ("PatrickBerger_", "Patrick Berger"),
    ],
}
# Global insiders (used when league unknown or as extra)
TWITTER_INSIDERS_GLOBAL = [
    ("David_Ornstein", "David Ornstein"),
    ("FabrizioRomano", "Fabrizio Romano"),
    ("GuillemBalague", "Guillem Balague"),
]

# Nitter instances (RSS: /handle/rss). First working is used.
NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.net",
]


# League → preferred RSS/search hints (media names for display; actual fetch via Google News RSS + NewsAPI)
LEAGUE_MEDIA: dict[str, list[str]] = {
    "Ligue 1": ["L'Équipe", "RMC Sport", "Foot Mercato", "France Bleu", "MadeInFoot", "Maxifoot", "Le10Sport"],
    "Premier League": ["BBC Sport", "Sky Sports", "The Athletic", "Goal", "Football London"],
    "La Liga": ["Marca", "AS", "Mundo Deportivo", "Sport"],
    "Serie A": ["La Gazzetta dello Sport", "Sky Sport Italia", "Tuttosport", "Football Italia", "Calciomercato"],
    "Bundesliga": ["Bild", "Kicker", "Sky Sport Deutschland"],
}

# Global / multi-league RSS feeds (URLs that work without auth)
RSS_FEEDS_GLOBAL = [
    "https://news.google.com/rss/search?q=football+soccer&hl=en&gl=US&ceid=US:en",
    "https://www.espn.com/espn/rss/soccer/news",
]


def _detect_keywords(text: str) -> list[str]:
    """Detect motivation keywords in text (case-insensitive). Returns list of found keywords."""
    if not text:
        return []
    text_lower = (text or "").lower()
    found = []
    for kw in MOTIVATION_KEYWORDS:
        if kw.lower() in text_lower:
            found.append(kw)
    return found


def _fetch_google_news_rss(query: str, max_items: int = 5, lang: str = "en") -> list[dict[str, Any]]:
    """Fetch Google News RSS for a search query. Returns list of { source, title, snippet, url, keywords_found }."""
    url = "https://news.google.com/rss/search"
    params = {
        "q": query,
        "hl": lang,
        "gl": "US" if lang == "en" else ("FR" if lang == "fr" else "ES"),
        "ceid": "US:en" if lang == "en" else ("FR:fr" if lang == "fr" else "ES:es"),
    }
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            r = client.get(url, params=params)
        if r.status_code != 200:
            return []
        # Google returns XML
        feed = feedparser.parse(r.content)
        items = []
        for e in getattr(feed, "entries", [])[:max_items]:
            title = (e.get("title") or "").strip()
            summary = (e.get("summary") or "").strip()
            link = (e.get("link") or "").strip()
            source = (e.get("source", {}) or {}).get("title", "") if isinstance(e.get("source"), dict) else (e.get("source") or "")
            if not title and not summary:
                continue
            snippet = summary or title
            keywords = _detect_keywords(title + " " + snippet)
            items.append({
                "source": source or "Google News",
                "title": title,
                "snippet": snippet[:500] if snippet else "",
                "url": link,
                "keywords_found": keywords,
            })
        return items
    except Exception:
        return []


def _fetch_newsapi_snippets(
    home_team: str,
    away_team: str,
    league: Optional[str] = None,
    max_per_team: int = 4,
    max_age_days: int = 7,
) -> list[dict[str, Any]]:
    """Use NewsAPI (if configured) and return same structure as RSS items with keyword detection."""
    key = (get_settings().news_api_key or "").strip()
    if not key:
        return []
    since = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).strftime("%Y-%m-%d")
    base = "https://newsapi.org/v2/everything"
    items = []
    for name in (home_team, away_team):
        if not (name or "").strip():
            continue
        q = f'"{name}" football'
        if league and league.strip():
            q += f' "{league.strip()}"'
        try:
            with httpx.Client(timeout=8.0) as client:
                r = client.get(
                    base,
                    params={
                        "q": q[:500],
                        "apiKey": key,
                        "language": "fr" if league and "Ligue 1" in (league or "") else "en",
                        "sortBy": "publishedAt",
                        "pageSize": max_per_team,
                        "from": since,
                    },
                )
            if r.status_code != 200:
                continue
            data = r.json()
            for a in (data.get("articles") or [])[:max_per_team]:
                title = (a.get("title") or "").strip()
                desc = (a.get("description") or "").strip()
                if not title and not desc:
                    continue
                snippet = f"{title}. {desc}" if desc else title
                source = (a.get("source") or {}) or {}
                source_name = source.get("name", "NewsAPI") if isinstance(source, dict) else "NewsAPI"
                keywords = _detect_keywords(title + " " + snippet)
                items.append({
                    "source": source_name,
                    "title": title,
                    "snippet": snippet[:500],
                    "url": (a.get("url") or "").strip(),
                    "keywords_found": keywords,
                })
        except Exception:
            continue
    return items


def _get_nitter_insiders_for_league(league: Optional[str]) -> list[tuple[str, str]]:
    """Return list of (handle, display_name) for the given league + global insiders."""
    seen_handles: set[str] = set()
    out: list[tuple[str, str]] = []
    if league and league.strip():
        for key, insiders in TWITTER_INSIDERS_BY_LEAGUE.items():
            if key.lower() in (league or "").lower():
                for h, name in insiders:
                    if h not in seen_handles:
                        seen_handles.add(h)
                        out.append((h, name))
                break
    for h, name in TWITTER_INSIDERS_GLOBAL:
        if h not in seen_handles:
            seen_handles.add(h)
            out.append((h, name))
    return out[:12]


def _fetch_nitter_user_rss(handle: str, display_name: str, max_items: int = 5) -> list[dict[str, Any]]:
    """Fetch Nitter RSS for a user timeline. Returns list of { source, title, snippet, url, keywords_found }."""
    handle = (handle or "").strip().lstrip("@")
    if not handle:
        return []
    for base in NITTER_INSTANCES:
        try:
            url = f"{base.rstrip('/')}/{handle}/rss"
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                r = client.get(url)
            if r.status_code != 200:
                continue
            feed = feedparser.parse(r.content)
            items = []
            for e in getattr(feed, "entries", [])[:max_items]:
                title = (e.get("title") or "").strip()
                summary = (e.get("summary") or "").strip()
                link = (e.get("link") or "").strip()
                if not title and not summary:
                    continue
                snippet = (summary or title).replace("<p>", " ").replace("</p>", " ")
                snippet = re.sub(r"<[^>]+>", "", snippet).strip()[:400]
                keywords = _detect_keywords(title + " " + snippet)
                items.append({
                    "source": f"Twitter: @{handle} ({display_name})",
                    "title": title[:200],
                    "snippet": snippet,
                    "url": link,
                    "keywords_found": keywords,
                })
            return items
        except Exception:
            continue
    return []


def _fetch_twitter_insiders(
    league: Optional[str],
    max_items_per_user: int = 3,
    max_total: int = 15,
) -> list[dict[str, Any]]:
    """Fetch recent tweets from league-relevant insiders via Nitter RSS."""
    insiders = _get_nitter_insiders_for_league(league)
    all_items: list[dict[str, Any]] = []
    for handle, display_name in insiders:
        all_items.extend(
            _fetch_nitter_user_rss(handle, display_name, max_items=max_items_per_user)
        )
        if len(all_items) >= max_total:
            break
    return all_items[:max_total]


def _dedupe_by_title(items: list[dict[str, Any]], max_total: int = 25) -> list[dict[str, Any]]:
    """Keep first occurrence of each similar title (normalized), cap total."""
    seen: set[str] = set()
    out = []
    for it in items:
        t = (it.get("title") or "").strip().lower()
        t_norm = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]", " ", t))[:60]
        if t_norm in seen or len(out) >= max_total:
            continue
        seen.add(t_norm)
        out.append(it)
    return out


def fetch_news_multi_source(
    home_team: str,
    away_team: str,
    league: Optional[str] = None,
    max_items_total: int = 35,
    max_age_days: int = 7,
) -> list[dict[str, Any]]:
    """
    Scrape news from Google News RSS (team + injury/lineup/rotation queries), NewsAPI,
    Twitter insiders via Nitter RSS, and optional league RSS. Detect motivation keywords. Return list of
    { source, title, snippet, url, keywords_found } for motivation analysis and summary.
    """
    lang = "fr" if league and "Ligue 1" in (league or "") else "en"
    all_items: list[dict[str, Any]] = []

    # 1) NewsAPI
    all_items.extend(
        _fetch_newsapi_snippets(home_team, away_team, league, max_per_team=4, max_age_days=max_age_days)
    )

    # 2) Google News RSS — team + football
    for name in (home_team, away_team):
        if not (name or "").strip():
            continue
        q = f"{name} football"
        if league and league.strip():
            q += f" {league}"
        all_items.extend(_fetch_google_news_rss(q, max_items=4, lang=lang))

    # 3) Google News — injury / lineup / rotation (high-signal queries)
    for name in (home_team, away_team):
        if not (name or "").strip():
            continue
        for extra in ["injury", "lineup", "rotation", "press conference"]:
            all_items.extend(
                _fetch_google_news_rss(f"{name} {extra}", max_items=2, lang=lang)
            )

    # 4) Twitter insiders via Nitter (RSS per user) — lineups, injuries, rotation often leak 30–60 min before bookmakers
    try:
        twitter_items = _fetch_twitter_insiders(league, max_items_per_user=3, max_total=15)
        all_items.extend(twitter_items)
    except Exception:
        pass

    # Dedupe and cap
    all_items = _dedupe_by_title(all_items, max_total=max_items_total)
    return all_items


def format_news_for_prompt(items: list[dict[str, Any]]) -> str:
    """Format scraped news for GPT context (summary + snippets with keywords highlighted)."""
    if not items:
        return ""
    lines = []
    for i, it in enumerate(items[:20], 1):
        title = it.get("title") or ""
        snippet = (it.get("snippet") or "")[:300]
        source = it.get("source") or ""
        kw = it.get("keywords_found") or []
        kw_str = f" [Keywords: {', '.join(kw)}]" if kw else ""
        lines.append(f"{i}. [{source}] {title}. {snippet}{kw_str}")
    return "SCRAPED NEWS (use for motivation and context):\n" + "\n".join(lines)
