#!/usr/bin/env python3
"""Incremental sync of Garmin Connect wellness data to local JSON files.

Usage (from repo root, using the project venv):

    .venv/bin/python scripts/garmin_sync.py

Logs in using ONLY the tokens already saved in ~/.garminconnect by
scripts/garmin_login.py. Never prompts for a password. If the saved
tokens are missing or expired, prints a message telling the user to run
scripts/garmin_login.py and exits with a non-zero status.

Fetches the last 30 days of: sleep (duration, phases, score, start/end
times), HRV (overnight average, status, baseline), resting heart rate,
Body Battery, stress, steps, and Training Readiness with its per-factor
breakdown (sleep, HRV, sleep history, stress history, recovery time,
ACWR/load), when the API returns it. Writes one JSON file per day to
data/garmin/YYYY-MM-DD.json (gitignored).

Runs incrementally: days that already have a saved file are skipped,
except for the two most recent days, which are always re-fetched since
Garmin keeps revising them as more data arrives. A short pause is added
between days that are actually fetched to stay polite to the API.
Missing fields are stored as null instead of raising errors.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

TOKENSTORE = Path("~/.garminconnect").expanduser()
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "garmin"
DAYS_TO_SYNC = 30
DAYS_ALWAYS_REFRESHED = 2
PAUSE_BETWEEN_DAYS_SECONDS = 0.5


def login() -> Garmin:
    """Log in using only saved tokens. Never prompts for credentials."""
    try:
        garmin = Garmin()
        garmin.login(str(TOKENSTORE))
        return garmin
    except GarminConnectAuthenticationError:
        print(
            "Brak ważnych tokenów Garmin Connect. Uruchom scripts/garmin_login.py, "
            "aby zalogować się ponownie.",
            file=sys.stderr,
        )
        sys.exit(1)
    except (GarminConnectConnectionError, GarminConnectTooManyRequestsError) as err:
        print(f"Błąd połączenia z Garmin Connect: {err}", file=sys.stderr)
        sys.exit(1)


def safe_call(fn: Callable[[str], Any], date_str: str) -> Any:
    """Call a garminconnect getter, returning None on any failure."""
    try:
        return fn(date_str)
    except Exception:
        return None


def dig(obj: Any, *path: str, default: Any = None) -> Any:
    """Safely walk a chain of dict keys, returning default on any miss."""
    cur = obj
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return default if cur is None else cur


def none_if_negative(value: Any) -> Any:
    """Garmin uses -1 (or negative) sentinels for 'no data'. Normalize to None."""
    if isinstance(value, (int, float)) and value < 0:
        return None
    return value


def extract_sleep(sleep_data: Any) -> dict[str, Any]:
    daily = dig(sleep_data, "dailySleepDTO", default={}) or {}
    scores = daily.get("sleepScores") or {}
    overall = scores.get("overall") or {}
    return {
        "total_seconds": daily.get("sleepTimeSeconds"),
        "deep_seconds": daily.get("deepSleepSeconds"),
        "light_seconds": daily.get("lightSleepSeconds"),
        "rem_seconds": daily.get("remSleepSeconds"),
        "awake_seconds": daily.get("awakeSleepSeconds"),
        "awake_count": daily.get("awakeCount"),
        "score": overall.get("value"),
        "score_qualifier": overall.get("qualifierKey"),
        "avg_heart_rate": daily.get("avgHeartRate"),
        "resting_heart_rate": (sleep_data or {}).get("restingHeartRate")
        if isinstance(sleep_data, dict)
        else None,
        "avg_respiration": daily.get("averageRespirationValue"),
        "avg_stress": daily.get("avgSleepStress"),
        # Garmin's "Local" sleep timestamps are epoch-ms already shifted by the
        # local UTC offset, so reading them back as UTC yields correct wall-clock
        # local time (no separate timezone conversion needed downstream).
        "start_local_ms": daily.get("sleepStartTimestampLocal"),
        "end_local_ms": daily.get("sleepEndTimestampLocal"),
    }


def extract_hrv(hrv_data: Any) -> dict[str, Any]:
    summary = dig(hrv_data, "hrvSummary", default={}) or {}
    baseline = summary.get("baseline") or {}
    return {
        "last_night_avg": summary.get("lastNightAvg"),
        "weekly_avg": summary.get("weeklyAvg"),
        "status": summary.get("status"),
        "baseline_low_upper": baseline.get("lowUpper"),
        "baseline_balanced_low": baseline.get("balancedLow"),
        "baseline_balanced_upper": baseline.get("balancedUpper"),
    }


def extract_resting_heart_rate(rhr_data: Any) -> Any:
    entries = dig(
        rhr_data,
        "allMetrics",
        "metricsMap",
        "WELLNESS_RESTING_HEART_RATE",
        default=[],
    )
    if isinstance(entries, list) and entries:
        first = entries[0]
        if isinstance(first, dict):
            return first.get("value")
    return None


def extract_body_battery(bb_data: Any) -> dict[str, Any]:
    entry = bb_data[0] if isinstance(bb_data, list) and bb_data else {}
    values_arr = entry.get("bodyBatteryValuesArray") or []
    levels = [
        v[1]
        for v in values_arr
        if isinstance(v, list) and len(v) > 1 and isinstance(v[1], (int, float)) and v[1] >= 0
    ]
    return {
        "charged": entry.get("charged"),
        "drained": entry.get("drained"),
        "max": max(levels) if levels else None,
        "min": min(levels) if levels else None,
    }


def extract_stress(stress_data: Any) -> dict[str, Any]:
    return {
        "avg": none_if_negative(dig(stress_data, "avgStressLevel")),
        "max": none_if_negative(dig(stress_data, "maxStressLevel")),
    }


def extract_steps(steps_data: Any) -> Any:
    if not isinstance(steps_data, list) or not steps_data:
        return None
    total = 0
    found_any = False
    for entry in steps_data:
        steps = entry.get("steps") if isinstance(entry, dict) else None
        if steps is not None:
            total += steps
            found_any = True
    return total if found_any else None


def extract_training_readiness(tr_data: Any) -> dict[str, Any]:
    entry = tr_data[0] if isinstance(tr_data, list) and tr_data else {}
    return {
        "score": entry.get("score"),
        "level": entry.get("level"),
        "recovery_time_hours": entry.get("recoveryTime"),
        "acute_load": entry.get("acuteLoad"),
        # Per-component contribution (0-100) behind the overall score. Only
        # the components Garmin actually returns for a given day are non-null.
        "factors": {
            "sleep": entry.get("sleepScoreFactorPercent"),
            "hrv": entry.get("hrvFactorPercent"),
            "sleep_history": entry.get("sleepHistoryFactorPercent"),
            "stress_history": entry.get("stressHistoryFactorPercent"),
            "recovery_time": entry.get("recoveryTimeFactorPercent"),
            "acwr": entry.get("acwrFactorPercent"),
        },
    }


def fetch_day(garmin: Garmin, day: date) -> dict[str, Any]:
    date_str = day.isoformat()

    sleep_data = safe_call(garmin.get_sleep_data, date_str)
    hrv_data = safe_call(garmin.get_hrv_data, date_str)
    rhr_data = safe_call(garmin.get_rhr_day, date_str)
    stress_data = safe_call(garmin.get_stress_data, date_str)
    steps_data = safe_call(garmin.get_steps_data, date_str)
    training_readiness_data = safe_call(garmin.get_training_readiness, date_str)
    try:
        bb_data = garmin.get_body_battery(date_str, date_str)
    except Exception:
        bb_data = None

    sleep = extract_sleep(sleep_data)
    if not sleep.get("resting_heart_rate"):
        sleep["resting_heart_rate"] = extract_resting_heart_rate(rhr_data)

    return {
        "date": date_str,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "sleep": sleep,
        "hrv": extract_hrv(hrv_data),
        "resting_heart_rate": sleep.get("resting_heart_rate")
        or extract_resting_heart_rate(rhr_data),
        "body_battery": extract_body_battery(bb_data),
        "stress": extract_stress(stress_data),
        "steps": extract_steps(steps_data),
        "training_readiness": extract_training_readiness(training_readiness_data),
    }


def main() -> None:
    garmin = login()
    print("Zalogowano przy użyciu zapisanej sesji.")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    today = date.today()
    all_days = [today - timedelta(days=i) for i in range(DAYS_TO_SYNC)]
    always_refresh = set(all_days[:DAYS_ALWAYS_REFRESHED])
    days_oldest_first = sorted(all_days)

    fetched = 0
    skipped = 0

    for day in days_oldest_first:
        out_path = DATA_DIR / f"{day.isoformat()}.json"
        if out_path.exists() and day not in always_refresh:
            skipped += 1
            continue

        record = fetch_day(garmin, day)
        out_path.write_text(
            json.dumps(record, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        fetched += 1
        print(f"{day.isoformat()}: zapisano")
        time.sleep(PAUSE_BETWEEN_DAYS_SECONDS)

    print(f"\nGotowe. Pobrano {fetched} dni, pominięto {skipped} dni (już zapisane).")


if __name__ == "__main__":
    main()
