#!/usr/bin/env python3
"""Habit tracker for the "Nawyki" tab of scripts/build_dashboard.py.

Habits are defined in data/habits.json (optional; DEFAULT_HABITS otherwise):

    {"habits": [
      {"id": "kroki", "name": "10 000 kroków", "type": "auto", "source": "steps", "min": 10000},
      {"id": "nauka", "name": "Nauka", "type": "manual"}
    ]}

Auto habits are evaluated from data the dashboard already loads - "steps"
(Garmin, min steps), "sleep" (Garmin, min hours; the night ending that
morning), "workout" (a Hevy session that day), "food" (data/food/<date>.json)
and "weight" (an entry in data/weight.json) - and exist only in the
dashboard: they are never written to daily notes or sent in the brief.
Manual habits are checkboxes in the "## 🔁 Nawyki" section of
daily/YYYY-MM-DD.md ("- [x] Czytanie"), matched by name or id (case and
Polish diacritics ignored; text after the name is allowed, e.g.
"- [x] Czytanie - 30 stron"). The bot's /nawyk ticks them.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
HABITS_PATH = REPO_ROOT / "data" / "habits.json"
DAILY_DIR = REPO_ROOT / "daily"

# Domyślne nawyki ręczne są też w bot.js (DEFAULT_MANUAL_HABITS) i w
# templates/daily.md - przy zmianie poprawić wszystkie trzy miejsca.
DEFAULT_HABITS: list[dict[str, Any]] = [
    {"id": "kroki", "name": "10 000 kroków", "type": "auto", "source": "steps", "min": 10000},
    {"id": "trening", "name": "Trening", "type": "auto", "source": "workout"},
    {"id": "jedzenie", "name": "Jedzenie zalogowane", "type": "auto", "source": "food"},
    {"id": "sen", "name": "Sen 7h+", "type": "auto", "source": "sleep", "min": 7},
    {"id": "waga", "name": "Waga zapisana", "type": "auto", "source": "weight"},
    {"id": "nauka", "name": "Nauka", "type": "manual"},
    {"id": "czytanie", "name": "Czytanie", "type": "manual"},
    {"id": "cardio", "name": "Cardio 20 min", "type": "manual"},
]
AUTO_SOURCES = {"steps", "sleep", "workout", "food", "weight"}
DEFAULT_MIN = {"steps": 10000, "sleep": 7}

HABITS_HEADING_RE = re.compile(r"^##\s+.*\bNawyki\b")
CHECKBOX_RE = re.compile(r"^\s*[-*]\s+\[([ xX])\]\s+(\S.*?)\s*$")

# Stany dnia: zrobione / niezrobione / brak danych (Garmin nie ma rekordu) /
# dziś jeszcze otwarte (nie psuje serii ani procentów).
DONE, MISSED, UNKNOWN, PENDING = "done", "missed", "unknown", "pending"


@dataclass
class Habit:
    id: str
    name: str
    type: str  # "auto" | "manual"
    source: str | None = None
    min: float | None = None


def _warn(msg: str) -> None:
    print(f"habits.json: {msg}", file=sys.stderr)


def _habit_from_dict(raw: Any) -> Habit | None:
    if not isinstance(raw, dict) or not str(raw.get("id") or "").strip() or not str(raw.get("name") or "").strip():
        _warn(f"pomijam wpis bez id lub nazwy: {raw!r}")
        return None
    hid, name, kind = str(raw["id"]).strip(), str(raw["name"]).strip(), raw.get("type")
    if kind == "manual":
        return Habit(hid, name, "manual")
    if kind != "auto":
        _warn(f"pomijam „{name}”: type musi być auto albo manual")
        return None
    default = next((d for d in DEFAULT_HABITS if d["id"] == hid and d["type"] == "auto"), {})
    source = raw.get("source") or default.get("source")
    if source not in AUTO_SOURCES:
        _warn(f"pomijam „{name}”: source musi być jednym z {', '.join(sorted(AUTO_SOURCES))}")
        return None
    minimum = raw.get("min", DEFAULT_MIN.get(source))
    if source in DEFAULT_MIN and (isinstance(minimum, bool) or not isinstance(minimum, (int, float)) or minimum <= 0):
        _warn(f"„{name}”: nieprawidłowe min - używam {DEFAULT_MIN[source]}")
        minimum = DEFAULT_MIN[source]
    return Habit(hid, name, "auto", source, minimum if source in DEFAULT_MIN else None)


def load_habits(path: Path = HABITS_PATH) -> list[Habit]:
    raw_list: Any = DEFAULT_HABITS
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            raw_list = data.get("habits") if isinstance(data, dict) else None
            if not isinstance(raw_list, list):
                raise ValueError('oczekiwano {"habits": [...]}')
        except (OSError, ValueError) as err:
            _warn(f"nie da się odczytać ({err}) - używam domyślnych nawyków")
            raw_list = DEFAULT_HABITS
    habits: list[Habit] = []
    for raw in raw_list:
        h = _habit_from_dict(raw)
        if h and any(x.id == h.id for x in habits):
            _warn(f"pomijam powtórzone id „{h.id}”")
        elif h:
            habits.append(h)
    return habits


def normalize(text: str) -> str:
    """Casefold, no diacritics (ł -> l too), single spaces."""
    text = unicodedata.normalize("NFKD", text.casefold().replace("ł", "l"))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip()


def label_matches(habit: Habit, label: str) -> bool:
    n = normalize(label)
    for key in (normalize(habit.name), normalize(habit.id)):
        if n == key or (n.startswith(key) and not n[len(key)].isalnum()):
            return True
    return False


def note_checkboxes(text: str) -> list[tuple[bool, str]]:
    """(checked, label) for every checkbox in the note's Nawyki section."""
    result = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = bool(HABITS_HEADING_RE.match(line))
            continue
        if in_section:
            m = CHECKBOX_RE.match(line)
            if m:
                result.append((m.group(1) in "xX", m.group(2)))
    return result


