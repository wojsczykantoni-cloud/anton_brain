#!/usr/bin/env python3
"""Fallback import of Hevy workouts from a CSV export (no API key / no Pro).

Usage (from repo root, using the project venv):

    .venv/bin/python scripts/hevy_csv_import.py

refresh_all.sh runs this when scripts/hevy_sync.py can't use the API (exit
4: no HEVY_API_KEY, exit 2: key rejected). It looks in the root of iCloud
Drive (~/Library/Mobile Documents/com~apple~CloudDocs/) for *workout_data*.csv
and hevy*.csv (case-insensitive), takes the newest by modification time and
writes its workouts to data/hevy/workouts/ in the same shape the API returns,
so the dashboard's "Trening" tab reads them unchanged. A candidate that is
only an iCloud placeholder (.<name>.icloud) is downloaded first with
`brctl download`; the newest file is picked once the downloads are in.

The export has 14 columns (title, start_time, end_time, description,
exercise_title, superset_id, exercise_notes, set_index, set_type, weight_kg,
reps, distance_km, duration_seconds, rpe), one set per row, weights in kg,
dates like "13 Oct 2026, 16:00" in local time. Dates are parsed with an
explicit English month lookup, not strptime's locale-dependent %b.

Each workout is stored as data/hevy/workouts/csv-<uuid5 of start_time>.json
and the workout (its start_time) is the unit of deduplication: a workout
already in data/hevy/workouts/ is replaced as a whole by its version from the
newest CSV, with no per-set deduplication. Re-importing the full history
therefore never duplicates anything, edits made in Hevy come through, and an
exercise done in two separate blocks (set_index restarting at 0) keeps all its
sets as two exercise entries. Unchanged files aren't rewritten. Warm-up sets
keep type "warmup" (the dashboard leaves them out of working sets) and are
counted separately in the summary. Workouts already present from the API
(same start minute) are skipped. Exercises get the real template id when
data/hevy/exercise_templates.json knows the title (cached by an earlier API
sync), otherwise a "csv-<title>" template with a primary muscle group guessed
from the exercise name, so the per-muscle tiles still work.

The read is retried with growing backoff on OSError (iCloud's "[Errno 11]
Resource deadlock avoided"), as in import_waga.py. Import bookkeeping (newest
CSV seen, its mtime, time of the last successful import) goes to
data/hevy/csv_import.json, read by status.py (alert hint when the CSV is
older than 10 days) and the bot's /status. The summary never includes
weights or reps.

Exit codes: 0 imported, 5 no CSV found, 1 error (unreadable / bad format).
"""

from __future__ import annotations

import csv
import fnmatch
import io
import json
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
ICLOUD_DIR = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs"
HEVY_DIR = REPO_ROOT / "data" / "hevy"
WORKOUTS_DIR = HEVY_DIR / "workouts"
TEMPLATES_PATH = HEVY_DIR / "exercise_templates.json"
CSV_STATE_PATH = HEVY_DIR / "csv_import.json"

CSV_PATTERNS = ("*workout_data*.csv", "hevy*.csv")
CSV_ID_PREFIX = "csv-"
# Fixed namespace: the same start_time always maps to the same workout file.
ID_NAMESPACE = uuid.UUID("6f1d3c8e-2b7a-4f0e-9c55-a1b2c3d40000")

RETRY_DELAYS_SECONDS = [2, 4, 8, 16, 32]
DOWNLOAD_TIMEOUT_SECONDS = 90
DOWNLOAD_POLL_SECONDS = 3

EXIT_NO_CSV = 5

EXPECTED_COLUMNS = [
    "title", "start_time", "end_time", "description", "exercise_title", "superset_id",
    "exercise_notes", "set_index", "set_type", "weight_kg", "reps", "distance_km",
    "duration_seconds", "rpe",
]

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
DATE_RE = re.compile(r"^\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4}),?\s+(\d{1,2}):(\d{2})(?::(\d{2}))?\s*$")

SET_TYPES = {
    "warmup": "warmup", "warm_up": "warmup", "warm-up": "warmup", "warm up": "warmup",
    "normal": "normal", "failure": "failure", "dropset": "dropset", "drop_set": "dropset",
}

