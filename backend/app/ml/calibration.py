"""
Calibration 1X2 à partir des erreurs du backtest.
Apprend des écarts entre prédictions et résultats réels et applique des facteurs de correction.
"""
from __future__ import annotations

import json
import os
from typing import Optional

# Fichier de persistance (backend/data/calibration.json)
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CALIBRATION_PATH = os.path.join(_BASE, "data", "calibration.json")


def _ensure_data_dir() -> None:
    d = os.path.dirname(_CALIBRATION_PATH)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)


def load_calibration() -> Optional[dict]:
    """Charge les facteurs de calibration depuis le fichier (si présent)."""
    if not os.path.isfile(_CALIBRATION_PATH):
        return None
    try:
        with open(_CALIBRATION_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        counts = data.get("counts") or {}
        pred_1 = max(1, counts.get("pred_1") or 0)
        pred_x = max(1, counts.get("pred_x") or 0)
        pred_2 = max(1, counts.get("pred_2") or 0)
        actual_1 = counts.get("actual_1") or 0
        actual_x = counts.get("actual_x") or 0
        actual_2 = counts.get("actual_2") or 0
        # Facteurs = ratio réel / prédit (si on sur-prédit 1, facteur < 1)
        f1 = actual_1 / pred_1 if pred_1 else 1.0
        fx = actual_x / pred_x if pred_x else 1.0
        f2 = actual_2 / pred_2 if pred_2 else 1.0
        return {"factor_1": f1, "factor_x": fx, "factor_2": f2, "n_matches": data.get("n_matches"), "updated_at": data.get("updated_at")}
    except Exception:
        return None


def update_from_backtest(details: list[dict], n_matches: int) -> dict:
    """
    Met à jour la calibration à partir des détails du backtest.
    details: liste de { "actual_1x2", "pred_1x2" } (au moins les 30 premiers, ou tous si fournis).
    n_matches: nombre total de matchs du backtest.
    Compte les prédictions et résultats réels 1/X/2, enregistre les facteurs.
    """
    pred_1 = pred_x = pred_2 = 0
    actual_1 = actual_x = actual_2 = 0
    for d in details:
        pred = (d.get("pred_1x2") or "").strip()
        actual = (d.get("actual_1x2") or "").strip()
        if pred == "1":
            pred_1 += 1
        elif pred == "X":
            pred_x += 1
        elif pred == "2":
            pred_2 += 1
        if actual == "1":
            actual_1 += 1
        elif actual == "X":
            actual_x += 1
        elif actual == "2":
            actual_2 += 1
    payload = {
        "counts": {
            "pred_1": pred_1,
            "pred_x": pred_x,
            "pred_2": pred_2,
            "actual_1": actual_1,
            "actual_x": actual_x,
            "actual_2": actual_2,
        },
        "n_matches": n_matches,
        "updated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }
    _ensure_data_dir()
    with open(_CALIBRATION_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return payload


def apply_calibration(p1: float, px: float, p2: float) -> tuple[float, float, float]:
    """
    Applique les facteurs de calibration aux probabilités 1X2 (en 0–1), puis renormalise.
    Retourne (p1', px', p2') avec somme = 1.
    """
    cal = load_calibration()
    if not cal:
        return (p1, px, p2)
    f1 = cal.get("factor_1") or 1.0
    fx = cal.get("factor_x") or 1.0
    f2 = cal.get("factor_2") or 1.0
    p1_ = p1 * f1
    px_ = px * fx
    p2_ = p2 * f2
    total = p1_ + px_ + p2_
    if total <= 0:
        return (p1, px, p2)
    return (p1_ / total, px_ / total, p2_ / total)
