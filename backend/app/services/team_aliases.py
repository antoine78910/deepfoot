"""Canonical football team names for search (TheSportsDB / Sportmonks).

Covers national teams and multilingual / Cyrillic / typo variants.
Does not call API-Football. Used before HTTP so cloned 1X2 can be rebuilt from real form.
"""
from __future__ import annotations

import unicodedata

# Query (normalized) -> English name TheSportsDB/Sportmonks understand.
_EXACT: dict[str, str] = {
    # National teams — English / French / local
    "england": "England",
    "angleterre": "England",
    "inghilterra": "England",
    "engeland": "England",
    "inglaterra": "England",
    "czechia": "Czech Republic",
    "czech republic": "Czech Republic",
    "tchequie": "Czech Republic",
    "republique tcheque": "Czech Republic",
    "cesko": "Czech Republic",
    "ceska republika": "Czech Republic",
    "italy": "Italy",
    "italia": "Italy",
    "italie": "Italy",
    "italien": "Italy",
    "belgie": "Belgium",
    "belgiee": "Belgium",
    "belgium": "Belgium",
    "belgique": "Belgium",
    "belgio": "Belgium",
    "belgien": "Belgium",
    "israel": "Israel",
    "israeli": "Israel",
    "israël": "Israel",
    "ireland": "Ireland",
    "irlande": "Ireland",
    "eire": "Ireland",
    "republic of ireland": "Ireland",
    "irland": "Ireland",
    "irlandid": "Ireland",
    "northern ireland": "Northern Ireland",
    "irlande du nord": "Northern Ireland",
    "france": "France",
    "spain": "Spain",
    "espagne": "Spain",
    "espana": "Spain",
    "germany": "Germany",
    "allemagne": "Germany",
    "deutschland": "Germany",
    "netherlands": "Netherlands",
    "pays bas": "Netherlands",
    "hollande": "Netherlands",
    "nederland": "Netherlands",
    "portugal": "Portugal",
    "brazil": "Brazil",
    "bresil": "Brazil",
    "brasil": "Brazil",
    "argentina": "Argentina",
    "argentine": "Argentina",
    "scotland": "Scotland",
    "ecosse": "Scotland",
    "wales": "Wales",
    "pays de galles": "Wales",
    "croatia": "Croatia",
    "croatie": "Croatia",
    "hrvatska": "Croatia",
    "poland": "Poland",
    "pologne": "Poland",
    "polska": "Poland",
    "ukraine": "Ukraine",
    "sweden": "Sweden",
    "suede": "Sweden",
    "sverige": "Sweden",
    "denmark": "Denmark",
    "danemark": "Denmark",
    "danmark": "Denmark",
    "norway": "Norway",
    "norvege": "Norway",
    "norge": "Norway",
    "switzerland": "Switzerland",
    "suisse": "Switzerland",
    "schweiz": "Switzerland",
    "austria": "Austria",
    "autriche": "Austria",
    "osterreich": "Austria",
    "hungary": "Hungary",
    "hongrie": "Hungary",
    "magyarorszag": "Hungary",
    "romania": "Romania",
    "roumanie": "Romania",
    "serbia": "Serbia",
    "serbie": "Serbia",
    "srbija": "Serbia",
    "turkey": "Turkey",
    "turquie": "Turkey",
    "turkiye": "Turkey",
    "greece": "Greece",
    "grece": "Greece",
    "usa": "United States",
    "united states": "United States",
    "etats unis": "United States",
    "mexico": "Mexico",
    "mexique": "Mexico",
    "japan": "Japan",
    "japon": "Japan",
    "south korea": "South Korea",
    "coree du sud": "South Korea",
    "morocco": "Morocco",
    "maroc": "Morocco",
    "senegal": "Senegal",
    "nigeria": "Nigeria",
    "cameroon": "Cameroon",
    "cameroun": "Cameroon",
    "australia": "Australia",
    "australie": "Australia",
    "canada": "Canada",
    "slovakia": "Slovakia",
    "slovaquie": "Slovakia",
    "slovenia": "Slovenia",
    "slovenie": "Slovenia",
    "finland": "Finland",
    "finlande": "Finland",
    "iceland": "Iceland",
    "islande": "Iceland",
    "albania": "Albania",
    "albanie": "Albania",
    "bosnia": "Bosnia and Herzegovina",
    "bosnie": "Bosnia and Herzegovina",
    "georgia": "Georgia",
    "georgie": "Georgia",
    # Clubs — user examples + common Cyrillic
    "valencia": "Valencia",
    "real sociedad": "Real Sociedad",
    "thailand": "Thailand",
    "vietnam": "Vietnam",
    "lesotho": "Lesotho",
    "espain": "Spain",
    "droatia": "Croatia",
    "noway": "Norway",
    "cxech republic": "Czech Republic",
    "cxech": "Czech Republic",
    "english": "England",
    "bratford": "Bradford",
    "athletico madried": "Atletico Madrid",
    "norvegia": "Norway",
    "greece national team": "Greece",
    "bonmouth": "Bournemouth",
    "qremio": "Gremio",
    "internasional": "Inter",
    "barcelone": "Barcelona",
    "seville": "Sevilla",
    "acmilan": "AC Milan",
    "udinese-": "Udinese",
}


