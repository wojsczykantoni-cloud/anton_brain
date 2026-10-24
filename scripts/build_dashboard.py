#!/usr/bin/env python3
"""Builds a self-contained Health Dashboard.html from data/garmin/*.json.

Usage (from repo root, using the project venv):

    .venv/bin/python scripts/build_dashboard.py

Reads every daily JSON file written by scripts/garmin_sync.py, the Hevy
workouts written by scripts/hevy_sync.py (data/hevy/), plus
data/food/*.json, data/weight.json and data/targets.json written by the
Telegram bot's /dzien, /waga and /cel commands. Generates a single
standalone HTML file at "Health/Health Dashboard.html" with inline SVG
charts (no external libraries or fonts, no network requests). Dark theme
by default, switching to a light theme when the system prefers light
(prefers-color-scheme). Days with missing data are rendered as gaps,
never errors; a missing data/targets.json simply omits target lines.

Two tabs (CSS-only radio tabs; a tiny script remembers the last one across
Obsidian's auto-reloads). "Zdrowie", 3-column grid. Row 1: Training
Readiness ring + per-factor bars (only the factors actually present in the
data) with a rule-based Polish summary, 14-day steps, resting heart rate
trend. Row 2: last night's sleep (duration, start/end times, score, phase
bar), yesterday's nutrition vs. target with a day rating, weight trend.
Rows 3-4: the last 7 days' nutrition rating, 14-day calorie/protein/carb/fat
bar charts with a dashed target line, and the threshold legend.

"Trening": Hevy data only (data/hevy/; plus data/weight.json for strength
relative to body weight), computed in scripts/training_analytics.py (also
used by the bot's /trening). Estimated 1RM (Epley) over time per exercise
with a linear trend line (exercise picked from a list), e1RM / body weight,
a double-progression tracker (rep range per exercise from
data/hevy_config.json: "raise the weight" / "add reps" / "stalled for N
sessions"), working sets per muscle group in the last 7 days vs. the target
range, volume per muscle group, workouts per week, records (best set and
best e1RM, with those from the last 4 weeks marked) and the last two
sessions of the same workout title side by side. Working sets = every set
except warm-ups; each exercise counts toward its primary muscle group only.
"Nawyki": habits from data/habits.json (scripts/habits.py) - today's state
as a list, then a 12-week grid (row per habit, cell per day) with the current
and longest streak and % done over the last 7 / 30 full days. Auto habits
(steps, sleep, Hevy session, food and weight logged) are computed only here;
manual ones come from the "Nawyki" checkboxes in daily/YYYY-MM-DD.md.

Nutrition is the one place with good/mid/bad colors: every macro value and
14-day bar is rated against NUTRITION_BANDS (green / yellow / red, always
with a ✓ / ! / ✕ glyph next to the color), and so are the day (rate_day) and
the last 7 days (rate_week). Days without a food file stay neutral ("brak
danych"). Colors are neutral throughout the weight, training and habit tiles -
no good/bad judgment, just numbers.
"""

from __future__ import annotations

import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import habits as hb
import training_analytics as ta

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "garmin"
FOOD_DIR = REPO_ROOT / "data" / "food"
WEIGHT_PATH = REPO_ROOT / "data" / "weight.json"
TARGETS_PATH = REPO_ROOT / "data" / "targets.json"
STATUS_PATH = REPO_ROOT / "data" / "status.json"
HEVY_DIR = REPO_ROOT / "data" / "hevy"
HEVY_CONFIG_PATH = REPO_ROOT / "data" / "hevy_config.json"
HABITS_PATH = REPO_ROOT / "data" / "habits.json"
DAILY_DIR = REPO_ROOT / "daily"
OUT_DIR = REPO_ROOT / "Health"
OUT_PATH = OUT_DIR / "Health Dashboard.html"

TREND_DAYS = 14
STALE_AFTER = timedelta(hours=24)

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
NUTRITION_MACROS = ("kcal", "protein", "carbs", "fat")
NUTRITION_WEEK_DAYS = 7

# Status -> (glyph, short label). The glyph always travels with the color so
# the state never depends on color alone.
NUTRITION_STATUS = {
    "good": ("✓", "w normie"),
    "mid": ("!", "blisko granicy"),
    "bad": ("✕", "poza zakresem"),
}
DAY_RATING_PL = {"good": "Dobry dzień", "mid": "Średni dzień", "bad": "Zły dzień"}
WEEK_RATING_PL = {"good": "Dobry tydzień", "mid": "Średni tydzień", "bad": "Zły tydzień"}

MONTHS_PL_GEN = [
    "stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca",
    "lipca", "sierpnia", "września", "października", "listopada", "grudnia",
]

SLEEP_QUALIFIER_PL = {
    "EXCELLENT": "Doskonały",
    "GOOD": "Dobry",
    "FAIR": "Przeciętny",
    "POOR": "Słaby",
}

TRAINING_WEEKS = 12
VOLUME_WINDOW_DAYS = 7
VOLUME_BASELINE_WINDOWS = 4
E1RM_MAX_POINTS = 24
REL_STRENGTH_ROWS = 8

MUSCLE_GROUP_PL = ta.MUSCLE_GROUP_PL

READINESS_LEVEL_PL = {
    "HIGH": "Wysoka",
    "MODERATE": "Umiarkowana",
    "LOW": "Niska",
    "VERY_LOW": "Bardzo niska",
    "PRIME": "Optymalna",
}

READINESS_COLORS = {
    "PRIME": "#4fb477",
    "HIGH": "#4fb477",
    "MODERATE": "#e3ad4c",
    "LOW": "#d98a4a",
    "VERY_LOW": "#d9694f",
}
READINESS_DEFAULT_COLOR = "#7c6fe0"

FACTOR_ORDER = ["sleep", "hrv", "sleep_history", "stress_history", "recovery_time", "acwr"]
FACTOR_LABELS_PL = {
    "sleep": "Sen",
    "hrv": "HRV",
    "sleep_history": "Historia snu",
    "stress_history": "Stres",
    "recovery_time": "Czas regeneracji",
    "acwr": "Obciążenie",
}

LEVEL_PHRASES_PL = {
    "PRIME": "Organizm jest w optymalnej formie do treningu.",
    "HIGH": "Organizm jest dobrze przygotowany do wysiłku.",
    "MODERATE": "Organizm jest umiarkowanie gotowy na wysiłek.",
    "LOW": "Organizm sygnalizuje ograniczoną gotowość na wysiłek.",
    "VERY_LOW": "Organizm potrzebuje dziś przede wszystkim odpoczynku.",
}


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


