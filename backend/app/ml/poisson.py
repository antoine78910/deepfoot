# backend/app/ml/poisson.py
"""
Modèle de Poisson pour score exact, xG, Over/Under et BTTS.
P(score i-j) = Poisson(i | λ_home) * Poisson(j | λ_away).
"""
from scipy.stats import poisson
from app.core.config import get_settings


def poisson_score_grid(lambda_home: float, lambda_away: float, max_goals: int | None = None) -> list[list[float]]:
    """Grille P(i,j) pour i,j = 0..max_goals."""
    max_goals = max_goals or get_settings().max_score_goals
    grid = []
    for i in range(max_goals + 1):
        row = []
        for j in range(max_goals + 1):
            p = poisson.pmf(i, lambda_home) * poisson.pmf(j, lambda_away)
            row.append(p)
        grid.append(row)
    return grid


def exact_score_probs(lambda_home: float, lambda_away: float, top_n: int = 10) -> list[tuple[int, int, float]]:
    """Liste des (home, away, prob) triée par proba décroissante."""
    grid = poisson_score_grid(lambda_home, lambda_away)
    max_g = len(grid) - 1
    flat = []
    for i in range(max_g + 1):
        for j in range(max_g + 1):
            flat.append((i, j, grid[i][j]))
    flat.sort(key=lambda x: -x[2])
    return flat[:top_n]


def prob_1x2_from_grid(grid: list[list[float]]) -> tuple[float, float, float]:
    """P(1) = sum i>j, P(X) = sum i=j, P(2) = sum i<j."""
    p1 = px = p2 = 0.0
    n = len(grid)
    for i in range(n):
        for j in range(n):
            p = grid[i][j]
            if i > j:
                p1 += p
            elif i == j:
                px += p
            else:
                p2 += p
    return (p1, px, p2)


def prob_over_under(total_goals: float, grid: list[list[float]]) -> tuple[float, float]:
    """P(Over total_goals), P(Under total_goals)."""
    over = 0.0
    n = len(grid)
    for i in range(n):
        for j in range(n):
            if i + j > total_goals:
                over += grid[i][j]
    under = 1.0 - over
    return (over, under)


def prob_btts(grid: list[list[float]]) -> tuple[float, float]:
    """P(BTTS Yes) = sum i>=1,j>=1 P(i,j)."""
    yes = 0.0
    n = len(grid)
    for i in range(1, n):
        for j in range(1, n):
            yes += grid[i][j]
    return (yes, 1.0 - yes)


def over_under_lines() -> list[float]:
    return [0.5, 1.5, 2.5, 3.5]


def prob_total_goals_distribution(grid: list[list[float]]) -> dict[str, float]:
    """P(total goals = 0, 1, 2, 3+)."""
    n = len(grid)
    p0 = p1 = p2 = p3plus = 0.0
    for i in range(n):
        for j in range(n):
            p = grid[i][j]
            s = i + j
            if s == 0:
                p0 += p
            elif s == 1:
                p1 += p
            elif s == 2:
                p2 += p
            else:
                p3plus += p
    return {"0": p0, "1": p1, "2": p2, "3+": p3plus}


def prob_goal_difference_distribution(grid: list[list[float]]) -> dict[str, float]:
    """P(|home - away| = 1, 2, 3+)."""
    n = len(grid)
    d1 = d2 = d3plus = 0.0
    for i in range(n):
        for j in range(n):
            p = grid[i][j]
            d = abs(i - j)
            if d == 1:
                d1 += p
            elif d == 2:
                d2 += p
            elif d >= 3:
                d3plus += p
    return {"1": d1, "2": d2, "3+": d3plus}


def prob_asian_handicap(grid: list[list[float]]) -> dict[str, float]:
    """
    Home -1: home wins with -1 goal (home - away > 1).
    Home +1: home wins with +1 goal (home + 1 > away) = home >= away.
    Away -1, Away +1: symétriques.
    """
    n = len(grid)
    h_minus1 = h_plus1 = a_minus1 = a_plus1 = 0.0
    for i in range(n):
        for j in range(n):
            p = grid[i][j]
            if i - j > 1:
                h_minus1 += p
            if i >= j:
                h_plus1 += p
            if j - i > 1:
                a_minus1 += p
            if j >= i:
                a_plus1 += p
    return {"home_neg1": h_minus1, "home_plus1": h_plus1, "away_neg1": a_minus1, "away_plus1": a_plus1}


