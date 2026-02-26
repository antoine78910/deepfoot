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


def predict_all(
    lambda_home: float,
    lambda_away: float,
) -> dict:
    """
    Retourne xG, 1X2, BTTS, Over/Under et top exact scores.
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

    return {
        "xg_home": round(lambda_home, 2),
        "xg_away": round(lambda_away, 2),
        "xg_total": round(lambda_home + lambda_away, 2),
        "prob_home": round(p1 * 100, 1),
        "prob_draw": round(px * 100, 1),
        "prob_away": round(p2 * 100, 1),
        "btts_yes_pct": round(btts_yes * 100, 1),
        "btts_no_pct": round(btts_no * 100, 1),
        "over_under": over_under,
        "exact_scores": exact_scores,
    }
