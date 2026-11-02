"""
Rebuild 1X2 in analysis_history from real recent form (TheSportsDB + Poisson).

Does not call OpenAI or API-Football. Service role required.

Usage (from backend/):
  python scripts/recalculate_history_predictions.py
"""
from __future__ import annotations

import os
import sys
from collections import Counter

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)
from dotenv import load_dotenv

load_dotenv(".env")
load_dotenv(".env.local")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from app.services.prediction_recalc import (
    apply_recomputed_probs,
    match_cache_key,
    prob_signature,
    recompute_match_model,
)


def _fetch_all(admin) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    page = 1000
    while True:
        r = (
            admin.table("analysis_history")
            .select("id, home_team, away_team, result")
            .order("created_at", desc=False)
            .range(offset, offset + page - 1)
            .execute()
        )
        chunk = [row for row in (r.data or []) if isinstance(row, dict)]
        rows.extend(chunk)
        if len(chunk) < page:
            break
        offset += page
    return rows


def main() -> int:
    from app.core.supabase_client import get_supabase_admin

    admin = get_supabase_admin()
    if admin is None:
        print("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env.local")
        return 1

    rows = _fetch_all(admin)
    print(f"loaded {len(rows)} analysis_history rows", flush=True)
    before = Counter(prob_signature(row.get("result") if isinstance(row.get("result"), dict) else {}) for row in rows)
    print("unique 1X2 before:", len(before), flush=True)
    for sig, n in before.most_common(5):
        print(f"  {n}x {sig}", flush=True)

    cache: dict[str, dict | None] = {}
    updated = 0
    skipped = 0
    skipped_done = 0
    failed = 0
    for i, row in enumerate(rows, start=1):
        home = str(row.get("home_team") or "").strip()
        away = str(row.get("away_team") or "").strip()
        result = row.get("result") if isinstance(row.get("result"), dict) else {}
        recap = result.get("analysis_recap") if isinstance(result.get("analysis_recap"), dict) else {}
        if result.get("recalculated_from_form") or recap.get("recalculated_from_form"):
            skipped_done += 1
            continue
        key = match_cache_key(home, away)
        if key not in cache:
            try:
                cache[key] = recompute_match_model(home, away)
                computed = cache[key]
                sig = prob_signature(computed) if computed else "no-form"
                print(f"compute {len(cache)} {ascii(home)} vs {ascii(away)} -> {sig}", flush=True)
            except Exception as exc:
                print("compute failed:", ascii(home), "vs", ascii(away), exc, flush=True)
                cache[key] = None
        computed = cache[key]
        if not computed:
            skipped += 1
            continue
        merged = apply_recomputed_probs(result, computed)
        try:
            admin.table("analysis_history").update({"result": merged}).eq("id", row["id"]).execute()
            updated += 1
            if updated % 25 == 0 or i == len(rows):
                print(f"progress rows={i}/{len(rows)} updated={updated} skipped={skipped}", flush=True)
        except Exception as exc:
            print(f"update failed {row.get('id')}: {exc}", flush=True)
            failed += 1

    print(
        f"updated={updated} skipped_no_form={skipped} already_recalculated={skipped_done} "
        f"failed={failed} unique_matches={len(cache)}",
        flush=True,
    )
    refreshed = _fetch_all(admin)
    after = Counter(
        prob_signature(row.get("result") if isinstance(row.get("result"), dict) else {}) for row in refreshed
    )
    print("unique 1X2 after:", len(after), flush=True)
    for sig, n in after.most_common(8):
        print(f"  {n}x {sig}", flush=True)
    demo_rows = sum(
        1
        for row in refreshed
        if "46.7" in prob_signature(row.get("result") if isinstance(row.get("result"), dict) else {})
        and "33.1" in prob_signature(row.get("result") if isinstance(row.get("result"), dict) else {})
    )
    print(f"cloned 46.7/33.1 remaining rows: {demo_rows}", flush=True)
    if len(after) <= 1 and len(refreshed) > 1:
        print("ERROR: predictions are still generic", flush=True)
        return 2
    return 0 if failed == 0 else 3


if __name__ == "__main__":
    sys.exit(main())
