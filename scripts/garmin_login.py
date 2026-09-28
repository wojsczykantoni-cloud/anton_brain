#!/usr/bin/env python3
"""Interactive Garmin Connect login + quick sleep-data sanity check.

Usage (from repo root, using the project venv):

    .venv/bin/python scripts/garmin_login.py

Prompts for your Garmin email and password (password via getpass, never
echoed), and for an MFA code if Garmin asks for one. Tokens are saved by
the ``garth``/``garminconnect`` library itself to ~/.garminconnect so
future scripts can reuse the session without prompting again. This script
never writes the email or password anywhere (no file, no .env, no log) -
they only ever live in local variables in memory for the duration of the
login call.
"""

from __future__ import annotations

import getpass
import os
import sys
from datetime import date, timedelta

from garth.exc import GarthHTTPError

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

TOKENSTORE = os.path.expanduser("~/.garminconnect")


def prompt_mfa() -> str:
    """Callback used by garminconnect when Garmin requires an MFA code."""
    return input("Kod MFA (z aplikacji/SMS-a): ").strip()


def prompt_credentials() -> tuple[str, str]:
    email = input("Email Garmin Connect: ").strip()
    password = getpass.getpass("Hasło Garmin Connect: ")
    return email, password


def login() -> Garmin:
    """Log in to Garmin Connect, reusing saved tokens when possible."""
    try:
        print(f"Próbuję zalogować się przy użyciu zapisanych tokenów z '{TOKENSTORE}'...")
        garmin = Garmin()
        garmin.login(TOKENSTORE)
        print("Zalogowano przy użyciu zapisanej sesji (bez podawania hasła).")
        return garmin
    except (FileNotFoundError, GarthHTTPError, GarminConnectAuthenticationError):
        print("Brak ważnych tokenów - wymagane logowanie interaktywne.\n")

    email, password = prompt_credentials()
    try:
        garmin = Garmin(email=email, password=password, prompt_mfa=prompt_mfa)
        # Passing TOKENSTORE here makes the library persist the session
        # tokens to that directory itself once login succeeds.
        garmin.login(TOKENSTORE)
    except (
        GarminConnectAuthenticationError,
        GarminConnectConnectionError,
        GarminConnectTooManyRequestsError,
        GarthHTTPError,
    ) as err:
        print(f"Logowanie nie powiodło się: {err}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Drop credentials from memory as soon as we're done with them.
        del password

    print(f"Zalogowano i zapisano tokeny sesji w '{TOKENSTORE}'.")
    return garmin


def fmt_hms(seconds) -> str:
    if not seconds:
        return "brak danych"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m = rem // 60
    return f"{h}h {m:02d}m"


def fetch_last_night_sleep(garmin: Garmin):
    """Try today's calendar date first (typical case), fall back to yesterday."""
    for cdate in (date.today(), date.today() - timedelta(days=1)):
        data = garmin.get_sleep_data(cdate.isoformat())
        daily = (data or {}).get("dailySleepDTO") or {}
        if daily.get("sleepTimeSeconds"):
            return cdate, data, daily
    # Nothing found for either day - return the most recent (empty) result anyway.
    cdate = date.today()
    data = garmin.get_sleep_data(cdate.isoformat())
    return cdate, data, (data or {}).get("dailySleepDTO") or {}


def print_sleep_summary(garmin: Garmin) -> None:
    cdate, data, daily = fetch_last_night_sleep(garmin)
    print(f"\n=== Podsumowanie snu ({cdate.isoformat()}) ===")

    if not daily.get("sleepTimeSeconds"):
        print("Brak danych o śnie dla tej doby.")
        return

    print(f"Czas snu łącznie: {fmt_hms(daily.get('sleepTimeSeconds'))}")
    print(f"  Głęboki: {fmt_hms(daily.get('deepSleepSeconds'))}")
    print(f"  Lekki:   {fmt_hms(daily.get('lightSleepSeconds'))}")
    print(f"  REM:     {fmt_hms(daily.get('remSleepSeconds'))}")
    print(f"  Wybudzenia: {fmt_hms(daily.get('awakeSleepSeconds'))}")

    scores = daily.get("sleepScores") or {}
    overall = scores.get("overall") or {}
    if overall.get("value") is not None:
        print(f"Ocena snu: {overall.get('value')} ({overall.get('qualifierKey', '')})")
    else:
        print("Ocena snu: brak danych")

    resting_hr = daily.get("restingHeartRate")
    if not resting_hr:
        try:
            hr_data = garmin.get_heart_rates(cdate.isoformat()) or {}
            resting_hr = hr_data.get("restingHeartRate")
        except Exception:
            resting_hr = None
    print(f"Tętno spoczynkowe: {resting_hr if resting_hr else 'brak danych'}")

    try:
        hrv_data = garmin.get_hrv_data(cdate.isoformat()) or {}
        hrv_summary = hrv_data.get("hrvSummary") or {}
        last_night_avg = hrv_summary.get("lastNightAvg")
        status = hrv_summary.get("status")
        if last_night_avg is not None:
            print(f"HRV (ostatnia noc, śr.): {last_night_avg} ms ({status or 'brak statusu'})")
        else:
            print("HRV: brak danych")
    except Exception as err:
        print(f"HRV: nie udało się pobrać ({err})")

    body_battery_change = daily.get("bodyBatteryChange")
    if body_battery_change is not None:
        print(f"Body Battery podczas snu: zmiana o {body_battery_change}")
    else:
        try:
            bb_data = garmin.get_body_battery(cdate.isoformat()) or []
            if bb_data:
                charged = bb_data[0].get("charged")
                drained = bb_data[0].get("drained")
                print(f"Body Battery: naładowano {charged}, rozładowano {drained}")
            else:
                print("Body Battery: brak danych")
        except Exception as err:
            print(f"Body Battery: nie udało się pobrać ({err})")


def main() -> None:
    garmin = login()
    print_sleep_summary(garmin)


if __name__ == "__main__":
    main()
