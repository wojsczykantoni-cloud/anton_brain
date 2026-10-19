#!/usr/bin/env python3
"""Imports a weight reading exported by an iOS Shortcut into data/weight.json.

Usage (from repo root, using the project venv):

    .venv/bin/python scripts/import_waga.py

Reads ~/Library/Mobile Documents/com~apple~CloudDocs/waga.txt, a single JSON
object like {"kg": 92.15000152587891, "date": "28 Sep 2026 at 22:51 "}
written daily by a Shortcut. Parses that date format, rounds the weight to
1 decimal place, and upserts an entry into data/weight.json in the exact
{date, kg} shape the Telegram bot's /waga command writes (one entry per
day, overwriting any existing entry for that day). On a successful write,
rebuilds the dashboard.

Before reading, asks iCloud to download the file (`brctl download`) and
waits up to 30 s until there is no ".waga.txt.icloud" placeholder (the file
evicted from the Mac) and the file's modification time and size stop
changing between two checks. If the file is still missing after that, the
run fails; if it's there but still changing, it is read anyway.

Whitespace (including no-break spaces) is trimmed from the date and the kg
before parsing, so "19 Oct 2026   at 11:17 " works; a decimal comma ("87,6",
quoted or not) is accepted as 87.6.

Every line is printed with a timestamp (stdout lands in logs/refresh.log
under refresh_all.sh). The log says when waga.txt was last modified and
whether that's fresh (today), and the exact reason when a reading is
skipped - never the weight itself. Skips without a usable reading (no
file, invalid JSON, missing/empty/non-numeric/out-of-range "kg") exit 0;
an unparseable date or a file iCloud never delivered exit 1.

Each run records its outcome in data/waga_import.json (checked_at,
file_mtime_epoch, result ok/skip/fail, reason, entry_date) - the bot's
/status uses it to warn when waga.txt is newer than the last weight entry
but the import didn't take it.

The file read is retried with growing backoff on OSError (e.g. "Resource
deadlock avoided"), since iCloud can briefly hold waga.txt locked right
after the Shortcut writes it - a single failed read isn't fatal.
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WAGA_TXT_PATH = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "waga.txt"
WEIGHT_PATH = REPO_ROOT / "data" / "weight.json"
STATE_PATH = REPO_ROOT / "data" / "waga_import.json"
PYTHON_BIN = REPO_ROOT / ".venv" / "bin" / "python"
BUILD_DASHBOARD_SCRIPT = REPO_ROOT / "scripts" / "build_dashboard.py"
BRCTL_BIN = "/usr/bin/brctl"

RETRY_DELAYS_SECONDS = [2, 4, 8, 16, 32]
# Łącznie na brctl download + pojawienie się pliku i ustabilizowanie mtime.
DOWNLOAD_WAIT_SECONDS = 30
STABLE_CHECK_SECONDS = 1.0
# Ten sam zakres co /waga w bocie.
KG_MIN, KG_MAX = 30, 250

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# Unquoted decimal comma, e.g. {"kg": 87,6, ...} from a Polish-locale
# Shortcut - invalid JSON as written, so it's normalised before parsing.
KG_DECIMAL_COMMA_RE = re.compile(r'("kg"\s*:\s*-?\d+)\s*,\s*(\d+)')
# "19 Oct 2026 at 11:17" - only the date part matters; the rest is optional.
WAGA_DATE_RE = re.compile(r"^(\d{1,2}) ([A-Za-z]{3,})\.? (\d{4})(?: at .*)?$")


class SkipReading(Exception):
    """A reading not imported; .fail = the run should exit 1."""

    def __init__(self, reason: str, fail: bool = False):
        super().__init__(reason)
        self.reason = reason
        self.fail = fail


def log(msg: str, err: bool = False) -> None:
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} - {msg}", file=sys.stderr if err else sys.stdout)


def placeholder_path(path: Path) -> Path:
    """iCloud replaces an evicted file with a hidden ".<name>.icloud" stub."""
    return path.with_name(f".{path.name}.icloud")


def request_download(path: Path, timeout: float) -> None:
    """`brctl download` - a failure isn't fatal (the file may be local already)."""
    try:
        result = subprocess.run(
            [BRCTL_BIN, "download", str(path)],
            capture_output=True, text=True, timeout=max(timeout, 1),
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        log(f"brctl download nieudane ({err}) - czekam na plik mimo to")
        return
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        log(f"brctl download: kod {result.returncode}"
            f"{': ' + detail[0][:200] if detail else ''} - czekam na plik mimo to")


def wait_until_ready(path: Path, deadline: float) -> tuple[bool, str]:
    """Waits until there's no .icloud placeholder and mtime + size are the
    same in two checks STABLE_CHECK_SECONDS apart. Returns (ready, reason)."""
    previous = None
    waited_for_change = False
    while True:
        placeholder = placeholder_path(path).exists()
        try:
            st = path.stat()
            current = (st.st_mtime_ns, st.st_size)
        except OSError:
            current = None
        if not placeholder and current is not None and current == previous:
            return True, "zmieniał się w trakcie oczekiwania" if waited_for_change else ""
        if previous is not None and current != previous:
            waited_for_change = True
        previous = None if placeholder else current
        if time.monotonic() >= deadline:
            if placeholder or current is None:
                return False, "nadal tylko znacznik .icloud - plik niepobrany z iCloud"
            return False, "data modyfikacji nadal się zmienia"
        time.sleep(STABLE_CHECK_SECONDS)


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
            log(f"Odczyt waga.txt powiódł się po {attempt} nieudanej/ych "
                f"próbie/ach (ostatni błąd: {last_err}).")
        return text
    raise last_err


def parse_payload(raw_text: str) -> dict:
    """waga.txt as a JSON object, falling back to a copy with an unquoted
    decimal comma in "kg" fixed."""
    text = raw_text.lstrip("﻿").strip()
    if not text:
        raise SkipReading("plik jest pusty")
    error = None
    for candidate in (text, KG_DECIMAL_COMMA_RE.sub(r"\1.\2", text)):
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as err:
            error = error or err
            continue
        if not isinstance(payload, dict):
            raise SkipReading(f"oczekiwano obiektu JSON, jest {type(payload).__name__}")
        return payload
    raise SkipReading(f"niepoprawny JSON ({error.msg}, linia {error.lineno}, kolumna {error.colno})")


def parse_kg(value: object) -> float:
    """The weight from a JSON number or a numeric string with a dot or a
    comma ("87,6" -> 87.6). The reason never includes the value itself."""
    if value is None:
        raise SkipReading('brak pola "kg"')
    if isinstance(value, bool):
        raise SkipReading('"kg" jest wartością logiczną, nie liczbą')
    if isinstance(value, (int, float)):
        kg = float(value)
    elif isinstance(value, str):
        cleaned = re.sub(r"\s+", "", value).replace(",", ".")
        if not cleaned:
            raise SkipReading('puste pole "kg"')
        try:
            kg = float(cleaned)
        except ValueError:
            raise SkipReading('"kg" nie jest liczbą') from None
    else:
        raise SkipReading(f'"kg" ma typ {type(value).__name__}, oczekiwano liczby')
    if not math.isfinite(kg):
        raise SkipReading('"kg" nie jest skończoną liczbą')
    if not KG_MIN <= kg <= KG_MAX:
        raise SkipReading(f'"kg" poza zakresem {KG_MIN}-{KG_MAX}')
    return kg


def parse_waga_date(raw: object) -> date:
    """Parses Shortcuts' "28 Sep 2026 at 22:51" format with any amount of
    whitespace (also no-break spaces). Explicit month lookup rather than
    strptime's locale-dependent %b."""
    if raw is None:
        raise SkipReading('brak pola "date"', fail=True)
    if not isinstance(raw, str):
        raise SkipReading(f'"date" ma typ {type(raw).__name__}, oczekiwano tekstu', fail=True)
    cleaned = re.sub(r"\s+", " ", raw).strip()
    m = WAGA_DATE_RE.match(cleaned)
    if not m:
        raise SkipReading(f'nie rozpoznaję daty {raw!r} (oczekiwano np. "19 Oct 2026 at 11:17")', fail=True)
    month = MONTHS.get(m.group(2)[:3].lower())
    if not month:
        raise SkipReading(f"nieznany miesiąc {m.group(2)!r} w dacie {raw!r}", fail=True)
    try:
        parsed = date(int(m.group(3)), month, int(m.group(1)))
    except ValueError as err:
        raise SkipReading(f"nieprawidłowa data {raw!r} ({err})", fail=True) from None
    if parsed > date.today():
        raise SkipReading(f"data {parsed.isoformat()} jest z przyszłości", fail=True)
    return parsed


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


def load_state() -> dict:
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(result: str, reason: str | None, mtime_epoch: int | None, entry_date: str | None = None) -> None:
    state = {
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "file_mtime_epoch": mtime_epoch,
        "result": result,
        "reason": reason,
        "entry_date": entry_date,
    }
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, STATE_PATH)
    except OSError as err:
        log(f"Nie udało się zapisać {STATE_PATH.name}: {err}", err=True)


