#!/usr/bin/env python3
"""Builds a self-contained Health Dashboard.html from data/garmin/*.json.

Usage (from repo root, using the project venv):

    .venv/bin/python scripts/build_dashboard.py

Reads every daily JSON file written by scripts/garmin_sync.py, the Hevy
workouts written by scripts/hevy_sync.py (data/hevy/), plus data/food/*.json
and data/weight.json written by the Telegram bot's /dzien and /waga commands.
Generates a single standalone HTML file at "Health/Health Dashboard.html"
with inline SVG charts (no external libraries or fonts, no network
requests). Styles and the page script live next to this file
(dashboard.css, dashboard.js) and are inlined at build time. Light theme
by default, dark when the system prefers it (prefers-color-scheme). Days
with missing data are rendered as gaps, never errors.

Look: Apple Health / Fitness - system font, cards, large light numbers,
small gray labels, neutral colors with one muted accent. No good/bad
colors and no nutrition targets anywhere: data/targets.json (/cel) is kept
for the bot and scripts/trener_report.py, the dashboard only shows the
logged numbers.

Header: greeting, date and a "Jarvis" badge with the last sync time; a
subtle banner when the data is older than 24 h. Tabs as a segmented
control (CSS-only radio tabs; dashboard.js remembers the last one across
Obsidian's auto-reloads).

"Zdrowie": four tiles (Training Readiness, last night's sleep with a phase
bar, steps, resting heart rate - each with a 14-day sparkline), then the
readiness factors, weight trend and 14-day calorie/protein/carb/fat charts.

"Trening": Hevy data only (data/hevy/; plus data/weight.json for strength
relative to body weight), computed in scripts/training_analytics.py (also
used by the bot's /trening). Tiles (workouts per week, working sets and
volume in the last 7 days, recent records), the exercise list (rep range,
last working sets, double-progression status and an e1RM sparkline per
exercise), estimated 1RM (Epley) over time with a linear trend (exercise
picked from a list), working sets per muscle group vs. the target range,
volume per muscle group, e1RM / body weight, records and the last two
sessions of the same workout title side by side. Working sets = every set
except warm-ups; each exercise counts toward its primary muscle group only.

"Nawyki": habits from data/habits.json (scripts/habits.py) - today's state
as a list, then a 12-week grid (row per habit, cell per day) with the current
and longest streak and % done over the last 7 / 30 full days. Auto habits
(steps, sleep, Hevy session, food and weight logged) are computed only here;
manual ones come from the "Nawyki" checkboxes in daily/YYYY-MM-DD.md.
"""

from __future__ import annotations

import itertools
import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import habits as hb
import training_analytics as ta

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
DATA_DIR = REPO_ROOT / "data" / "garmin"
FOOD_DIR = REPO_ROOT / "data" / "food"
WEIGHT_PATH = REPO_ROOT / "data" / "weight.json"
TARGETS_PATH = REPO_ROOT / "data" / "targets.json"
STATUS_PATH = REPO_ROOT / "data" / "status.json"
HEVY_DIR = REPO_ROOT / "data" / "hevy"
HEVY_CONFIG_PATH = REPO_ROOT / "data" / "hevy_config.json"
HABITS_PATH = REPO_ROOT / "data" / "habits.json"
DAILY_DIR = REPO_ROOT / "daily"
CSS_PATH = SCRIPTS_DIR / "dashboard.css"
JS_PATH = SCRIPTS_DIR / "dashboard.js"
OUT_DIR = REPO_ROOT / "Health"
OUT_PATH = OUT_DIR / "Health Dashboard.html"

GREETING_NAME = "Antoni"
TREND_DAYS = 14
WEIGHT_POINTS = 30
STALE_AFTER = timedelta(hours=24)

MONTHS_PL_GEN = [
    "stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca",
    "lipca", "sierpnia", "września", "października", "listopada", "grudnia",
]
WEEKDAYS_PL = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]

SLEEP_QUALIFIER_PL = {
    "EXCELLENT": "doskonały",
    "GOOD": "dobry",
    "FAIR": "przeciętny",
    "POOR": "słaby",
}

TRAINING_WEEKS = 12
VOLUME_WINDOW_DAYS = 7
VOLUME_BASELINE_WINDOWS = 4
E1RM_MAX_POINTS = 24
EXERCISE_SPARK_POINTS = 12
REL_STRENGTH_ROWS = 8

MUSCLE_GROUP_PL = ta.MUSCLE_GROUP_PL

READINESS_LEVEL_PL = {
    "HIGH": "Wysoka",
    "MODERATE": "Umiarkowana",
    "LOW": "Niska",
    "VERY_LOW": "Bardzo niska",
    "PRIME": "Optymalna",
}

FACTOR_ORDER = ["sleep", "hrv", "sleep_history", "stress_history", "recovery_time", "acwr"]
FACTOR_LABELS_PL = {
    "sleep": "Sen",
    "hrv": "HRV",
    "sleep_history": "Historia snu",
    "stress_history": "Stres",
    "recovery_time": "Czas regeneracji",
    "acwr": "Obciążenie",
}

SLEEP_PHASES = [
    ("deep_seconds", "Głęboki", "ph-deep"),
    ("rem_seconds", "REM", "ph-rem"),
    ("light_seconds", "Lekki", "ph-light"),
    ("awake_seconds", "Wybudzenia", "ph-awake"),
]


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------

