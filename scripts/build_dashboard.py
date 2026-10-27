#!/usr/bin/env python3
"""Builds a self-contained Health Dashboard.html from data/garmin/*.json.

Usage (from repo root, using the project venv):

    .venv/bin/python scripts/build_dashboard.py

Reads every daily JSON file written by scripts/garmin_sync.py, the Hevy
workouts written by scripts/hevy_sync.py (data/hevy/), plus data/food/*.json
and data/weight.json written by the Telegram bot's /dzien and /waga commands
(data/targets.json only for an optional "bands" override). Generates a
single standalone HTML file at "Health/Health Dashboard.html" with inline
SVG charts (no external libraries or fonts, no network requests). Styles
and the page script live next to this file (dashboard.css, dashboard.js)
and are inlined at build time. Light theme by default, dark when the system
prefers it. Days with missing data are rendered as gaps, never errors.

One screen, no scrolling (from 700 px wide): a thin top bar (segmented
control, "Dane nieaktualne" when the Garmin data is older than 24 h, Jarvis
with the last sync time) and a 4 x 2 grid of cards that stretch to fill the
window. Charts are drawn in a 0-100 viewBox stretched to the card
(preserveAspectRatio="none"); axis labels and dots are HTML on top, so
text never distorts. Below 700 px: 2 columns, scrolling allowed.

"Zdrowie": Training Readiness, last night's sleep (phase bar + 14 nights),
resting heart rate, steps (each with a 14-day trend), weight, and 14-day
calorie / protein / carb bars colored by NUTRITION_BANDS (good / mid / bad,
always with a ✓ / ! / ✕ glyph next to the color). The top row and weight
carry a dashed reference line and one progress line under the number:
goals from data/goals.json (steps, weight, sleep hours - set with /cel
kroki|waga|sen), Garmin's "high" readiness threshold, and the 30-day
resting heart rate average.

"Trening": Hevy data only (computed in scripts/training_analytics.py, also
used by the bot's /trening): workouts per week, working sets per muscle
group vs. the target range, the top 5 exercises by progression status with
an e1RM sparkline, steps and weight.

"Nawyki": habits from data/habits.json (scripts/habits.py) - today's state
and a 12-week grid with streaks and % done.
"""

from __future__ import annotations

import itertools
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import habits as hb
import import_waga as iw
import training_analytics as ta

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
DATA_DIR = REPO_ROOT / "data" / "garmin"
FOOD_DIR = REPO_ROOT / "data" / "food"
WEIGHT_PATH = REPO_ROOT / "data" / "weight.json"
TARGETS_PATH = REPO_ROOT / "data" / "targets.json"
GOALS_PATH = REPO_ROOT / "data" / "goals.json"
STATUS_PATH = REPO_ROOT / "data" / "status.json"
HEVY_DIR = REPO_ROOT / "data" / "hevy"
HEVY_CONFIG_PATH = REPO_ROOT / "data" / "hevy_config.json"
HABITS_PATH = REPO_ROOT / "data" / "habits.json"
DAILY_DIR = REPO_ROOT / "daily"
CSS_PATH = SCRIPTS_DIR / "dashboard.css"
JS_PATH = SCRIPTS_DIR / "dashboard.js"
OUT_DIR = REPO_ROOT / "Health"
OUT_PATH = OUT_DIR / "Health Dashboard.html"

TREND_DAYS = 14
WEIGHT_POINTS = 30
STALE_AFTER = timedelta(hours=24)

# Garmin's "high" Training Readiness starts here.
READINESS_THRESHOLD = 75
RHR_AVG_DAYS = 30
WEIGHT_PACE_DAYS = 7
# No "goal reached around ..." date further out than this.
WEIGHT_ETA_MAX_DAYS = 730

# Nutrition bands ("dobre / średnie / złe jedzenie") - the only place the
# thresholds live. Per macro: the green range and the wider yellow range around
# it (both inclusive); outside the yellow range is red. "week_kcal" rates the
# average kcal of the last NUTRITION_WEEK_DAYS days. Any key can be overridden
# in data/targets.json, e.g. {"bands": {"fat": {"green": [60, 85], "yellow": [50, 100]}}};
# an invalid override falls back to the default for that key.
NUTRITION_BANDS: dict[str, dict[str, tuple[float, float]]] = {
    "kcal": {"green": (2480, 2740), "yellow": (2350, 2870)},
    "protein": {"green": (170, 210), "yellow": (150, 240)},
    "fat": {"green": (60, 85), "yellow": (50, 100)},
    "carbs": {"green": (250, 330), "yellow": (220, 360)},
    "week_kcal": {"green": (2560, 2660), "yellow": (2450, 2770)},
}
NUTRITION_WEEK_DAYS = 7

# Status -> (glyph, short label). The glyph always travels with the color so
# the state never depends on color alone.
NUTRITION_STATUS = {
    "good": ("✓", "w normie"),
    "mid": ("!", "blisko granicy"),
    "bad": ("✕", "poza zakresem"),
}

MONTHS_PL_GEN = [
    "stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca",
    "lipca", "sierpnia", "września", "października", "listopada", "grudnia",
]

TRAINING_WEEKS = 12
TOP_EXERCISES = 5
TOP_MUSCLE_GROUPS = 7
EXERCISE_SPARK_POINTS = 12