def latest_sync_dt(records: list[dict[str, Any]]) -> datetime | None:
    best: datetime | None = None
    for r in records:
        fetched_at = r.get("fetched_at")
        if not fetched_at:
            continue
        try:
            dt = datetime.strptime(fetched_at, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue
        if best is None or dt > best:
            best = dt
    return best


def load_garmin_status() -> dict[str, Any]:
    """The garmin step from data/status.json (written by scripts/status.py)."""
    try:
        data = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        return dig(data, "steps", "garmin", default={}) or {}
    except (OSError, ValueError):
        return {}


def build_stale_banner(records: list[dict[str, Any]]) -> str:
    """Yellow bar when the newest Garmin sync is older than 24 h."""
    garmin = load_garmin_status()
    candidates = [latest_sync_dt(records)]
    try:
        candidates.append(datetime.strptime(garmin.get("last_success") or "", "%Y-%m-%dT%H:%M:%S"))
    except ValueError:
        pass
    last_ok = max((c for c in candidates if c), default=None)
    if last_ok and datetime.now() - last_ok <= STALE_AFTER:
        return ""

    since = last_ok.strftime("%d.%m") if last_ok else "zawsze"
    if garmin.get("result") == "fail" and garmin.get("message"):
        reason = garmin["message"]
    else:
        reason = "brak udanej synchronizacji (Mac uśpiony lub wyłączony w porach zadań?)"
    fix = garmin.get("fix") or "cd ~/anton_brain && scripts/refresh_all.sh"
    return (
        '<div class="stale-banner" role="alert">'
        f"<b>Dane nieaktualne od {esc(since)}</b>, powód: {esc(reason)}"
        f'<br><span class="fix">Naprawa: <code>{esc(fix)}</code></span>'
        "</div>"
    )


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
    if not TARGETS_PATH.exists():
        return None
    try:
        data = json.loads(TARGETS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


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


def macro_statuses(
    rec: dict[str, Any] | None, bands: dict[str, dict[str, tuple[float, float]]]
) -> dict[str, str | None]:
    return {k: band_status((rec or {}).get(k), bands[k]) for k in NUTRITION_MACROS}


def rate_day(
    rec: dict[str, Any] | None, bands: dict[str, dict[str, tuple[float, float]]] = NUTRITION_BANDS
) -> str | None:
    """Day rating from one food record; None when any macro is missing.

    bad:  kcal or protein red, or two or more reds overall.
    good: kcal and protein green, at most one yellow among fat/carbs, no red.
    mid:  everything else (e.g. two yellows or one red among fat/carbs, or a
          yellow kcal/protein).
    """
    s = macro_statuses(rec, bands)
    if any(v is None for v in s.values()):
        return None
    if s["kcal"] == "bad" or s["protein"] == "bad" or list(s.values()).count("bad") >= 2:
        return "bad"
    side = [s["fat"], s["carbs"]]
    if s["kcal"] == "good" and s["protein"] == "good" and "bad" not in side and side.count("mid") <= 1:
        return "good"
    return "mid"


def rate_week(
    food_by_date: dict[str, dict[str, Any]],
    end: date,
    bands: dict[str, dict[str, tuple[float, float]]] = NUTRITION_BANDS,
    days: int = NUTRITION_WEEK_DAYS,
) -> dict[str, Any]:
    """Rates the `days` calendar days ending at `end` (inclusive) by average
    kcal over the days that have it. Days without a food file count as
    "no data", never as bad."""
    window = [end - timedelta(days=i) for i in range(days - 1, -1, -1)]
    per_day = [(d, rate_day(food_by_date.get(d.isoformat()), bands)) for d in window]
    kcals = [
        k for d in window
        if isinstance(k := (food_by_date.get(d.isoformat()) or {}).get("kcal"), (int, float))
    ]
    avg = sum(kcals) / len(kcals) if kcals else None
    counts = {"good": 0, "mid": 0, "bad": 0, None: 0}
    for _, r in per_day:
        counts[r] += 1
    return {
        "days": per_day,
        "avg_kcal": avg,
        "kcal_days": len(kcals),
        "status": band_status(avg, bands["week_kcal"]),
        "counts": counts,
    }


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


def fmt_generated_at() -> str:
    return fmt_dt_pl(datetime.now())


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


# --------------------------------------------------------------------------
# SVG chart builders
# --------------------------------------------------------------------------

CHART_W = 320
CHART_H = 100
# PAD_L gives the widest expected Y-axis label ("5000 kcal") enough room to
# the left of the chart's inner area without its text (anchored at
# PAD_L - 8, growing leftward) crossing x=0 and getting clipped.
PAD_L = 50
PAD_R = 14
PAD_T = 10
PAD_B = 18


def _label_indices(n: int) -> list[int]:
    """First/middle/last index only, so an X-axis label is never cut off at
    the tile's right edge and always sits under its own data point."""
    if not n:
        return []
    return sorted({0, (n - 1) // 2, n - 1})


def _scale_points(
    values: list[float | None],
    y_min: float,
    y_max: float,
    x_fracs: list[float] | None = None,
) -> list[tuple[float, float | None]]:
    n = len(values)
    inner_w = CHART_W - PAD_L - PAD_R
    inner_h = CHART_H - PAD_T - PAD_B
    span = (y_max - y_min) or 1.0
    points = []
    for i, v in enumerate(values):
        if x_fracs is not None:
            x = PAD_L + inner_w * x_fracs[i]
        else:
            x = PAD_L + (inner_w * i / (n - 1) if n > 1 else inner_w / 2)
        if v is None:
            points.append((x, None))
        else:
            y = PAD_T + inner_h - ((v - y_min) / span) * inner_h
            points.append((x, y))
    return points


def svg_line_chart(
    labels: list[str],
    values: list[float | None],
    color: str,
    unit: str = "",
    baseline_band: tuple[float, float] | None = None,
    y_fmt: str = "{:.0f}",
    point_titles: list[str] | None = None,
    x_fracs: list[float] | None = None,
    trend: list[float | None] | None = None,
) -> str:
    """x_fracs (0..1 per point) places points by date instead of evenly;
    trend is drawn as a dashed line through the same x positions."""
    non_null = [v for v in values if v is not None]
    if not non_null:
        return '<p class="empty-msg">Brak danych do wykresu.</p>'

    all_vals = list(non_null)
    if baseline_band:
        all_vals.extend(baseline_band)
    if trend:
        all_vals.extend(v for v in trend if v is not None)
    y_min = min(all_vals)
    y_max = max(all_vals)
    if y_min == y_max:
        y_min -= 1
        y_max += 1
    pad = (y_max - y_min) * 0.12
    y_min -= pad
    y_max += pad

    points = _scale_points(values, y_min, y_max, x_fracs)
    inner_w = CHART_W - PAD_L - PAD_R

    # Dimensions are set as SVG attributes (width/height/viewBox), not CSS,
    # so the chart still renders at the right size even where the host
    # strips or ignores stylesheet rules (e.g. Obsidian's Balanced mode).
    parts: list[str] = [
        f'<svg width="100%" height="{CHART_H}" viewBox="0 0 {CHART_W} {CHART_H}" '
        f'preserveAspectRatio="xMidYMid meet" class="chart" role="img" '
        f'aria-label="Wykres liniowy">'
    ]

    for frac in (0.0, 0.5, 1.0):
        gy = PAD_T + (CHART_H - PAD_T - PAD_B) * (1 - frac)
        gv = y_min + (y_max - y_min) * frac
        parts.append(
            f'<line x1="{PAD_L}" y1="{gy:.1f}" x2="{CHART_W - PAD_R}" y2="{gy:.1f}" '
            f'stroke-width="1" class="grid-line" />'
        )
        parts.append(
            f'<text x="{PAD_L - 8}" y="{gy + 3:.1f}" font-size="9" class="axis-label" text-anchor="end">'
            f'{y_fmt.format(gv)}{unit}</text>'
        )

    if baseline_band:
        lo, hi = baseline_band
        for v in (lo, hi):
            by = PAD_T + (CHART_H - PAD_T - PAD_B) * (1 - (v - y_min) / (y_max - y_min))
            parts.append(
                f'<line x1="{PAD_L}" y1="{by:.1f}" x2="{CHART_W - PAD_R}" y2="{by:.1f}" '
                f'stroke-width="1.2" stroke-dasharray="3 3" opacity="0.6" '
                f'class="baseline-line" style="stroke:{color}" />'
            )

    if trend:
        trend_pts = [
            f"{x:.1f},{y:.1f}"
            for x, y in _scale_points(trend, y_min, y_max, x_fracs) if y is not None
        ]
        if len(trend_pts) > 1:
            parts.append(
                f'<polyline points="{" ".join(trend_pts)}" fill="none" class="trend-line" '
                f'stroke-width="1.5" stroke-dasharray="4 3" />'
            )

    # No stroke-linecap="round" here on purpose: a round cap draws a small
    # protruding tail past the first/last vertex in the direction of travel,
    # which reads as a stray line segment beyond the last real data point.
    segment: list[str] = []
    for x, y in points:
        if y is None:
            if len(segment) > 1:
                parts.append(
                    f'<polyline points="{" ".join(segment)}" fill="none" '
                    f'stroke="{color}" stroke-width="2.5" stroke-linejoin="round" />'
                )
            segment = []
        else:
            segment.append(f"{x:.1f},{y:.1f}")
    if len(segment) > 1:
        parts.append(
            f'<polyline points="{" ".join(segment)}" fill="none" '
            f'stroke="{color}" stroke-width="2.5" stroke-linejoin="round" />'
        )

    for i, (x, y) in enumerate(points):
        if y is not None:
            # Optional hover text per point (e.g. "12.10: 80 kg × 6").
            title = f"<title>{esc(point_titles[i])}</title>" if point_titles else ""
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}">{title}</circle>')

    for i in _label_indices(len(labels)):
        x = points[i][0]
        parts.append(
            f'<text x="{x:.1f}" y="{CHART_H - 4}" font-size="9" class="axis-label" text-anchor="middle">'
            f"{esc(labels[i])}</text>"
        )

    parts.append("</svg>")
    return "".join(parts)


# Extra scale headroom above the top gridline value (a round number, computed
# by nice_axis_top), so the tallest possible bar - and its value label -
# never touch the very top of the chart canvas.
GRID_TOP_HEADROOM = 1.12

# Value-label sizing, in the 320-unit chart viewBox (renders close to the
# ~10px the labels are meant to look like once scaled to the tile's actual
# width). Used only to decide whether adjacent labels would overlap.
BAR_LABEL_FONT_SIZE = 9
BAR_LABEL_CHAR_W = 5.3
BAR_LABEL_MIN_GAP = 4
# Minimum vertical clearance a value label needs from the dashed target
# line - below this, a bar whose value sits close to the target would
# otherwise print its label right through the dashes.
BAR_LABEL_TARGET_GAP = 8
# Status glyph (✓ / ! / ✕) drawn inside the bar near its base; bars shorter
# than BAR_GLYPH_MIN_H get it just above their top instead.
BAR_GLYPH_FONT_SIZE = 8
BAR_GLYPH_MIN_H = 12


def nice_axis_top(values: list[float | None], target: float | None, step: float) -> float:
    """Smallest multiple of 2*step at or above the larger of the data max and
    the target, so the axis top - and its midpoint - are both round numbers
    instead of whatever the data happened to max out at."""
    candidates = [v for v in values if v is not None]
    raw = max(candidates) if candidates else 0.0
    if target:
        raw = max(raw, float(target))
    unit = step * 2
    if raw <= 0:
        return unit
    top = math.ceil(raw / unit) * unit
    return top if top > 0 else unit


def svg_bar_chart(
    labels: list[str],
    values: list[float | None],
    color: str,
    unit: str = "",
    y_fmt: str = "{:.0f}",
    target: float | None = None,
    y_top: float | None = None,
    statuses: list[str | None] | None = None,
) -> str:
    """With `statuses` (one NUTRITION_STATUS key per value), each bar is
    colored by its status and carries the status glyph, every bar gets a
    hover tooltip, and days without data get a neutral "brak danych" mark."""
    non_null_idx = [i for i, v in enumerate(values) if v is not None]
    if not non_null_idx:
        return '<p class="empty-msg">Brak danych do wykresu.</p>'

    non_null = [values[i] for i in non_null_idx]
    all_vals = list(non_null) + ([target] if target is not None else [])
    top = y_top if y_top is not None else (max(all_vals) * 1.15 or 1.0)
    scale_max = top * GRID_TOP_HEADROOM if y_top is not None else top
    n = len(values)
    inner_w = CHART_W - PAD_L - PAD_R
    inner_h = CHART_H - PAD_T - PAD_B
    slot_w = inner_w / n
    bar_w = slot_w * 0.6

    parts = [
        f'<svg width="100%" height="{CHART_H}" viewBox="0 0 {CHART_W} {CHART_H}" '
        f'preserveAspectRatio="xMidYMid meet" class="chart" role="img" '
        f'aria-label="Wykres słupkowy">'
    ]

    for frac in (0.0, 0.5, 1.0):
        gv = top * frac
        gy = PAD_T + inner_h * (1 - gv / scale_max)
        parts.append(
            f'<line x1="{PAD_L}" y1="{gy:.1f}" x2="{CHART_W - PAD_R}" y2="{gy:.1f}" '
            f'stroke-width="1" class="grid-line" />'
        )
        parts.append(
            f'<text x="{PAD_L - 8}" y="{gy + 3:.1f}" font-size="9" class="axis-label" text-anchor="end">'
            f'{y_fmt.format(gv)}{unit}</text>'
        )

    # Value labels: one per bar when the tile is wide enough for every label
    # to fit without touching its neighbor; otherwise only the most recent
    # day with data, stepping back every 2nd/3rd day (however many slots a
    # label actually needs) so they stay legible instead of overlapping.
    max_text_len = max(len(f"{v:.0f}") for v in non_null)
    label_w_est = max_text_len * BAR_LABEL_CHAR_W + BAR_LABEL_MIN_GAP
    if slot_w >= label_w_est:
        value_label_idx = set(non_null_idx)
    else:
        step_k = max(1, math.ceil(label_w_est / slot_w))
        value_label_idx = set()
        idx = non_null_idx[-1]
        while idx >= 0:
            if values[idx] is not None:
                value_label_idx.add(idx)
            idx -= step_k

    # Drawn before the bars/labels so a bar that crosses it paints over it
    # cleanly; value labels are also kept clear of it below (BAR_LABEL_TARGET_GAP).
    ty: float | None = None
    if target is not None and scale_max:
        ty = PAD_T + inner_h - (target / scale_max) * inner_h
        parts.append(
            f'<line x1="{PAD_L}" y1="{ty:.1f}" x2="{CHART_W - PAD_R}" y2="{ty:.1f}" '
            f'stroke-width="1.5" stroke-dasharray="4 3" class="target-line" />'
        )

    label_idx_set = set(_label_indices(n))
    for i, v in enumerate(values):
        x = PAD_L + slot_w * i + (slot_w - bar_w) / 2
        status = statuses[i] if statuses else None
        if v is not None:
            bar_h = (v / scale_max) * inner_h if scale_max else 0
            y = PAD_T + inner_h - bar_h
            glyph_above = False
            if status in NUTRITION_STATUS:
                glyph, word = NUTRITION_STATUS[status]
                parts.append(
                    f'<g class="bar-st"><title>{esc(labels[i])}: {v:.0f}{esc(unit)} · {glyph} {word}</title>'
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" '
                    f'rx="2" fill="var(--st-{status})" />'
                )
                glyph_above = bar_h < BAR_GLYPH_MIN_H
                if glyph_above:
                    gy, gcls = y - 3, f"st-text-{status}"
                else:
                    gy, gcls = PAD_T + inner_h - 3, "bar-glyph"
                parts.append(
                    f'<text x="{x + bar_w / 2:.1f}" y="{gy:.1f}" font-size="{BAR_GLYPH_FONT_SIZE}" '
                    f'font-weight="700" class="{gcls}" text-anchor="middle">{glyph}</text></g>'
                )
            else:
                parts.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" '
                    f'rx="2" fill="{color}" />'
                )
            if i in value_label_idx:
                label_y = y - 4 - (BAR_GLYPH_FONT_SIZE if glyph_above else 0)
                if ty is not None and abs(label_y - ty) < BAR_LABEL_TARGET_GAP:
                    # Always resolve the collision by moving above the line, never
                    # below it: at this chart scale the gap between the target line
                    # and a bar close enough to collide is only ever a few px - not
                    # enough to fit a label between them without it touching one
                    # side or the other. Above is always safe: GRID_TOP_HEADROOM
                    # guarantees room between the line and the chart's top edge.
                    label_y = ty - BAR_LABEL_TARGET_GAP
                parts.append(
                    f'<text x="{x + bar_w / 2:.1f}" y="{label_y:.1f}" font-size="{BAR_LABEL_FONT_SIZE}" '
                    f'class="axis-label" text-anchor="middle">{v:.0f}</text>'
                )
        elif statuses is not None:
            parts.append(
                f'<g><title>{esc(labels[i])}: brak danych</title>'
                f'<line x1="{x + 1:.1f}" y1="{PAD_T + inner_h - 1:.1f}" x2="{x + bar_w - 1:.1f}" '
                f'y2="{PAD_T + inner_h - 1:.1f}" stroke-width="2" stroke-dasharray="2 2" class="bar-missing" />'
                f'</g>'
            )
        if i in label_idx_set:
            parts.append(
                f'<text x="{x + bar_w / 2:.1f}" y="{CHART_H - 4}" font-size="9" class="axis-label" '
                f'text-anchor="middle">{esc(labels[i])}</text>'
            )

    parts.append("</svg>")
    return "".join(parts)


def svg_phase_bar(deep: Any, light: Any, rem: Any, awake: Any) -> str:
    segments = [
        ("Głęboki", deep, "var(--c-deep)"),
        ("Lekki", light, "var(--c-light)"),
        ("REM", rem, "var(--c-rem)"),
        ("Wybudzenia", awake, "var(--c-awake)"),
    ]
    total = sum(v for _, v, _ in segments if isinstance(v, (int, float)) and v > 0)

    if not total:
        return '<p class="empty-msg">Brak danych o fazach snu.</p>'

    # Widths are percentages of a 0-100 viewBox, computed once here and
    # reused for both the rects and the legend below, so a rendering bug
    # can't make them diverge - they are, by construction, the same numbers.
    widths: dict[str, float] = {}
    for name, v, _ in segments:
        widths[name] = (v / total * 100) if isinstance(v, (int, float)) and v > 0 else 0.0

    total_width = sum(widths.values())
    assert abs(total_width - 100) < 0.01, (
        f"svg_phase_bar: segment widths sum to {total_width}, expected 100"
    )
    for name, v, _ in segments:
        if isinstance(v, (int, float)) and v > 0:
            assert widths[name] > 0, f"svg_phase_bar: {name} has a value but zero width"

    # width/height are explicit attributes (not CSS) so the bar still scales
    # correctly if the host strips stylesheet rules.
    rects = []
    x = 0.0
    for name, v, color in segments:
        w = widths[name]
        if w > 0:
            rects.append(f'<rect x="{x:.3f}" y="0" width="{w:.3f}" height="10" fill="{color}" />')
        x += w
    svg = (
        '<svg width="100%" height="14" viewBox="0 0 100 10" preserveAspectRatio="none" '
        'class="phase-bar" role="img" aria-label="Fazy snu">' + "".join(rects) + "</svg>"
    )

    legend_items = []
    for name, v, color in segments:
        pct = f"{widths[name]:.0f}%"
        legend_items.append(
            f'<span class="legend-item"><i style="background:{color}"></i>{esc(name)} '
            f'<b>{fmt_hms(v) if isinstance(v, (int, float)) else "brak danych"}</b> '
            f'<span class="dim">({pct})</span></span>'
        )
    legend = f'<div class="legend">{"".join(legend_items)}</div>'
    return svg + legend


def svg_ring(score: Any, color: str, diameter: int = 110, stroke: int = 10) -> str:
    if score is None:
        return '<p class="empty-msg">Brak danych.</p>'
    # viewBox is padded beyond the stroke's outer edge so the arc and the
    # centered score text never get clipped by the SVG's own bounds.
    margin = 6
    size = diameter + margin * 2
    r = (diameter - stroke) / 2
    cx = cy = size / 2
    circumference = 2 * 3.14159265 * r
    frac = max(0.0, min(1.0, score / 100))
    dash = circumference * frac
    # width/height/viewBox as attributes (not CSS) so the ring keeps its
    # size even if the host strips stylesheet rules. The score text uses
    # text-anchor="middle" + dy=".35em" rather than dominant-baseline, which
    # some SVG renderers (older/embedded engines) center inconsistently or
    # not at all - dy-based centering is the more universally reliable trick.
    return f'''<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" class="ring" role="img" aria-label="Pierścień gotowości">
<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="var(--border)" stroke-width="{stroke}" />
<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="{stroke}"
  stroke-linecap="round" stroke-dasharray="{dash:.1f} {circumference:.1f}"
  transform="rotate(-90 {cx} {cy})" />
<text x="{cx}" y="{cy}" text-anchor="middle" dy=".35em" font-size="30" font-weight="700" class="ring-score">{int(score)}</text>
</svg>'''


def factor_bar_color(pct: float) -> str:
    if pct >= 80:
        return "#4fb477"
    if pct >= 60:
        return "#e3ad4c"
    return "#d9694f"


def factor_bars_html(factors: dict[str, Any]) -> str:
    present = [(k, factors.get(k)) for k in FACTOR_ORDER if factors.get(k) is not None]
    if not present:
        return '<div class="factor-bars empty-fill"><p class="empty-msg">Brak danych o składowych.</p></div>'

    rows = []
    for key, value in present:
        color = factor_bar_color(value)
        rows.append(
            f'<div class="factor-row">'
            f'<span class="factor-label">{esc(FACTOR_LABELS_PL[key])}</span>'
            f'<span class="factor-track"><span class="factor-fill" '
            f'style="width:{max(0, min(100, value)):.0f}%;background:{color}"></span></span>'
            f'<span class="factor-value">{int(value)}%</span>'
            f"</div>"
        )
    return f'<div class="factor-bars">{"".join(rows)}</div>'


def build_readiness_description(score: Any, level: Any, factors: dict[str, Any]) -> str:
    if score is None:
        return ""
    present = {k: v for k, v in factors.items() if v is not None}
    sentence1 = LEVEL_PHRASES_PL.get(level, f"Gotowość na dziś wynosi {int(score)}/100.")
    if not present:
        return sentence1

    worst_key = min(present, key=present.get)
    worst_val = present[worst_key]
    best_key = max(present, key=present.get)
    best_val = present[best_key]

    if worst_val < 70 and worst_key != best_key:
        sentence2 = (
            f"Najbardziej obniża ją {FACTOR_LABELS_PL[worst_key].lower()} ({worst_val:.0f}%), "
            f"a najlepiej wygląda {FACTOR_LABELS_PL[best_key].lower()} ({best_val:.0f}%)."
        )
    elif worst_val < 70:
        sentence2 = f"Najbardziej obniża ją {FACTOR_LABELS_PL[worst_key].lower()} ({worst_val:.0f}%)."
    else:
        sentence2 = "Wszystkie mierzone składowe są w dobrym zakresie."

    return f"{sentence1} {sentence2}"


def status_value_html(text: str, status: str | None) -> str:
    """A value with its status glyph, colored by status (plain when None)."""
    if status not in NUTRITION_STATUS:
        return text
    glyph, word = NUTRITION_STATUS[status]
    return (
        f'<span class="st-text-{status}" title="{word}">'
        f'<span class="st-glyph" aria-hidden="true">{glyph}</span>{text}'
        f'<span class="sr-only"> ({word})</span></span>'
    )


def status_badge_html(status: str | None, labels: dict[str, str], empty_label: str) -> str:
    if status not in NUTRITION_STATUS:
        return f'<span class="st-badge st-badge-none">{esc(empty_label)}</span>'
    glyph = NUTRITION_STATUS[status][0]
    return (
        f'<span class="st-badge st-badge-{status}">'
        f'<span aria-hidden="true">{glyph}</span> {esc(labels[status])}</span>'
    )


def nutrient_bar_html(
    label: str, value: Any, target: Any, unit: str = "g", status: str | None = None
) -> str:
    value_text = (
        status_value_html(f"{value:.0f}{unit}", status) if value is not None else "brak danych"
    )
    fill_cls = f"nutrient-fill st-fill-{status}" if status in NUTRITION_STATUS else "nutrient-fill"
    if target:
        frac = max(0.0, min(100.0, (value / target) * 100)) if value is not None else 0.0
        return (
            f'<div class="nutrient-row">'
            f'<span class="nutrient-label">{esc(label)}</span>'
            f'<span class="nutrient-track"><span class="{fill_cls}" '
            f'style="width:{frac:.0f}%"></span></span>'
            f'<span class="nutrient-value">{value_text} <span class="dim">/ {target:.0f}{unit}</span></span>'
            f"</div>"
        )
    return (
        f'<div class="nutrient-row">'
        f'<span class="nutrient-label">{esc(label)}</span>'
        f'<span class="nutrient-value nutrient-value-wide">{value_text}</span>'
        f"</div>"
    )


# --------------------------------------------------------------------------
# Tile builders
# --------------------------------------------------------------------------

def build_readiness_tile(records: list[dict[str, Any]]) -> str:
    with_tr = [r for r in records if dig(r, "training_readiness", "score") is not None]
    if not with_tr:
        return _card(
            "Gotowość (Training Readiness)",
            '<div class="empty-fill"><p class="empty-msg">Brak danych Training Readiness.</p></div>',
        )

    latest = with_tr[-1]
    tr = latest.get("training_readiness") or {}
    score = tr.get("score")
    level = tr.get("level")
    factors = tr.get("factors") or {}
    color = READINESS_COLORS.get(level, READINESS_DEFAULT_COLOR)

    ring = svg_ring(score, color)
    level_pl = pl_word(READINESS_LEVEL_PL, level)
    bars = factor_bars_html(factors)
    description = esc(build_readiness_description(score, level, factors))

    body = f'''
<div class="readiness-row">
  <div class="ring-col">
    {ring}
    <div class="ring-level">{esc(level_pl)}</div>
    <div class="dim">{fmt_short_date(latest["_date"])}</div>
  </div>
  {bars}
</div>
<p class="tile-desc">{description}</p>
'''
    return _card("Gotowość (Training Readiness)", body)


def build_steps_tile(records: list[dict[str, Any]]) -> str:
    by_date = {r["_date"]: r.get("steps") for r in records}
    days = last_n_calendar_days(TREND_DAYS)
    labels = [fmt_short_date(d) for d in days]
    values = [by_date.get(d) for d in days]

    # Today is still in progress, so the headline is yesterday's full day.
    yesterday = values[-2] if len(values) > 1 else None
    known = [v for v in values[:-1] if v is not None]
    avg = sum(known) / len(known) if known else None
    value_text = (
        f"{yesterday:,.0f}".replace(",", " ") + '<span class="stat-unit">wczoraj</span>'
        if yesterday is not None else "brak danych"
    )
    sub_text = (
        f"średnio {avg:,.0f} / dzień (pełne dni)".replace(",", " ") if avg is not None else "&nbsp;"
    )

    if not any(v is not None for v in values):
        chart = '<p class="empty-msg">Brak danych do wykresu.</p>'
    else:
        chart = svg_bar_chart(
            labels, values, "var(--c-neutral)", y_top=nice_axis_top(values, None, 2500)
        )
    body = f'''
<div class="stat-row">
  <div class="stat-big">{value_text}</div>
  <div class="stat-sub">{sub_text}</div>
</div>
<div class="chart-wrap">{chart}</div>
'''
    return _card("Kroki — ostatnie 14 dni", body)


def build_rhr_tile(records: list[dict[str, Any]]) -> str:
    trend = records[-TREND_DAYS:]
    labels = [fmt_short_date(r["_date"]) for r in trend]
    values = [r.get("resting_heart_rate") for r in trend]

    latest = next((v for v in reversed(values) if v is not None), None)
    value_text = f'{int(latest)}<span class="stat-unit">bpm</span>' if latest is not None else "brak danych"

    chart = svg_line_chart(labels, values, "var(--c-rhr)", unit=" bpm")
    body = f'''
<div class="stat-row">
  <div class="stat-big">{value_text}</div>
  <div class="stat-sub">&nbsp;</div>
</div>
<div class="chart-wrap">{chart}</div>
'''
    return _card("Tętno spoczynkowe — ostatnie 14 nocy", body)


def build_sleep_tile(records: list[dict[str, Any]]) -> str:
    with_sleep = [r for r in records if dig(r, "sleep", "total_seconds") is not None]
    if not with_sleep:
        return _card(
            "Sen — ostatnia noc",
            '<div class="empty-fill"><p class="empty-msg">Brak danych o śnie.</p></div>',
        )

    r = with_sleep[-1]
    sleep = r.get("sleep") or {}
    d: date = r["_date"]

    total = fmt_hms(sleep.get("total_seconds"))
    start_txt = fmt_local_time(sleep.get("start_local_ms"))
    end_txt = fmt_local_time(sleep.get("end_local_ms"))
    times_text = f"{start_txt} &ndash; {end_txt}" if start_txt and end_txt else "brak danych"

    score = sleep.get("score")
    qualifier = pl_word(SLEEP_QUALIFIER_PL, sleep.get("score_qualifier"))
    score_text = f"{int(score)}/100 &middot; {esc(qualifier)}" if score is not None else "brak danych"

    phase_bar = svg_phase_bar(
        sleep.get("deep_seconds"), sleep.get("light_seconds"),
        sleep.get("rem_seconds"), sleep.get("awake_seconds"),
    )

    body = f'''
<div class="stat-row">
  <div class="stat-big">{total}</div>
  <div class="stat-sub">Zasypianie &ndash; pobudka: <b>{times_text}</b> &middot; Ocena snu: <b>{score_text}</b></div>
</div>
{phase_bar}
'''
    return _card(f"Sen — ostatnia noc ({fmt_short_date(d)})", body)


def build_food_yesterday_tile(
    food_by_date: dict[str, dict[str, Any]],
    targets: dict[str, Any] | None,
    bands: dict[str, dict[str, tuple[float, float]]],
) -> str:
    y = date.today() - timedelta(days=1)
    rec = food_by_date.get(y.isoformat())
    if not rec:
        return _card(
            "Wczoraj: paliwo",
            '<div class="empty-fill"><p class="empty-msg">Wyślij /dzien do bota.</p></div>',
        )

    kcal = rec.get("kcal")
    kcal_target = (targets or {}).get("kcal")
    st = macro_statuses(rec, bands)

    kcal_text = (
        status_value_html(f"{kcal:.0f}", st["kcal"]) + '<span class="stat-unit">kcal</span>'
        if kcal is not None
        else "brak danych"
    )
    kcal_sub = f"Cel: {kcal_target:.0f} kcal" if kcal_target else "&nbsp;"
    badge = status_badge_html(rate_day(rec, bands), DAY_RATING_PL, "Niepełne dane")
    bars = "".join(
        nutrient_bar_html(label, rec.get(key), (targets or {}).get(key), status=st[key])
        for label, key in (("Białko", "protein"), ("Węgle", "carbs"), ("Tłuszcz", "fat"))
    )

    body = f'''
<div class="stat-row stat-row-split">
  <div>
    <div class="stat-big">{kcal_text}</div>
    <div class="stat-sub">{kcal_sub}</div>
  </div>
  {badge}
</div>
<div class="nutrient-bars-wrap"><div class="nutrient-bars">{bars}</div></div>
'''
    return _card(f"Wczoraj: paliwo ({fmt_short_date(y)})", body)


def build_weight_tile(weight_entries: list[dict[str, Any]]) -> str:
    if not weight_entries:
        return _card(
            "Waga",
            '<div class="empty-fill"><p class="empty-msg">Wyślij /waga do bota.</p></div>',
        )

    latest = weight_entries[-1]
    latest_kg = latest.get("kg")
    latest_date_str = latest.get("date")

    change_text = ""
    try:
        latest_d = date.fromisoformat(latest_date_str)
        cutoff = latest_d - timedelta(days=7)
        prior = [
            e for e in weight_entries
            if e.get("date") and date.fromisoformat(e["date"]) <= cutoff
        ]
        if prior and latest_kg is not None and prior[-1].get("kg") is not None:
            diff = latest_kg - prior[-1]["kg"]
            sign = "+" if diff > 0 else ""
            change_text = f"{sign}{diff:.1f} kg / 7 dni"
    except (ValueError, TypeError):
        change_text = ""

    trend = weight_entries[-30:]
    labels = []
    values = []
    for e in trend:
        try:
            labels.append(fmt_short_date(date.fromisoformat(e["date"])))
        except (ValueError, TypeError, KeyError):
            labels.append("")
        values.append(e.get("kg"))

    chart = svg_line_chart(
        labels, values, "var(--c-neutral)", unit=" kg", y_fmt="{:.1f}"
    )

    kg_text = f'{latest_kg:.1f}<span class="stat-unit">kg</span>' if latest_kg is not None else "brak danych"
    title_date = fmt_short_date(date.fromisoformat(latest_date_str)) if latest_date_str else ""
    change_sub = esc(change_text) if change_text else "Brak danych sprzed 7 dni"

    body = f'''
<div class="stat-row">
  <div class="stat-big">{kg_text}</div>
  <div class="stat-sub">{change_sub}</div>
</div>
<div class="chart-wrap">{chart}</div>
'''
    return _card(f"Waga ({title_date})" if title_date else "Waga", body)


def build_nutrition_trend_cards(
    food_by_date: dict[str, dict[str, Any]],
    targets: dict[str, Any] | None,
    bands: dict[str, dict[str, tuple[float, float]]],
) -> tuple[str, str]:
    """(kcal + protein cards, carbs + fat cards) - split so the weekly tile
    and the legend can sit at the start / end of the two nutrition rows."""
    days14 = last_n_calendar_days(TREND_DAYS)
    labels = [fmt_short_date(d) for d in days14]

    def series(key: str) -> list[float | None]:
        return [(food_by_date.get(d.isoformat()) or {}).get(key) for d in days14]

    def bar_tile(title: str, key: str, unit: str, step: float) -> str:
        values = series(key)
        if not any(v is not None for v in values):
            return _card(title, '<div class="empty-fill"><p class="empty-msg">Brak danych.</p></div>')
        target = (targets or {}).get(key)
        top = nice_axis_top(values, target, step)
        statuses = [band_status(v, bands[key]) for v in values]
        chart = svg_bar_chart(
            labels, values, "var(--c-neutral)", unit=unit, target=target, y_top=top, statuses=statuses
        )
        return _card(title, f'<div class="chart-wrap">{chart}</div>')

    first = bar_tile("Kalorie — ostatnie 14 dni", "kcal", " kcal", step=500) + bar_tile(
        "Białko — ostatnie 14 dni", "protein", " g", step=50
    )
    second = bar_tile("Węgle — ostatnie 14 dni", "carbs", " g", step=50) + bar_tile(
        "Tłuszcz — ostatnie 14 dni", "fat", " g", step=25
    )
    return first, second


def build_nutrition_week_tile(
    food_by_date: dict[str, dict[str, Any]], bands: dict[str, dict[str, tuple[float, float]]]
) -> str:
    end = date.today() - timedelta(days=1)
    week = rate_week(food_by_date, end, bands)
    title = f"Odżywianie — ostatnie {NUTRITION_WEEK_DAYS} dni"
    if week["avg_kcal"] is None:
        return _card(
            title, '<div class="empty-fill"><p class="empty-msg">Brak danych z ostatnich 7 dni.</p></div>'
        )

    g_lo, g_hi = bands["week_kcal"]["green"]
    avg_text = status_value_html(f"{week['avg_kcal']:.0f}", week["status"])
    badge = status_badge_html(week["status"], WEEK_RATING_PL, "Brak danych")

    chips = []
    for d, rating in week["days"]:
        if rating in NUTRITION_STATUS:
            glyph, cls, word = NUTRITION_STATUS[rating][0], rating, DAY_RATING_PL[rating]
        else:
            has_file = d.isoformat() in food_by_date
            glyph, cls, word = "–", "none", "niepełne dane" if has_file else "brak danych"
        chips.append(
            f'<li class="day-chip day-chip-{cls}" title="{fmt_short_date(d)}: {esc(word)}">'
            f'<span class="day-chip-glyph" aria-hidden="true">{glyph}</span>'
            f'<span class="day-chip-date">{fmt_short_date(d)}</span>'
            f'<span class="sr-only">{esc(word)}</span></li>'
        )

    c = week["counts"]
    counts = (
        f'<span class="st-text-good">✓ dobre: <b>{c["good"]}</b></span>'
        f'<span class="st-text-mid">! średnie: <b>{c["mid"]}</b></span>'
        f'<span class="st-text-bad">✕ złe: <b>{c["bad"]}</b></span>'
    )
    if c[None]:
        counts += f'<span class="dim">– brak danych: <b>{c[None]}</b></span>'

    body = f'''
<div class="stat-row stat-row-split">
  <div>
    <div class="stat-big">{avg_text}<span class="stat-unit">kcal / dzień</span></div>
    <div class="stat-sub">Średnia z {week["kcal_days"]} dni &middot; <span class="nowrap">norma {g_lo:.0f}–{g_hi:.0f}</span></div>
  </div>
  {badge}
</div>
<ul class="day-chips">{"".join(chips)}</ul>
<div class="day-counts">{counts}</div>
'''
    return _card(title, body)


def _band_ranges_text(band: dict[str, tuple[float, float]], unit: str) -> tuple[str, str, str]:
    """(green, yellow, red) ranges as text, e.g. yellow "2350–2479 · 2741–2870"."""
    (g_lo, g_hi), (y_lo, y_hi) = band["green"], band["yellow"]
    whole = all(float(x).is_integer() for x in (g_lo, g_hi, y_lo, y_hi))
    step = 1 if whole else 0

    def f(x: float) -> str:
        return f"{x:.0f}" if whole else f"{x:g}"

    yellow = []
    if y_lo < g_lo:
        yellow.append(f"{f(y_lo)}–{f(g_lo - step)}")
    if g_hi < y_hi:
        yellow.append(f"{f(g_hi + step)}–{f(y_hi)}")
    return (
        f"{f(g_lo)}–{f(g_hi)}{unit}",
        "<br>".join(f"{y}{unit}" for y in yellow) or "—",
        f"&lt; {f(y_lo)} · &gt; {f(y_hi)}{unit}",
    )


def build_nutrition_legend_tile(bands: dict[str, dict[str, tuple[float, float]]]) -> str:
    rows = []
    for label, key, unit in (
        ("Kalorie", "kcal", ""),
        ("Białko", "protein", " g"),
        ("Węgle", "carbs", " g"),
        ("Tłuszcz", "fat", " g"),
        ("Średnia 7 dni", "week_kcal", ""),
    ):
        green, yellow, red = _band_ranges_text(bands[key], unit)
        rows.append(
            f'<tr><th scope="row">{label}</th><td>{green}</td><td>{yellow}</td><td>{red}</td></tr>'
        )
    body = f'''
<table class="band-table">
  <thead><tr><th></th><th class="st-text-good">✓ w normie</th><th class="st-text-mid">! blisko</th><th class="st-text-bad">✕ poza</th></tr></thead>
  <tbody>{"".join(rows)}</tbody>
</table>
<details class="band-rules">
  <summary>Jak liczona jest ocena dnia</summary>
  <p><b class="st-text-good">✓ Dobry</b>: kalorie i białko w normie, w tłuszczu i węglach najwyżej jedno „blisko”.</p>
  <p><b class="st-text-mid">! Średni</b>: kalorie i białko nie poza zakresem, a w tłuszczu i węglach dwa „blisko” albo jedno „poza” (też: kalorie lub białko „blisko”).</p>
  <p><b class="st-text-bad">✕ Zły</b>: kalorie lub białko poza zakresem albo dwa i więcej makro poza zakresem.</p>
  <p class="dim">Tydzień: średnia kcal z dni z danymi (bez dzisiaj). Dni bez wpisu /dzien są pomijane, nie liczą się jako złe. Progi: NUTRITION_BANDS w scripts/build_dashboard.py lub klucz "bands" w data/targets.json.</p>
</details>
'''
    return _card("Progi odżywiania", body)


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _thousands(v: float) -> str:
    return f"{v:,.0f}".replace(",", " ")


def build_workouts_per_week_tile(workouts: list[ta.Workout]) -> str:
    this_week = _week_start(date.today())
    weeks = [this_week - timedelta(weeks=i) for i in range(TRAINING_WEEKS - 1, -1, -1)]
    counts = {wk: 0 for wk in weeks}
    for w in workouts:
        wk = _week_start(w.day)
        if wk in counts:
            counts[wk] += 1
    values = [float(counts[wk]) for wk in weeks]
    prev_weeks = values[-1 - VOLUME_BASELINE_WINDOWS:-1]
    avg = sum(prev_weeks) / len(prev_weeks) if prev_weeks else 0.0

    chart = svg_bar_chart(
        [fmt_short_date(wk) for wk in weeks], values, "var(--c-neutral)",
        y_top=nice_axis_top(values, None, 1),
    )
    body = f'''
<div class="stat-row">
  <div class="stat-big">{int(values[-1])}<span class="stat-unit">w tym tygodniu</span></div>
  <div class="stat-sub">średnio {avg:.1f} / tydzień (4 poprzednie tygodnie)</div>
</div>
<div class="chart-wrap">{chart}</div>
'''
    return _card(f"Treningi w tygodniu — {TRAINING_WEEKS} tygodni", body)


def _muscle_volume(workouts: list[ta.Workout], start: date, end: date) -> dict[str, float]:
    """Volume (kg) per primary muscle group for start <= day <= end."""
    volume: dict[str, float] = {}
    for w in workouts:
        if start <= w.day <= end:
            for ex in w.exercises:
                volume[ex.muscle] = volume.get(ex.muscle, 0.0) + ex.volume
    return volume


def _muscle_bars_html(current: dict[str, float], baseline: dict[str, float], unit: str) -> str:
    groups = sorted(
        {m for m, v in current.items() if v} | {m for m, v in baseline.items() if v},
        key=lambda m: (-current.get(m, 0), -baseline.get(m, 0)),
    )[:10]
    if not groups:
        return '<div class="empty-fill"><p class="empty-msg">Brak serii w tym okresie.</p></div>'
    top = max(max(current.get(m, 0), baseline.get(m, 0)) for m in groups) or 1
    rows = []
    for m in groups:
        cur = current.get(m, 0)
        base = baseline.get(m, 0)
        tick = (
            f'<span class="mg-tick" style="left:{base / top * 100:.1f}%" '
            f'title="średnia: {_thousands(base)}{unit}"></span>'
            if base else ""
        )
        rows.append(
            f'<div class="mg-row">'
            f'<span class="mg-label">{esc(MUSCLE_GROUP_PL.get(m, m))}</span>'
            f'<span class="mg-track"><span class="mg-fill" style="width:{cur / top * 100:.1f}%"></span>{tick}</span>'
            f'<span class="mg-value">{_thousands(cur)}{unit}</span>'
            f"</div>"
        )
    legend = (
        '<div class="legend"><span class="legend-item"><i class="legend-bar"></i>ostatnie 7 dni</span>'
        '<span class="legend-item"><i class="legend-tick"></i>średnia z 4 poprzednich okresów 7-dniowych</span></div>'
    )
    return f'<div class="mg-bars">{"".join(rows)}</div>{legend}'


def build_volume_tile(workouts: list[ta.Workout]) -> str:
    today = date.today()
    cur_start = today - timedelta(days=VOLUME_WINDOW_DAYS - 1)
    cur_vol = _muscle_volume(workouts, cur_start, today)
    base_vol: dict[str, float] = {}
    for i in range(VOLUME_BASELINE_WINDOWS):
        end = cur_start - timedelta(days=VOLUME_WINDOW_DAYS * i + 1)
        for m, v in _muscle_volume(workouts, end - timedelta(days=VOLUME_WINDOW_DAYS - 1), end).items():
            base_vol[m] = base_vol.get(m, 0) + v / VOLUME_BASELINE_WINDOWS
    body = (
        f'<div class="stat-row"><div class="stat-big">{_thousands(sum(cur_vol.values()))}'
        '<span class="stat-unit">kg łącznie</span></div></div>'
        + _muscle_bars_html(cur_vol, base_vol, " kg")
    )
    return _card("Objętość per partia — ostatnie 7 dni", body)


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


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-") or "x"


def _sessions_word(n: int) -> str:
    return f"{n} {ta.plural_pl(n, 'sesja', 'sesje', 'sesji')}"


def _picker(group: str, options: list[tuple[str, str]], aria_label: str) -> str:
    """<select> showing one of the panels with data-panel=group (script at
    the bottom of the page); without scripts every panel stays visible."""
    opts = "".join(f'<option value="{pid}">{esc(label)}</option>' for pid, label in options)
    return (
        f'<div class="picker-row"><select class="picker" data-group="{group}" '
        f'aria-label="{aria_label}">{opts}</select></div>'
    )


def _empty_card(title: str, message: str, extra_class: str = "") -> str:
    return _card(title, f'<div class="empty-fill"><p class="empty-msg">{message}</p></div>', extra_class)


def build_e1rm_tile(workouts: list[ta.Workout]) -> str:
    title = "Szacowany 1RM (Epley)"
    series = {
        ex_id: [s for s in sessions if s.best_e1rm is not None]
        for ex_id, sessions in ta.exercise_history(workouts).items()
    }
    series = {k: v for k, v in series.items() if v}
    if not series:
        return _empty_card(title, "Brak serii z ciężarem.", "card-wide")

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
        trend_text = f"trend od {ta.TREND_MIN_SESSIONS} sesji"
        if len(pts) >= ta.TREND_MIN_SESSIONS:
            fit = ta.linear_trend([(s.day, s.best_e1rm) for s in pts])
            if fit:
                a, b = fit
                trend = [a + b * (s.day - d0).days for s in pts]
                trend_text = f"trend <b>{_fmt_delta(b * 28)} / 4 tyg.</b>"
        best = max(all_pts, key=lambda s: s.best_e1rm)
        titles = [
            f"{fmt_short_date(s.day)}: e1RM {_fmt_kg(s.best_e1rm)} kg ({_fmt_set(s.best_e1rm_set)})"
            for s in pts
        ]
        chart = svg_line_chart(
            [fmt_short_date(s.day) for s in pts], [s.best_e1rm for s in pts], "var(--c-train)",
            unit=" kg", point_titles=titles, x_fracs=x_fracs, trend=trend,
        )
        panels.append(f'''
<div class="picker-panel" data-panel="e1rm" id="{pid}">
<div class="stat-row">
  <div class="stat-big">{_fmt_kg(last.best_e1rm)}<span class="stat-unit">kg e1RM</span></div>
  <div class="stat-sub">{fmt_short_date(last.day)} z {_fmt_set(last.best_e1rm_set)} · najlepiej <b>{_fmt_kg(best.best_e1rm)} kg</b> ({fmt_short_date(best.day)}) · {trend_text}</div>
</div>
<div class="chart-wrap">{chart}</div>
</div>''')
    desc = (
        '<p class="tile-desc">e1RM = ciężar × (1 + powtórzenia / 30), z najlepszej serii roboczej '
        f"w sesji. Przerywana linia: trend liniowy (od {ta.TREND_MIN_SESSIONS} sesji).</p>"
    )
    return _card(title, _picker("e1rm", options, "Ćwiczenie") + "".join(panels) + desc, "card-wide")


def build_relative_strength_tile(
    workouts: list[ta.Workout], bodyweights: list[tuple[date, float]]
) -> str:
    title = "Siła względem masy ciała"
    if not bodyweights:
        return _empty_card(title, "Wyślij /waga do bota, żeby policzyć siłę względną.")
    rows = ta.relative_strength(workouts, bodyweights, date.today())
    if not rows:
        return _empty_card(title, "Brak serii z ciężarem w ostatnich 6 tygodniach przy pomiarze wagi.")
    shown = rows[:REL_STRENGTH_ROWS]
    body_rows = "".join(
        f'<tr title="e1RM {_fmt_kg(r.e1rm)} kg / masa ciała {_fmt_kg(r.bodyweight)} kg ({fmt_short_date(r.day)})">'
        f"<td>{esc(r.name)}</td>"
        f'<td class="num">{r.ratio:.2f}×</td>'
        f'<td class="num dim">{r.best_ratio:.2f}×</td></tr>'
        for r in shown
    )
    more = f" Pokazano {len(shown)} z {len(rows)}." if len(rows) > len(shown) else ""
    body = (
        '<div class="table-wrap"><table class="data-table">'
        '<thead><tr><th>Ćwiczenie</th><th class="num">e1RM / masa</th><th class="num">najlepiej</th></tr></thead>'
        f"<tbody>{body_rows}</tbody></table></div>"
        '<p class="tile-desc">Ostatnia sesja: e1RM ÷ masa ciała z ostatniego pomiaru /waga przed sesją.'
        f"{more}</p>"
    )
    return _card(title, body)


def build_progression_tile(workouts: list[ta.Workout], cfg: ta.Config) -> str:
    title = "Podwójna progresja"
    progs = ta.progressions(workouts, cfg, date.today())
    if not progs:
        return _empty_card(title, "Brak serii z powtórzeniami w ostatnich 6 tygodniach.", "card-full")
    n_raise = sum(p.status == "raise" for p in progs)
    n_stall = sum(p.status == "stall" for p in progs)
    rows = []
    for p in progs:
        label = ta.status_label(p)
        if p.status == "reps" and p.below_range:
            label += " · poniżej widełek"
        lo, hi = p.rep_range
        rows.append(
            f"<tr><td>{esc(p.name)}</td>"
            f'<td class="nowrap">{lo}–{hi}</td>'
            f'<td class="nowrap">{fmt_short_date(p.last.day)}</td>'
            f"<td>{esc(_fmt_sets(p.last.sets))}</td>"
            f'<td><span class="pill pill-{p.status}">{esc(label)}</span></td></tr>'
        )
    lo, hi = cfg.rep_range
    body = f'''
<div class="stat-row">
  <div class="stat-big">{n_raise}<span class="stat-unit">do podniesienia ciężaru</span></div>
  <div class="stat-sub">stagnacja: <b>{n_stall}</b> · dobijanie powtórzeń: <b>{len(progs) - n_raise - n_stall}</b></div>
</div>
<div class="table-wrap"><table class="data-table">
<thead><tr><th>Ćwiczenie</th><th>Widełki</th><th>Ostatnio</th><th>Serie robocze</th><th>Status</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
<p class="tile-desc">Widełki domyślnie {lo}–{hi} powtórzeń (data/hevy_config.json). Podnieś ciężar: każda seria
przy najwyższym ciężarze ma co najmniej górną granicę. Stagnacja: {cfg.stagnation_sessions}+ sesji bez większego
ciężaru, większej liczby powtórzeń przy nim ani nowego e1RM. Ćwiczenia z ostatnich 6 tygodni.</p>
'''
    return _card(title, body, "card-full")


def build_weekly_sets_tile(workouts: list[ta.Workout], cfg: ta.Config) -> str:
    title = "Serie robocze per partia — 7 dni vs cel"
    groups = ta.weekly_muscle_sets(workouts, cfg, date.today())
    if not groups:
        return _empty_card(title, "Brak serii w ostatnich 4 tygodniach.")
    top = max(max(g.target[1], g.sets, g.previous) for g in groups) * 1.05
    rows = []
    for g in groups:
        lo, hi = g.target
        status = {"low": "poniżej zakresu", "ok": "w zakresie", "high": "powyżej zakresu"}[g.status]
        rows.append(
            f'<div class="mg-row mg-row-target" title="{status}; poprzednie 7 dni: {g.previous}">'
            f'<span class="mg-label">{esc(g.label)}</span>'
            f'<span class="mg-track mg-track-target">'
            f'<span class="mg-band" style="left:{lo / top * 100:.1f}%;width:{(hi - lo) / top * 100:.1f}%"></span>'
            f'<span class="mg-fill" style="width:{g.sets / top * 100:.1f}%"></span>'
            + (f'<span class="mg-tick" style="left:{g.previous / top * 100:.1f}%"></span>' if g.previous else "")
            + f'</span><span class="mg-value">{g.sets} <span class="dim">/ {lo}–{hi}</span></span>'
            f"</div>"
        )
    low = [g.label for g in groups if g.status == "low"]
    sub = f"poniżej zakresu: <b>{esc(', '.join(low))}</b>" if low else "wszystkie partie w zakresie lub powyżej"
    legend = (
        '<div class="legend"><span class="legend-item"><i class="legend-bar"></i>ostatnie 7 dni</span>'
        '<span class="legend-item"><i class="legend-band"></i>zakres docelowy</span>'
        '<span class="legend-item"><i class="legend-tick"></i>poprzednie 7 dni</span></div>'
    )
    body = (
        f'<div class="stat-row"><div class="stat-big">{sum(g.sets for g in groups)}'
        f'<span class="stat-unit">serii roboczych</span></div><div class="stat-sub">{sub}</div></div>'
        f'<div class="mg-bars">{"".join(rows)}</div>{legend}'
    )
    return _card(title, body)


def build_records_tile(workouts: list[ta.Workout]) -> str:
    title = "Rekordy"
    recs = ta.records(workouts)
    if not recs:
        return _empty_card(title, "Brak serii z powtórzeniami.", "card-full")
    cutoff = date.today() - timedelta(days=ta.RECENT_RECORD_DAYS - 1)

    def day_cell(d: date | None) -> str:
        if d is None:
            return "—"
        badge = ' <span class="badge">nowy</span>' if d >= cutoff else ""
        return f"{fmt_short_date(d)}{badge}"

    rows = []
    for r in recs:
        e1rm = (
            f"{_fmt_kg(r.best_e1rm_set.e1rm)} kg <span class=\"dim\">({_fmt_set(r.best_e1rm_set)})</span>"
            if r.best_e1rm_set else "—"
        )
        rows.append(
            f"<tr><td>{esc(r.name)}</td>"
            f'<td class="nowrap">{_fmt_set(r.best_set)}</td><td class="nowrap">{day_cell(r.best_set_day)}</td>'
            f'<td class="nowrap">{e1rm}</td><td class="nowrap">{day_cell(r.best_e1rm_day)}</td></tr>'
        )
    recent = sum(1 for r in recs if r.latest_day >= cutoff)
    body = f'''
<div class="stat-row">
  <div class="stat-big">{recent}<span class="stat-unit">{ta.plural_pl(recent, "ćwiczenie", "ćwiczenia", "ćwiczeń")} z rekordem w ostatnich 4 tygodniach</span></div>
  <div class="stat-sub">{len(recs)} {ta.plural_pl(len(recs), "ćwiczenie", "ćwiczenia", "ćwiczeń")} w danych</div>
</div>
<div class="table-wrap"><table class="data-table">
<thead><tr><th>Ćwiczenie</th><th>Najlepsza seria</th><th>Data</th><th>Najlepszy e1RM</th><th>Data</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
<p class="tile-desc">Najlepsza seria: najwyższy ciężar, przy remisie więcej powtórzeń; data pierwszego osiągnięcia.</p>
'''
    return _card(title, body, "card-full")


def build_session_compare_tile(workouts: list[ta.Workout]) -> str:
    title = "Porównanie sesji"
    comps = ta.session_comparisons(workouts)
    if not comps:
        counts: dict[str, list[str]] = {}
        for w in workouts:
            counts.setdefault(ta.normalize_title(w.title), []).append(w.title)
        seen = ", ".join(f"{esc(v[-1])} ×{len(v)}" for v in counts.values())
        return _empty_card(
            title, f"Potrzebne dwie sesje o tym samym tytule. Na razie: {seen}.", "card-full"
        )

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
                f"<td>{esc(_fmt_sets(prev_ex.sets)) if prev_ex else '—'}</td>"
                f"<td>{esc(_fmt_sets(last_ex.sets)) if last_ex else '—'}</td>"
                f'<td class="num">{delta_e}</td><td class="num">{delta_v}</td></tr>'
            )

        def total(w: ta.Workout) -> str:
            reps = sum(ex.total_reps for ex in w.exercises)
            vol = sum(ex.volume for ex in w.exercises)
            return f"{w.set_count} serii · {reps} powt. · {_thousands(vol)} kg"

        vol_delta = sum(ex.volume for ex in c.last.exercises) - sum(ex.volume for ex in c.previous.exercises)
        panels.append(f'''
<div class="picker-panel" data-panel="cmp" id="{pid}">
<div class="table-wrap"><table class="data-table">
<thead><tr><th>Ćwiczenie</th><th>Poprzednia ({prev_d})</th><th>Ostatnia ({last_d})</th><th class="num">Δ e1RM</th><th class="num">Δ objętość</th></tr></thead>
<tbody>{"".join(rows)}</tbody>
<tfoot><tr><td>Razem</td><td>{total(c.previous)}</td><td>{total(c.last)}</td><td></td><td class="num">{_fmt_delta(vol_delta)}</td></tr></tfoot>
</table></div>
</div>''')
    desc = '<p class="tile-desc">Dwie ostatnie sesje o tym samym tytule z Hevy, serie robocze bez rozgrzewek.</p>'
    return _card(title, _picker("cmp", options, "Trening") + "".join(panels) + desc, "card-full")


def build_hevy_meta(workouts: list[ta.Workout]) -> str:
    try:
        status = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        hevy = dig(status, "steps", "hevy", default={}) or {}
    except (OSError, ValueError):
        hevy = {}
    parts = [f"Treningów w danych: <b>{len(workouts)}</b>"]
    last = hevy.get("last_success")
    if last:
        last_dt = datetime.strptime(last, "%Y-%m-%dT%H:%M:%S")
        parts.append(f"ostatnia synchronizacja Hevy: <b>{esc(fmt_dt_pl(last_dt))}</b>")
    if hevy.get("result") == "fail":
        parts.append(f"ostatni przebieg nieudany: {esc(hevy.get('message'))}")
    return f'<p class="panel-meta">{" &middot; ".join(parts)}</p>'


def build_training_panel(
    workouts: list[ta.Workout],
    cfg: ta.Config,
    bodyweights: list[tuple[date, float]],
) -> str:
    if not workouts:
        return build_hevy_meta(workouts) + _empty_card(
            "Brak treningów z Hevy",
            "Dodaj HEVY_API_KEY do .env (hevy.com/settings?developer, wymaga Hevy Pro) "
            "i uruchom scripts/refresh_all.sh.",
        )
    return (
        build_hevy_meta(workouts)
        + build_e1rm_tile(workouts)
        + build_relative_strength_tile(workouts, bodyweights)
        + build_progression_tile(workouts, cfg)
        + build_weekly_sets_tile(workouts, cfg)
        + build_volume_tile(workouts)
        + build_workouts_per_week_tile(workouts)
        + build_records_tile(workouts)
        + build_session_compare_tile(workouts)
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
        return f"auto · Garmin · {so_far}"
    if h.source == "sleep":
        v = src.sleep_hours.get(today)
        return f"auto · Garmin · {fmt_hms(v * 3600) if v is not None else 'brak danych'} / {_fmt_kg(h.min)}h"
    return f"auto · {HABIT_SOURCE_PL[h.source]}"


def build_habits_today_tile(stats: list[hb.HabitStats], src: hb.Sources, today: date) -> str:
    done = sum(s.states[today] == hb.DONE for s in stats)
    items = []
    for s in stats:
        state = s.states[today]
        items.append(
            f'<li class="habit-today-item"><span class="hmark hmark-{state}" title="{HABIT_STATE_PL[state]}"></span>'
            f'<span class="habit-today-name">{esc(s.habit.name)}</span>'
            f'<span class="habit-today-detail">{_habit_today_detail(s.habit, src, today)}</span></li>'
        )
    body = f'''
<div class="stat-row">
  <div class="stat-big">{done}<span class="stat-unit">/ {len(stats)} zrobione</span></div>
</div>
<ul class="habit-today">{"".join(items)}</ul>
'''
    return _card(f"Dziś ({fmt_short_date(today)})", body, "card-full")


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
            f'<rect x="{x}" y="1" width="{HABIT_CELL}" height="{HABIT_CELL}" rx="2" class="hc hc-{state}{today_cls}">'
            f"<title>{fmt_short_date(d)}: {HABIT_STATE_PL[state]}</title></rect>"
        )
    # width/height jako atrybuty (jak przy innych wykresach); CSS skaluje do szerokości.
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
            f'<span><span class="dim">najdłuższa</span> <b>{s.longest_streak}</b></span>'
            f'<span><span class="dim">7 dni</span> <b>{_fmt_pct(s.pct_7)}</b></span>'
            f'<span><span class="dim">30 dni</span> <b>{_fmt_pct(s.pct_30)}</b></span>'
            f"</div></div>"
        )
    legend = (
        '<div class="legend">'
        '<span class="legend-item"><i class="hlegend hc-done"></i>zrobione</span>'
        '<span class="legend-item"><i class="hlegend hc-missed"></i>niezrobione</span>'
        '<span class="legend-item"><i class="hlegend hc-unknown"></i>brak danych</span>'
        '<span class="legend-item"><i class="hlegend hc-pending"></i>dziś, jeszcze otwarte</span>'
        "</div>"
    )
    body = f'''
<div class="habit-row habit-head"><div></div><div class="habit-weeks">{week_labels}</div><div></div></div>
{"".join(rows)}
{legend}
<p class="tile-desc">Kolumny to tygodnie (od poniedziałku), komórka to dzień. Seria: dni z rzędu do dziś
(otwarte dziś jej nie przerywa); najdłuższa z ostatniego roku. Procent z ostatnich 7 / 30 pełnych dni, bez dni
bez danych. Automatyczne nawyki liczą się tylko tutaj; ręczne odhaczasz w sekcji „Nawyki” notatki dziennej
albo przez /nawyk w bocie. Lista nawyków: data/habits.json.</p>
'''
    return _card(f"Nawyki — {HABIT_WEEKS} tygodni", body, "card-full")