# Substring (normalized query contains needle) -> English search name.
_SUBSTRING: list[tuple[str, str]] = [
    ("чехия", "Czech Republic"),
    ("чешск", "Czech Republic"),
    ("англия", "England"),
    ("англии", "England"),
    ("италия", "Italy"),
    ("бельгия", "Belgium"),
    ("израиль", "Israel"),
    ("ирландия", "Ireland"),
    ("валенсия", "Valencia"),
    ("сосьедад", "Real Sociedad"),
    ("сосьсс", "Real Sociedad"),
    ("ноттингем", "Nottingham Forest"),
    ("тоттенхэм", "Tottenham"),
    ("тоттенхем", "Tottenham"),
    ("шальке", "Schalke 04"),
    ("бавария", "Bayern Munich"),
    ("эспаньол", "Espanyol"),
    ("севилья", "Sevilla"),
    ("фенербахче", "Fenerbahce"),
    ("украина", "Ukraine"),
    ("франция", "France"),
    ("германия", "Germany"),
    ("испания", "Spain"),
    ("португалия", "Portugal"),
    ("нидерланды", "Netherlands"),
    ("польша", "Poland"),
    ("шотландия", "Scotland"),
    ("хорватия", "Croatia"),
    ("турция", "Turkey"),
    ("швеция", "Sweden"),
    ("дания", "Denmark"),
    ("норвегия", "Norway"),
    ("швейцария", "Switzerland"),
    ("австрия", "Austria"),
    ("венгрия", "Hungary"),
    ("румыния", "Romania"),
    ("сербия", "Serbia"),
    ("греция", "Greece"),
    ("марокко", "Morocco"),
    ("бразилия", "Brazil"),
    ("аргентина", "Argentina"),
    ("אספנול", "Espanyol"),
    ("סבילה", "Sevilla"),
    ("γερμανια", "Germany"),
    ("ελλαδα", "Greece"),
    ("كندا", "Canada"),
    ("امريكا", "United States"),
    ("الولايات", "United States"),
]


def normalize_team_query(s: str) -> str:
    n = unicodedata.normalize("NFD", (s or "").strip().lower())
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    n = n.replace("-", " ").replace(".", " ").replace("'", " ")
    return " ".join(n.split())


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            ins = cur[j - 1] + 1
            delete = prev[j] + 1
            sub = prev[j - 1] + (0 if ca == cb else 1)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def canonical_search_name(raw: str) -> str | None:
    """Map a user/history team label to a searchable English name, or None."""
    key = normalize_team_query(raw)
    if not key:
        return None
    exact = _EXACT.get(key)
    if exact:
        return exact
    for needle, english in _SUBSTRING:
        if needle in key:
            return english
    if len(key) >= 5:
        best_name: str | None = None
        best_d = 3
        for alias_key, english in _EXACT.items():
            if abs(len(alias_key) - len(key)) > 2:
                continue
            d = _levenshtein(key, alias_key)
            if d < best_d:
                best_d = d
                best_name = english
        if best_name:
            return best_name
    return None
