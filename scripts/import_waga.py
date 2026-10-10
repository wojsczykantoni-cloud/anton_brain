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
just says so and exits cleanly. Likewise for a waga.txt without a usable
reading (invalid JSON, or a missing, empty or non-numeric "kg"): the
script logs one timestamped "waga.txt: brak pomiaru, pomijam" line, leaves
data/weight.json untouched and exits 0. A decimal comma ("87,6", quoted or
not) is accepted as 87.6. On a successful write, rebuilds the dashboard.

The file read is retried with growing backoff on OSError (e.g. "Resource
deadlock avoided"), since iCloud can briefly hold waga.txt locked right
after the Shortcut writes it - a single failed read isn't fatal. Retry
recoveries are printed to stdout, which lands in logs/garmin-sync.log when
this runs under garmin_daily.sh via launchd.
"""

from __future__ import annotations

import json
import math
import re
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WAGA_TXT_PATH = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "waga.txt"
WEIGHT_PATH = REPO_ROOT / "data" / "weight.json"
PYTHON_BIN = REPO_ROOT / ".venv" / "bin" / "python"
BUILD_DASHBOARD_SCRIPT = REPO_ROOT / "scripts" / "build_dashboard.py"

RETRY_DELAYS_SECONDS = [2, 4, 8, 16, 32]

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


# Unquoted decimal comma, e.g. {"kg": 87,6, ...} from a Polish-locale
# Shortcut - invalid JSON as written, so it's normalised before parsing.
KG_DECIMAL_COMMA_RE = re.compile(r'("kg"\s*:\s*-?\d+),(\d+)')


def log_no_reading() -> None:
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} - waga.txt: brak pomiaru, pomijam")


def parse_payload(raw_text: str) -> dict | None:
    """Parses waga.txt as a JSON object, falling back to a copy with an unquoted
    decimal comma in "kg" fixed. Returns None if it's still not a JSON object."""
    for text in (raw_text, KG_DECIMAL_COMMA_RE.sub(r"\1.\2", raw_text)):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        return payload if isinstance(payload, dict) else None
    return None


def parse_kg(value: object) -> float | None:
    """Returns the weight as a finite float - from a JSON number or a numeric
    string with either a dot or a comma ("87,6" -> 87.6). None for anything
    else (missing, empty, non-numeric)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        kg = float(value)
    elif isinstance(value, str):
        try:
            kg = float(value.strip().replace(",", "."))
        except ValueError:
            return None
    else:
        return None
    return kg if math.isfinite(kg) else None


def parse_waga_date(raw: str) -> date:
    """Parses Shortcuts' "28 Sep 2026 at 22:51" format (English month name,
    tolerates the trailing space the Shortcut sometimes appends). Done with
    an explicit month lookup rather than strptime's locale-dependent %b, so
    this doesn't break if the machine's locale isn't English."""
    day_str, month_str, year_str, _at, _time = raw.split()
    month = MONTHS[month_str[:3].lower()]
    return date(int(year_str), month, int(day_str))


def read_waga_text() -> str:
    """Reads waga.txt, retrying on OSError with growing backoff (2s, 4s, 8s,
    16s, 32s - 5 retries, 6 attempts total) before giving up. Raises the
    last OSError if every attempt fails."""
    last_err: OSError | None = None
    for attempt, delay in enumerate([0, *RETRY_DELAYS_SECONDS]):
        if delay:
            time.sleep(delay)
        try:
            text = WAGA_TXT_PATH.read_text(encoding="utf-8")
        except OSError as err:
            last_err = err
            continue
        if attempt > 0:
            print(
                f"Odczyt waga.txt powiódł się po {attempt} nieudanej/ych "
                f"próbie/ach (ostatni błąd: {last_err})."
            )
        return text
    raise last_err


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
        raw_text = read_waga_text()
    except OSError as err:
        tries = len(RETRY_DELAYS_SECONDS) + 1
        print(f"Nie udało się odczytać waga.txt po {tries} próbach: {err}", file=sys.stderr)
        sys.exit(1)

    payload = parse_payload(raw_text)
    kg = parse_kg(payload.get("kg")) if payload is not None else None
    if kg is None:
        log_no_reading()
        return

    date_raw = payload.get("date")
    if not isinstance(date_raw, str):
        print("waga.txt nie zawiera oczekiwanego pola 'date'.", file=sys.stderr)
        sys.exit(1)

    try:
        entry_date = parse_waga_date(date_raw)
    except (ValueError, KeyError) as err:
        print(f"Nie udało się rozpoznać daty w waga.txt ({date_raw!r}): {err}", file=sys.stderr)
        sys.exit(1)

    date_str = entry_date.isoformat()
    kg_rounded = round(kg, 1)

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
