#!/usr/bin/env python3
"""Training analytics on Hevy workouts (data/hevy/), shared by the "Trening"
tab of scripts/build_dashboard.py and the Telegram bot's /trening command.

Usage (from repo root, using the project venv):

    .venv/bin/python scripts/training_analytics.py --telegram

prints the /trening message (at most 8 lines, no weights in kg).

Working sets = every set except warm-ups; only sets with reps count toward
e1RM and progression. e1RM (Epley) = weight x (1 + reps / 30), or the weight
itself for a single. Each exercise counts toward its primary muscle group.

Optional data/hevy_config.json (every key optional):

    {
      "rep_range": [8, 12],
      "exercise_rep_ranges": {"Face Pull": [12, 15]},
      "stagnation_sessions": 3,
      "weekly_sets": [10, 20],
      "muscle_weekly_sets": {"biceps": [6, 12]}
    }

exercise_rep_ranges keys are Hevy exercise titles (case-insensitive) or
template ids; muscle_weekly_sets keys are Hevy muscle groups (e.g. "chest")
or their Polish labels from MUSCLE_GROUP_PL (e.g. "Klatka").
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
HEVY_DIR = REPO_ROOT / "data" / "hevy"
CONFIG_PATH = REPO_ROOT / "data" / "hevy_config.json"
WEIGHT_PATH = REPO_ROOT / "data" / "weight.json"

DEFAULT_REP_RANGE = (8, 12)
DEFAULT_WEEKLY_SETS = (10, 20)
DEFAULT_STAGNATION_SESSIONS = 3

# Rekord "świeży", gdy padł w ciągu ostatnich 4 tygodni.
RECENT_RECORD_DAYS = 28
# Serie per partia: okno kroczące 7 dni (bez zer w poniedziałek, jak przy
# tygodniu kalendarzowym); partie trenowane w ostatnich 28 dniach.
SETS_WINDOW_DAYS = 7
ACTIVE_MUSCLE_DAYS = 28
# Status progresji tylko dla ćwiczeń robionych w ostatnich 6 tygodniach.
ACTIVE_EXERCISE_DAYS = 42
# Linia trendu e1RM dopiero od 3 sesji - przez 2 punkty to po prostu odcinek.
TREND_MIN_SESSIONS = 3
# Masa ciała: ostatni pomiar przed sesją, a gdy go brak - pierwszy po niej,
# o ile nie dalej niż 14 dni.
BODYWEIGHT_MAX_LOOKAHEAD_DAYS = 14

TELEGRAM_MAX_LINES = 8
TELEGRAM_MAX_NAMES = 4

MUSCLE_GROUP_PL = {
    "chest": "Klatka",
    "lats": "Najszersze",
    "upper_back": "Górne plecy",
    "lower_back": "Dolne plecy",
    "traps": "Kaptury",
    "shoulders": "Barki",
    "biceps": "Biceps",
    "triceps": "Triceps",
    "forearms": "Przedramiona",
    "quadriceps": "Czworogłowe",
    "hamstrings": "Dwugłowe ud",
    "glutes": "Pośladki",
    "calves": "Łydki",
    "abductors": "Odwodziciele",
    "adductors": "Przywodziciele",
    "abdominals": "Brzuch",
    "neck": "Szyja",
    "full_body": "Całe ciało",
    "cardio": "Cardio",
    "other": "Inne",
}


# --------------------------------------------------------------------------
# Data model and loading
# --------------------------------------------------------------------------

def epley(weight: float | None, reps: int | None) -> float | None:
    if not weight or weight <= 0 or not reps or reps < 1:
        return None
    return float(weight) if reps == 1 else weight * (1 + reps / 30)


@dataclass
class WorkingSet:
    weight: float | None
    reps: int | None

    @property
    def e1rm(self) -> float | None:
        return epley(self.weight, self.reps)


@dataclass
class ExerciseSession:
    """One exercise within one workout (entries of the same exercise in a
    workout are merged)."""
    exercise_id: str
    name: str
    muscle: str
    day: date
    workout_title: str
    sets: list[WorkingSet] = field(default_factory=list)

    @property
    def rep_sets(self) -> list[WorkingSet]:
        return [s for s in self.sets if s.reps]

    @property
    def top_weight(self) -> float | None:
        reps = self.rep_sets
        return max((s.weight or 0.0) for s in reps) if reps else None

    @property
    def top_sets(self) -> list[WorkingSet]:
        tw = self.top_weight
        return [s for s in self.rep_sets if (s.weight or 0.0) == tw] if tw is not None else []

    @property
    def best_e1rm_set(self) -> WorkingSet | None:
        cands = [s for s in self.sets if s.e1rm is not None]
        return max(cands, key=lambda s: s.e1rm) if cands else None

    @property
    def best_e1rm(self) -> float | None:
        s = self.best_e1rm_set
        return s.e1rm if s else None

    @property
    def best_set(self) -> WorkingSet | None:
        reps = self.rep_sets
        return max(reps, key=lambda s: (s.weight or 0.0, s.reps)) if reps else None

    @property
    def volume(self) -> float:
        return sum((s.weight or 0.0) * (s.reps or 0) for s in self.sets)

    @property
    def total_reps(self) -> int:
        return sum(s.reps or 0 for s in self.sets)


@dataclass
class Workout:
    id: str
    title: str
    start: datetime
    day: date
    exercises: list[ExerciseSession]

    @property
    def set_count(self) -> int:
        return sum(len(ex.sets) for ex in self.exercises)


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def load_workouts(hevy_dir: Path = HEVY_DIR) -> list[Workout]:
    """Workouts sorted by start, warm-ups dropped."""
    workouts_dir = hevy_dir / "workouts"
    if not workouts_dir.exists():
        return []
    try:
        templates = json.loads((hevy_dir / "exercise_templates.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        templates = {}
    if not isinstance(templates, dict):
        templates = {}

    workouts = []
    for path in workouts_dir.glob("*.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            start = datetime.fromisoformat(str(raw["start_time"]).replace("Z", "+00:00"))
        except (OSError, ValueError, KeyError, TypeError):
            continue
        day = start.astimezone().date()
        title = str(raw.get("title") or "").strip() or "Trening"
        by_id: dict[str, ExerciseSession] = {}
        for ex in raw.get("exercises") or []:
            ex_id = str(ex.get("exercise_template_id") or ex.get("title") or "?")
            tpl = templates.get(ex_id)
            muscle = (tpl.get("primary_muscle_group") if isinstance(tpl, dict) else None) or "other"
            sets = []
            for st in ex.get("sets") or []:
                if st.get("type") == "warmup":
                    continue
                reps = _number(st.get("reps"))
                sets.append(WorkingSet(
                    weight=_number(st.get("weight_kg")),
                    reps=int(reps) if reps and reps >= 1 else None,
                ))
            if not sets:
                continue
            if ex_id in by_id:
                by_id[ex_id].sets.extend(sets)
            else:
                by_id[ex_id] = ExerciseSession(ex_id, str(ex.get("title") or "?"), muscle, day, title, sets)
        workouts.append(Workout(str(raw.get("id") or path.stem), title, start, day, list(by_id.values())))
    workouts.sort(key=lambda w: w.start)
    return workouts


def load_bodyweights(path: Path = WEIGHT_PATH) -> list[tuple[date, float]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    result = []
    for e in data if isinstance(data, list) else []:
        try:
            kg = _number(e.get("kg"))
            if kg and kg > 0:
                result.append((date.fromisoformat(e["date"]), kg))
        except (AttributeError, KeyError, TypeError, ValueError):
            continue
    result.sort()
    return result


def bodyweight_on(day: date, weights: list[tuple[date, float]]) -> float | None:
    before = [kg for d, kg in weights if d <= day]
    if before:
        return before[-1]
    after = [kg for d, kg in weights if 0 < (d - day).days <= BODYWEIGHT_MAX_LOOKAHEAD_DAYS]
    return after[0] if after else None


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

@dataclass
class Config:
    rep_range: tuple[int, int] = DEFAULT_REP_RANGE
    exercise_rep_ranges: dict[str, tuple[int, int]] = field(default_factory=dict)
    stagnation_sessions: int = DEFAULT_STAGNATION_SESSIONS
    weekly_sets: tuple[int, int] = DEFAULT_WEEKLY_SETS
    muscle_weekly_sets: dict[str, tuple[int, int]] = field(default_factory=dict)

    def rep_range_for(self, exercise_id: str, name: str) -> tuple[int, int]:
        return (
            self.exercise_rep_ranges.get(exercise_id.casefold())
            or self.exercise_rep_ranges.get(name.strip().casefold())
            or self.rep_range
        )

    def weekly_sets_for(self, muscle: str) -> tuple[int, int]:
        return self.muscle_weekly_sets.get(muscle, self.weekly_sets)


def _warn(msg: str) -> None:
    print(f"hevy_config.json: {msg}", file=sys.stderr)


def _parse_range(value: Any, what: str) -> tuple[int, int] | None:
    if (
        isinstance(value, (list, tuple)) and len(value) == 2
        and all(_number(v) is not None for v in value)
        and 0 < value[0] <= value[1]
    ):
        return int(value[0]), int(value[1])
    _warn(f"pomijam {what}: oczekiwano [od, do], np. [8, 12]")
    return None


def load_config(path: Path = CONFIG_PATH) -> Config:
    cfg = Config()
    if not path.exists():
        return cfg
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        _warn(f"nie da się odczytać ({err}) - używam wartości domyślnych")
        return cfg
    if not isinstance(raw, dict):
        _warn("oczekiwano obiektu JSON - używam wartości domyślnych")
        return cfg

    if "rep_range" in raw:
        cfg.rep_range = _parse_range(raw["rep_range"], "rep_range") or cfg.rep_range
    if "weekly_sets" in raw:
        cfg.weekly_sets = _parse_range(raw["weekly_sets"], "weekly_sets") or cfg.weekly_sets
    stag = raw.get("stagnation_sessions")
    if stag is not None:
        if isinstance(stag, int) and not isinstance(stag, bool) and stag >= 2:
            cfg.stagnation_sessions = stag
        else:
            _warn("pomijam stagnation_sessions: oczekiwano liczby całkowitej >= 2")

    for key, value in (raw.get("exercise_rep_ranges") or {}).items():
        r = _parse_range(value, f"exercise_rep_ranges[{key}]")
        if r:
            cfg.exercise_rep_ranges[str(key).strip().casefold()] = r

    muscle_by_label = {v.casefold(): k for k, v in MUSCLE_GROUP_PL.items()}
    for key, value in (raw.get("muscle_weekly_sets") or {}).items():
        k = str(key).strip().casefold()
        muscle = k if k in MUSCLE_GROUP_PL else muscle_by_label.get(k)
        if not muscle:
            _warn(f"pomijam muscle_weekly_sets[{key}]: nieznana partia")
            continue
        r = _parse_range(value, f"muscle_weekly_sets[{key}]")
        if r:
            cfg.muscle_weekly_sets[muscle] = r
    return cfg


# --------------------------------------------------------------------------
# Analytics
# --------------------------------------------------------------------------

def exercise_history(workouts: list[Workout]) -> dict[str, list[ExerciseSession]]:
    """exercise_id -> sessions in chronological order."""
    history: dict[str, list[ExerciseSession]] = {}
    for w in workouts:
        for ex in w.exercises:
            history.setdefault(ex.exercise_id, []).append(ex)
    return history


def linear_trend(points: list[tuple[date, float]]) -> tuple[float, float] | None:
    """Least squares value = a + b * days since points[0]; returns (a, b per
    day), or None without at least two distinct days."""
    if len(points) < 2:
        return None
    d0 = points[0][0]
    xs = [(d - d0).days for d, _ in points]
    ys = [v for _, v in points]
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if not sxx:
        return None
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return my - b * mx, b


@dataclass
class Progression:
    exercise_id: str
    name: str
    rep_range: tuple[int, int]
    last: ExerciseSession
    status: str  # "raise" | "stall" | "reps"
    sessions_without_progress: int
    below_range: bool


STATUS_LABEL_PL = {
    "raise": "podnieś ciężar",
    "reps": "dobijaj powtórzenia",
}


def status_label(p: Progression) -> str:
    if p.status == "stall":
        return f"stagnacja od {p.sessions_without_progress} sesji"
    return STATUS_LABEL_PL[p.status]


def progression(
    sessions: list[ExerciseSession], rep_range: tuple[int, int], stagnation_sessions: int
) -> Progression | None:
    """Double progression. Progress in a session = heavier top weight than
    ever, more total reps at the best top weight so far, or a new e1RM high.
    Top-of-range in every set at the top weight -> raise the weight."""
    usable = [s for s in sessions if s.top_sets]
    if not usable:
        return None
    best_weight: float | None = None
    best_reps_at_best = 0
    best_e1rm: float | None = None
    since = 0
    for s in usable:
        tw = s.top_weight
        total = sum(st.reps for st in s.top_sets)
        e = s.best_e1rm
        improved = (
            best_weight is None
            or tw > best_weight
            or (tw == best_weight and total > best_reps_at_best)
            or (e is not None and (best_e1rm is None or e > best_e1rm))
        )
        if best_weight is None or tw > best_weight:
            best_weight, best_reps_at_best = tw, total
        elif tw == best_weight:
            best_reps_at_best = max(best_reps_at_best, total)
        if e is not None:
            best_e1rm = max(best_e1rm or e, e)
        since = 0 if improved else since + 1

    last = usable[-1]
    lo, hi = rep_range
    if all(st.reps >= hi for st in last.top_sets):
        status = "raise"
    elif since >= stagnation_sessions:
        status = "stall"
    else:
        status = "reps"
    return Progression(
        exercise_id=last.exercise_id,
        name=last.name,
        rep_range=rep_range,
        last=last,
        status=status,
        sessions_without_progress=since,
        below_range=min(st.reps for st in last.top_sets) < lo,
    )


def progressions(workouts: list[Workout], cfg: Config, today: date) -> list[Progression]:
    """Exercises done in the last ACTIVE_EXERCISE_DAYS: raise first, then
    stagnation, then the rest, most recent first within a group."""
    cutoff = today - timedelta(days=ACTIVE_EXERCISE_DAYS)
    result = []
    for ex_id, sessions in exercise_history(workouts).items():
        if sessions[-1].day < cutoff:
            continue
        p = progression(sessions, cfg.rep_range_for(ex_id, sessions[-1].name), cfg.stagnation_sessions)
        if p:
            result.append(p)
    order = {"raise": 0, "stall": 1, "reps": 2}
    result.sort(key=lambda p: (order[p.status], -p.last.day.toordinal(), p.name))
    return result


@dataclass
class Record:
    exercise_id: str
    name: str
    best_set: WorkingSet
    best_set_day: date
    best_e1rm_set: WorkingSet | None
    best_e1rm_day: date | None

    @property
    def latest_day(self) -> date:
        return max(d for d in (self.best_set_day, self.best_e1rm_day) if d)


def records(workouts: list[Workout]) -> list[Record]:
    """Best set (heaviest, then most reps) and best e1RM per exercise; a tie
    keeps the date it was first reached."""
    result = []
    for ex_id, sessions in exercise_history(workouts).items():
        best_set = best_set_day = best_e = best_e_day = None
        for s in sessions:
            bs = s.best_set
            if bs and (best_set is None or (bs.weight or 0.0, bs.reps) > (best_set.weight or 0.0, best_set.reps)):
                best_set, best_set_day = bs, s.day
            be = s.best_e1rm_set
            if be and (best_e is None or be.e1rm > best_e.e1rm):
                best_e, best_e_day = be, s.day
        if best_set:
            result.append(Record(ex_id, sessions[-1].name, best_set, best_set_day, best_e, best_e_day))
    result.sort(key=lambda r: (-r.latest_day.toordinal(), r.name))
    return result


@dataclass
class MuscleSets:
    muscle: str
    sets: int
    previous: int
    target: tuple[int, int]

    @property
    def label(self) -> str:
        return MUSCLE_GROUP_PL.get(self.muscle, self.muscle)

    @property
    def status(self) -> str:
        lo, hi = self.target
        return "low" if self.sets < lo else "high" if self.sets > hi else "ok"


def weekly_muscle_sets(workouts: list[Workout], cfg: Config, today: date) -> list[MuscleSets]:
    """Working sets per primary muscle group in the last 7 days (and the 7
    before), for groups trained in the last 28 days or configured explicitly."""
    start = today - timedelta(days=SETS_WINDOW_DAYS - 1)
    prev_start = start - timedelta(days=SETS_WINDOW_DAYS)
    active_from = today - timedelta(days=ACTIVE_MUSCLE_DAYS - 1)
    cur: dict[str, int] = {}
    prev: dict[str, int] = {}
    active: set[str] = set(cfg.muscle_weekly_sets)
    for w in workouts:
        for ex in w.exercises:
            n = len(ex.sets)
            if start <= w.day <= today:
                cur[ex.muscle] = cur.get(ex.muscle, 0) + n
            elif prev_start <= w.day < start:
                prev[ex.muscle] = prev.get(ex.muscle, 0) + n
            if active_from <= w.day <= today:
                active.add(ex.muscle)
    result = [MuscleSets(m, cur.get(m, 0), prev.get(m, 0), cfg.weekly_sets_for(m)) for m in active]
    result.sort(key=lambda m: (-m.sets, -m.previous, m.label))
    return result


@dataclass
class RelativeStrength:
    name: str
    e1rm: float
    bodyweight: float
    ratio: float
    best_ratio: float
    day: date


def relative_strength(
    workouts: list[Workout], weights: list[tuple[date, float]], today: date
) -> list[RelativeStrength]:
    """Latest and best e1RM / body weight for exercises done in the last
    ACTIVE_EXERCISE_DAYS, strongest ratio first."""
    cutoff = today - timedelta(days=ACTIVE_EXERCISE_DAYS)
    result = []
    for sessions in exercise_history(workouts).values():
        ratios = []
        for s in sessions:
            bw = bodyweight_on(s.day, weights)
            if s.best_e1rm is not None and bw:
                ratios.append((s, bw, s.best_e1rm / bw))
        if not ratios or ratios[-1][0].day < cutoff:
            continue
        s, bw, ratio = ratios[-1]
        result.append(RelativeStrength(s.name, s.best_e1rm, bw, ratio, max(r for _, _, r in ratios), s.day))
    result.sort(key=lambda r: -r.ratio)
    return result


@dataclass
class Comparison:
    title: str
    previous: Workout
    last: Workout
    rows: list[tuple[str, ExerciseSession | None, ExerciseSession | None]]


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title).strip().casefold()


def session_comparisons(workouts: list[Workout]) -> list[Comparison]:
    """Last two sessions of every workout title that occurs at least twice,
    most recent title first. Rows: exercises of the latest session in order,
    then those only in the previous one."""
    by_title: dict[str, list[Workout]] = {}
    for w in workouts:
        by_title.setdefault(normalize_title(w.title), []).append(w)
    result = []
    for sessions in by_title.values():
        if len(sessions) < 2:
            continue
        prev, last = sessions[-2], sessions[-1]
        prev_by_id = {ex.exercise_id: ex for ex in prev.exercises}
        rows = [(ex.name, prev_by_id.pop(ex.exercise_id, None), ex) for ex in last.exercises]
        rows += [(ex.name, ex, None) for ex in prev_by_id.values()]
        result.append(Comparison(last.title, prev, last, rows))
    result.sort(key=lambda c: c.last.start, reverse=True)
    return result


# --------------------------------------------------------------------------
# /trening message
# --------------------------------------------------------------------------

def plural_pl(n: int, one: str, few: str, many: str) -> str:
    if n == 1:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def fmt_day(d: date) -> str:
    return f"{d.day:02d}.{d.month:02d}"


def _days_ago(d: date, today: date) -> str:
    n = (today - d).days
    if n <= 0:
        return "dziś"
    if n == 1:
        return "wczoraj"
    return f"{n} dni temu"


def _names(items: list[str]) -> str:
    shown = items[:TELEGRAM_MAX_NAMES]
    rest = len(items) - len(shown)
    return ", ".join(shown) + (f" i {rest} {plural_pl(rest, 'inne', 'inne', 'innych')}" if rest else "")


def telegram_summary(
    workouts: list[Workout], cfg: Config, today: date | None = None
) -> str:
    """At most TELEGRAM_MAX_LINES lines; counts and names only, no weights."""
    today = today or date.today()
    if not workouts:
        return "Brak treningów w danych Hevy (data/hevy/)."

    last = workouts[-1]
    lines = [f"🏋️ Ostatnia sesja: {last.title} · {fmt_day(last.day)} ({_days_ago(last.day, today)})"]

    n_ex = len(last.exercises)
    n_sets = last.set_count
    detail = (
        f"{n_ex} {plural_pl(n_ex, 'ćwiczenie', 'ćwiczenia', 'ćwiczeń')} · "
        f"{n_sets} {plural_pl(n_sets, 'seria robocza', 'serie robocze', 'serii roboczych')}"
    )
    cmp = next((c for c in session_comparisons(workouts) if c.last is last), None)
    if cmp:
        diff = n_sets - cmp.previous.set_count
        up = down = 0
        for _, prev_ex, last_ex in cmp.rows:
            if prev_ex and last_ex and prev_ex.best_e1rm and last_ex.best_e1rm:
                up += last_ex.best_e1rm > prev_ex.best_e1rm
                down += last_ex.best_e1rm < prev_ex.best_e1rm
        detail += f" · vs {fmt_day(cmp.previous.day)}: serie {diff:+d}, e1RM ↑{up} ↓{down}"
    lines.append(detail)

    progs = progressions(workouts, cfg, today)
    raise_names = [p.name for p in progs if p.status == "raise"]
    if raise_names:
        lines.append(f"⬆️ Podnieś ciężar ({len(raise_names)}): {_names(raise_names)}")
    else:
        lines.append("⬆️ Podnieś ciężar: na razie nic - dobijaj powtórzenia")
    stalled = [f"{p.name} ({p.sessions_without_progress})" for p in progs if p.status == "stall"]
    if stalled:
        lines.append(f"⏸️ Stagnacja (sesje bez progresu): {_names(stalled)}")

    muscles = weekly_muscle_sets(workouts, cfg, today)
    low = [m for m in muscles if m.status == "low"]
    if low:
        low.sort(key=lambda m: (m.sets - m.target[0], m.label))
        lines.append(
            f"📉 Za mało serii (7 dni): {_names([f'{m.label} {m.sets}/{m.target[0]}' for m in low])}"
        )
    elif muscles:
        lines.append("✅ Serie we wszystkich partiach w zakresie (7 dni)")

    return "\n".join(lines[:TELEGRAM_MAX_LINES])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--telegram", action="store_true", help="wypisz wiadomość /trening")
    args = parser.parse_args()
    if not args.telegram:
        parser.print_help()
        return
    print(telegram_summary(load_workouts(), load_config()))


if __name__ == "__main__":
    main()
