#!/usr/bin/env python3
"""Incremental sync of Garmin Connect wellness data to local JSON files.

Usage (from repo root, using the project venv):

    .venv/bin/python scripts/garmin_sync.py

Logs in using ONLY the tokens already saved in ~/.garminconnect by
scripts/garmin_login.py. Never prompts for a password. Network errors
(common right after the Mac wakes) are retried; on an authentication error
the DI token is refreshed explicitly once and the login retried. After every
successful run the (possibly refreshed) tokens are written back to
~/.garminconnect, so the rotating refresh token on disk never goes stale.

Exit codes: 0 OK, 2 tokens invalid (run scripts/garmin_login.py),
3 network / Garmin unavailable, 1 anything else.

Fetches the last 30 days of: sleep (duration, phases, score, start/end
times), HRV (overnight average, status, baseline), resting heart rate,
Body Battery, stress, steps, and Training Readiness with its per-factor
breakdown (sleep, HRV, sleep history, stress history, recovery time,
ACWR/load), when the API returns it. Writes one JSON file per day to
data/garmin/YYYY-MM-DD.json (gitignored).

Runs incrementally and catches up after outages: a day is fetched when
its file is missing, was saved before the day was over, or was saved while
some API calls failed ("incomplete"); the two most recent days are always
re-fetched since Garmin keeps revising them. A day where every API call
failed is NOT written (that would store a file of nulls) and the run exits
non-zero. A short pause is added between fetched days to stay polite to
the API. Missing fields are stored as null instead of raising errors.
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
LOGIN_ATTEMPTS = 3
LOGIN_RETRY_SECONDS = 20
MAX_CONSECUTIVE_DAY_FAILURES = 2

EXIT_AUTH = 2
EXIT_NETWORK = 3


class DayFetchError(Exception):
    """Every API call for a day failed - nothing worth saving."""

    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors[:3]))
        self.errors = errors

    @property
    def is_auth(self) -> bool:
        return any("Authentication" in e for e in self.errors)


def fail_auth(err: Exception) -> None:
    print(
        f"Tokeny Garmin Connect nieważne i nie dało się ich odświeżyć ({err}). "
        "Uruchom scripts/garmin_login.py, aby zalogować się ponownie.",
        file=sys.stderr,
    )
    sys.exit(EXIT_AUTH)


def force_token_refresh(garmin: Garmin) -> None:
    """Explicitly refresh the DI token and persist it.

    garminconnect refreshes on its own, but swallows refresh errors and then
    reports a plain 401 - so we do one explicit refresh to tell "refresh token
    dead" (4xx -> GarminConnectAuthenticationError) from "network down"
    (any other exception). Uses the library's private _refresh_di_token,
    since there is no public API for it (garminconnect 0.3.x).
    """
    client = garmin.client
    try:
        client.load(str(TOKENSTORE))
    except Exception as err:
        raise GarminConnectAuthenticationError(f"nie można odczytać {TOKENSTORE}: {err}") from err
    try:
        client._refresh_di_token()
    except GarminConnectAuthenticationError as err:
        # 429/5xx are Garmin-side hiccups, not a dead refresh token.
        code = str(err).rsplit(":", 1)[-1].strip()
        if code.isdigit() and (int(code) == 429 or int(code) >= 500):
            raise GarminConnectConnectionError(str(err)) from err
        raise
    client.dump(str(TOKENSTORE))
    print("Odświeżono token Garmin i zapisano w ~/.garminconnect.")


def login() -> Garmin:
    """Log in using only saved tokens. Never prompts for credentials."""
    refresh_tried = False
    last_err: Exception | None = None
    for attempt in range(1, LOGIN_ATTEMPTS + 1):
        garmin = Garmin()
        try:
            garmin.login(str(TOKENSTORE))
            return garmin
        except GarminConnectAuthenticationError as err:
            if refresh_tried:
                fail_auth(err)
            refresh_tried = True
            try:
                force_token_refresh(garmin)
                continue  # retry login immediately with the fresh token
            except GarminConnectAuthenticationError as refresh_err:
                fail_auth(refresh_err)
            except Exception as refresh_err:  # network while refreshing
                refresh_tried = False
                last_err = refresh_err
        except Exception as err:  # connection errors, 429, transport errors
            last_err = err
        print(
            f"Logowanie do Garmin Connect, próba {attempt}/{LOGIN_ATTEMPTS} nieudana: {last_err}",
            file=sys.stderr,
        )
        if attempt < LOGIN_ATTEMPTS:
            time.sleep(LOGIN_RETRY_SECONDS)
    print(
        f"Błąd połączenia z Garmin Connect po {LOGIN_ATTEMPTS} próbach: {last_err}",
        file=sys.stderr,
    )
    sys.exit(EXIT_NETWORK)


def save_tokens(garmin: Garmin) -> None:
    """Persist the current (possibly refreshed/rotated) tokens."""
    garmin.client.dump(str(TOKENSTORE))


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
    errors: list[str] = []
    calls = 0

    def safe_call(fn: Callable[..., Any], *args: str) -> Any:
        """Call a garminconnect getter, returning None on any failure."""
        nonlocal calls
        calls += 1
        try:
            return fn(*args)
        except Exception as err:
            errors.append(f"{fn.__name__}: {type(err).__name__}: {err}"[:200])
            return None

    sleep_data = safe_call(garmin.get_sleep_data, date_str)
    hrv_data = safe_call(garmin.get_hrv_data, date_str)
    rhr_data = safe_call(garmin.get_rhr_day, date_str)
    stress_data = safe_call(garmin.get_stress_data, date_str)
    steps_data = safe_call(garmin.get_steps_data, date_str)
    training_readiness_data = safe_call(garmin.get_training_readiness, date_str)
    bb_data = safe_call(garmin.get_body_battery, date_str, date_str)

    if len(errors) == calls:
        raise DayFetchError(errors)

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
        # Some calls failed (e.g. network dropped mid-day) - re-fetch next run.
        "incomplete": bool(errors),
    }


def needs_fetch(out_path: Path, day: date, always_refresh: set[date]) -> bool:
    """Missing, recent, incomplete, or saved before the day was over."""
    if day in always_refresh or not out_path.exists():
        return True
    try:
        record = json.loads(out_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return True
    if record.get("incomplete"):
        return True
    fetched_at = str(record.get("fetched_at") or "")
    return fetched_at[:10] <= day.isoformat()


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
    failed: list[str] = []
    auth_failure = False
    consecutive_failures = 0

    for day in days_oldest_first:
        out_path = DATA_DIR / f"{day.isoformat()}.json"
        if not needs_fetch(out_path, day, always_refresh):
            skipped += 1
            continue

        try:
            record = fetch_day(garmin, day)
        except DayFetchError as err:
            failed.append(day.isoformat())
            auth_failure = auth_failure or err.is_auth
            consecutive_failures += 1
            print(f"{day.isoformat()}: BŁĄD, nie zapisano ({err})", file=sys.stderr)
            if consecutive_failures >= MAX_CONSECUTIVE_DAY_FAILURES:
                print("Kolejne dni też nie przechodzą - przerywam ten przebieg.", file=sys.stderr)
                break
            continue
        consecutive_failures = 0
        out_path.write_text(
            json.dumps(record, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        fetched += 1
        print(f"{day.isoformat()}: zapisano" + (" (niepełne)" if record["incomplete"] else ""))
        time.sleep(PAUSE_BETWEEN_DAYS_SECONDS)

    try:
        save_tokens(garmin)
    except Exception as err:
        print(f"Nie udało się zapisać tokenów do {TOKENSTORE}: {err}", file=sys.stderr)
        sys.exit(1)

    if failed:
        print(
            f"Nie pobrano {len(failed)} dni ({', '.join(failed)}); zapisano {fetched}.",
            file=sys.stderr,
        )
        sys.exit(EXIT_AUTH if auth_failure else EXIT_NETWORK)

    print(f"\nGotowe. Pobrano {fetched} dni, pominięto {skipped} dni (już kompletne).")


if __name__ == "__main__":
    main()
