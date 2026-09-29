#!/usr/bin/env python3
"""Builds a self-contained Health Dashboard.html from data/garmin/*.json.

Usage (from repo root, using the project venv):

    .venv/bin/python scripts/build_dashboard.py

Reads every daily JSON file written by scripts/garmin_sync.py, plus
data/food/*.json, data/weight.json and data/targets.json written by the
Telegram bot's /dzien, /waga and /cel commands. Generates a single
standalone HTML file at "Health/Health Dashboard.html" with inline SVG
charts (no external libraries or fonts, no network requests). Dark theme
by default, switching to a light theme when the system prefers light
(prefers-color-scheme). Days with missing data are rendered as gaps,
never errors; a missing data/targets.json simply omits target lines.

3-column grid. Row 1: Training Readiness ring + per-factor bars (only the
factors actually present in the data) with a rule-based Polish summary,
HRV trend, resting heart rate trend. Row 2: last night's sleep (duration,
start/end times, score, phase bar), yesterday's nutrition vs. target,
weight trend. Row 3: 14-day calorie/protein/carb bar charts with a
dashed target line. Colors are neutral throughout the nutrition/weight
tiles - no good/bad judgment, just numbers.
"""

from __future__ import annotations

import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "garmin"
FOOD_DIR = REPO_ROOT / "data" / "food"
WEIGHT_PATH = REPO_ROOT / "data" / "weight.json"
TARGETS_PATH = REPO_ROOT / "data" / "targets.json"
OUT_DIR = REPO_ROOT / "Health"
OUT_PATH = OUT_DIR / "Health Dashboard.html"

TREND_DAYS = 14

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