def implied_odds(p: float, min_p: float = 0.5) -> float:
    """Cote décimale implicite (100 / prob). Évite division par zéro."""
    pct = max(p, min_p)
    return round(100 / pct, 2)


def predict_all(
    lambda_home: float,
    lambda_away: float,
) -> dict:
    """
    Retourne xG, 1X2, BTTS, Over/Under et top exact scores.
    Modèle Poisson pur : basé uniquement sur la forme et les matchs passés (lambdas).
    """
    grid = poisson_score_grid(lambda_home, lambda_away)
    p1, px, p2 = prob_1x2_from_grid(grid)
    btts_yes, btts_no = prob_btts(grid)

    over_under = []
    for line in over_under_lines():
        over_p, under_p = prob_over_under(line, grid)
        over_under.append({
            "line": str(line),
            "over_pct": round(over_p * 100, 1),
            "under_pct": round(under_p * 100, 1),
        })

    exact = exact_score_probs(lambda_home, lambda_away, top_n=5)
    exact_scores = [{"home": i, "away": j, "probability": round(p * 100, 1)} for i, j, p in exact]

    # Score le plus probable (premier de la liste)
    most_likely = exact[0] if exact else (0, 0, 0.0)
    most_likely_score = {"home": most_likely[0], "away": most_likely[1], "probability": round(most_likely[2] * 100, 1)}

    # Cotes implicites 1X2
    impl_1 = implied_odds(p1 * 100)
    impl_x = implied_odds(px * 100)
    impl_2 = implied_odds(p2 * 100)

    # Distribution total buts (0, 1, 2, 3+)
    total_dist = prob_total_goals_distribution(grid)
    total_goals_distribution = {k: round(v * 100, 1) for k, v in total_dist.items()}

    # Double chance
    double_chance_1x = (p1 + px) * 100
    double_chance_x2 = (px + p2) * 100
    double_chance_12 = (p1 + p2) * 100

    # Handicap asiatique
    ah = prob_asian_handicap(grid)
    asian_handicap = {
        "home_neg1_pct": round(ah["home_neg1"] * 100, 1),
        "home_plus1_pct": round(ah["home_plus1"] * 100, 1),
        "away_neg1_pct": round(ah["away_neg1"] * 100, 1),
        "away_plus1_pct": round(ah["away_plus1"] * 100, 1),
    }

    # Écart de buts (1, 2, 3+)
    gd = prob_goal_difference_distribution(grid)
    goal_difference_dist = {k: round(v * 100, 1) for k, v in gd.items()}

    # Probabilité upset (l'outsider gagne)
    upset_probability = round(min(p1, p2) * 100, 1)

    return {
        "xg_home": round(lambda_home, 2),
        "xg_away": round(lambda_away, 2),
        "xg_total": round(lambda_home + lambda_away, 2),
        "prob_home": round(p1 * 100, 1),
        "prob_draw": round(px * 100, 1),
        "prob_away": round(p2 * 100, 1),
        "implied_odds_home": impl_1,
        "implied_odds_draw": impl_x,
        "implied_odds_away": impl_2,
        "btts_yes_pct": round(btts_yes * 100, 1),
        "btts_no_pct": round(btts_no * 100, 1),
        "over_under": over_under,
        "exact_scores": exact_scores,
        "most_likely_score": most_likely_score,
        "total_goals_distribution": total_goals_distribution,
        "double_chance_1x": round(double_chance_1x, 1),
        "double_chance_x2": round(double_chance_x2, 1),
        "double_chance_12": round(double_chance_12, 1),
        "asian_handicap": asian_handicap,
        "goal_difference_dist": goal_difference_dist,
        "upset_probability": upset_probability,
    }
