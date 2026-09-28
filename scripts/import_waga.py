#!/usr/bin/env python3
"""Imports a weight reading exported by an iOS Shortcut into data/weight.json.

Usage (from repo root, using the project venv):

    .venv/bin/python scripts/import_waga.py

Reads ~/Library/Mobile Documents/com~apple~CloudDocs/waga.txt, a single JSON
object like {"kg": 92.15000152587891, "date": "28 Sep 2026 at 22:51 "}
written daily by a Shortcut. Parses that date format, rounds the weight to
1 decimal place, and upserts an entry into data/weight.json in the exact
{date, kg} shape the Telegram bot's /waga command writes (one entry per
day, overwriting any existing entry for that day). If waga.txt doesn't
exist yet (the Shortcut hasn't run), this is not an error - the script
just says so and exits cleanly. On a successful write, rebuilds the
dashboard.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WAGA_TXT_PATH = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "waga.txt"
WEIGHT_PATH = REPO_ROOT / "data" / "weight.json"
PYTHON_BIN = REPO_ROOT / ".venv" / "bin" / "python"
BUILD_DASHBOARD_SCRIPT = REPO_ROOT / "scripts" / "build_dashboard.py"

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def parse_waga_date(raw: str) -> date:
    """Parses Shortcuts' "28 Sep 2026 at 22:51" format (English month name,
    tolerates the trailing space the Shortcut sometimes appends). Done with
    an explicit month lookup rather than strptime's locale-dependent %b, so
    this doesn't break if the machine's locale isn't English."""
    day_str, month_str, year_str, _at, _time = raw.split()
    month = MONTHS[month_str[:3].lower()]
    return date(int(year_str), month, int(day_str))


def load_weight_entries() -> list[dict]:
    if not WEIGHT_PATH.exists():
        return []
    try:
        data = json.loads(WEIGHT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def upsert_entry(entries: list[dict], date_str: str, kg: float) -> list[dict]:
    entries = [e for e in entries if not (isinstance(e, dict) and e.get("date") == date_str)]
    entries.append({"date": date_str, "kg": kg})
    entries.sort(key=lambda e: e["date"])
    return entries


def main() -> None:
    if not WAGA_TXT_PATH.exists():
        print("Brak pliku waga.txt - pomijam import wagi.")
        return

    try:
        payload = json.loads(WAGA_TXT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        print(f"Nie udało się odczytać waga.txt: {err}", file=sys.stderr)
        sys.exit(1)

    kg = payload.get("kg")
    date_raw = payload.get("date")
    if kg is None or not isinstance(date_raw, str):
        print("waga.txt nie zawiera oczekiwanych pól 'kg'/'date'.", file=sys.stderr)
        sys.exit(1)

    try:
        entry_date = parse_waga_date(date_raw)
    except (ValueError, KeyError) as err:
        print(f"Nie udało się rozpoznać daty w waga.txt ({date_raw!r}): {err}", file=sys.stderr)
        sys.exit(1)

    date_str = entry_date.isoformat()
    kg_rounded = round(float(kg), 1)

    entries = load_weight_entries()
    entries = upsert_entry(entries, date_str, kg_rounded)
    WEIGHT_PATH.parent.mkdir(parents=True, exist_ok=True)
    WEIGHT_PATH.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Zapisano wagę za {date_str}.")

    try:
        subprocess.run(
            [str(PYTHON_BIN), str(BUILD_DASHBOARD_SCRIPT)],
            check=True, cwd=REPO_ROOT,
        )
    except subprocess.CalledProcessError as err:
        print(f"Błąd przebudowy dashboardu: {err}", file=sys.stderr)


if __name__ == "__main__":
    main()