HRV_STATUS_PL = {
    "BALANCED": "Zbalansowane",
    "UNBALANCED": "Niezbalansowane",
    "LOW": "Niskie",
    "POOR": "Słabe",
}

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
) -> list[tuple[float, float | None]]:
    n = len(values)
    inner_w = CHART_W - PAD_L - PAD_R
    inner_h = CHART_H - PAD_T - PAD_B
    span = (y_max - y_min) or 1.0
    points = []
    for i, v in enumerate(values):
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
) -> str:
    non_null = [v for v in values if v is not None]
    if not non_null:
        return '<p class="empty-msg">Brak danych do wykresu.</p>'

    all_vals = list(non_null)
    if baseline_band:
        all_vals.extend(baseline_band)
    y_min = min(all_vals)
    y_max = max(all_vals)
    if y_min == y_max:
        y_min -= 1
        y_max += 1
    pad = (y_max - y_min) * 0.12
    y_min -= pad
    y_max += pad

    points = _scale_points(values, y_min, y_max)
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

    for x, y in points:
        if y is not None:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}" />')

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
) -> str:
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
        if v is not None:
            bar_h = (v / scale_max) * inner_h if scale_max else 0
            y = PAD_T + inner_h - bar_h
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" '
                f'rx="2" fill="{color}" />'
            )
            if i in value_label_idx:
                label_y = y - 4
                if ty is not None and abs(label_y - ty) < BAR_LABEL_TARGET_GAP:
                    # Push the label away from the dashed target line rather than
                    # letting it sit on top of it: above the line for a bar that
                    # reaches/exceeds the target, below it otherwise - but only if
                    # there's room between the line and the bar's own top edge,
                    # since a very close call has nowhere to go but back above.
                    below_y = ty + BAR_LABEL_TARGET_GAP + BAR_LABEL_FONT_SIZE * 0.75
                    if v >= target:
                        label_y = ty - BAR_LABEL_TARGET_GAP
                    elif below_y <= y - 2:
                        label_y = below_y
                    else:
                        label_y = ty - BAR_LABEL_TARGET_GAP
                parts.append(
                    f'<text x="{x + bar_w / 2:.1f}" y="{label_y:.1f}" font-size="{BAR_LABEL_FONT_SIZE}" '
                    f'class="axis-label" text-anchor="middle">{v:.0f}</text>'
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


def nutrient_bar_html(label: str, value: Any, target: Any, unit: str = "g") -> str:
    value_text = f"{value:.0f}{unit}" if value is not None else "brak danych"
    if target:
        frac = max(0.0, min(100.0, (value / target) * 100)) if value is not None else 0.0
        return (
            f'<div class="nutrient-row">'
            f'<span class="nutrient-label">{esc(label)}</span>'
            f'<span class="nutrient-track"><span class="nutrient-fill" '
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


def build_hrv_tile(records: list[dict[str, Any]]) -> str:
    trend = records[-TREND_DAYS:]
    labels = [fmt_short_date(r["_date"]) for r in trend]
    values = [dig(r, "hrv", "last_night_avg") for r in trend]

    baseline_band = None
    for r in reversed(trend):
        lo = dig(r, "hrv", "baseline_balanced_low")
        hi = dig(r, "hrv", "baseline_balanced_upper")
        if lo is not None and hi is not None:
            baseline_band = (lo, hi)
            break

    latest = next((v for v in reversed(values) if v is not None), None)
    latest_status = next(
        (dig(r, "hrv", "status") for r in reversed(trend) if dig(r, "hrv", "status")), None
    )
    value_text = f'{latest:.0f}<span class="stat-unit">ms</span>' if latest is not None else "brak danych"
    status_text = pl_word(HRV_STATUS_PL, latest_status) if latest is not None else ""
    baseline_text = f"baseline {baseline_band[0]:.0f}–{baseline_band[1]:.0f} ms" if baseline_band else ""
    sub_parts = [t for t in (status_text, baseline_text) if t]
    sub_text = " · ".join(sub_parts)

    chart = svg_line_chart(
        labels, values, "var(--c-hrv)", unit=" ms", baseline_band=baseline_band
    )
    body = f'''
<div class="stat-row">
  <div class="stat-big">{value_text}</div>
  <div class="stat-sub">{esc(sub_text)}</div>
</div>
<div class="chart-wrap">{chart}</div>
'''
    return _card("HRV — ostatnie 14 nocy", body)


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
    food_by_date: dict[str, dict[str, Any]], targets: dict[str, Any] | None
) -> str:
    y = date.today() - timedelta(days=1)
    rec = food_by_date.get(y.isoformat())
    if not rec:
        return _card(
            "Wczoraj: paliwo",
            '<div class="empty-fill"><p class="empty-msg">Wyślij /dzien do bota.</p></div>',
        )

    kcal = rec.get("kcal")
    protein = rec.get("protein")
    carbs = rec.get("carbs")
    kcal_target = (targets or {}).get("kcal")
    protein_target = (targets or {}).get("protein")
    carbs_target = (targets or {}).get("carbs")

    kcal_text = f'{kcal:.0f}<span class="stat-unit">kcal</span>' if kcal is not None else "brak danych"
    kcal_sub = f"Cel: {kcal_target:.0f} kcal" if kcal_target else "&nbsp;"
    bars = nutrient_bar_html("Białko", protein, protein_target) + nutrient_bar_html(
        "Węgle", carbs, carbs_target
    )

    body = f'''
<div class="stat-row">
  <div class="stat-big">{kcal_text}</div>
  <div class="stat-sub">{kcal_sub}</div>
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
    food_by_date: dict[str, dict[str, Any]], targets: dict[str, Any] | None
) -> str:
    days14 = last_n_calendar_days(TREND_DAYS)
    labels = [fmt_short_date(d) for d in days14]

    def series(key: str) -> list[float | None]:
        return [(food_by_date.get(d.isoformat()) or {}).get(key) for d in days14]

    kcal_target = (targets or {}).get("kcal")
    protein_target = (targets or {}).get("protein")
    carbs_target = (targets or {}).get("carbs")

    def bar_tile(
        title: str, values: list[float | None], unit: str, target: float | None, step: float
    ) -> str:
        if not any(v is not None for v in values):
            return _card(title, '<div class="empty-fill"><p class="empty-msg">Brak danych.</p></div>')
        top = nice_axis_top(values, target, step)
        chart = svg_bar_chart(labels, values, "var(--c-neutral)", unit=unit, target=target, y_top=top)
        return _card(title, f'<div class="chart-wrap">{chart}</div>')

    kcal_card = bar_tile("Kalorie — ostatnie 14 dni", series("kcal"), " kcal", kcal_target, step=500)
    protein_card = bar_tile("Białko — ostatnie 14 dni", series("protein"), " g", protein_target, step=50)
    carbs_card = bar_tile("Węgle — ostatnie 14 dni", series("carbs"), " g", carbs_target, step=50)
    return kcal_card + protein_card + carbs_card


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

  --c-hrv: #5b9dd9;
  --c-rhr: #e5735a;
  --c-neutral: #7c8ba1;

  --shadow: 0 1px 3px rgba(0, 0, 0, 0.35);
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
  }
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
"""


def build_html(
    records: list[dict[str, Any]],
    food_by_date: dict[str, dict[str, Any]],
    weight_entries: list[dict[str, Any]],
    targets: dict[str, Any] | None,
) -> str:
    if records:
        layout = (
            build_readiness_tile(records)
            + build_hrv_tile(records)
            + build_rhr_tile(records)
        )
    else:
        layout = _card(
            "Brak danych Garmin",
            '<div class="empty-fill"><p class="empty-msg">Uruchom scripts/garmin_sync.py, '
            "aby pobrać dane z Garmin Connect.</p></div>",
        )

    layout += build_sleep_tile(records)
    layout += build_food_yesterday_tile(food_by_date, targets)
    layout += build_weight_tile(weight_entries)
    layout += build_nutrition_trend_cards(food_by_date, targets)

    generated = esc(fmt_generated_at())
    sync_dt = latest_sync_dt(records)
    sync_text = esc(fmt_dt_pl(sync_dt)) if sync_dt else "brak danych"

    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Health Dashboard</title>
<style>{CSS}</style>
</head>
<body>
<header>
  <h1>Health Dashboard</h1>
  <p class="meta">Ostatnia synchronizacja danych: <b>{sync_text}</b> &middot; Wygenerowano: {generated}</p>
</header>
<main class="layout">
{layout}
</main>
</body>
</html>
"""


def main() -> None:
    records = load_records()
    food_by_date = load_food_records()
    weight_entries = load_weight_entries()
    targets = load_targets()
    html = build_html(records, food_by_date, weight_entries, targets)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Zapisano dashboard: {OUT_PATH} ({len(records)} dni danych, {len(html)} znaków).")


if __name__ == "__main__":
    main()