def load_records() -> list[dict[str, Any]]:
    if not DATA_DIR.exists():
        return []
    records = []
    for path in sorted(DATA_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        date_str = data.get("date") or path.stem
        try:
            parsed_date = date.fromisoformat(date_str)
        except ValueError:
            continue
        data["_date"] = parsed_date
        records.append(data)
    records.sort(key=lambda r: r["_date"])
    return records


def dig(obj: Any, *path: str, default: Any = None) -> Any:
    cur = obj
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return default if cur is None else cur


def _parse_dt(raw: Any) -> datetime | None:
    try:
        return datetime.strptime(raw or "", "%Y-%m-%dT%H:%M:%S")
    except (TypeError, ValueError):
        return None


def latest_sync_dt(records: list[dict[str, Any]]) -> datetime | None:
    return max((dt for r in records if (dt := _parse_dt(r.get("fetched_at")))), default=None)


def load_status_steps() -> dict[str, Any]:
    """The per-step results from data/status.json (written by scripts/status.py)."""
    try:
        data = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        return dig(data, "steps", default={}) or {}
    except (OSError, ValueError):
        return {}


def last_garmin_ok(records: list[dict[str, Any]], garmin: dict[str, Any]) -> datetime | None:
    candidates = [latest_sync_dt(records), _parse_dt(garmin.get("last_success"))]
    return max((c for c in candidates if c), default=None)


def load_food_records() -> dict[str, dict[str, Any]]:
    """Returns {date_str: {kcal, protein, carbs, fat, ...}} from data/food/*.json."""
    if not FOOD_DIR.exists():
        return {}
    result: dict[str, dict[str, Any]] = {}
    for path in FOOD_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        date_str = data.get("date") or path.stem
        if not isinstance(date_str, str):
            continue
        result[date_str] = data
    return result


def load_weight_entries() -> list[dict[str, Any]]:
    """Returns [{date, kg}, ...] sorted by date, from data/weight.json."""
    if not WEIGHT_PATH.exists():
        return []
    try:
        data = json.loads(WEIGHT_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    entries = [e for e in data if isinstance(e, dict) and e.get("date")]
    entries.sort(key=lambda e: e["date"])
    return entries


def load_targets() -> dict[str, Any] | None:
    """data/targets.json (/cel). Not shown in the dashboard; used by
    scripts/trener_report.py."""
    if not TARGETS_PATH.exists():
        return None
    try:
        data = json.loads(TARGETS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def last_n_calendar_days(n: int) -> list[date]:
    today = date.today()
    return [today - timedelta(days=i) for i in range(n - 1, -1, -1)]


# --------------------------------------------------------------------------
# Formatting helpers
# --------------------------------------------------------------------------

def esc(text: Any) -> str:
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def fmt_hms(seconds: Any) -> str:
    if seconds is None:
        return "brak danych"
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return "brak danych"
    h, rem = divmod(seconds, 3600)
    m = rem // 60
    return f"{h}h {m:02d}m"


def fmt_short_date(d: date) -> str:
    return f"{d.day:02d}.{d.month:02d}"


def fmt_dt_pl(dt: datetime) -> str:
    return f"{dt.day} {MONTHS_PL_GEN[dt.month - 1]} {dt.year}, {dt.strftime('%H:%M')}"


def fmt_long_date_pl(d: date) -> str:
    """'Sobota, 24 października'."""
    return f"{WEEKDAYS_PL[d.weekday()]}, {d.day} {MONTHS_PL_GEN[d.month - 1]}"


def fmt_when(dt: datetime) -> str:
    """'dziś 23:14' / 'wczoraj 21:00' / '22.10 21:00'."""
    days = (date.today() - dt.date()).days
    day = "dziś" if days == 0 else "wczoraj" if days == 1 else fmt_short_date(dt.date())
    return f"{day} {dt.strftime('%H:%M')}"


def fmt_local_time(ms: Any) -> str | None:
    """Garmin's 'Local' sleep timestamps are epoch-ms already shifted by the
    local UTC offset, so reading them back as UTC yields the correct
    wall-clock local time."""
    if not isinstance(ms, (int, float)):
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%H:%M")


def pl_word(value_pl_map: dict[str, str], raw: Any) -> str:
    if not raw:
        return "brak danych"
    return value_pl_map.get(raw, str(raw).replace("_", " ").title())


def _thousands(v: float) -> str:
    return f"{v:,.0f}".replace(",", " ")


def _fmt_kg(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".")


def _fmt_set(s: ta.WorkingSet | None) -> str:
    if s is None:
        return "—"
    return f"{_fmt_kg(s.weight)} kg × {s.reps}" if s.weight else f"× {s.reps}"


def _fmt_sets(sets: list[ta.WorkingSet]) -> str:
    """'60 kg × 12, 12, 11 · 50 kg × 15' - consecutive sets at one weight grouped."""
    groups: list[tuple[float | None, list[str]]] = []
    for s in sets:
        reps = str(s.reps) if s.reps else "—"
        if groups and groups[-1][0] == s.weight:
            groups[-1][1].append(reps)
        else:
            groups.append((s.weight, [reps]))
    return " · ".join(
        (f"{_fmt_kg(wt)} kg × " if wt else "× ") + ", ".join(reps) for wt, reps in groups
    )


def _fmt_delta(v: float, unit: str = " kg") -> str:
    if abs(v) < 0.05:
        return f"0{unit}"
    return f"{'+' if v > 0 else '−'}{_fmt_kg(abs(v))}{unit}"


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-") or "x"


def _sessions_word(n: int) -> str:
    return f"{n} {ta.plural_pl(n, 'sesja', 'sesje', 'sesji')}"


def _unit(text: str) -> str:
    return f'<span class="u">{esc(text)}</span>'


def _duration_html(seconds: float) -> str:
    h, m = divmod(int(seconds) // 60, 60)
    return f"{h}{_unit('h')} {m}{_unit('min')}"


def _tip(when: str, value: str) -> str:
    """data-tip value: the page script shows 'when' small and 'value' bold."""
    return esc(f"{when}|{value}")


# --------------------------------------------------------------------------
# SVG charts
#
# Every chart is an inline SVG with only a viewBox (it scales to the card's
# width). Each data point has a hover column (<g class="col" data-tip>) -
# CSS shows the point's dot, dashboard.js the tooltip. Colors come from CSS
# classes, so both themes share the markup.
# --------------------------------------------------------------------------

_UID = itertools.count(1)

SPARK_W, SPARK_H = 240, 64
SPARK_PAD = (4, 4, 8, 8)  # left, right, top, bottom
CHART_W, CHART_H = 320, 140
CHART_PAD = (2, 34, 10, 22)  # Y labels on the right, X labels below

EMPTY_CHART = '<p class="empty">Brak danych.</p>'


def _nice_step(span: float, n: int) -> float:
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def _ticks(lo: float, hi: float, n: int = 3) -> list[float]:
    """3-5 round values covering lo..hi (the chart's horizontal lines)."""
    if hi <= lo:
        lo, hi = lo - 1, hi + 1
    step = _nice_step(hi - lo, n)
    start = math.floor(lo / step + 1e-9) * step
    end = math.ceil(hi / step - 1e-9) * step
    count = int(round((end - start) / step))
    return [start + step * i for i in range(count + 1)]


def _label_indices(n: int) -> list[int]:
    return sorted({0, (n - 1) // 2, n - 1}) if n else []


def _axis_fmt(v: float) -> str:
    if abs(v) >= 10000:
        return f"{v / 1000:g}k"
    return f"{v:g}" if v != int(v) else f"{int(v)}"


def _svg_open(w: int, h: int, cls: str, label: str) -> str:
    return (
        f'<svg class="chart {cls}" viewBox="0 0 {w} {h}" width="100%" '
        f'preserveAspectRatio="xMidYMid meet" role="img" aria-label="{esc(label)}">'
    )


def _x_labels(labels: list[str], xs: list[float], y: float) -> str:
    out = []
    n = len(labels)
    for i in _label_indices(n):
        anchor = "start" if i == 0 else "end" if i == n - 1 else "middle"
        out.append(
            f'<text x="{xs[i]:.1f}" y="{y:.1f}" class="axis" text-anchor="{anchor}">{esc(labels[i])}</text>'
        )
    return "".join(out)


def _grid(ticks: list[float], y_of, x0: float, x1: float, label_x: float) -> str:
    out = []
    for t in ticks:
        y = y_of(t)
        out.append(f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" y2="{y:.1f}" class="grid" />')
        out.append(f'<text x="{label_x:.1f}" y="{y + 3.5:.1f}" class="axis">{_axis_fmt(t)}</text>')
    return "".join(out)


def _hover_cols(xs: list[float], ys: list[float | None], tips: list[str], top: float, bottom: float, guide: bool) -> str:
    out = []
    n = len(xs)
    for i, x in enumerate(xs):
        left = (xs[i - 1] + x) / 2 if i else x - (xs[1] - x) / 2 if n > 1 else x - 20
        right = (x + xs[i + 1]) / 2 if i < n - 1 else x + (x - xs[i - 1]) / 2 if n > 1 else x + 20
        inner = f'<rect x="{left:.1f}" y="{top:.1f}" width="{max(right - left, 1):.1f}" height="{bottom - top:.1f}" class="hit" />'
        if ys[i] is not None:
            if guide:
                inner += f'<line x1="{x:.1f}" y1="{top:.1f}" x2="{x:.1f}" y2="{bottom:.1f}" class="guide" />'
            inner += f'<circle cx="{x:.1f}" cy="{ys[i]:.1f}" r="3.5" class="dot" />'
        out.append(f'<g class="col" data-tip="{tips[i]}">{inner}</g>')
    return "".join(out)


def svg_line(
    values: list[float | None],
    tips: list[str],
    *,
    full: bool = False,
    labels: list[str] | None = None,
    x_fracs: list[float] | None = None,
    trend: list[float | None] | None = None,
    aria: str = "Wykres",
) -> str:
    """Line with a gradient fill fading to transparent. full=False: a
    sparkline (no axes); full=True: 3-5 light horizontal lines with values
    on the right and first/middle/last dates below. Gaps (None) split the
    line; x_fracs (0..1 per point) places points by date instead of evenly;
    trend is drawn dashed through the same x positions."""
    known = [v for v in values if v is not None]
    if not known:
        return EMPTY_CHART
    w, h = (CHART_W, CHART_H) if full else (SPARK_W, SPARK_H)
    pl, pr, pt, pb = CHART_PAD if full else SPARK_PAD
    scale_vals = known + [v for v in (trend or []) if v is not None]
    lo, hi = min(scale_vals), max(scale_vals)
    if full:
        ticks = _ticks(lo, hi)
        lo, hi = ticks[0], ticks[-1]
    else:
        pad = (hi - lo) * 0.15 or 1.0
        lo, hi = lo - pad, hi + pad
    n = len(values)
    iw, ih = w - pl - pr, h - pt - pb
    bottom = pt + ih

    def x_of(i: int) -> float:
        if x_fracs is not None:
            return pl + iw * x_fracs[i]
        return pl + (iw * i / (n - 1) if n > 1 else iw / 2)

    def y_of(v: float) -> float:
        return pt + ih * (1 - (v - lo) / (hi - lo))

    xs = [x_of(i) for i in range(n)]
    ys = [y_of(v) if v is not None else None for v in values]
    gid = f"grad{next(_UID)}"
    parts = [
        _svg_open(w, h, "chart-full" if full else "spark", aria),
        f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" class="grad-top" /><stop offset="1" class="grad-bottom" /></linearGradient></defs>',
    ]
    if full:
        parts.append(_grid(ticks, y_of, pl, w - pr, w - pr + 6))

    segments: list[list[tuple[float, float]]] = [[]]
    for x, y in zip(xs, ys):
        if y is None:
            segments.append([])
        else:
            segments[-1].append((x, y))
    for seg in segments:
        if len(seg) == 1:
            parts.append(f'<circle cx="{seg[0][0]:.1f}" cy="{seg[0][1]:.1f}" r="2.5" class="solo" />')
        elif seg:
            line = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in seg)
            parts.append(
                f'<path d="{line} L{seg[-1][0]:.1f},{bottom:.1f} L{seg[0][0]:.1f},{bottom:.1f} Z" '
                f'fill="url(#{gid})" class="area" />'
            )
            parts.append(f'<path d="{line}" pathLength="1" class="line" />')

    if trend:
        pts = [f"{x:.1f},{y_of(v):.1f}" for x, v in zip(xs, trend) if v is not None]
        if len(pts) > 1:
            parts.append(f'<path d="M{" L".join(pts)}" class="trend" />')

    last = next(((x, y) for x, y in zip(reversed(xs), reversed(ys)) if y is not None), None)
    if last:
        parts.append(f'<circle cx="{last[0]:.1f}" cy="{last[1]:.1f}" r="3" class="end" />')
    if full and labels:
        parts.append(_x_labels(labels, xs, h - 6))
    parts.append(_hover_cols(xs, ys, tips, pt, bottom, guide=full))
    parts.append("</svg>")
    return "".join(parts)


def svg_bars(values: list[float | None], tips: list[str], labels: list[str], *, aria: str = "Wykres") -> str:
    """Rounded-top bars from zero, same axes as a full svg_line."""
    known = [v for v in values if v is not None]
    if not known:
        return EMPTY_CHART
    w, h = CHART_W, CHART_H
    pl, pr, pt, pb = CHART_PAD
    ticks = _ticks(0, max(known) or 1)
    hi = ticks[-1]
    n = len(values)
    iw, ih = w - pl - pr, h - pt - pb
    bottom = pt + ih
    slot = iw / n
    bw = slot * 0.56

    def y_of(v: float) -> float:
        return pt + ih * (1 - v / hi)

    xs = [pl + slot * (i + 0.5) for i in range(n)]
    parts = [_svg_open(w, h, "chart-full bars", aria), _grid(ticks, y_of, pl, w - pr, w - pr + 6)]
    cols = []
    for i, (x, v) in enumerate(zip(xs, values)):
        hit = f'<rect x="{x - slot / 2:.1f}" y="{pt:.1f}" width="{slot:.1f}" height="{ih:.1f}" class="hit" />'
        bar = ""
        if v is not None and v > 0:
            top = y_of(v)
            r = min(3.0, bw / 2, bottom - top)
            x0, x1 = x - bw / 2, x + bw / 2
            bar = (
                f'<path d="M{x0:.1f},{bottom:.1f} L{x0:.1f},{top + r:.1f} Q{x0:.1f},{top:.1f} {x0 + r:.1f},{top:.1f} '
                f'L{x1 - r:.1f},{top:.1f} Q{x1:.1f},{top:.1f} {x1:.1f},{top + r:.1f} L{x1:.1f},{bottom:.1f} Z" class="bar" />'
            )
        cols.append(f'<g class="col" data-tip="{tips[i]}">{hit}{bar}</g>')
    parts.append(f'<g class="bar-group">{"".join(cols)}</g>')
    parts.append(_x_labels(labels, xs, h - 6))
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------
# Cards
# --------------------------------------------------------------------------

def _card(label: str, body_html: str, extra_class: str = "") -> str:
    cls = f"card {extra_class}".strip()
    return f'<section class="{cls}"><h3 class="label">{esc(label)}</h3>{body_html}</section>'


def _tile(label: str, value_html: str, sub_html: str = "", viz_html: str = "", extra_class: str = "") -> str:
    """One main number + caption + optional mini chart."""
    sub = f'<p class="sub">{sub_html}</p>' if sub_html else ""
    viz = f'<div class="viz">{viz_html}</div>' if viz_html else ""
    return _card(label, f'<div class="value">{value_html}</div>{sub}{viz}', f"tile {extra_class}".strip())


def _empty_card(label: str, message: str, extra_class: str = "") -> str:
    return _card(label, f'<p class="empty">{esc(message)}</p>', extra_class)


def _value_text(v: float | None, fmt=_thousands, unit: str = "") -> str:
    if v is None:
        return '<span class="none">—</span>'
    return fmt(v) + (_unit(unit) if unit else "")


def _section(title: str) -> str:
    return f'<h2 class="section-title">{esc(title)}</h2>'


def _grid_html(cards: str, cls: str) -> str:
    return f'<div class="grid {cls}">{cards}</div>'


# --------------------------------------------------------------------------
# Zdrowie
# --------------------------------------------------------------------------

def _daily_series(records: list[dict[str, Any]], getter) -> tuple[list[date], list[float | None]]:
    by_date = {r["_date"]: getter(r) for r in records}
    days = last_n_calendar_days(TREND_DAYS)
    return days, [v if isinstance(v, (int, float)) else None for v in (by_date.get(d) for d in days)]


def _day_label(d: date) -> str:
    return "dziś" if d == date.today() else fmt_short_date(d)


def build_readiness_tile(records: list[dict[str, Any]]) -> str:
    with_tr = [r for r in records if dig(r, "training_readiness", "score") is not None]
    if not with_tr:
        return _tile("Gotowość", _value_text(None), "brak danych")
    latest = with_tr[-1]
    tr = latest.get("training_readiness") or {}
    days, values = _daily_series(records, lambda r: dig(r, "training_readiness", "score"))
    tips = [_tip(_day_label(d), f"{v:.0f}" if v is not None else "brak danych") for d, v in zip(days, values)]
    sub = f"{esc(pl_word(READINESS_LEVEL_PL, tr.get('level')))} · {_day_label(latest['_date'])}"
    return _tile(
        "Gotowość", _value_text(tr.get("score"), lambda v: f"{v:.0f}"), sub,
        svg_line(values, tips, aria="Gotowość, 14 dni"),
    )


def svg_phase_bar(sleep: dict[str, Any]) -> str:
    phases = [(label, sleep.get(key), cls) for key, label, cls in SLEEP_PHASES]
    phases = [(label, v, cls) for label, v, cls in phases if isinstance(v, (int, float)) and v > 0]
    total = sum(v for _, v, _ in phases)
    if not total:
        return '<p class="empty">Brak danych o fazach.</p>'
    segs = "".join(
        f'<span class="ph {cls}" style="flex-grow:{v:.0f}" data-tip="{_tip(label, f"{fmt_hms(v)} · {v / total * 100:.0f}%")}"></span>'
        for label, v, cls in phases
    )
    legend = "".join(
        f'<li><i class="ph {cls}"></i>{esc(label)}<b>{fmt_hms(v)}</b></li>' for label, v, cls in phases
    )
    return f'<div class="phases" role="img" aria-label="Fazy snu">{segs}</div><ul class="phase-legend">{legend}</ul>'


def build_sleep_tile(records: list[dict[str, Any]]) -> str:
    with_sleep = [r for r in records if dig(r, "sleep", "total_seconds") is not None]
    if not with_sleep:
        return _tile("Sen", _value_text(None), "brak danych")
    r = with_sleep[-1]
    sleep = r.get("sleep") or {}
    start_txt = fmt_local_time(sleep.get("start_local_ms"))
    end_txt = fmt_local_time(sleep.get("end_local_ms"))
    sub = [f"{start_txt}–{end_txt}" if start_txt and end_txt else _day_label(r["_date"])]
    if sleep.get("score") is not None:
        qualifier = SLEEP_QUALIFIER_PL.get(sleep.get("score_qualifier"), "")
        sub.append(f"ocena {int(sleep['score'])}" + (f", {qualifier}" if qualifier else ""))
    return _tile(
        "Sen", _duration_html(sleep["total_seconds"]), esc(" · ".join(sub)), svg_phase_bar(sleep), "tile-sleep"
    )


def build_steps_tile(records: list[dict[str, Any]]) -> str:
    days, values = _daily_series(records, lambda r: r.get("steps"))
    # Today is still in progress, so the headline is yesterday's full day.
    yesterday = values[-2] if len(values) > 1 else None
    known = [v for v in values[:-1] if v is not None]
    avg = sum(known) / len(known) if known else None
    sub = "wczoraj" + (f" · średnio {_thousands(avg)}" if avg is not None else "")
    tips = [
        _tip(_day_label(d) + (" (w toku)" if d == date.today() else ""),
             f"{_thousands(v)} kroków" if v is not None else "brak danych")
        for d, v in zip(days, values)
    ]
    return _tile("Kroki", _value_text(yesterday), sub, svg_line(values, tips, aria="Kroki, 14 dni"))


def build_rhr_tile(records: list[dict[str, Any]]) -> str:
    days, values = _daily_series(records, lambda r: r.get("resting_heart_rate"))
    latest_i = next((i for i in range(len(values) - 1, -1, -1) if values[i] is not None), None)
    latest = values[latest_i] if latest_i is not None else None
    sub = _day_label(days[latest_i]) if latest_i is not None else "brak danych"
    tips = [_tip(_day_label(d), f"{v:.0f} bpm" if v is not None else "brak danych") for d, v in zip(days, values)]
    return _tile(
        "Tętno spoczynkowe", _value_text(latest, lambda v: f"{v:.0f}", "bpm"), sub,
        svg_line(values, tips, aria="Tętno spoczynkowe, 14 dni"),
    )


def build_factors_card(records: list[dict[str, Any]]) -> str:
    label = "Gotowość · składowe"
    with_tr = [r for r in records if dig(r, "training_readiness", "factors")]
    if not with_tr:
        return _empty_card(label, "Brak danych.")
    factors = dig(with_tr[-1], "training_readiness", "factors", default={})
    present = [(k, factors.get(k)) for k in FACTOR_ORDER if isinstance(factors.get(k), (int, float))]
    if not present:
        return _empty_card(label, "Brak danych.")
    rows = "".join(
        f'<div class="meter-row"><span class="meter-label">{esc(FACTOR_LABELS_PL[k])}</span>'
        f'<span class="meter"><span class="meter-fill" style="width:{max(0, min(100, v)):.0f}%"></span></span>'
        f'<span class="meter-value">{v:.0f}</span></div>'
        for k, v in present
    )
    return _card(f"{label} · {_day_label(with_tr[-1]['_date'])}", f'<div class="meters">{rows}</div>')


def build_weight_card(weight_entries: list[dict[str, Any]]) -> str:
    entries = []
    for e in weight_entries:
        try:
            entries.append((date.fromisoformat(e["date"]), e.get("kg")))
        except (TypeError, ValueError, KeyError):
            continue
    entries = [(d, kg) for d, kg in entries if isinstance(kg, (int, float))]
    if not entries:
        return _empty_card("Waga", "Brak pomiarów. /waga w bocie.")
    last_d, last_kg = entries[-1]
    prior = [kg for d, kg in entries if d <= last_d - timedelta(days=7)]
    sub = f"{_fmt_delta(last_kg - prior[-1])} / 7 dni" if prior else _day_label(last_d)
    trend = entries[-WEIGHT_POINTS:]
    chart = svg_line(
        [kg for _, kg in trend],
        [_tip(_day_label(d), f"{kg:.1f} kg") for d, kg in trend],
        full=True, labels=[fmt_short_date(d) for d, _ in trend], aria="Waga",
    )
    return _tile("Waga", _value_text(last_kg, lambda v: f"{v:.1f}", "kg"), esc(sub), chart)


NUTRITION_CARDS = [
    ("Kalorie", "kcal", "kcal"),
    ("Białko", "protein", "g"),
    ("Węglowodany", "carbs", "g"),
    ("Tłuszcze", "fat", "g"),
]


def build_nutrition_cards(food_by_date: dict[str, dict[str, Any]]) -> str:
    """14-day bars per macro, average of the logged days as the headline -
    plain numbers, no targets or ratings."""
    days = last_n_calendar_days(TREND_DAYS)
    labels = [fmt_short_date(d) for d in days]
    cards = []
    for label, key, unit in NUTRITION_CARDS:
        values = [
            v if isinstance(v := (food_by_date.get(d.isoformat()) or {}).get(key), (int, float)) else None
            for d in days
        ]
        known = [v for v in values if v is not None]
        if not known:
            cards.append(_empty_card(label, "Brak wpisów. /dzien w bocie."))
            continue
        tips = [_tip(_day_label(d), f"{v:.0f} {unit}" if v is not None else "brak wpisu") for d, v in zip(days, values)]
        avg = sum(known) / len(known)
        days_word = ta.plural_pl(len(known), "dzień", "dni", "dni")
        cards.append(_tile(
            label, _value_text(avg, unit=unit), f"średnio · {len(known)} {days_word} z wpisem",
            svg_bars(values, tips, labels, aria=f"{label}, 14 dni"),
        ))
    return "".join(cards)


def build_health_panel(
    records: list[dict[str, Any]],
    food_by_date: dict[str, dict[str, Any]],
    weight_entries: list[dict[str, Any]],
) -> str:
    if records:
        hero = (
            build_readiness_tile(records) + build_sleep_tile(records)
            + build_steps_tile(records) + build_rhr_tile(records)
        )
    else:
        hero = _empty_card("Garmin", "Brak danych. Uruchom scripts/garmin_sync.py.", "span-all")
    more = build_factors_card(records) + build_weight_card(weight_entries)
    return (
        _grid_html(hero, "grid-hero")
        + _grid_html(more, "grid-two")
        + _section("Odżywianie")
        + _grid_html(build_nutrition_cards(food_by_date), "grid-two")
    )


# --------------------------------------------------------------------------
# Trening
# --------------------------------------------------------------------------

def _training_weeks() -> list[date]:
    this_week = _week_start(date.today())
    return [this_week - timedelta(weeks=i) for i in range(TRAINING_WEEKS - 1, -1, -1)]


def build_workouts_tile(workouts: list[ta.Workout]) -> str:
    weeks = _training_weeks()
    counts = {wk: 0 for wk in weeks}
    for w in workouts:
        if (wk := _week_start(w.day)) in counts:
            counts[wk] += 1
    values = [float(counts[wk]) for wk in weeks]
    prev = values[-1 - VOLUME_BASELINE_WINDOWS:-1]
    avg = sum(prev) / len(prev) if prev else 0.0
    tips = [_tip(f"tydz. od {fmt_short_date(wk)}", f"{v:.0f}") for wk, v in zip(weeks, values)]
    return _tile(
        "Treningi", f"{values[-1]:.0f}", f"ten tydzień · średnio {avg:.1f}",
        svg_line(values, tips, aria=f"Treningi, {TRAINING_WEEKS} tygodni"),
    )


def _muscle_volume(workouts: list[ta.Workout], start: date, end: date) -> dict[str, float]:
    """Volume (kg) per primary muscle group for start <= day <= end."""
    volume: dict[str, float] = {}
    for w in workouts:
        if start <= w.day <= end:
            for ex in w.exercises:
                volume[ex.muscle] = volume.get(ex.muscle, 0.0) + ex.volume
    return volume


def build_sets_tile(workouts: list[ta.Workout], cfg: ta.Config) -> str:
    groups = ta.weekly_muscle_sets(workouts, cfg, date.today())
    cur = sum(g.sets for g in groups)
    prev = sum(g.previous for g in groups)
    return _tile("Serie robocze", f"{cur}", f"7 dni · poprzednio {prev}")


def build_volume_tile(workouts: list[ta.Workout]) -> str:
    today = date.today()
    cur = sum(_muscle_volume(workouts, today - timedelta(days=VOLUME_WINDOW_DAYS - 1), today).values())
    weeks = _training_weeks()
    values = [sum(_muscle_volume(workouts, wk, wk + timedelta(days=6)).values()) for wk in weeks]
    tips = [_tip(f"tydz. od {fmt_short_date(wk)}", f"{_thousands(v)} kg") for wk, v in zip(weeks, values)]
    return _tile(
        "Objętość", _value_text(cur, unit="kg"), "7 dni",
        svg_line(values, tips, aria=f"Objętość, {TRAINING_WEEKS} tygodni"),
    )


def build_records_tile(workouts: list[ta.Workout]) -> str:
    recs = ta.records(workouts)
    cutoff = date.today() - timedelta(days=ta.RECENT_RECORD_DAYS - 1)
    recent = sum(1 for r in recs if r.latest_day >= cutoff)
    return _tile(
        "Rekordy", f"{recent}",
        f"{ta.plural_pl(recent, 'ćwiczenie', 'ćwiczenia', 'ćwiczeń')} · 4 tygodnie",
    )


def _e1rm_series(workouts: list[ta.Workout]) -> dict[str, list[ta.ExerciseSession]]:
    series = {
        ex_id: [s for s in sessions if s.best_e1rm is not None]
        for ex_id, sessions in ta.exercise_history(workouts).items()
    }
    return {k: v for k, v in series.items() if v}


def build_exercise_list(workouts: list[ta.Workout], cfg: ta.Config) -> str:
    """Every exercise from the last 6 weeks: rep range, last working sets,
    progression status and an e1RM sparkline."""
    label = "Ćwiczenia"
    progs = ta.progressions(workouts, cfg, date.today())
    if not progs:
        return _empty_card(label, "Brak serii z ostatnich 6 tygodni.", "span-all")
    series = _e1rm_series(workouts)
    items = []
    for p in progs:
        pts = series.get(p.exercise_id, [])[-EXERCISE_SPARK_POINTS:]
        spark = svg_line(
            [s.best_e1rm for s in pts],
            [_tip(fmt_short_date(s.day), f"e1RM {_fmt_kg(s.best_e1rm)} kg") for s in pts],
            aria=f"e1RM: {p.name}",
        ) if len(pts) > 1 else ""
        status = ta.status_label(p)
        if p.status == "reps" and p.below_range:
            status += " · poniżej widełek"
        lo, hi = p.rep_range
        e1rm = (
            f'{_fmt_kg(pts[-1].best_e1rm)}{_unit("kg")}' if pts else '<span class="none">—</span>'
        )
        items.append(
            f'<li class="ex">'
            f'<div class="ex-main"><span class="ex-name">{esc(p.name)}</span>'
            f'<span class="ex-sub">{lo}–{hi} powt. · {fmt_short_date(p.last.day)} · {esc(_fmt_sets(p.last.sets))}</span></div>'
            f'<div class="ex-spark">{spark}</div>'
            f'<div class="ex-side"><span class="ex-val">{e1rm}</span>'
            f'<span class="pill pill-{p.status}">{esc(status)}</span></div>'
            f"</li>"
        )
    n_raise = sum(p.status == "raise" for p in progs)
    n_stall = sum(p.status == "stall" for p in progs)
    head = (
        f'<p class="sub">{len(progs)} {ta.plural_pl(len(progs), "ćwiczenie", "ćwiczenia", "ćwiczeń")} · 6 tygodni · '
        f"do podniesienia {n_raise} · stagnacja {n_stall} · e1RM z najlepszej serii</p>"
    )
    return _card(label, head + f'<ul class="ex-list">{"".join(items)}</ul>', "span-all")


def _picker(group: str, options: list[tuple[str, str]], aria_label: str) -> str:
    """<select> showing one of the panels with data-panel=group
    (dashboard.js); without scripts every panel stays visible."""
    opts = "".join(f'<option value="{pid}">{esc(label)}</option>' for pid, label in options)
    return f'<select class="picker" data-group="{group}" aria-label="{esc(aria_label)}">{opts}</select>'


def build_e1rm_card(workouts: list[ta.Workout]) -> str:
    label = "Szacowany 1RM"
    series = _e1rm_series(workouts)
    if not series:
        return _empty_card(label, "Brak serii z ciężarem.", "span-all")
    order = sorted(series, key=lambda k: (-len(series[k]), -series[k][-1].day.toordinal(), series[k][-1].name))
    options = []
    panels = []
    for ex_id in order:
        all_pts = series[ex_id]
        pts = all_pts[-E1RM_MAX_POINTS:]
        last = pts[-1]
        pid = f"e1rm-{_slug(ex_id)}"
        options.append((pid, f"{last.name} · {_sessions_word(len(all_pts))}"))
        d0 = pts[0].day
        span = (last.day - d0).days
        x_fracs = [(s.day - d0).days / span if span else 0.5 for s in pts]
        trend = None
        sub = [f"{fmt_short_date(last.day)} · {_fmt_set(last.best_e1rm_set)}"]
        best = max(all_pts, key=lambda s: s.best_e1rm)
        sub.append(f"najlepiej {_fmt_kg(best.best_e1rm)} kg")
        if len(pts) >= ta.TREND_MIN_SESSIONS and (fit := ta.linear_trend([(s.day, s.best_e1rm) for s in pts])):
            a, b = fit
            trend = [a + b * (s.day - d0).days for s in pts]
            sub.append(f"trend {_fmt_delta(b * 28)} / 4 tyg.")
        chart = svg_line(
            [s.best_e1rm for s in pts],
            [_tip(fmt_short_date(s.day), f"{_fmt_kg(s.best_e1rm)} kg · {_fmt_set(s.best_e1rm_set)}") for s in pts],
            full=True, labels=[fmt_short_date(s.day) for s in pts], x_fracs=x_fracs, trend=trend,
            aria=f"e1RM: {last.name}",
        )
        panels.append(
            f'<div class="picker-panel" data-panel="e1rm" id="{pid}">'
            f'<div class="value">{_fmt_kg(last.best_e1rm)}{_unit("kg")}</div>'
            f'<p class="sub">{esc(" · ".join(sub))}</p><div class="viz">{chart}</div></div>'
        )
    body = f'<div class="card-head">{_picker("e1rm", options, "Ćwiczenie")}</div>' + "".join(panels)
    return _card(label, body, "span-all card-picker")


def _bar_rows(rows: list[str]) -> str:
    return f'<div class="meters">{"".join(rows)}</div>'


def build_weekly_sets_card(workouts: list[ta.Workout], cfg: ta.Config) -> str:
    label = "Serie per partia · 7 dni"
    groups = ta.weekly_muscle_sets(workouts, cfg, date.today())
    if not groups:
        return _empty_card(label, "Brak serii w ostatnich 4 tygodniach.")
    top = max(max(g.target[1], g.sets, g.previous) for g in groups) * 1.05
    rows = []
    for g in groups:
        lo, hi = g.target
        prev = f'<span class="meter-tick" style="left:{g.previous / top * 100:.1f}%"></span>' if g.previous else ""
        rows.append(
            f'<div class="meter-row" data-tip="{_tip(g.label, f"{g.sets} serii · zakres {lo}–{hi} · poprzednio {g.previous}")}">'
            f'<span class="meter-label">{esc(g.label)}</span>'
            f'<span class="meter">'
            f'<span class="meter-band" style="left:{lo / top * 100:.1f}%;width:{(hi - lo) / top * 100:.1f}%"></span>'
            f'<span class="meter-fill" style="width:{g.sets / top * 100:.1f}%"></span>{prev}</span>'
            f'<span class="meter-value">{g.sets}<span class="dim">/{lo}–{hi}</span></span></div>'
        )
    legend = (
        '<ul class="legend"><li><i class="lg-fill"></i>7 dni</li><li><i class="lg-band"></i>zakres</li>'
        '<li><i class="lg-tick"></i>poprzednie 7 dni</li></ul>'
    )
    return _card(label, _bar_rows(rows) + legend)


def build_volume_card(workouts: list[ta.Workout]) -> str:
    label = "Objętość per partia · 7 dni"
    today = date.today()
    cur_start = today - timedelta(days=VOLUME_WINDOW_DAYS - 1)
    cur = _muscle_volume(workouts, cur_start, today)
    base: dict[str, float] = {}
    for i in range(VOLUME_BASELINE_WINDOWS):
        end = cur_start - timedelta(days=VOLUME_WINDOW_DAYS * i + 1)
        for m, v in _muscle_volume(workouts, end - timedelta(days=VOLUME_WINDOW_DAYS - 1), end).items():
            base[m] = base.get(m, 0) + v / VOLUME_BASELINE_WINDOWS
    groups = sorted(
        {m for m, v in cur.items() if v} | {m for m, v in base.items() if v},
        key=lambda m: (-cur.get(m, 0), -base.get(m, 0)),
    )[:10]
    if not groups:
        return _empty_card(label, "Brak serii w tym okresie.")
    top = max(max(cur.get(m, 0), base.get(m, 0)) for m in groups) or 1
    rows = []
    for m in groups:
        c, b = cur.get(m, 0), base.get(m, 0)
        name = MUSCLE_GROUP_PL.get(m, m)
        tick = f'<span class="meter-tick" style="left:{b / top * 100:.1f}%"></span>' if b else ""
        rows.append(
            f'<div class="meter-row" data-tip="{_tip(name, f"{_thousands(c)} kg · średnio {_thousands(b)} kg")}">'
            f'<span class="meter-label">{esc(name)}</span>'
            f'<span class="meter"><span class="meter-fill" style="width:{c / top * 100:.1f}%"></span>{tick}</span>'
            f'<span class="meter-value">{_thousands(c)}</span></div>'
        )
    legend = '<ul class="legend"><li><i class="lg-fill"></i>kg, 7 dni</li><li><i class="lg-tick"></i>średnia 4 poprzednich</li></ul>'
    return _card(label, _bar_rows(rows) + legend)


def _table(head: list[str], rows: list[str], num_cols: set[int] = frozenset(), foot: str = "") -> str:
    ths = "".join(f'<th{" class=\"num\"" if i in num_cols else ""}>{h}</th>' for i, h in enumerate(head))
    return (
        f'<div class="table-wrap"><table class="table"><thead><tr>{ths}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>{foot}</table></div>'
    )


def build_relative_strength_card(workouts: list[ta.Workout], bodyweights: list[tuple[date, float]]) -> str:
    label = "Siła względna"
    if not bodyweights:
        return _empty_card(label, "Brak pomiarów. /waga w bocie.")
    rows = ta.relative_strength(workouts, bodyweights, date.today())
    if not rows:
        return _empty_card(label, "Brak serii z ciężarem w ostatnich 6 tygodniach.")
    body = [
        f'<tr data-tip="{_tip(r.name, f"e1RM {_fmt_kg(r.e1rm)} kg / {_fmt_kg(r.bodyweight)} kg · {fmt_short_date(r.day)}")}">'
        f"<td>{esc(r.name)}</td><td class=\"num\">{r.ratio:.2f}×</td><td class=\"num dim\">{r.best_ratio:.2f}×</td></tr>"
        for r in rows[:REL_STRENGTH_ROWS]
    ]
    return _card(label, _table(["Ćwiczenie", "e1RM / masa", "Najlepiej"], body, {1, 2}))


def build_records_card(workouts: list[ta.Workout]) -> str:
    label = "Rekordy"
    recs = ta.records(workouts)
    if not recs:
        return _empty_card(label, "Brak serii z powtórzeniami.", "span-all")
    cutoff = date.today() - timedelta(days=ta.RECENT_RECORD_DAYS - 1)

    def day_cell(d: date | None) -> str:
        if d is None:
            return "—"
        return fmt_short_date(d) + (' <span class="badge">nowy</span>' if d >= cutoff else "")

    rows = [
        f"<tr><td>{esc(r.name)}</td>"
        f'<td class="nowrap">{_fmt_set(r.best_set)}</td><td class="nowrap dim">{day_cell(r.best_set_day)}</td>'
        f'<td class="nowrap">{(_fmt_kg(r.best_e1rm_set.e1rm) + " kg") if r.best_e1rm_set else "—"}</td>'
        f'<td class="nowrap dim">{day_cell(r.best_e1rm_day)}</td></tr>'
        for r in recs
    ]
    return _card(label, _table(["Ćwiczenie", "Najlepsza seria", "", "Najlepszy e1RM", ""], rows), "span-all")


def build_session_compare_card(workouts: list[ta.Workout]) -> str:
    label = "Porównanie sesji"
    comps = ta.session_comparisons(workouts)
    if not comps:
        return _empty_card(label, "Potrzebne dwie sesje o tym samym tytule.", "span-all")
    options = []
    panels = []
    for c in comps:
        pid = f"cmp-{_slug(ta.normalize_title(c.title))}"
        prev_d, last_d = fmt_short_date(c.previous.day), fmt_short_date(c.last.day)
        options.append((pid, f"{c.title} · {prev_d} vs {last_d}"))
        rows = []
        for name, prev_ex, last_ex in c.rows:
            delta_e = "—"
            if prev_ex and last_ex and prev_ex.best_e1rm and last_ex.best_e1rm:
                delta_e = _fmt_delta(last_ex.best_e1rm - prev_ex.best_e1rm)
            delta_v = _fmt_delta((last_ex.volume if last_ex else 0) - (prev_ex.volume if prev_ex else 0))
            rows.append(
                f"<tr><td>{esc(name)}</td>"
                f'<td class="dim">{esc(_fmt_sets(prev_ex.sets)) if prev_ex else "—"}</td>'
                f"<td>{esc(_fmt_sets(last_ex.sets)) if last_ex else '—'}</td>"
                f'<td class="num">{delta_e}</td><td class="num">{delta_v}</td></tr>'
            )

        def total(w: ta.Workout) -> str:
            reps = sum(ex.total_reps for ex in w.exercises)
            vol = sum(ex.volume for ex in w.exercises)
            return f"{w.set_count} serii · {reps} powt. · {_thousands(vol)} kg"

        vol_delta = sum(ex.volume for ex in c.last.exercises) - sum(ex.volume for ex in c.previous.exercises)
        foot = (
            f'<tfoot><tr><td>Razem</td><td class="dim">{total(c.previous)}</td><td>{total(c.last)}</td>'
            f'<td></td><td class="num">{_fmt_delta(vol_delta)}</td></tr></tfoot>'
        )
        table = _table(["Ćwiczenie", prev_d, last_d, "Δ e1RM", "Δ objętość"], rows, {3, 4}, foot)
        panels.append(f'<div class="picker-panel" data-panel="cmp" id="{pid}">{table}</div>')
    body = f'<div class="card-head">{_picker("cmp", options, "Trening")}</div>' + "".join(panels)
    return _card(label, body, "span-all card-picker")


def build_hevy_banner(steps: dict[str, Any]) -> str:
    hevy = steps.get("hevy") or {}
    if hevy.get("result") != "fail":
        return ""
    return f'<div class="banner" role="status"><span class="banner-dot"></span><div>Hevy: {esc(hevy.get("message") or "ostatnia synchronizacja nieudana")}</div></div>'


def build_training_panel(
    workouts: list[ta.Workout],
    cfg: ta.Config,
    bodyweights: list[tuple[date, float]],
    steps: dict[str, Any],
) -> str:
    banner = build_hevy_banner(steps)
    if not workouts:
        return banner + _grid_html(
            _empty_card("Hevy", "Brak treningów. Dodaj HEVY_API_KEY do .env i uruchom scripts/refresh_all.sh.", "span-all"),
            "grid-two",
        )
    hero = (
        build_workouts_tile(workouts) + build_sets_tile(workouts, cfg)
        + build_volume_tile(workouts) + build_records_tile(workouts)
    )
    return (
        banner
        + _grid_html(hero, "grid-hero")
        + _grid_html(build_exercise_list(workouts, cfg) + build_e1rm_card(workouts), "grid-two")
        + _section("Partie")
        + _grid_html(build_weekly_sets_card(workouts, cfg) + build_volume_card(workouts), "grid-two")
        + _section("Historia")
        + _grid_html(
            build_relative_strength_card(workouts, bodyweights)
            + build_records_card(workouts) + build_session_compare_card(workouts),
            "grid-two",
        )
    )


# --------------------------------------------------------------------------
# Nawyki
# --------------------------------------------------------------------------

HABIT_WEEKS = 12
# Najdłuższa seria liczona z ostatniego roku.
HABIT_HISTORY_DAYS = 365
HABIT_CELL = 10
HABIT_GAP = 2
HABIT_WEEK_GAP = 5

HABIT_STATE_PL = {
    hb.DONE: "zrobione",
    hb.MISSED: "niezrobione",
    hb.UNKNOWN: "brak danych",
    hb.PENDING: "dziś jeszcze otwarte",
}
HABIT_SOURCE_PL = {
    "steps": "Garmin",
    "sleep": "Garmin",
    "workout": "Hevy",
    "food": "/dzien",
    "weight": "/waga",
}


def build_habit_sources(
    records: list[dict[str, Any]],
    food_by_date: dict[str, dict[str, Any]],
    weight_entries: list[dict[str, Any]],
    workouts: list[ta.Workout],
    start: date,
    today: date,
) -> hb.Sources:
    src = hb.Sources(workout_days={w.day for w in workouts})
    for r in records:
        if isinstance(r.get("steps"), (int, float)):
            src.steps[r["_date"]] = r["steps"]
        secs = dig(r, "sleep", "total_seconds")
        if isinstance(secs, (int, float)):
            src.sleep_hours[r["_date"]] = secs / 3600
    for key in food_by_date:
        try:
            src.food_days.add(date.fromisoformat(key))
        except ValueError:
            pass
    for e in weight_entries:
        try:
            if e.get("kg") is not None:
                src.weight_days.add(date.fromisoformat(e["date"]))
        except (TypeError, ValueError):
            pass
    src.notes = hb.load_note_checkboxes(DAILY_DIR, start, today)
    return src


def _habit_today_detail(h: hb.Habit, src: hb.Sources, today: date) -> str:
    if h.type == "manual":
        return f"ręczny · /nawyk {esc(h.name.split()[0].lower())}"
    if h.source == "steps":
        v = src.steps.get(today)
        so_far = f"{_thousands(v)} / {_thousands(h.min)}" if v is not None else "brak danych"
        return f"Garmin · {so_far}"
    if h.source == "sleep":
        v = src.sleep_hours.get(today)
        return f"Garmin · {fmt_hms(v * 3600) if v is not None else 'brak danych'} / {_fmt_kg(h.min)}h"
    return HABIT_SOURCE_PL[h.source]


def build_habits_today_tile(stats: list[hb.HabitStats], src: hb.Sources, today: date) -> str:
    done = sum(s.states[today] == hb.DONE for s in stats)
    items = "".join(
        f'<li class="habit-today-item"><span class="hmark hmark-{s.states[today]}" title="{HABIT_STATE_PL[s.states[today]]}"></span>'
        f'<span class="habit-today-name">{esc(s.habit.name)}</span>'
        f'<span class="habit-today-detail">{_habit_today_detail(s.habit, src, today)}</span></li>'
        for s in stats
    )
    body = f'<div class="value">{done}{_unit(f"/ {len(stats)}")}</div><ul class="habit-today">{items}</ul>'
    return _card("Dziś", body, "span-all")


def _habit_cells_svg(states: dict[date, str], first_monday: date, today: date) -> str:
    week_w = 7 * (HABIT_CELL + HABIT_GAP) - HABIT_GAP
    width = HABIT_WEEKS * week_w + (HABIT_WEEKS - 1) * HABIT_WEEK_GAP
    rects = []
    for i in range(HABIT_WEEKS * 7):
        d = first_monday + timedelta(days=i)
        if d > today:
            break
        week, dow = divmod(i, 7)
        x = week * (week_w + HABIT_WEEK_GAP) + dow * (HABIT_CELL + HABIT_GAP)
        state = states.get(d, hb.UNKNOWN)
        today_cls = " hc-today" if d == today else ""
        rects.append(
            f'<rect x="{x}" y="1" width="{HABIT_CELL}" height="{HABIT_CELL}" rx="3" class="hc hc-{state}{today_cls}" '
            f'data-tip="{_tip(fmt_short_date(d), HABIT_STATE_PL[state])}" />'
        )
    return (
        f'<svg width="100%" viewBox="0 0 {width} {HABIT_CELL + 2}" class="habit-cells" '
        f'preserveAspectRatio="xMinYMid meet" role="img" aria-label="Ostatnie {HABIT_WEEKS} tygodni">'
        + "".join(rects) + "</svg>"
    )


def _fmt_pct(v: float | None) -> str:
    return f"{v:.0f}%" if v is not None else "—"


def build_habits_grid_tile(stats: list[hb.HabitStats], today: date) -> str:
    first_monday = _week_start(today) - timedelta(weeks=HABIT_WEEKS - 1)
    week_labels = "".join(
        f"<span>{fmt_short_date(first_monday + timedelta(weeks=i))}</span>" for i in range(HABIT_WEEKS)
    )
    rows = []
    for s in stats:
        kind = "auto" if s.habit.type == "auto" else "ręczny"
        rows.append(
            f'<div class="habit-row">'
            f'<div class="habit-name">{esc(s.habit.name)}<span class="habit-kind">{kind}</span></div>'
            f'<div class="habit-cells-wrap">{_habit_cells_svg(s.states, first_monday, today)}</div>'
            f'<div class="habit-stats">'
            f'<span><span class="dim">seria</span> <b>{s.current_streak}</b></span>'
            f'<span><span class="dim">rekord</span> <b>{s.longest_streak}</b></span>'
            f'<span><span class="dim">7 dni</span> <b>{_fmt_pct(s.pct_7)}</b></span>'
            f'<span><span class="dim">30 dni</span> <b>{_fmt_pct(s.pct_30)}</b></span>'
            f"</div></div>"
        )
    legend = (
        '<ul class="legend">'
        '<li><i class="hlegend hc-done"></i>zrobione</li>'
        '<li><i class="hlegend hc-missed"></i>niezrobione</li>'
        '<li><i class="hlegend hc-unknown"></i>brak danych</li>'
        '<li><i class="hlegend hc-pending"></i>dziś, otwarte</li>'
        "</ul>"
    )
    body = (
        f'<div class="habit-row habit-head"><div></div><div class="habit-weeks">{week_labels}</div><div></div></div>'
        f'{"".join(rows)}{legend}'
    )
    return _card(f"{HABIT_WEEKS} tygodni", body, "span-all")


def build_habits_panel(
    records: list[dict[str, Any]],
    food_by_date: dict[str, dict[str, Any]],
    weight_entries: list[dict[str, Any]],
    workouts: list[ta.Workout],
    habits: list[hb.Habit],
) -> str:
    if not habits:
        return _grid_html(_empty_card("Nawyki", "Brak nawyków w data/habits.json.", "span-all"), "grid-two")
    today = date.today()
    start = today - timedelta(days=HABIT_HISTORY_DAYS - 1)
    src = build_habit_sources(records, food_by_date, weight_entries, workouts, start, today)
    stats = hb.habit_stats(habits, src, start, today)
    return _grid_html(build_habits_today_tile(stats, src, today) + build_habits_grid_tile(stats, today), "grid-two")


# --------------------------------------------------------------------------
# Page assembly
# --------------------------------------------------------------------------

def build_stale_banner(records: list[dict[str, Any]], steps: dict[str, Any]) -> str:
    """Subtle banner when the newest Garmin sync is older than 24 h."""
    garmin = steps.get("garmin") or {}
    last_ok = last_garmin_ok(records, garmin)
    if last_ok and datetime.now() - last_ok <= STALE_AFTER:
        return ""
    since = f" od {fmt_short_date(last_ok.date())}" if last_ok else ""
    if garmin.get("result") == "fail" and garmin.get("message"):
        reason = garmin["message"]
    else:
        reason = "brak udanej synchronizacji (Mac uśpiony w porach zadań?)"
    fix = garmin.get("fix") or "cd ~/anton_brain && scripts/refresh_all.sh"
    return (
        '<div class="banner" role="status"><span class="banner-dot"></span><div>'
        f"<b>Dane nieaktualne{since}</b> · {esc(reason)}"
        f'<code>{esc(fix)}</code></div></div>'
    )


def build_jarvis_badge(records: list[dict[str, Any]], steps: dict[str, Any]) -> str:
    last = max(
        (dt for dt in (
            last_garmin_ok(records, steps.get("garmin") or {}),
            _parse_dt((steps.get("hevy") or {}).get("last_success")),
        ) if dt),
        default=None,
    )
    when = fmt_when(last) if last else "brak synchronizacji"
    title = f"Ostatnia synchronizacja: {fmt_dt_pl(last)}" if last else "Brak synchronizacji"
    return f'<span class="jarvis" title="{esc(title)}"><span class="jarvis-dot"></span>Jarvis · {esc(when)}</span>'


TABS = [("zdrowie", "Zdrowie"), ("trening", "Trening"), ("nawyki", "Nawyki")]


def build_html(
    records: list[dict[str, Any]],
    food_by_date: dict[str, dict[str, Any]],
    weight_entries: list[dict[str, Any]],
    workouts: list[ta.Workout],
    training_cfg: ta.Config,
    bodyweights: list[tuple[date, float]],
    habits: list[hb.Habit],
) -> str:
    steps = load_status_steps()
    panels = {
        "zdrowie": build_health_panel(records, food_by_date, weight_entries),
        "trening": build_training_panel(workouts, training_cfg, bodyweights, steps),
        "nawyki": build_habits_panel(records, food_by_date, weight_entries, workouts, habits),
    }
    inputs = "".join(
        f'<input type="radio" name="tab" id="tab-{key}" class="tab-input"{" checked" if i == 0 else ""}>'
        for i, (key, _) in enumerate(TABS)
    )
    labels = "".join(f'<label for="tab-{key}">{name}</label>' for key, name in TABS)
    mains = "".join(f'<main class="panel panel-{key}">{panels[key]}</main>' for key, _ in TABS)
    css = CSS_PATH.read_text(encoding="utf-8")
    js = JS_PATH.read_text(encoding="utf-8")

    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Health Dashboard</title>
<style>{css}</style>
</head>
<body>
{inputs}
<header class="top">
  <div>
    <p class="today">{esc(fmt_long_date_pl(date.today()))}</p>
    <h1>Cześć {esc(GREETING_NAME)}</h1>
  </div>
  {build_jarvis_badge(records, steps)}
</header>
{build_stale_banner(records, steps)}
<nav class="seg-wrap" aria-label="Zakładki"><div class="seg"><span class="seg-thumb"></span>{labels}</div></nav>
{mains}
<script>{js}</script>
</body>
</html>
"""


def main() -> None:
    records = load_records()
    food_by_date = load_food_records()
    weight_entries = load_weight_entries()
    workouts = ta.load_workouts(HEVY_DIR)
    training_cfg = ta.load_config(HEVY_CONFIG_PATH)
    bodyweights = ta.load_bodyweights(WEIGHT_PATH)
    habits = hb.load_habits(HABITS_PATH)
    html = build_html(records, food_by_date, weight_entries, workouts, training_cfg, bodyweights, habits)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Zapisano dashboard: {OUT_PATH} ({len(records)} dni danych, {len(workouts)} treningów, {len(html)} znaków).")


if __name__ == "__main__":
    main()