def build_habits_panel(
    records: list[dict[str, Any]],
    food_by_date: dict[str, dict[str, Any]],
    weight_entries: list[dict[str, Any]],
    workouts: list[ta.Workout],
    habits: list[hb.Habit],
) -> str:
    if not habits:
        return _empty_card("Nawyki", "Brak nawyków w data/habits.json.", "card-full")
    today = date.today()
    start = today - timedelta(days=HABIT_HISTORY_DAYS - 1)
    src = build_habit_sources(records, food_by_date, weight_entries, workouts, start, today)
    stats = hb.habit_stats(habits, src, start, today)
    return build_habits_today_tile(stats, src, today) + build_habits_grid_tile(stats, today)


def _card(title: str, body_html: str, extra_class: str = "") -> str:
    cls = f"card {extra_class}".strip()
    return f'<section class="{cls}"><h2>{esc(title)}</h2>{body_html}</section>'


# --------------------------------------------------------------------------
# Page assembly
# --------------------------------------------------------------------------

CSS = """
:root {
  --bg: #0b0e14;
  --bg-card: #141821;
  --text: #e6e9ef;
  --text-dim: #8b93a3;
  --border: #232838;
  --grid-line: #1c212e;
  --track: #1c212e;

  --c-deep: #7c6fe0;
  --c-light: #5fb3d9;
  --c-rem: #f2b84b;
  --c-awake: #5b6472;

  --c-rhr: #e5735a;
  --c-neutral: #7c8ba1;
  --c-train: #8fa3c4;

  --shadow: 0 1px 3px rgba(0, 0, 0, 0.35);

  --warn-bg: #3a2f0b;
  --warn-border: #d4a72c;
  --warn-text: #f5d77a;

  /* Nutrition status (good / mid / bad). Checked against --bg-card: >= 4.5:1
     as text, and pairwise distinguishable under protan/deutan/tritan
     simulation. Always paired with a ✓ / ! / ✕ glyph, never color alone. */
  --st-good: #3cb8a0;
  --st-mid: #e3ad4c;
  --st-bad: #f06a7a;
  --st-good-bg: rgba(60, 184, 160, 0.14);
  --st-mid-bg: rgba(227, 173, 76, 0.14);
  --st-bad-bg: rgba(240, 106, 122, 0.14);
}

@media (prefers-color-scheme: light) {
  :root {
    --bg: #f4f5f7;
    --bg-card: #ffffff;
    --text: #1a1d24;
    --text-dim: #5b6472;
    --border: #e2e5ea;
    --grid-line: #edeff3;
    --track: #edeff3;

    --shadow: 0 1px 3px rgba(15, 23, 42, 0.06);

    --warn-bg: #fff4c2;
    --warn-border: #d4a72c;
    --warn-text: #5c4400;

    --st-good: #0e7a6a;
    --st-mid: #9a6500;
    --st-bad: #c0266e;
    --st-good-bg: rgba(14, 122, 106, 0.10);
    --st-mid-bg: rgba(154, 101, 0, 0.10);
    --st-bad-bg: rgba(192, 38, 110, 0.09);
  }
}

.stale-banner {
  max-width: 1200px;
  margin: 12px auto 0;
  padding: 10px 16px;
  background: var(--warn-bg);
  border: 1px solid var(--warn-border);
  border-radius: 10px;
  color: var(--warn-text);
  font-size: 0.9rem;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.stale-banner .fix {
  font-size: 0.8rem;
}

.stale-banner code {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
}

header {
  padding: 18px 20px 6px;
  max-width: 1200px;
  margin: 0 auto;
}

header h1 {
  margin: 0 0 2px;
  font-size: 1.35rem;
  font-weight: 650;
}

header .meta {
  margin: 0;
  color: var(--text-dim);
  font-size: 0.8rem;
}

main.layout {
  max-width: 1200px;
  margin: 0 auto;
  padding: 8px 20px 24px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  /* Tiles keep their own natural content height and sit flush at the top
     of their row instead of being stretched to match the tallest sibling
     (Gotowość is the one tile that's naturally taller; the rest stay low
     and compact). */
  align-items: start;
  gap: 12px;
}

@media (max-width: 900px) {
  main.layout { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 600px) {
  main.layout { grid-template-columns: 1fr; }
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 16px;
  box-shadow: var(--shadow);
}

.card h2 {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.stat-row { margin-bottom: 8px; }

.stat-big {
  font-size: 30px;
  font-weight: 650;
  line-height: 1.1;
}

.stat-unit {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-dim);
  margin-left: 4px;
}

.stat-sub, .tile-sub {
  color: var(--text-dim);
  font-size: 13px;
  margin: 4px 0 0;
}

.stat-sub b, .tile-sub b { color: var(--text); font-weight: 600; }

.dim { color: var(--text-dim); }

/* A fixed-height slot for a chart (or its "no data" message), so tiles in
   the same row line up predictably without relying on grid/flex stretching.
   The chart's own actual size comes from its SVG width/height attributes,
   not from this wrapper - this just centers a short "brak danych" message
   when there's no chart to show. */
.chart-wrap {
  min-height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.chart { display: block; width: 100%; overflow: hidden; }

.grid-line { stroke: var(--grid-line); }

.axis-label { fill: var(--text-dim); }

.baseline-line { opacity: 0.6; }

.phase-bar { display: block; width: 100%; border-radius: 4px; overflow: hidden; }

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  margin-top: 8px;
  font-size: 11px;
}

.legend-item { display: inline-flex; align-items: center; gap: 6px; color: var(--text-dim); }

.legend-item i {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
}

.legend-item b { color: var(--text); font-weight: 600; }

.readiness-row { display: flex; align-items: flex-start; gap: 16px; margin-bottom: 8px; }

.ring-col { display: flex; flex-direction: column; align-items: center; gap: 2px; }

.ring { display: block; }

.ring-score { fill: var(--text); }

.ring-level {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: var(--text);
  margin-top: 2px;
}

.ring-col .dim { font-size: 11px; }

.factor-bars { display: flex; flex-direction: column; gap: 8px; }

.factor-row { display: grid; grid-template-columns: 104px 1fr 32px; align-items: center; gap: 8px; }

.factor-label { font-size: 11px; color: var(--text-dim); white-space: nowrap; }

.factor-track {
  height: 6px;
  border-radius: 3px;
  background: var(--track);
  overflow: hidden;
}

.factor-fill { display: block; height: 100%; border-radius: 3px; }

.factor-value { font-size: 11px; text-align: right; color: var(--text-dim); }

.tile-desc {
  font-size: 12px;
  color: var(--text-dim);
  margin: 8px 0 0;
  line-height: 1.3;
}

.target-line { stroke: var(--text-dim); }

.nutrient-bars-wrap { min-height: 40px; display: flex; align-items: center; }

.nutrient-bars { display: flex; flex-direction: column; gap: 8px; width: 100%; }

.nutrient-row { display: grid; grid-template-columns: 60px 1fr auto; align-items: center; gap: 10px; }

.nutrient-label { font-size: 12px; color: var(--text-dim); }

.nutrient-track {
  height: 7px;
  border-radius: 3px;
  background: var(--track);
  overflow: hidden;
}

.nutrient-fill { display: block; height: 100%; border-radius: 3px; background: var(--c-neutral); }

.nutrient-value { font-size: 12px; text-align: right; white-space: nowrap; }

.nutrient-value-wide { grid-column: 2 / span 2; text-align: left; }

/* Nutrition status: colored text + glyph, bar fills, badges, day chips. */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

.st-text-good { color: var(--st-good); fill: var(--st-good); }
.st-text-mid { color: var(--st-mid); fill: var(--st-mid); }
.st-text-bad { color: var(--st-bad); fill: var(--st-bad); }

.st-glyph { font-weight: 700; margin-right: 0.25em; }

.stat-big .st-glyph { font-size: 0.6em; vertical-align: 0.25em; }

.nutrient-fill.st-fill-good { background: var(--st-good); }
.nutrient-fill.st-fill-mid { background: var(--st-mid); }
.nutrient-fill.st-fill-bad { background: var(--st-bad); }

.bar-glyph { fill: var(--bg-card); }

.bar-missing { stroke: var(--text-dim); opacity: 0.6; }

.stat-row-split {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.st-badge {
  flex-shrink: 0;
  padding: 3px 10px;
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 650;
  white-space: nowrap;
  color: var(--text-dim);
}

.st-badge-good { color: var(--st-good); border-color: var(--st-good); background: var(--st-good-bg); }
.st-badge-mid { color: var(--st-mid); border-color: var(--st-mid); background: var(--st-mid-bg); }
.st-badge-bad { color: var(--st-bad); border-color: var(--st-bad); background: var(--st-bad-bg); }
.st-badge-none { border-style: dashed; }

.day-chips {
  list-style: none;
  margin: 4px 0 8px;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}

.day-chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  padding: 4px 0 3px;
  border: 1px solid var(--border);
  border-radius: 8px;
  min-width: 0;
}

.day-chip-glyph { font-size: 13px; font-weight: 700; line-height: 1.1; }

.day-chip-date { font-size: 10px; color: var(--text-dim); }

.day-chip-good { border-color: var(--st-good); background: var(--st-good-bg); color: var(--st-good); }
.day-chip-mid { border-color: var(--st-mid); background: var(--st-mid-bg); color: var(--st-mid); }
.day-chip-bad { border-color: var(--st-bad); background: var(--st-bad-bg); color: var(--st-bad); }
.day-chip-none { border-style: dashed; color: var(--text-dim); }

.day-counts { display: flex; flex-wrap: wrap; gap: 4px 12px; font-size: 12px; }

.day-counts b { font-weight: 700; }

.band-table { width: 100%; border-collapse: collapse; font-size: 11px; font-variant-numeric: tabular-nums; }

.band-table th, .band-table td {
  padding: 3px 6px 3px 0;
  text-align: left;
  vertical-align: top;
  border-bottom: 1px solid var(--grid-line);
}

.band-table thead th { font-weight: 650; white-space: nowrap; border-bottom-color: var(--border); }

.band-table tbody th { font-weight: 500; color: var(--text-dim); }

.band-table tbody tr:last-child th, .band-table tbody tr:last-child td { border-bottom: 0; }

.band-rules { margin-top: 8px; font-size: 11px; line-height: 1.4; }

.band-rules summary { cursor: pointer; color: var(--text-dim); }

.band-rules p { margin: 6px 0 0; }

/* Tabs: CSS-only (radio + label), so they work even with scripts off. */
.tab-input { position: absolute; opacity: 0; pointer-events: none; }

.tabs {
  max-width: 1200px;
  margin: 6px auto 0;
  padding: 0 20px;
  display: flex;
  gap: 6px;
}

.tabs label {
  padding: 7px 16px;
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-dim);
  cursor: pointer;
  user-select: none;
}

#tab-zdrowie:checked ~ .tabs label[for="tab-zdrowie"],
#tab-trening:checked ~ .tabs label[for="tab-trening"],
#tab-nawyki:checked ~ .tabs label[for="tab-nawyki"] {
  background: var(--bg-card);
  color: var(--text);
  border-color: var(--c-neutral);
}

#tab-zdrowie:focus-visible ~ .tabs label[for="tab-zdrowie"],
#tab-trening:focus-visible ~ .tabs label[for="tab-trening"],
#tab-nawyki:focus-visible ~ .tabs label[for="tab-nawyki"] {
  outline: 2px solid var(--c-neutral);
  outline-offset: 2px;
}

main.panel { display: none; }
#tab-zdrowie:checked ~ .panel-zdrowie,
#tab-trening:checked ~ .panel-trening,
#tab-nawyki:checked ~ .panel-nawyki { display: grid; }

.panel-meta {
  grid-column: 1 / -1;
  margin: 0;
  font-size: 12px;
  color: var(--text-dim);
}

.panel-meta b { color: var(--text); font-weight: 600; }

/* Per-muscle-group horizontal bars with a tick for the baseline average. */
.mg-bars { display: flex; flex-direction: column; gap: 7px; }

.mg-row { display: grid; grid-template-columns: 96px 1fr 64px; align-items: center; gap: 8px; }

.mg-label {
  font-size: 11px;
  color: var(--text-dim);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mg-track { position: relative; height: 7px; border-radius: 3px; background: var(--track); }

.mg-fill { display: block; height: 100%; border-radius: 3px; background: var(--c-neutral); }

.mg-tick {
  position: absolute;
  top: -3px;
  width: 2px;
  height: 13px;
  margin-left: -1px;
  background: var(--text);
  opacity: 0.7;
  border-radius: 1px;
}

.mg-value { font-size: 11px; text-align: right; white-space: nowrap; }

.legend-item i.legend-bar { background: var(--c-neutral); }

.legend-item i.legend-tick { width: 2px; height: 12px; background: var(--text); opacity: 0.7; }

/* Shared by every "no data" state: a short, fixed-height hint (tile stays
   around 90px tall total) instead of a tall padded block. */
.empty-fill {
  min-height: 46px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.empty-msg { color: var(--text-dim); font-size: 0.85rem; margin: 0; }

/* Trening: wide tiles, pickers, tables. */
.panel-trening > .card,
.panel-nawyki > .card { min-width: 0; }

.card-wide { grid-column: span 2; }

.card-full { grid-column: 1 / -1; }

@media (max-width: 600px) {
  .card-wide { grid-column: 1 / -1; }
}

.picker-row { margin-bottom: 8px; }

.picker {
  max-width: 100%;
  padding: 5px 8px;
  font: inherit;
  font-size: 12px;
  color: var(--text);
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
}

.picker-panel[hidden] { display: none; }

.trend-line { stroke: var(--text-dim); }

.table-wrap { overflow-x: auto; }

.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }

.data-table th {
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-dim);
  padding: 4px 10px 6px 0;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

.data-table td {
  padding: 6px 10px 6px 0;
  border-bottom: 1px solid var(--grid-line);
  vertical-align: top;
}

.data-table tbody tr:last-child td { border-bottom: 0; }

.data-table tfoot td { border-top: 1px solid var(--border); color: var(--text-dim); }

.data-table .num { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }

.nowrap { white-space: nowrap; }

.pill {
  display: inline-block;
  padding: 1px 8px;
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: 11px;
  color: var(--text-dim);
  white-space: nowrap;
}

.pill-raise { border-color: var(--c-train); color: var(--text); font-weight: 600; }

.pill-stall { border-style: dashed; border-color: var(--text-dim); color: var(--text); }

.badge {
  display: inline-block;
  margin-left: 4px;
  padding: 0 5px;
  border-radius: 4px;
  background: var(--track);
  color: var(--text);
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.mg-row-target { grid-template-columns: 96px 1fr 72px; }

.mg-band {
  position: absolute;
  top: 0;
  bottom: 0;
  background: var(--text-dim);
  opacity: 0.25;
  border-radius: 3px;
}

.mg-track-target .mg-fill { position: relative; }

.legend-item i.legend-band { background: var(--text-dim); opacity: 0.35; }

/* Nawyki: neutral cells - done is filled, nothing is red or green. */
.habit-today {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 6px 16px;
}

.habit-today-item { display: grid; grid-template-columns: 14px 1fr; column-gap: 8px; align-items: center; }

.habit-today-name { font-size: 13px; font-weight: 600; }

.habit-today-detail { grid-column: 2; font-size: 11px; color: var(--text-dim); }

.hmark { width: 12px; height: 12px; border-radius: 50%; border: 1.5px solid var(--text-dim); }

.hmark-done { background: var(--c-neutral); border-color: var(--c-neutral); }

.hmark-unknown { border-style: dashed; }

.hmark-missed { border-color: var(--border); }

.habit-row {
  display: grid;
  grid-template-columns: 150px 1fr 250px;
  gap: 12px;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid var(--grid-line);
}

.habit-head { border-bottom: 0; padding-bottom: 0; }

.habit-name { font-size: 12px; font-weight: 600; min-width: 0; }

.habit-kind { display: block; font-size: 10px; font-weight: 500; color: var(--text-dim); }

.habit-cells { display: block; width: 100%; height: auto; }

.hc { stroke-width: 1; }

.hc-done { fill: var(--c-neutral); }

.hc-missed { fill: var(--track); }

.hc-unknown { fill: none; stroke: var(--border); stroke-dasharray: 2 2; }

.hc-pending { fill: none; stroke: var(--text-dim); }

.hc-today { stroke: var(--text); stroke-width: 1.5; }

.habit-weeks { display: grid; grid-template-columns: repeat(12, 1fr); font-size: 10px; color: var(--text-dim); }

.habit-stats { display: grid; grid-template-columns: repeat(4, auto); justify-content: end; gap: 10px; font-size: 11px; white-space: nowrap; }

.habit-stats b { font-weight: 600; }

.legend-item i.hlegend { border: 1px solid transparent; }

.legend-item i.hlegend.hc-done { background: var(--c-neutral); }

.legend-item i.hlegend.hc-missed { background: var(--track); }

.legend-item i.hlegend.hc-unknown { border: 1px dashed var(--border); }

.legend-item i.hlegend.hc-pending { border-color: var(--text-dim); }

@media (max-width: 760px) {
  .habit-row { grid-template-columns: 1fr auto; row-gap: 6px; }
  .habit-cells-wrap, .habit-weeks { grid-column: 1 / -1; }
  .habit-head > div:empty { display: none; }
  .habit-weeks span:nth-child(even) { visibility: hidden; }
}
"""


