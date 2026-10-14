#!/usr/bin/env python3
"""Builds the morning-brief Telegram message (used by scripts/morning-brief.sh).

Usage (from repo root, using the project venv):

    .venv/bin/python scripts/brief_message.py daily/YYYY-MM-DD.md
        [--events-json PATH | --calendar-unavailable] [--calendar-only]

Prints exactly:

    ☀️ <Polish weekday>, DD.MM

    📅 Dziś
    HH:MM <title>            (one line per event; all-day: "Cały dzień <title>")

    🎯 Priorytety            (only if the note has open "- [ ] ..." items)
    ☐ <item>

With no events the "📅 Dziś" section says "Dziś wolne od zajęć". Events come
from `ical today -o json` (start times are UTC, converted to local time), or
from --events-json PATH, a file holding that output (morning-brief.sh fetches
it with retries); declined and cancelled events, and events from the calendars in
SKIPPED_CALENDARS ("Święta w Polsce"), are left out. If the calendar
can't be read, the section says so instead of pretending the day is free; with
--calendar-unavailable (every retry failed) the whole section is the single
line "📅 Dziś: kalendarz chwilowo niedostępny, spróbuję ponownie".
--calendar-only prints just the "📅 Dziś" section (the follow-up message
morning-brief.sh sends when a later calendar retry succeeds).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

ICAL_BIN = "/usr/local/bin/ical"
WEEKDAYS_PL = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
OPEN_TASK_RE = re.compile(r"^\s*[-*] \[ \]\s+(\S.*?)\s*$")
SKIPPED_CALENDARS = {"Święta w Polsce"}
CALENDAR_UNAVAILABLE = "📅 Dziś: kalendarz chwilowo niedostępny, spróbuję ponownie"


def _nfc(text: object) -> str:
    return unicodedata.normalize("NFC", str(text or "")).strip()


def event_lines(today: date, events_json: Path | None = None) -> list[str]:
    if events_json is not None:
        raw = events_json.read_text(encoding="utf-8")
    else:
        res = subprocess.run(
            [ICAL_BIN, "today", "-o", "json"], capture_output=True, text=True, timeout=60
        )
        if res.returncode != 0:
            print(f"ical today nie powiodło się: {res.stderr.strip()[:200]}", file=sys.stderr)
            return ["Nie udało się odczytać kalendarza"]
        raw = res.stdout
    events = json.loads(raw or "[]") or []
    skipped = {_nfc(c) for c in SKIPPED_CALENDARS}

    all_day: list[str] = []
    timed: list[tuple[datetime, str]] = []
    for ev in events:
        if ev.get("self_status") == "declined" or ev.get("status") == "canceled":
            continue
        if _nfc(ev.get("calendar")) in skipped:
            continue
        title = " ".join(str(ev.get("title") or "(bez tytułu)").split())
        if ev.get("all_day"):
            all_day.append(f"Cały dzień {title}")
            continue
        try:
            start = datetime.fromisoformat(str(ev["start_date"]).replace("Z", "+00:00")).astimezone()
        except (KeyError, ValueError):
            continue
        # `ical today` also returns events that started earlier and run into today.
        if start.date() == today:
            timed.append((start, title))
    timed.sort(key=lambda t: t[0])
    return all_day + [f"{start:%H:%M} {title}" for start, title in timed]


def open_priorities(note_path: Path) -> list[str]:
    try:
        lines = note_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    items: list[str] = []
    in_section = False
    for line in lines:
        if line.startswith("## "):
            in_section = "Priorytety" in line
            continue
        if in_section:
            m = OPEN_TASK_RE.match(line)
            if m:
                items.append(m.group(1))
    return items


def main() -> None:
    parser = argparse.ArgumentParser(description="Treść porannego briefu na Telegram.")
    parser.add_argument("note", type=Path, help="ścieżka notatki dziennej")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--events-json", type=Path, help="gotowy wynik `ical today -o json`")
    source.add_argument("--calendar-unavailable", action="store_true", help="kalendarz nieosiągalny")
    parser.add_argument("--calendar-only", action="store_true", help="tylko sekcja 📅 Dziś")
    args = parser.parse_args()
    today = date.today()

    if args.calendar_unavailable:
        calendar = CALENDAR_UNAVAILABLE
    else:
        events = event_lines(today, args.events_json) or ["Dziś wolne od zajęć"]
        calendar = "📅 Dziś\n" + "\n".join(events)
    if args.calendar_only:
        print(calendar)
        return

    parts = [f"☀️ {WEEKDAYS_PL[today.weekday()]}, {today:%d.%m}", calendar]
    priorities = open_priorities(args.note)
    if priorities:
        parts.append("🎯 Priorytety\n" + "\n".join(f"☐ {p}" for p in priorities))
    print("\n\n".join(parts))


if __name__ == "__main__":
    main()
