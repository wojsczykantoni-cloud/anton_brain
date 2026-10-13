#!/usr/bin/env python3
"""Incremental sync of Hevy workouts to local JSON files.

Usage (from repo root, using the project venv):

    .venv/bin/python scripts/hevy_sync.py

Reads HEVY_API_KEY from .env (the public Hevy API is available to Hevy Pro
accounts only; the key comes from https://hevy.com/settings?developer). The
key is sent only in the ``api-key`` header and never printed or logged.

First run: pages through GET /v1/workouts and saves every workout to
data/hevy/workouts/<id>.json. Later runs: GET /v1/workouts/events?since=<last
sync> and apply the "updated" (rewrite file) and "deleted" (remove file)
events, so edits and deletions made in the app are mirrored too. Exercise
templates (muscle groups for the training dashboard) are cached in
data/hevy/exercise_templates.json and re-fetched only when a workout refers
to a template that isn't cached yet. The sync cursor lives in
data/hevy/state.json and only advances after a fully successful run.

Requests are retried with growing backoff on network errors, 429 and 5xx.
Timestamps in the log come from scripts/refresh_all.sh, which runs this.

Exit codes: 0 OK, 2 key rejected (401/403 - invalid key or no Hevy Pro),
3 network / Hevy unavailable, 4 HEVY_API_KEY missing in .env, 1 other.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"
HEVY_DIR = REPO_ROOT / "data" / "hevy"
WORKOUTS_DIR = HEVY_DIR / "workouts"
TEMPLATES_PATH = HEVY_DIR / "exercise_templates.json"
STATE_PATH = HEVY_DIR / "state.json"

API_BASE = "https://api.hevyapp.com/v1"
PAGE_SIZE = 10  # API maximum for workouts and events
TEMPLATES_PAGE_SIZE = 100  # API maximum for exercise templates
RETRY_DELAYS_SECONDS = [5, 15, 45]
PAUSE_BETWEEN_PAGES_SECONDS = 0.3
# Overlap the events window so an update made right around the previous sync
# is never missed; re-applying an "updated" event is idempotent.
SINCE_OVERLAP = timedelta(hours=1)

EXIT_AUTH = 2
EXIT_NETWORK = 3
EXIT_NO_KEY = 4


class HevyAuthError(Exception):
    pass


class HevyNetworkError(Exception):
    pass


def read_api_key() -> str | None:
    try:
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.strip().partition("=")
            if sep and key.strip() == "HEVY_API_KEY":
                return value.strip().strip('"').strip("'") or None
    except OSError:
        pass
    return os.environ.get("HEVY_API_KEY") or None


class HevyClient:
    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({"api-key": api_key, "Accept": "application/json"})

    def get(self, path: str, **params: Any) -> Any:
        last_err = ""
        for attempt, delay in enumerate([0, *RETRY_DELAYS_SECONDS], start=1):
            if delay:
                time.sleep(delay)
            try:
                resp = self.session.get(f"{API_BASE}{path}", params=params, timeout=30)
            except requests.RequestException as err:
                # Only the exception class: messages can echo request details.
                last_err = type(err).__name__
            else:
                if resp.status_code in (401, 403):
                    raise HevyAuthError(
                        f"Hevy odrzuciło klucz API (HTTP {resp.status_code}: "
                        f"{resp.text[:80].strip()}) - zły klucz albo brak Hevy Pro"
                    )
                if resp.status_code == 429 or resp.status_code >= 500:
                    last_err = f"HTTP {resp.status_code}"
                elif resp.status_code == 404:
                    return None
                elif not resp.ok:
                    raise HevyNetworkError(f"{path}: HTTP {resp.status_code} {resp.text[:120].strip()}")
                else:
                    return resp.json()
            print(
                f"Hevy {path}: próba {attempt}/{len(RETRY_DELAYS_SECONDS) + 1} nieudana ({last_err})",
                file=sys.stderr,
            )
        raise HevyNetworkError(f"Hevy niedostępne ({path}: {last_err})")

    def paged(self, path: str, key: str, page_size: int, **params: Any):
        page = 1
        while True:
            data = self.get(path, page=page, pageSize=page_size, **params) or {}
            yield from data.get(key) or []
            if page >= int(data.get("page_count") or 0):
                return
            page += 1
            time.sleep(PAUSE_BETWEEN_PAGES_SECONDS)


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def workout_path(workout_id: str) -> Path:
    # IDs are UUIDs; keep the filename safe regardless.
    safe = "".join(c for c in str(workout_id) if c.isalnum() or c == "-")
    return WORKOUTS_DIR / f"{safe}.json"


def utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sync_workouts(client: HevyClient, state: dict[str, Any]) -> tuple[int, int]:
    """Returns (saved, deleted) counts."""
    saved = deleted = 0
    last_sync = state.get("last_sync")
    if not last_sync or not any(WORKOUTS_DIR.glob("*.json")):
        print("Pierwsza synchronizacja Hevy - pobieram wszystkie treningi.")
        for workout in client.paged("/workouts", "workouts", PAGE_SIZE):
            write_json(workout_path(workout["id"]), workout)
            saved += 1
        return saved, deleted

    since_dt = datetime.strptime(last_sync, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    since = utc_iso(since_dt - SINCE_OVERLAP)
    for event in client.paged("/workouts/events", "events", PAGE_SIZE, since=since):
        if event.get("type") == "updated" and isinstance(event.get("workout"), dict):
            write_json(workout_path(event["workout"]["id"]), event["workout"])
            saved += 1
        elif event.get("type") == "deleted" and event.get("id"):
            path = workout_path(event["id"])
            if path.exists():
                path.unlink()
                deleted += 1
    return saved, deleted


def sync_templates(client: HevyClient) -> int:
    """Fetch exercise templates if any workout uses one not cached yet."""
    cached = load_json(TEMPLATES_PATH, {})
    used: set[str] = set()
    for path in WORKOUTS_DIR.glob("*.json"):
        for ex in load_json(path, {}).get("exercises") or []:
            if ex.get("exercise_template_id"):
                used.add(ex["exercise_template_id"])
    if used <= set(cached):
        return 0
    templates = {
        t["id"]: {
            "title": t.get("title"),
            "type": t.get("type"),
            "primary_muscle_group": t.get("primary_muscle_group"),
            "secondary_muscle_groups": t.get("secondary_muscle_groups") or [],
            "equipment": t.get("equipment"),
        }
        for t in client.paged("/exercise_templates", "exercise_templates", TEMPLATES_PAGE_SIZE)
        if t.get("id")
    }
    # Templates missing from the listing (e.g. deleted custom ones) - try by id.
    for template_id in sorted(used - set(templates)):
        t = client.get(f"/exercise_templates/{template_id}")
        if isinstance(t, dict) and t.get("id"):
            templates[t["id"]] = {
                "title": t.get("title"),
                "type": t.get("type"),
                "primary_muscle_group": t.get("primary_muscle_group"),
                "secondary_muscle_groups": t.get("secondary_muscle_groups") or [],
                "equipment": t.get("equipment"),
            }
    write_json(TEMPLATES_PATH, templates)
    return len(templates)


def main() -> None:
    api_key = read_api_key()
    if not api_key:
        print("Brak HEVY_API_KEY w .env - pomijam synchronizację Hevy.", file=sys.stderr)
        sys.exit(EXIT_NO_KEY)

    client = HevyClient(api_key)
    state = load_json(STATE_PATH, {})
    started = datetime.now(timezone.utc)
    WORKOUTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        saved, deleted = sync_workouts(client, state)
        templates = sync_templates(client)
    except HevyAuthError as err:
        print(str(err), file=sys.stderr)
        sys.exit(EXIT_AUTH)
    except HevyNetworkError as err:
        print(str(err), file=sys.stderr)
        sys.exit(EXIT_NETWORK)

    state["last_sync"] = utc_iso(started)
    write_json(STATE_PATH, state)
    total = len(list(WORKOUTS_DIR.glob("*.json")))
    extra = f", odświeżono {templates} szablonów ćwiczeń" if templates else ""
    print(f"Gotowe. Hevy: {saved} nowych/zmienionych, {deleted} usuniętych, razem {total} treningów{extra}.")


if __name__ == "__main__":
    main()