def build_html(
    records: list[dict[str, Any]],
    food_by_date: dict[str, dict[str, Any]],
    weight_entries: list[dict[str, Any]],
    targets: dict[str, Any] | None,
    workouts: list[ta.Workout],
    training_cfg: ta.Config,
    bodyweights: list[tuple[date, float]],
    habits: list[hb.Habit],
) -> str:
    if records:
        layout = (
            build_readiness_tile(records)
            + build_steps_tile(records)
            + build_rhr_tile(records)
        )
    else:
        layout = _card(
            "Brak danych Garmin",
            '<div class="empty-fill"><p class="empty-msg">Uruchom scripts/garmin_sync.py, '
            "aby pobrać dane z Garmin Connect.</p></div>",
        )

    bands = resolve_bands(targets)
    trend_first, trend_second = build_nutrition_trend_cards(food_by_date, targets, bands)
    layout += build_sleep_tile(records)
    layout += build_food_yesterday_tile(food_by_date, targets, bands)
    layout += build_weight_tile(weight_entries)
    layout += build_nutrition_week_tile(food_by_date, bands) + trend_first
    layout += trend_second + build_nutrition_legend_tile(bands)

    generated = esc(fmt_generated_at())
    sync_dt = latest_sync_dt(records)
    sync_text = esc(fmt_dt_pl(sync_dt)) if sync_dt else "brak danych"
    stale_banner = build_stale_banner(records)
    training = build_training_panel(workouts, training_cfg, bodyweights)
    habits_panel = build_habits_panel(records, food_by_date, weight_entries, workouts, habits)

    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Health Dashboard</title>
