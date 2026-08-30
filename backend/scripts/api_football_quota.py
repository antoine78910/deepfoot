#!/usr/bin/env python3
"""Print API-Football daily quota. Local file only unless --refresh (1 request)."""
import argparse
import json
import os
import sys
from pathlib import Path

backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend))
os.chdir(backend)


def main() -> None:
    parser = argparse.ArgumentParser(description="API-Football daily quota")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Call GET /status (counts as 1 request) to sync remaining with the provider",
    )
    args = parser.parse_args()

    from app.services.api_football import get_quota, get_api_status, _use_api

    if not _use_api():
        print("API_FOOTBALL_KEY is not set in backend/.env or .env.local")
        sys.exit(1)

    if args.refresh:
        status = get_api_status()
        requests = {}
        if isinstance(status, dict):
            inner = status.get("requests") if isinstance(status.get("requests"), dict) else status
            requests = inner if isinstance(inner, dict) else {}
        print("Provider /status:", json.dumps(requests or status, default=str)[:500])

    q = get_quota()
    print(
        f"date={q['date']} used={q['used']}/{q['limit']} remaining={q['remaining']}"
        + (f" (provider remaining={q['remaining_from_api']})" if q.get("remaining_from_api") is not None else "")
    )


if __name__ == "__main__":
    main()