# First match wins, so the specific patterns come before the generic ones
# ("leg curl" before "curl", "triceps ... pushdown" before "pulldown").
MUSCLE_KEYWORDS: list[tuple[str, str]] = [
    ("crunch", "abdominals"), ("plank", "abdominals"), ("sit up", "abdominals"),
    ("leg raise", "abdominals"), ("ab wheel", "abdominals"), ("russian twist", "abdominals"),
    ("leg curl", "hamstrings"), ("romanian", "hamstrings"), ("good morning", "hamstrings"),
    ("calf", "calves"), ("hip thrust", "glutes"), ("glute", "glutes"),
    ("hip abduction", "abductors"), ("hip adduction", "adductors"),
    ("squat", "quadriceps"), ("leg press", "quadriceps"), ("leg extension", "quadriceps"),
    ("lunge", "quadriceps"), ("step up", "quadriceps"),
    ("deadlift", "lower_back"), ("back extension", "lower_back"), ("hyperextension", "lower_back"),
    ("tricep", "triceps"), ("pushdown", "triceps"), ("skull", "triceps"), ("dip", "triceps"),
    ("wrist", "forearms"), ("curl", "biceps"),
    ("face pull", "shoulders"), ("lateral raise", "shoulders"), ("front raise", "shoulders"),
    ("rear delt", "shoulders"), ("reverse fly", "shoulders"), ("shoulder press", "shoulders"),
    ("overhead press", "shoulders"), ("military press", "shoulders"), ("arnold", "shoulders"),
    ("shrug", "traps"),
    ("pulldown", "lats"), ("pull up", "lats"), ("pull-up", "lats"), ("chin up", "lats"),
    ("pullover", "lats"), ("row", "upper_back"),
    ("bench press", "chest"), ("chest", "chest"), ("fly", "chest"), ("crossover", "chest"),
    ("push up", "chest"), ("push-up", "chest"),
]


class CsvFormatError(Exception):
    pass


def log(msg: str) -> None:
    print(msg, flush=True)


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path: Path, data: Any) -> bool:
    """Writes atomically; returns False (and leaves the file alone) if the
    content is already identical."""
    text = json.dumps(data, indent=2, ensure_ascii=False)
    try:
        if path.read_text(encoding="utf-8") == text:
            return False
    except OSError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return True


# --- Finding the CSV ----------------------------------------------------------

def _matches(name: str) -> bool:
    lower = name.lower()
    return any(fnmatch.fnmatchcase(lower, p) for p in CSV_PATTERNS)


def scan_candidates() -> tuple[list[Path], list[Path]]:
    """(downloaded CSVs, real paths of CSVs that are only .icloud placeholders)."""
    files: list[Path] = []
    placeholders: list[Path] = []
    try:
        entries = list(ICLOUD_DIR.iterdir())
    except OSError:
        return files, placeholders
    names = {e.name for e in entries}
    for entry in entries:
        name = entry.name
        if name.startswith(".") and name.endswith(".icloud"):
            real = name[1:-len(".icloud")]
            if _matches(real) and real not in names:
                placeholders.append(ICLOUD_DIR / real)
        elif _matches(name) and entry.is_file():
            files.append(entry)
    return files, placeholders


def download_placeholders(placeholders: list[Path]) -> None:
    for real in placeholders:
        log(f"{real.name} jest tylko w iCloud - pobieram (brctl download).")
        try:
            subprocess.run(["brctl", "download", str(real)], capture_output=True, timeout=30)
        except (OSError, subprocess.SubprocessError) as err:
            log(f"brctl download {real.name} nieudane: {err}")
    deadline = time.monotonic() + DOWNLOAD_TIMEOUT_SECONDS
    pending = list(placeholders)
    while pending and time.monotonic() < deadline:
        time.sleep(DOWNLOAD_POLL_SECONDS)
        pending = [p for p in pending if not p.exists()]
    for p in pending:
        log(f"{p.name} nie pobrał się z iCloud w {DOWNLOAD_TIMEOUT_SECONDS} s - pomijam go w tym przebiegu.")