def _age(delta_seconds: float) -> str:
    minutes = int(delta_seconds // 60)
    if minutes < 60:
        return f"{minutes} min temu"
    if minutes < 48 * 60:
        return f"{minutes // 60} h temu"
    return f"{minutes // (24 * 60)} dni temu"


def log_freshness(mtime: datetime, mtime_epoch: int, previous: dict) -> None:
    fresh = "świeży (zmieniony dziś)" if mtime.date() == date.today() else "nieświeży (nie zmieniony dziś)"
    same = previous.get("file_mtime_epoch") == mtime_epoch
    since = ""
    if same:
        since = f", bez zmian od poprzedniego sprawdzenia ({previous.get('result')})"
    log(f"waga.txt zmodyfikowany {mtime:%Y-%m-%d %H:%M:%S} "
        f"({_age(time.time() - mtime_epoch)}) - {fresh}{since}")


def main() -> None:
    path = WAGA_TXT_PATH
    if not path.exists() and not placeholder_path(path).exists():
        log("Brak pliku waga.txt w iCloud Drive (ani znacznika .icloud) - pomijam import wagi.")
        save_state("skip", "brak pliku", None)
        return

    deadline = time.monotonic() + DOWNLOAD_WAIT_SECONDS
    request_download(path, deadline - time.monotonic())
    ready, note = wait_until_ready(path, deadline)
    if not ready and not path.exists():
        reason = f"po {DOWNLOAD_WAIT_SECONDS} s {note}"
        log(f"waga.txt: pomijam wpis - {reason}", err=True)
        save_state("fail", reason, None)
        sys.exit(1)
    if not ready:
        log(f"waga.txt: po {DOWNLOAD_WAIT_SECONDS} s {note} - czytam mimo to")
    elif note:
        log(f"waga.txt {note} - odczekano, aż się ustabilizuje")

    st = path.stat()
    mtime_epoch = int(st.st_mtime)
    log_freshness(datetime.fromtimestamp(st.st_mtime), mtime_epoch, load_state())

    try:
        raw_text = read_waga_text()
    except OSError as err:
        tries = len(RETRY_DELAYS_SECONDS) + 1
        reason = f"nie udało się odczytać pliku po {tries} próbach: {err}"
        log(f"waga.txt: pomijam wpis - {reason}", err=True)
        save_state("fail", reason, mtime_epoch)
        sys.exit(1)

    try:
        payload = parse_payload(raw_text)
        kg = parse_kg(payload.get("kg"))
        entry_date = parse_waga_date(payload.get("date"))
    except SkipReading as skip:
        log(f"waga.txt: pomijam wpis - {skip.reason}", err=skip.fail)
        save_state("fail" if skip.fail else "skip", skip.reason, mtime_epoch)
        if skip.fail:
            sys.exit(1)
        return

    date_str = entry_date.isoformat()
    entries = upsert_entry(load_weight_entries(), date_str, round(kg, 1))
    WEIGHT_PATH.parent.mkdir(parents=True, exist_ok=True)
    WEIGHT_PATH.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
    save_state("ok", None, mtime_epoch, date_str)
    log(f"Zapisano wagę za {date_str}.")

    try:
        subprocess.run(
            [str(PYTHON_BIN), str(BUILD_DASHBOARD_SCRIPT)],
            check=True, cwd=REPO_ROOT,
        )
    except subprocess.CalledProcessError as err:
        log(f"Błąd przebudowy dashboardu: {err}", err=True)


if __name__ == "__main__":
    main()