def load_note_checkboxes(daily_dir: Path, start: date, end: date) -> dict[date, list[tuple[bool, str]]]:
    result = {}
    d = start
    while d <= end:
        try:
            result[d] = note_checkboxes((daily_dir / f"{d.isoformat()}.md").read_text(encoding="utf-8"))
        except OSError:
            pass
        d += timedelta(days=1)
    return result


@dataclass
class Sources:
    steps: dict[date, float] = field(default_factory=dict)
    sleep_hours: dict[date, float] = field(default_factory=dict)
    workout_days: set[date] = field(default_factory=set)
    food_days: set[date] = field(default_factory=set)
    weight_days: set[date] = field(default_factory=set)
    notes: dict[date, list[tuple[bool, str]]] = field(default_factory=dict)


def day_state(habit: Habit, d: date, src: Sources, today: date) -> str:
    is_today = d == today
    if habit.type == "manual":
        done = any(checked and label_matches(habit, label) for checked, label in src.notes.get(d, []))
    elif habit.source in ("steps", "sleep"):
        values = src.steps if habit.source == "steps" else src.sleep_hours
        value = values.get(d)
        if value is None:
            # Brak rekordu Garmina to "nie wiadomo", nie porażka.
            return PENDING if is_today else UNKNOWN
        done = value >= habit.min
        if not done and habit.source == "sleep":
            return MISSED  # dzisiejsza noc już się skończyła
    else:
        days = {"workout": src.workout_days, "food": src.food_days, "weight": src.weight_days}[habit.source]
        done = d in days
    if done:
        return DONE
    return PENDING if is_today else MISSED


@dataclass
class HabitStats:
    habit: Habit
    states: dict[date, str]  # od start do today
    current_streak: int
    longest_streak: int
    pct_7: float | None
    pct_30: float | None


def _pct(states: dict[date, str], today: date, days: int) -> float | None:
    """Share of done among the last `days` full days (today excluded), days
    without data left out of the denominator."""
    window = [states.get(today - timedelta(days=i)) for i in range(1, days + 1)]
    known = [s for s in window if s in (DONE, MISSED)]
    return 100 * sum(s == DONE for s in known) / len(known) if known else None


def habit_stats(habits: list[Habit], src: Sources, start: date, today: date) -> list[HabitStats]:
    result = []
    for h in habits:
        states = {}
        d = start
        while d <= today:
            states[d] = day_state(h, d, src, today)
            d += timedelta(days=1)

        longest = run = 0
        for s in states.values():
            run = run + 1 if s == DONE else (run if s == PENDING else 0)
            longest = max(longest, run)
        # Bieżąca seria: dziś liczy się, gdy już zrobione; otwarte dziś jej nie przerywa.
        current = 0
        d = today - timedelta(days=1) if states[today] == PENDING else today
        while d >= start and states.get(d) == DONE:
            current += 1
            d -= timedelta(days=1)
        result.append(HabitStats(h, states, current, longest, _pct(states, today, 7), _pct(states, today, 30)))
    return result