def find_newest_csv() -> Path | None:
    files, placeholders = scan_candidates()
    if placeholders:
        download_placeholders(placeholders)
        files, _ = scan_candidates()
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def read_csv_text(path: Path) -> str:
    """Reads the CSV, retrying on OSError with growing backoff (2s, 4s, 8s,
    16s, 32s) - iCloud can briefly hold a freshly synced file locked
    ("[Errno 11] Resource deadlock avoided"). Raises the last OSError."""
    last_err: OSError | None = None
    for attempt, delay in enumerate([0, *RETRY_DELAYS_SECONDS]):
        if delay:
            time.sleep(delay)
        try:
            text = path.read_text(encoding="utf-8-sig")
        except OSError as err:
            last_err = err
            continue
        if attempt > 0:
            log(f"Odczyt {path.name} powiódł się po {attempt} nieudanej/ych próbie/ach (ostatni błąd: {last_err}).")
        return text
    raise last_err


# --- Parsing ------------------------------------------------------------------

def parse_hevy_date(raw: str) -> datetime:
    """"13 Oct 2026, 16:00" (local time) -> aware datetime in the system zone."""
    m = DATE_RE.match(raw or "")
    if not m:
        raise ValueError(f"nieznany format daty: {raw!r}")
    day, month_str, year, hour, minute, second = m.groups()
    month = MONTHS.get(month_str[:3].lower())
    if month is None:
        raise ValueError(f"nieznany miesiąc: {raw!r}")
    naive = datetime(int(year), month, int(day), int(hour), int(minute), int(second or 0))
    return naive.astimezone()  # interpret as local time, DST-aware


def utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _num(raw: str | None) -> float | None:
    raw = (raw or "").strip().replace(",", ".")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _int(raw: str | None) -> int | None:
    v = _num(raw)
    return int(v) if v is not None else None


def _clean(v: float | None) -> float | int | None:
    """15.0 -> 15, so files look like the API's JSON."""
    return int(v) if v is not None and v.is_integer() else v


def _text(raw: str | None) -> str | None:
    raw = (raw or "").strip()
    return raw or None


def guess_muscle(title: str) -> str:
    lower = title.lower()
    for keyword, muscle in MUSCLE_KEYWORDS:
        if keyword in lower:
            return muscle
    return "other"