<style>{CSS}</style>
</head>
<body>
<input type="radio" name="tab" id="tab-zdrowie" class="tab-input" checked>
<input type="radio" name="tab" id="tab-trening" class="tab-input">
<input type="radio" name="tab" id="tab-nawyki" class="tab-input">
{stale_banner}
<header>
  <h1>Health Dashboard</h1>
  <p class="meta">Ostatnia synchronizacja danych: <b>{sync_text}</b> &middot; Wygenerowano: {generated}</p>
</header>
<nav class="tabs" aria-label="Zakładki">
  <label for="tab-zdrowie">Zdrowie</label>
  <label for="tab-trening">Trening</label>
  <label for="tab-nawyki">Nawyki</label>
</nav>
<main class="layout panel panel-zdrowie">
{layout}
</main>
<main class="layout panel panel-trening">
{training}
</main>
<main class="layout panel panel-nawyki">
{habits_panel}
</main>
<script>
// Obsidian reloads the file after every rebuild - keep the chosen tab.
(function () {{
  var KEY = "health-dashboard-tab";
  try {{
    var saved = localStorage.getItem(KEY);
    var el = saved && document.getElementById(saved);
    if (el) el.checked = true;
  }} catch (e) {{}}
  document.querySelectorAll(".tab-input").forEach(function (input) {{
    input.addEventListener("change", function () {{
      try {{ localStorage.setItem(KEY, input.id); }} catch (e) {{}}
    }});
  }});
  // Pickers (e1RM, session comparison): show one panel, remember the choice.
  document.querySelectorAll("select.picker").forEach(function (sel) {{
    var group = sel.getAttribute("data-group");
    var key = "health-dashboard-" + group;
    var panels = document.querySelectorAll('[data-panel="' + group + '"]');
    function show() {{
      panels.forEach(function (p) {{ p.hidden = p.id !== sel.value; }});
    }}
    try {{
      var saved = localStorage.getItem(key);
      if (saved && document.getElementById(saved)) sel.value = saved;
    }} catch (e) {{}}
    sel.addEventListener("change", function () {{
      show();
      try {{ localStorage.setItem(key, sel.value); }} catch (e) {{}}
    }});
    show();
  }});
}})();
</script>
</body>
</html>
"""


def main() -> None:
    records = load_records()
    food_by_date = load_food_records()
    weight_entries = load_weight_entries()
    targets = load_targets()
    workouts = ta.load_workouts(HEVY_DIR)
    training_cfg = ta.load_config(HEVY_CONFIG_PATH)
    bodyweights = ta.load_bodyweights(WEIGHT_PATH)
    habits = hb.load_habits(HABITS_PATH)
    html = build_html(
        records, food_by_date, weight_entries, targets, workouts, training_cfg, bodyweights, habits
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Zapisano dashboard: {OUT_PATH} ({len(records)} dni danych, {len(workouts)} treningów, {len(html)} znaków).")


if __name__ == "__main__":
    main()