READINESS_LEVEL_PL = {
    "HIGH": "wysoka",
    "MODERATE": "umiarkowana",
    "LOW": "niska",
    "VERY_LOW": "bardzo niska",
    "PRIME": "optymalna",
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
    """data/targets.json (/cel). Only its optional "bands" key is used here;
    the targets themselves are read by scripts/trener_report.py."""
    if not TARGETS_PATH.exists():
        return None
    try:
        data = json.loads(TARGETS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def load_goals() -> dict[str, float]:
    """{"steps", "weight", "sleep" (hours)} from data/goals.json (/cel
    kroki|waga|sen); missing or invalid keys are left out."""
    try:
        data = json.loads(GOALS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        k: float(v) for k in ("steps", "weight", "sleep")
        if isinstance(v := data.get(k), (int, float)) and not isinstance(v, bool) and v > 0
    }


def last_n_calendar_days(n: int) -> list[date]:
    today = date.today()
    return [today - timedelta(days=i) for i in range(n - 1, -1, -1)]


# --------------------------------------------------------------------------
# Nutrition bands (pure functions - covered by scripts/test_nutrition_bands.py)
# --------------------------------------------------------------------------

def _valid_range(raw: Any) -> tuple[float, float] | None:
    if (
        isinstance(raw, (list, tuple))
        and len(raw) == 2
        and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in raw)
        and raw[0] <= raw[1]
    ):
        return (raw[0], raw[1])
    return None


def resolve_bands(targets: dict[str, Any] | None) -> dict[str, dict[str, tuple[float, float]]]:
    """NUTRITION_BANDS with any valid per-key override from targets["bands"]."""
    bands = {k: dict(v) for k, v in NUTRITION_BANDS.items()}
    overrides = (targets or {}).get("bands")
    if not isinstance(overrides, dict):
        return bands
    for key, default in NUTRITION_BANDS.items():
        o = overrides.get(key)
        if not isinstance(o, dict):
            continue
        green = _valid_range(o.get("green", default["green"]))
        yellow = _valid_range(o.get("yellow", default["yellow"]))
        if green and yellow and yellow[0] <= green[0] and green[1] <= yellow[1]:
            bands[key] = {"green": green, "yellow": yellow}
    return bands


def band_status(value: Any, band: dict[str, tuple[float, float]]) -> str | None:
    """"good" / "mid" / "bad" for a value against one band, None when missing."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    g_lo, g_hi = band["green"]
    y_lo, y_hi = band["yellow"]
    if g_lo <= value <= g_hi:
        return "good"
    if y_lo <= value <= y_hi:
        return "mid"
    return "bad"


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


def fmt_local_time(ms: Any) -> str | None:
    """Garmin's 'Local' sleep timestamps are epoch-ms already shifted by the
    local UTC offset, so reading them back as UTC yields the correct
    wall-clock local time."""
    if not isinstance(ms, (int, float)):
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%H:%M")


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


def _day_label(d: date) -> str:
    return "dziś" if d == date.today() else fmt_short_date(d)


def _unit(text: str) -> str:
    return f'<span class="u">{esc(text)}</span>'


def _duration_html(seconds: float) -> str:
    h, m = divmod(int(seconds) // 60, 60)
    return f"{h}{_unit('h')} {m}{_unit('min')}"


def _tip(when: str, value: str) -> str:
    """data-tip value: the page script shows 'when' small and 'value' bold."""
    return esc(f"{when}|{value}")


# --------------------------------------------------------------------------
# Charts
#
# Shapes live in a 0-100 x 0-100 viewBox stretched to the card
# (preserveAspectRatio="none", strokes with vector-effect: non-scaling-stroke
# in CSS); axis labels and dots are HTML positioned in %, so nothing
# distorts. Each point has a hover column (<g class="col" data-tip data-x
# data-y>) - dashboard.js shows the tooltip and moves the dot.
# --------------------------------------------------------------------------

_UID = itertools.count(1)

EMPTY_CHART = '<p class="empty">Brak danych</p>'


def _nice_step(span: float, n: int) -> float:
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def _ticks(lo: float, hi: float, n: int = 2) -> list[float]:
    """3-4 round values covering lo..hi (the chart's horizontal lines)."""
    if hi <= lo:
        lo, hi = lo - 1, hi + 1
    step = _nice_step(hi - lo, n)
    start = math.floor(lo / step + 1e-9) * step
    end = math.ceil(hi / step - 1e-9) * step
    count = int(round((end - start) / step))
    return [start + step * i for i in range(count + 1)]


def _axis_fmt(v: float) -> str:
    if abs(v) >= 10000:
        return f"{v / 1000:g}k"
    return f"{v:g}" if v != int(v) else f"{int(v)}"


def _x_positions(n: int) -> list[float]:
    return [100 * i / (n - 1) if n > 1 else 50.0 for i in range(n)]


def _hover_cols(xs: list[float], ys: list[float | None], tips: list[str]) -> str:
    out = []
    n = len(xs)
    for i, x in enumerate(xs):
        left = 0.0 if i == 0 else (xs[i - 1] + x) / 2
        right = 100.0 if i == n - 1 else (x + xs[i + 1]) / 2
        y = f' data-y="{ys[i]:.2f}"' if ys[i] is not None else ""
        guide = f'<line x1="{x:.2f}" y1="0" x2="{x:.2f}" y2="100" class="guide" />' if ys[i] is not None else ""
        out.append(
            f'<g class="col" data-tip="{tips[i]}" data-x="{x:.2f}"{y}>'
            f'<rect x="{left:.2f}" y="0" width="{max(right - left, 0.1):.2f}" height="100" class="hit" />{guide}</g>'
        )
    return "".join(out)


# A tick label closer than this (in % of the plot height) to a reference
# label is dropped, so the two never overlap.
REF_TICK_GAP = 9


def _y_axis(ticks: list[float], y_of, ref_labels: str = "", ref_ys: list[float] | None = None) -> str:
    labels = "".join(
        f'<span style="top:{y_of(t):.2f}%">{_axis_fmt(t)}</span>' for t in ticks
        if all(abs(y_of(t) - ry) >= REF_TICK_GAP for ry in ref_ys or [])
    )
    return f'<div class="yaxis">{labels}{ref_labels}</div>'


def _grid_lines(ticks: list[float], y_of) -> str:
    return "".join(
        f'<line x1="0" y1="{y_of(t):.2f}" x2="100" y2="{y_of(t):.2f}" class="grid" />' for t in ticks
    )


def _ref_lines(refs: list[tuple[float, str]], y_of, axes: bool) -> tuple[str, str]:
    """(SVG dashed lines, HTML labels) for reference values (goal,
    threshold, average). On axis charts the label sits on the Y axis."""
    lines = "".join(
        f'<line x1="0" y1="{y_of(v):.2f}" x2="100" y2="{y_of(v):.2f}" class="ref" />' for v, _ in refs
    )
    cls = "ref-tick" if axes else "ref-label"
    labels = "".join(f'<span class="{cls}" style="top:{y_of(v):.2f}%">{esc(text)}</span>' for v, text in refs)
    return lines, labels


def chart_line(
    values: list[float | None],
    tips: list[str],
    *,
    axes: bool = False,
    refs: list[tuple[float, str]] | None = None,
    aria: str = "Wykres",
) -> str:
    """Line with a gradient fill fading to transparent, stretched to its
    box. axes=False: a sparkline; axes=True: 3-4 light horizontal lines
    with values on the right. Gaps (None) split the line. refs: (value,
    label) drawn as thin dashed lines; the scale always includes them."""
    known = [v for v in values if v is not None]
    if not known:
        return EMPTY_CHART
    refs = refs or []
    lo = min(known + [v for v, _ in refs])
    hi = max(known + [v for v, _ in refs])
    ticks: list[float] = []
    if axes:
        ticks = _ticks(lo, hi)
        lo, hi = ticks[0], ticks[-1]
    else:
        pad = (hi - lo) * 0.18 or 1.0
        lo, hi = lo - pad, hi + pad

    def y_of(v: float) -> float:
        return 100 * (1 - (v - lo) / (hi - lo))

    xs = _x_positions(len(values))
    ys = [y_of(v) if v is not None else None for v in values]
    gid = f"grad{next(_UID)}"
    parts = [
        f'<svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="{esc(aria)}">'
        f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" class="grad-top" /><stop offset="1" class="grad-bottom" /></linearGradient></defs>',
        _grid_lines(ticks, y_of),
    ]
    segments: list[list[tuple[float, float]]] = [[]]
    for x, y in zip(xs, ys):
        if y is None:
            segments.append([])
        else:
            segments[-1].append((x, y))
    solos = []
    for seg in segments:
        if len(seg) == 1:
            solos.append(seg[0])
        elif seg:
            line = "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in seg)
            parts.append(f'<path d="{line} L{seg[-1][0]:.2f},100 L{seg[0][0]:.2f},100 Z" fill="url(#{gid})" class="area" />')
            parts.append(f'<path d="{line}" class="line" />')
    ref_svg, ref_html = _ref_lines(refs, y_of, axes)
    parts.append(ref_svg)
    parts.append(_hover_cols(xs, ys, tips))
    parts.append("</svg>")
    dots = "".join(f'<span class="pt solo" style="left:{x:.2f}%;top:{y:.2f}%"></span>' for x, y in solos)
    last = next(((x, y) for x, y in zip(reversed(xs), reversed(ys)) if y is not None), None)
    if last:
        dots += f'<span class="pt end" style="left:{last[0]:.2f}%;top:{last[1]:.2f}%"></span>'
    if not axes:
        plot = f'<div class="plot">{"".join(parts)}{dots}{ref_html}<span class="pt hover"></span></div>'
        return f'<div class="chart">{plot}</div>'
    plot = f'<div class="plot">{"".join(parts)}{dots}<span class="pt hover"></span></div>'
    axis = _y_axis(ticks, y_of, ref_html, [y_of(v) for v, _ in refs])
    return f'<div class="chart with-axes">{plot}{axis}</div>'


def chart_bars(values: list[float | None], tips: list[str], statuses: list[str | None], *, aria: str = "Wykres") -> str:
    """Rounded-top bars from zero colored by status, with the status glyph
    under every bar (a dot for days without a status)."""
    known = [v for v in values if v is not None]
    if not known:
        return EMPTY_CHART
    ticks = _ticks(0, max(known) or 1)
    hi = ticks[-1]
    slot = 100 / len(values)
    bw = slot * 0.62

    def y_of(v: float) -> float:
        return 100 * (1 - v / hi)

    cols = []
    for i, v in enumerate(values):
        x = slot * (i + 0.5)
        bar = ""
        if v is not None and v > 0:
            top = y_of(v)
            r = min(1.5, 100 - top)
            x0, x1 = x - bw / 2, x + bw / 2
            bar = (
                f'<path d="M{x0:.2f},100 L{x0:.2f},{top + r:.2f} Q{x0:.2f},{top:.2f} {x0 + bw * 0.2:.2f},{top:.2f} '
                f'L{x1 - bw * 0.2:.2f},{top:.2f} Q{x1:.2f},{top:.2f} {x1:.2f},{top + r:.2f} L{x1:.2f},100 Z" '
                f'class="bar st-{statuses[i] or "none"}" />'
            )
        cols.append(
            f'<g class="col" data-tip="{tips[i]}">'
            f'<rect x="{x - slot / 2:.2f}" y="0" width="{slot:.2f}" height="100" class="hit" />{bar}</g>'
        )
    glyphs = "".join(
        f'<span class="st-text-{s}">{NUTRITION_STATUS[s][0]}</span>' if s in NUTRITION_STATUS else "<span>·</span>"
        for s in statuses
    )
    svg = (
        f'<svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="{esc(aria)}">'
        f'{_grid_lines(ticks, y_of)}<g class="bar-group">{"".join(cols)}</g></svg>'
    )
    return (
        f'<div class="chart with-axes bars"><div class="plot">{svg}</div>{_y_axis(ticks, y_of)}'
        f'<div class="glyphs" aria-hidden="true">{glyphs}</div></div>'
    )


# --------------------------------------------------------------------------
# Cards
# --------------------------------------------------------------------------

def _card(
    label: str,
    value_html: str = "",
    viz_html: str = "",
    extra_class: str = "",
    label_extra: str = "",
    progress: str = "",
) -> str:
    """Label + one main number (+ one progress line) + a chart that takes
    the rest of the card."""
    cls = f"card {extra_class}".strip()
    extra = f'<span class="label-extra">{label_extra}</span>' if label_extra else ""
    value = f'<div class="value">{value_html}</div>' if value_html else ""
    line = f'<p class="progress">{esc(progress)}</p>' if progress else ""
    viz = f'<div class="viz">{viz_html}</div>' if viz_html else ""
    return f'<section class="{cls}"><h3 class="label"><span>{esc(label)}</span>{extra}</h3>{value}{line}{viz}</section>'


def _empty_card(label: str, message: str, extra_class: str = "") -> str:
    return _card(label, viz_html=f'<p class="empty">{esc(message)}</p>', extra_class=extra_class)


def _value_text(v: float | None, fmt=_thousands, unit: str = "") -> str:
    if v is None:
        return '<span class="none">—</span>'
    return fmt(v) + (_unit(unit) if unit else "")


def _daily_series_n(records: list[dict[str, Any]], getter, n: int) -> tuple[list[date], list[float | None]]:
    by_date = {r["_date"]: getter(r) for r in records}
    days = last_n_calendar_days(n)
    return days, [v if isinstance(v, (int, float)) else None for v in (by_date.get(d) for d in days)]


def _daily_series(records: list[dict[str, Any]], getter) -> tuple[list[date], list[float | None]]:
    return _daily_series_n(records, getter, TREND_DAYS)


def _latest(values: list[float | None]) -> float | None:
    return next((v for v in reversed(values) if v is not None), None)


# --------------------------------------------------------------------------
# Zdrowie
# --------------------------------------------------------------------------

def _signed(v: float, unit: str = "") -> str:
    """'+5' / '−3' (typographic minus), no sign for 0."""
    sign = "+" if v > 0 else "−" if v < 0 else ""
    return f"{sign}{abs(v):.0f}{unit}"


def build_readiness_card(records: list[dict[str, Any]]) -> str:
    days, values = _daily_series(records, lambda r: dig(r, "training_readiness", "score"))
    with_tr = [r for r in records if dig(r, "training_readiness", "score") is not None]
    level = dig(with_tr[-1], "training_readiness", "level") if with_tr else None
    tips = [_tip(_day_label(d), f"{v:.0f}" if v is not None else "brak danych") for d, v in zip(days, values)]
    latest = _latest(values)
    progress = ""
    if latest is not None:
        diff = round(latest) - READINESS_THRESHOLD
        progress = (
            f"+{diff} ponad progiem" if diff > 0 else f"{-diff} poniżej progu" if diff < 0 else "na progu"
        )
    return _card(
        "Gotowość", _value_text(latest, lambda v: f"{v:.0f}"),
        chart_line(values, tips, refs=[(READINESS_THRESHOLD, str(READINESS_THRESHOLD))], aria="Gotowość, 14 dni"),
        label_extra=esc(READINESS_LEVEL_PL.get(level, "")), progress=progress,
    )


def _phase_bar(sleep: dict[str, Any]) -> str:
    phases = [(label, sleep.get(key), cls) for key, label, cls in SLEEP_PHASES]
    phases = [(label, v, cls) for label, v, cls in phases if isinstance(v, (int, float)) and v > 0]
    total = sum(v for _, v, _ in phases)
    if not total:
        return ""
    segs = "".join(
        f'<span class="ph {cls}" style="flex-grow:{v:.0f}" data-tip="{_tip(label, f"{fmt_hms(v)} · {v / total * 100:.0f}%")}"></span>'
        for label, v, cls in phases
    )
    legend = "".join(f'<li><i class="ph {cls}"></i>{esc(label)} <b>{fmt_hms(v)}</b></li>' for label, v, cls in phases)
    return f'<div class="phases" role="img" aria-label="Fazy snu">{segs}</div><ul class="phase-legend">{legend}</ul>'


def build_sleep_card(records: list[dict[str, Any]], goals: dict[str, float]) -> str:
    days, values = _daily_series(records, lambda r: dig(r, "sleep", "total_seconds"))
    with_sleep = [r for r in records if dig(r, "sleep", "total_seconds") is not None]
    if not with_sleep:
        return _empty_card("Sen", "Brak danych")
    sleep = with_sleep[-1].get("sleep") or {}
    start_txt = fmt_local_time(sleep.get("start_local_ms"))
    end_txt = fmt_local_time(sleep.get("end_local_ms"))
    tips = [_tip(_day_label(d), fmt_hms(v) if v is not None else "brak danych") for d, v in zip(days, values)]
    hours = [v / 3600 if v is not None else None for v in values]
    goal = goals.get("sleep")
    refs, progress = [], ""
    if goal:
        refs = [(goal, f"cel {_fmt_kg(goal)}h")]
        diff_min = round((sleep["total_seconds"] - goal * 3600) / 60)
        progress = f"{_signed(diff_min)} min do celu" if diff_min < 0 else f"{_signed(diff_min)} min ponad cel"
    viz = _phase_bar(sleep) + chart_line(hours, tips, refs=refs, aria="Sen, 14 nocy")
    return _card(
        "Sen", _duration_html(sleep["total_seconds"]), viz, "card-sleep",
        label_extra=f"{start_txt}–{end_txt}" if start_txt and end_txt else "", progress=progress,
    )


def build_rhr_card(records: list[dict[str, Any]]) -> str:
    days, values = _daily_series(records, lambda r: r.get("resting_heart_rate"))
    tips = [_tip(_day_label(d), f"{v:.0f} bpm" if v is not None else "brak danych") for d, v in zip(days, values)]
    latest = _latest(values)
    # Average over the last RHR_AVG_DAYS calendar days, or fewer when the
    # data starts later; no good/bad judgment.
    window_days, window = _daily_series_n(records, lambda r: r.get("resting_heart_rate"), RHR_AVG_DAYS)
    known = [(d, v) for d, v in zip(window_days, window) if v is not None]
    refs, progress = [], ""
    if known:
        avg = sum(v for _, v in known) / len(known)
        span = (date.today() - known[0][0]).days + 1
        refs = [(avg, f"śr. {avg:.0f}")]
        if latest is not None:
            progress = f"{_signed(latest - avg)} bpm vs średnia {span} dni"
    return _card(
        "Tętno spoczynkowe", _value_text(latest, lambda v: f"{v:.0f}", "bpm"),
        chart_line(values, tips, refs=refs, aria="Tętno spoczynkowe, 14 dni"), progress=progress,
    )


def build_steps_card(records: list[dict[str, Any]], goals: dict[str, float]) -> str:
    days, values = _daily_series(records, lambda r: r.get("steps"))
    # Today is still in progress, so the headline is yesterday's full day.
    yesterday = values[-2] if len(values) > 1 else None
    tips = [
        _tip(_day_label(d) + (" (w toku)" if d == date.today() else ""),
             f"{_thousands(v)} kroków" if v is not None else "brak danych")
        for d, v in zip(days, values)
    ]
    goal = goals.get("steps")
    refs = [(goal, f"cel {_thousands(goal)}")] if goal else []
    progress = f"{yesterday / goal * 100:.0f}% celu" if goal and yesterday is not None else ""
    return _card(
        "Kroki", _value_text(yesterday), chart_line(values, tips, refs=refs, aria="Kroki, 14 dni"),
        label_extra="wczoraj", progress=progress,
    )


def _weight_progress(entries: list[tuple[date, float]], goal: float) -> str:
    """'do celu X kg · ±Y kg/tydz. · ok. DD.MM' - pace from a linear fit of
    the last WEIGHT_PACE_DAYS days; the date only when the pace points
    toward the goal."""
    last_d, last_kg = entries[-1]
    remaining = goal - last_kg
    if abs(remaining) < 0.05:
        return "cel osiągnięty"
    parts = [f"do celu {_fmt_kg(abs(remaining))} kg"]
    recent = [(d, kg) for d, kg in entries if d >= last_d - timedelta(days=WEIGHT_PACE_DAYS)]
    fit = ta.linear_trend(recent)
    if fit:
        per_day = fit[1]
        parts.append(f"{_fmt_delta(per_day * 7)}/tydz.")
        if per_day * remaining > 0:
            days = abs(remaining / per_day)
            if days <= WEIGHT_ETA_MAX_DAYS:
                eta = last_d + timedelta(days=round(days))
                parts.append(f"ok. {fmt_short_date(eta)}" + (f".{eta.year}" if eta.year != date.today().year else ""))
    return " · ".join(parts)


def build_weight_card(weight_entries: list[dict[str, Any]], goals: dict[str, float]) -> str:
    entries = []
    for e in weight_entries:
        try:
            kg = e.get("kg")
            if isinstance(kg, (int, float)):
                entries.append((date.fromisoformat(e["date"]), kg))
        except (TypeError, ValueError, KeyError):
            continue
    if not entries:
        return _empty_card("Waga", "Brak pomiarów")
    last_day, last_kg = entries[-1]
    goal = goals.get("weight")
    trend = entries[-WEIGHT_POINTS:]
    chart = chart_line(
        [kg for _, kg in trend], [_tip(_day_label(d), f"{kg:.1f} kg") for d, kg in trend],
        axes=True, refs=[(goal, f"cel {_fmt_kg(goal)}")] if goal else None, aria="Waga",
    )
    # Data pomiaru tylko, gdy nie jest z dziś - skrypt strony ukrywa ją też
    # po północy, gdy dashboard nie był od tamtej pory przebudowany.
    hidden = " hidden" if last_day == date.today() else ""
    measured = f'<span data-measured="{last_day.isoformat()}"{hidden}>pomiar: {fmt_short_date(last_day)}</span>'
    return _card(
        "Waga", _value_text(last_kg, lambda v: f"{v:.1f}", "kg"), chart,
        label_extra=measured, progress=_weight_progress(entries, goal) if goal else "",
    )


NUTRITION_CARDS = [
    ("Kalorie", "kcal", "kcal", "week_kcal"),
    ("Białko", "protein", "g", "protein"),
    ("Węglowodany", "carbs", "g", "carbs"),
]


def _status_value(text: str, status: str | None) -> str:
    if status not in NUTRITION_STATUS:
        return text
    glyph, word = NUTRITION_STATUS[status]
    return (
        f'<span class="st-text-{status}" title="{word}"><span class="st-glyph" aria-hidden="true">{glyph}</span>'
        f'{text}<span class="sr-only"> ({word})</span></span>'
    )


def build_nutrition_cards(
    food_by_date: dict[str, dict[str, Any]], bands: dict[str, dict[str, tuple[float, float]]]
) -> str:
    """14-day bars per macro colored by its band; the headline is the average
    of the last 7 full days with a food entry (kcal rated with week_kcal)."""
    days = last_n_calendar_days(TREND_DAYS)
    week = set(days[-1 - NUTRITION_WEEK_DAYS:-1])
    cards = []
    for label, key, unit, avg_band in NUTRITION_CARDS:
        values = [
            v if isinstance(v := (food_by_date.get(d.isoformat()) or {}).get(key), (int, float)) else None
            for d in days
        ]
        if not any(v is not None for v in values):
            cards.append(_empty_card(label, "Brak wpisów /dzien"))
            continue
        statuses = [band_status(v, bands[key]) for v in values]
        tips = [
            _tip(_day_label(d), f"{v:.0f} {unit} · {' '.join(NUTRITION_STATUS[s])}" if s else "brak wpisu")
            for d, v, s in zip(days, values, statuses)
        ]
        week_vals = [v for d, v in zip(days, values) if v is not None and d in week]
        avg = sum(week_vals) / len(week_vals) if week_vals else None
        value = (
            _status_value(_thousands(avg), band_status(avg, bands[avg_band])) + _unit(unit)
            if avg is not None else _value_text(None)
        )
        cards.append(_card(
            label, value, chart_bars(values, tips, statuses, aria=f"{label}, 14 dni"), label_extra="śr. 7 dni"
        ))
    return "".join(cards)


def build_health_panel(
    records: list[dict[str, Any]],
    food_by_date: dict[str, dict[str, Any]],
    weight_entries: list[dict[str, Any]],
    bands: dict[str, dict[str, tuple[float, float]]],
    goals: dict[str, float],
) -> str:
    return (
        build_readiness_card(records) + build_sleep_card(records, goals)
        + build_rhr_card(records) + build_steps_card(records, goals)
        + build_weight_card(weight_entries, goals) + build_nutrition_cards(food_by_date, bands)
    )


# --------------------------------------------------------------------------
# Trening
# --------------------------------------------------------------------------

def build_workouts_card(workouts: list[ta.Workout]) -> str:
    this_week = _week_start(date.today())
    weeks = [this_week - timedelta(weeks=i) for i in range(TRAINING_WEEKS - 1, -1, -1)]
    counts = {wk: 0 for wk in weeks}
    for w in workouts:
        if (wk := _week_start(w.day)) in counts:
            counts[wk] += 1
    values = [float(counts[wk]) for wk in weeks]
    tips = [_tip(f"tydz. od {fmt_short_date(wk)}", f"{v:.0f}") for wk, v in zip(weeks, values)]
    return _card(
        "Treningi", f"{values[-1]:.0f}", chart_line(values, tips, aria=f"Treningi, {TRAINING_WEEKS} tygodni"),
        label_extra="ten tydzień",
    )


def build_sets_card(workouts: list[ta.Workout], cfg: ta.Config) -> str:
    label = "Serie na partię"
    groups = ta.weekly_muscle_sets(workouts, cfg, date.today())[:TOP_MUSCLE_GROUPS]
    if not groups:
        return _empty_card(label, "Brak serii")
    top = max(max(g.target[1], g.sets, g.previous) for g in groups) * 1.05
    rows = []
    for g in groups:
        lo, hi = g.target
        prev = f'<span class="meter-tick" style="left:{g.previous / top * 100:.1f}%"></span>' if g.previous else ""
        rows.append(
            f'<div class="meter-row" data-tip="{_tip(g.label, f"{g.sets} serii · zakres {lo}–{hi} · poprzednio {g.previous}")}">'
            f'<span class="meter-label">{esc(g.label)}</span>'
            f'<span class="meter-value">{g.sets}<span class="dim">/{lo}–{hi}</span></span>'
            f'<span class="meter">'
            f'<span class="meter-band" style="left:{lo / top * 100:.1f}%;width:{(hi - lo) / top * 100:.1f}%"></span>'
            f'<span class="meter-fill" style="width:{g.sets / top * 100:.1f}%"></span>{prev}</span></div>'
        )
    return _card(label, viz_html=f'<div class="meters">{"".join(rows)}</div>', label_extra="7 dni")


def build_exercises_card(workouts: list[ta.Workout], cfg: ta.Config) -> str:
    """Top TOP_EXERCISES by progression status ("raise" first) with an e1RM
    sparkline."""
    label = "Ćwiczenia"
    progs = ta.progressions(workouts, cfg, date.today())[:TOP_EXERCISES]
    if not progs:
        return _empty_card(label, "Brak serii z 6 tygodni", "card-big")
    history = ta.exercise_history(workouts)
    items = []
    for p in progs:
        pts = [s for s in history.get(p.exercise_id, []) if s.best_e1rm is not None][-EXERCISE_SPARK_POINTS:]
        spark = chart_line(
            [s.best_e1rm for s in pts],
            [_tip(fmt_short_date(s.day), f"e1RM {_fmt_kg(s.best_e1rm)} kg · {_fmt_set(s.best_e1rm_set)}") for s in pts],
            aria=f"e1RM: {p.name}",
        ) if len(pts) > 1 else ""
        value = f'{_fmt_kg(pts[-1].best_e1rm)}{_unit("kg")}' if pts else '<span class="none">—</span>'
        items.append(
            f'<li class="ex" data-tip="{_tip(p.name, f"{fmt_short_date(p.last.day)} · {_fmt_sets(p.last.sets)}")}">'
            f'<div class="ex-main"><span class="ex-name">{esc(p.name)}</span>'
            f'<span class="pill pill-{p.status}">{esc(ta.status_label(p))}</span></div>'
            f'<div class="ex-spark">{spark}</div>'
            f'<span class="ex-val">{value}</span></li>'
        )
    return _card(label, viz_html=f'<ul class="ex-list">{"".join(items)}</ul>', extra_class="card-big", label_extra="e1RM")


def build_training_panel(
    records: list[dict[str, Any]],
    weight_entries: list[dict[str, Any]],
    workouts: list[ta.Workout],
    cfg: ta.Config,
    goals: dict[str, float],
) -> str:
    if workouts:
        hevy = build_exercises_card(workouts, cfg) + build_sets_card(workouts, cfg)
    else:
        hevy = _empty_card("Hevy", "Brak treningów. Dodaj HEVY_API_KEY do .env.", "card-big")
    return (
        hevy + build_workouts_card(workouts)
        + build_steps_card(records, goals) + build_weight_card(weight_entries, goals)
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
        return f"/nawyk {esc(h.name.split()[0].lower())}"
    if h.source == "steps":
        v = src.steps.get(today)
        return f"{_thousands(v)} / {_thousands(h.min)}" if v is not None else "Garmin"
    if h.source == "sleep":
        v = src.sleep_hours.get(today)
        return f"{fmt_hms(v * 3600)} / {_fmt_kg(h.min)}h" if v is not None else "Garmin"
    return HABIT_SOURCE_PL[h.source]


def build_habits_today_card(stats: list[hb.HabitStats], src: hb.Sources, today: date) -> str:
    done = sum(s.states[today] == hb.DONE for s in stats)
    items = "".join(
        f'<li class="habit-today-item"><span class="hmark hmark-{s.states[today]}" title="{HABIT_STATE_PL[s.states[today]]}"></span>'
        f'<span class="habit-today-name">{esc(s.habit.name)}</span>'
        f'<span class="habit-today-detail">{_habit_today_detail(s.habit, src, today)}</span></li>'
        for s in stats
    )
    return _card("Dziś", f"{done}{_unit(f'/ {len(stats)}')}", f'<ul class="habit-today">{items}</ul>', "card-tall")


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


def build_habits_grid_card(stats: list[hb.HabitStats], today: date) -> str:
    first_monday = _week_start(today) - timedelta(weeks=HABIT_WEEKS - 1)
    week_labels = "".join(
        f"<span>{fmt_short_date(first_monday + timedelta(weeks=i))}</span>" for i in range(HABIT_WEEKS)
    )
    rows = "".join(
        f'<div class="habit-row">'
        f'<div class="habit-name">{esc(s.habit.name)}</div>'
        f'<div class="habit-cells-wrap">{_habit_cells_svg(s.states, first_monday, today)}</div>'
        f'<div class="habit-stats">'
        f'<span><span class="dim">seria</span> <b>{s.current_streak}</b></span>'
        f'<span><span class="dim">rekord</span> <b>{s.longest_streak}</b></span>'
        f'<span><span class="dim">7 dni</span> <b>{_fmt_pct(s.pct_7)}</b></span>'
        f'<span><span class="dim">30 dni</span> <b>{_fmt_pct(s.pct_30)}</b></span>'
        f"</div></div>"
        for s in stats
    )
    body = (
        f'<div class="habits"><div class="habit-row habit-head"><div></div>'
        f'<div class="habit-weeks">{week_labels}</div><div></div></div>{rows}</div>'
    )
    return _card(f"{HABIT_WEEKS} tygodni", viz_html=body, extra_class="card-wide-tall")


def build_habits_panel(
    records: list[dict[str, Any]],
    food_by_date: dict[str, dict[str, Any]],
    weight_entries: list[dict[str, Any]],
    workouts: list[ta.Workout],
    habits: list[hb.Habit],
) -> str:
    if not habits:
        return _empty_card("Nawyki", "Brak nawyków w data/habits.json", "card-big")
    today = date.today()
    start = today - timedelta(days=HABIT_HISTORY_DAYS - 1)
    src = build_habit_sources(records, food_by_date, weight_entries, workouts, start, today)
    stats = hb.habit_stats(habits, src, start, today)
    return build_habits_today_card(stats, src, today) + build_habits_grid_card(stats, today)


# --------------------------------------------------------------------------
# Page assembly
# --------------------------------------------------------------------------

def build_stale_pill(records: list[dict[str, Any]], steps: dict[str, Any]) -> str:
    """'Dane nieaktualne' in the top bar when the newest Garmin sync is older
    than 24 h; the reason and the fix are in its tooltip."""
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
        f'<span class="stale" role="status" data-tip="{_tip(reason, fix)}">'
        f'<span class="stale-dot"></span>Dane nieaktualne{since}</span>'
    )


def build_weight_pill() -> str:
    """'Waga: ostatni pomiar DD.MM' (neutral gray, information - not an
    alert) when weight.json has no reading from today - the same text as
    the "waga" step in /status. Rendered hidden for today's reading so the
    page script can show it after midnight without a rebuild."""
    last = iw.last_weight_date()
    message = iw.not_today_message(last)
    hidden = " hidden" if last == date.today().isoformat() else ""
    return (
        f'<span class="info" role="status" data-measured="{esc(last or "")}" '
        f'data-tip="{_tip("", message)}"{hidden}><span class="info-dot"></span>{esc(message)}</span>'
    )


def build_jarvis(records: list[dict[str, Any]], steps: dict[str, Any]) -> str:
    last = max(
        (dt for dt in (
            last_garmin_ok(records, steps.get("garmin") or {}),
            _parse_dt((steps.get("hevy") or {}).get("last_success")),
        ) if dt),
        default=None,
    )
    if last is None:
        when = "brak"
    elif last.date() == date.today():
        when = last.strftime("%H:%M")
    else:
        when = f"{fmt_short_date(last.date())} {last.strftime('%H:%M')}"
    title = fmt_dt_pl(last) if last else "brak synchronizacji"
    return (
        f'<span class="jarvis" title="{esc(title)}"><span class="jarvis-dot"></span>'
        f"Jarvis · ostatnia synchronizacja {esc(when)}</span>"
    )


TABS = [("zdrowie", "Zdrowie"), ("trening", "Trening"), ("nawyki", "Nawyki")]


def build_html(
    records: list[dict[str, Any]],
    food_by_date: dict[str, dict[str, Any]],
    weight_entries: list[dict[str, Any]],
    bands: dict[str, dict[str, tuple[float, float]]],
    workouts: list[ta.Workout],
    training_cfg: ta.Config,
    habits: list[hb.Habit],
    goals: dict[str, float],
) -> str:
    steps = load_status_steps()
    panels = {
        "zdrowie": build_health_panel(records, food_by_date, weight_entries, bands, goals),
        "trening": build_training_panel(records, weight_entries, workouts, training_cfg, goals),
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
<nav class="bar" aria-label="Zakładki">
  <div class="seg"><span class="seg-thumb"></span>{labels}</div>
  {build_stale_pill(records, steps)}
  {build_weight_pill()}
  {build_jarvis(records, steps)}
</nav>
{mains}
<script>{js}</script>
</body>
</html>
"""


def main() -> None:
    records = load_records()
    food_by_date = load_food_records()
    weight_entries = load_weight_entries()
    bands = resolve_bands(load_targets())
    workouts = ta.load_workouts(HEVY_DIR)
    training_cfg = ta.load_config(HEVY_CONFIG_PATH)
    habits = hb.load_habits(HABITS_PATH)
    html = build_html(
        records, food_by_date, weight_entries, bands, workouts, training_cfg, habits, load_goals()
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Zapisano dashboard: {OUT_PATH} ({len(records)} dni danych, {len(workouts)} treningów, {len(html)} znaków).")


if __name__ == "__main__":
    main()