def csv_template_id(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return f"{CSV_ID_PREFIX}{slug or 'cwiczenie'}"


def parse_rows(text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    header = [h.strip() for h in (reader.fieldnames or [])]
    missing = [c for c in EXPECTED_COLUMNS if c not in header]
    if missing:
        raise CsvFormatError(f"brak kolumn: {', '.join(missing)}")
    return [{(k or "").strip(): v for k, v in row.items()} for row in reader]


def build_workouts(rows: list[dict[str, str]], templates: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any], int]:
    """Returns (workouts in API shape, csv templates to add, warm-up sets).

    Rows are grouped into workouts by start_time. Within a workout, a new
    exercise entry starts whenever the exercise title changes or set_index
    doesn't grow (the same exercise done again as a separate block)."""
    template_by_title = {
        str(t.get("title")).lower(): tid
        for tid, t in templates.items()
        if isinstance(t, dict) and t.get("title") and not tid.startswith(CSV_ID_PREFIX)
    }
    new_templates: dict[str, Any] = {}
    workouts: dict[str, dict[str, Any]] = {}
    warmups = 0

    for line_no, row in enumerate(rows, start=2):
        start_raw = (row.get("start_time") or "").strip()
        exercise_title = (row.get("exercise_title") or "").strip()
        set_index = _int(row.get("set_index"))
        if not start_raw or not exercise_title or set_index is None:
            raise CsvFormatError(f"wiersz {line_no}: brak start_time, exercise_title lub set_index")
        try:
            start = parse_hevy_date(start_raw)
            end_raw = (row.get("end_time") or "").strip()
            end = parse_hevy_date(end_raw) if end_raw else None
        except ValueError as err:
            raise CsvFormatError(f"wiersz {line_no}: {err}") from None

        start_iso = utc_iso(start)
        w = workouts.get(start_iso)
        if w is None:
            w = workouts[start_iso] = {
                "id": f"{CSV_ID_PREFIX}{uuid.uuid5(ID_NAMESPACE, start_iso)}",
                "title": _text(row.get("title")) or "Trening",
                "description": _text(row.get("description")),
                "start_time": start_iso,
                "end_time": utc_iso(end) if end else None,
                "updated_at": None,
                "created_at": None,
                "source": "csv",
                "exercises": [],
            }
        exercise = w["exercises"][-1] if w["exercises"] else None
        if (
            exercise is None
            or exercise["title"] != exercise_title
            or set_index <= exercise["sets"][-1]["index"]
        ):
            template_id = template_by_title.get(exercise_title.lower())
            if template_id is None:
                template_id = csv_template_id(exercise_title)
                new_templates[template_id] = {
                    "title": exercise_title,
                    "type": None,
                    "primary_muscle_group": guess_muscle(exercise_title),
                    "secondary_muscle_groups": [],
                    "equipment": None,
                    "source": "csv",
                }
            exercise = {
                "index": len(w["exercises"]),
                "title": exercise_title,
                "notes": _text(row.get("exercise_notes")),
                "exercise_template_id": template_id,
                "superset_id": _int(row.get("superset_id")),
                "sets": [],
            }
            w["exercises"].append(exercise)

        set_type = SET_TYPES.get((row.get("set_type") or "").strip().lower(), "normal")
        if set_type == "warmup":
            warmups += 1
        distance_km = _num(row.get("distance_km"))
        exercise["sets"].append({
            "index": set_index,
            "type": set_type,
            "weight_kg": _clean(_num(row.get("weight_kg"))),
            "reps": _int(row.get("reps")),
            "distance_meters": _clean(round(distance_km * 1000, 1)) if distance_km is not None else None,
            "duration_seconds": _int(row.get("duration_seconds")),
            "rpe": _clean(_num(row.get("rpe"))),
            "custom_metric": None,
        })

    return sorted(workouts.values(), key=lambda w: w["start_time"]), new_templates, warmups


def api_start_minutes() -> set[str]:
    """Start minutes (UTC, "YYYY-MM-DDTHH:MM") of workouts synced from the API."""
    minutes = set()
    for path in WORKOUTS_DIR.glob("*.json"):
        if path.name.startswith(CSV_ID_PREFIX):
            continue
        start = load_json(path, {}).get("start_time")
        if start:
            try:
                dt = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
            except ValueError:
                continue
            minutes.add(utc_iso(dt)[:16])
    return minutes


# --- Main ---------------------------------------------------------------------

def main() -> None:
    state = load_json(CSV_STATE_PATH, {})
    csv_path = find_newest_csv()
    if csv_path is None:
        log(f"Brak pliku CSV z Hevy ({' / '.join(CSV_PATTERNS)}) w iCloud Drive - pomijam import.")
        sys.exit(EXIT_NO_CSV)

    mtime = datetime.fromtimestamp(csv_path.stat().st_mtime)
    state.update({"newest_file": csv_path.name, "newest_mtime": mtime.strftime("%Y-%m-%dT%H:%M:%S")})
    write_json(CSV_STATE_PATH, state)

    try:
        text = read_csv_text(csv_path)
    except OSError as err:
        log(f"Nie udało się odczytać {csv_path.name} po {len(RETRY_DELAYS_SECONDS) + 1} próbach: {err}")
        sys.exit(1)

    templates = load_json(TEMPLATES_PATH, {})
    if not isinstance(templates, dict):
        templates = {}
    try:
        workouts, new_templates, warmups = build_workouts(parse_rows(text), templates)
    except CsvFormatError as err:
        log(f"Niepoprawny format {csv_path.name}: {err}")
        sys.exit(1)

    WORKOUTS_DIR.mkdir(parents=True, exist_ok=True)
    from_api = api_start_minutes()
    added = changed = skipped_api = 0
    for w in workouts:
        if w["start_time"][:16] in from_api:
            skipped_api += 1
            continue
        path = WORKOUTS_DIR / f"{w['id']}.json"
        existed = path.exists()
        if write_json(path, w):
            changed += existed
            added += not existed

    if new_templates:
        write_json(TEMPLATES_PATH, {**templates, **new_templates})

    state["last_import"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    state["last_import_file"] = csv_path.name
    write_json(CSV_STATE_PATH, state)

    sets_total = sum(len(ex["sets"]) for w in workouts for ex in w["exercises"])
    extras = []
    if skipped_api:
        extras.append(f"treningi już pobrane z API: {skipped_api}")
    extra = f"; {', '.join(extras)}" if extras else ""
    log(
        f"Import CSV {csv_path.name} (z {mtime:%d.%m %H:%M}): treningi: {len(workouts)} "
        f"(nowe: {added}, zmienione: {changed}), serie: {sets_total}, w tym rozgrzewkowe: "
        f"{warmups}{extra}."
    )


if __name__ == "__main__":
    main()
