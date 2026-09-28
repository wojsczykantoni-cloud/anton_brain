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


def fmt_big_with_target(value: Any, target: Any, unit: str) -> str:
    if value is None:
        return "brak danych"
    text = f"{value:.0f}"
    if target:
        text += f" / {target:.0f}"
    return f"{text} {unit}"


# --------------------------------------------------------------------------
# SVG chart builders
# --------------------------------------------------------------------------

CHART_W = 480
CHART_H = 110
PAD_L = 44
PAD_R = 12
PAD_T = 10
PAD_B = 18


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

    parts: list[str] = [
        f'<svg viewBox="0 0 {CHART_W} {CHART_H}" class="chart" role="img" '
        f'preserveAspectRatio="none" aria-label="Wykres liniowy">'
    ]

    for frac in (0.0, 0.5, 1.0):
        gy = PAD_T + (CHART_H - PAD_T - PAD_B) * (1 - frac)
        gv = y_min + (y_max - y_min) * frac
        parts.append(
            f'<line x1="{PAD_L}" y1="{gy:.1f}" x2="{CHART_W - PAD_R}" y2="{gy:.1f}" '
            f'class="grid-line" />'
        )
        parts.append(
            f'<text x="{PAD_L - 8}" y="{gy + 3:.1f}" class="axis-label" text-anchor="end">'
            f'{y_fmt.format(gv)}{unit}</text>'
        )

    if baseline_band:
        lo, hi = baseline_band
        y_lo = PAD_T + (CHART_H - PAD_T - PAD_B) * (1 - (lo - y_min) / (y_max - y_min))
        y_hi = PAD_T + (CHART_H - PAD_T - PAD_B) * (1 - (hi - y_min) / (y_max - y_min))
        parts.append(
            f'<rect x="{PAD_L}" y="{min(y_lo, y_hi):.1f}" width="{inner_w:.1f}" '
            f'height="{abs(y_lo - y_hi):.1f}" class="baseline-band" />'
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

    # Only first/middle/last day get an X-axis label, to keep it legible at
    # tile width.
    n = len(labels)
    label_indices = sorted({0, (n - 1) // 2, n - 1}) if n else []
    for i in label_indices:
        x = points[i][0]
        parts.append(
            f'<text x="{x:.1f}" y="{CHART_H - 4}" class="axis-label" text-anchor="middle">'
            f"{esc(labels[i])}</text>"
        )

    parts.append("</svg>")
    return "".join(parts)


def svg_bar_chart(
    labels: list[str],
    values: list[float | None],
    color: str,
    unit: str = "",
    y_fmt: str = "{:.0f}",
    target: float | None = None,
) -> str:
    non_null = [v for v in values if v is not None]
    if not non_null:
        return '<p class="empty-msg">Brak danych do wykresu.</p>'

    all_vals = list(non_null)
    if target is not None:
        all_vals.append(target)
    y_max = max(all_vals) * 1.15 or 1.0
    n = len(values)
    inner_w = CHART_W - PAD_L - PAD_R
    inner_h = CHART_H - PAD_T - PAD_B
    slot_w = inner_w / n
    bar_w = slot_w * 0.6

    parts = [
        f'<svg viewBox="0 0 {CHART_W} {CHART_H}" class="chart" role="img" '
        f'preserveAspectRatio="none" aria-label="Wykres słupkowy">'
    ]

    for frac in (0.0, 0.5, 1.0):
        gy = PAD_T + inner_h * (1 - frac)
        gv = y_max * frac
        parts.append(
            f'<line x1="{PAD_L}" y1="{gy:.1f}" x2="{CHART_W - PAD_R}" y2="{gy:.1f}" '
            f'class="grid-line" />'
        )
        parts.append(
            f'<text x="{PAD_L - 8}" y="{gy + 3:.1f}" class="axis-label" text-anchor="end">'
            f'{y_fmt.format(gv)}{unit}</text>'
        )

    step = max(1, round(n / 6))
    for i, v in enumerate(values):
        x = PAD_L + slot_w * i + (slot_w - bar_w) / 2
        if v is not None:
            bar_h = (v / y_max) * inner_h if y_max else 0
            y = PAD_T + inner_h - bar_h
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" '
                f'rx="2" fill="{color}" />'
            )
        if i % step == 0 or i == n - 1:
            parts.append(
                f'<text x="{x + bar_w / 2:.1f}" y="{CHART_H - 4}" class="axis-label" '
                f'text-anchor="middle">{esc(labels[i])}</text>'
            )

    if target is not None and y_max:
        ty = PAD_T + inner_h - (target / y_max) * inner_h
        parts.append(
            f'<line x1="{PAD_L}" y1="{ty:.1f}" x2="{CHART_W - PAD_R}" y2="{ty:.1f}" '
            f'class="target-line" />'
        )

    parts.append("</svg>")
    return "".join(parts)


def svg_phase_bar(deep: Any, rem: Any, light: Any, awake: Any) -> str:
    segments = [
        ("Głęboki", deep, "var(--c-deep)"),
        ("REM", rem, "var(--c-rem)"),
        ("Lekki", light, "var(--c-light)"),
        ("Wybudzenia", awake, "var(--c-awake)"),
    ]
    total = sum(v for _, v, _ in segments if isinstance(v, (int, float)))
    width = 640
    height = 14

    if not total:
        return '<p class="empty-msg">Brak danych o fazach snu.</p>'

    parts = [
        f'<svg viewBox="0 0 {width} {height}" class="phase-bar" role="img" '
        f'aria-label="Fazy snu">'
    ]
    x = 0.0
    for _, v, color in segments:
        if not isinstance(v, (int, float)) or v <= 0:
            continue
        w = (v / total) * width
        parts.append(f'<rect x="{x:.1f}" y="0" width="{w:.1f}" height="{height}" fill="{color}" />')
        x += w
    parts.append("</svg>")

    legend_items = []
    for name, v, color in segments:
        pct = f"{(v / total * 100):.0f}%" if isinstance(v, (int, float)) and v else "0%"
        legend_items.append(
            f'<span class="legend-item"><i style="background:{color}"></i>{esc(name)} '
            f'<b>{fmt_hms(v) if isinstance(v, (int, float)) else "brak danych"}</b> '
            f'<span class="dim">({pct})</span></span>'
        )
    parts.append(f'<div class="legend">{"".join(legend_items)}</div>')
    return "".join(parts)


def svg_ring(score: Any, color: str, diameter: int = 100, stroke: int = 10) -> str:
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
    return f'''<svg viewBox="0 0 {size} {size}" class="ring" role="img" aria-label="Pierścień gotowości">
<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="var(--border)" stroke-width="{stroke}" />
<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="{stroke}"
  stroke-linecap="round" stroke-dasharray="{dash:.1f} {circumference:.1f}"
  transform="rotate(-90 {cx} {cy})" />
<text x="{cx}" y="{cy}" text-anchor="middle" dominant-baseline="central" class="ring-score">{int(score)}</text>
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
        return '<p class="empty-msg">Brak danych o składowych gotowości.</p>'

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
        return _card("Gotowość (Training Readiness)", '<p class="empty-msg">Brak danych Training Readiness.</p>')

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
<div class="ring-row">
  {ring}
  <div class="ring-label">
    <div class="stat-sub">Poziom: <b>{esc(level_pl)}</b></div>
    <div class="dim">{fmt_short_date(latest["_date"])}</div>
  </div>
</div>
{bars}
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
    value_text = f"{latest:.0f} ms" if latest is not None else "brak danych"
    status_text = pl_word(HRV_STATUS_PL, latest_status) if latest is not None else ""

    chart = svg_line_chart(labels, values, "var(--c-hrv)", unit=" ms", baseline_band=baseline_band)
    body = f'''
<div class="stat-row">
  <div class="stat-big">{value_text}</div>
  <div class="stat-sub">{esc(status_text)}</div>
</div>
{chart}
'''
    return _card("HRV — ostatnie 14 nocy", body)


def build_rhr_tile(records: list[dict[str, Any]]) -> str:
    trend = records[-TREND_DAYS:]
    labels = [fmt_short_date(r["_date"]) for r in trend]
    values = [r.get("resting_heart_rate") for r in trend]

    latest = next((v for v in reversed(values) if v is not None), None)
    value_text = f"{int(latest)} bpm" if latest is not None else "brak danych"

    chart = svg_line_chart(labels, values, "var(--c-rhr)", unit=" bpm")
    body = f'''
<div class="stat-row">
  <div class="stat-big">{value_text}</div>
  <div class="stat-sub">Tętno spoczynkowe, ostatni pomiar</div>
</div>
{chart}
'''
    return _card("Tętno spoczynkowe — ostatnie 14 nocy", body)


def build_sleep_tile(records: list[dict[str, Any]]) -> str:
    with_sleep = [r for r in records if dig(r, "sleep", "total_seconds") is not None]
    if not with_sleep:
        return _card("Sen — ostatnia noc", '<p class="empty-msg">Brak danych o śnie.</p>')

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
        sleep.get("deep_seconds"), sleep.get("rem_seconds"),
        sleep.get("light_seconds"), sleep.get("awake_seconds"),
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
            '<p class="empty-msg empty-compact">Brak wpisu. Wyślij /dzien do bota.</p>',
        )

    kcal = rec.get("kcal")
    protein = rec.get("protein")
    carbs = rec.get("carbs")
    kcal_target = (targets or {}).get("kcal")
    protein_target = (targets or {}).get("protein")
    carbs_target = (targets or {}).get("carbs")

    kcal_big = fmt_big_with_target(kcal, kcal_target, "kcal")
    bars = nutrient_bar_html("Białko", protein, protein_target) + nutrient_bar_html(
        "Węgle", carbs, carbs_target
    )

    body = f'''
<div class="stat-row">
  <div class="stat-big">{esc(kcal_big)}</div>
</div>
<div class="nutrient-bars">{bars}</div>
'''
    return _card(f"Wczoraj: paliwo ({fmt_short_date(y)})", body)


def build_weight_tile(weight_entries: list[dict[str, Any]]) -> str:
    if not weight_entries:
        return _card(
            "Waga", '<p class="empty-msg empty-compact">Brak wpisów. Wyślij /waga do bota.</p>'
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

    chart = svg_line_chart(labels, values, "var(--c-neutral)", unit=" kg", y_fmt="{:.1f}")

    kg_text = f"{latest_kg:.1f} kg" if latest_kg is not None else "brak danych"
    title_date = fmt_short_date(date.fromisoformat(latest_date_str)) if latest_date_str else ""

    body = f'''
<div class="stat-row">
  <div class="stat-big">{esc(kg_text)}</div>
  <div class="stat-sub">{esc(change_text) if change_text else "Brak danych sprzed 7 dni"}</div>
</div>
{chart}
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

    kcal_card = _card(
        "Kalorie — ostatnie 14 dni",
        svg_bar_chart(labels, series("kcal"), "var(--c-neutral)", unit=" kcal", target=kcal_target),
    )
    protein_card = _card(
        "Białko — ostatnie 14 dni",
        svg_bar_chart(labels, series("protein"), "var(--c-neutral)", unit=" g", target=protein_target),
    )
    carbs_card = _card(
        "Węgle — ostatnie 14 dni",
        svg_bar_chart(labels, series("carbs"), "var(--c-neutral)", unit=" g", target=carbs_target),
    )
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
  padding: 10px 20px 14px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 14px;
}

.card h2 {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.stat-row { margin-bottom: 6px; }

.stat-big {
  font-size: 30px;
  font-weight: 650;
  line-height: 1.1;
}

.stat-sub, .tile-sub {
  color: var(--text-dim);
  font-size: 12px;
  margin: 2px 0 6px;
}

.stat-sub b, .tile-sub b { color: var(--text); font-weight: 600; }

.dim { color: var(--text-dim); }

.chart { width: 100%; height: 110px; display: block; }

.grid-line { stroke: var(--grid-line); stroke-width: 1; }

.axis-label {
  fill: var(--text-dim);
  font-size: 10px;
}

.baseline-band { fill: var(--c-hrv); opacity: 0.12; }

.phase-bar { width: 100%; height: auto; display: block; border-radius: 4px; overflow: hidden; }

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 10px;
  margin-top: 6px;
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

.ring-row { display: flex; align-items: center; gap: 16px; margin-bottom: 8px; }

.ring { width: 112px; height: 112px; flex: none; }

.ring-score { font-size: 26px; font-weight: 700; fill: var(--text); }

.ring-label .dim { font-size: 0.8rem; margin-top: 2px; }

.factor-bars { display: flex; flex-direction: column; gap: 5px; margin-bottom: 8px; }

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
  margin: 6px 0 0;
  line-height: 1.3;
}

.target-line { stroke: var(--text-dim); stroke-width: 1.5; stroke-dasharray: 4 3; }

.nutrient-bars { display: flex; flex-direction: column; gap: 8px; }

.nutrient-row { display: grid; grid-template-columns: 60px 1fr auto; align-items: center; gap: 10px; }

.nutrient-label { font-size: 0.82rem; color: var(--text-dim); }

.nutrient-track {
  height: 7px;
  border-radius: 3px;
  background: var(--track);
  overflow: hidden;
}

.nutrient-fill { display: block; height: 100%; border-radius: 3px; background: var(--c-neutral); }

.nutrient-value { font-size: 0.82rem; text-align: right; white-space: nowrap; }

.nutrient-value-wide { grid-column: 2 / span 2; text-align: left; }

.empty-msg { color: var(--text-dim); font-size: 0.85rem; padding: 10px 0; margin: 0; }

.empty-compact { padding: 2px 0; }

footer {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px 16px;
  color: var(--text-dim);
  font-size: 0.78rem;
}
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
            '<p class="empty-msg">Uruchom scripts/garmin_sync.py, aby pobrać dane z Garmin Connect.</p>',
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
<footer>Dane z Garmin Connect, zapisane lokalnie w data/garmin. Wygenerowano przez scripts/build_dashboard.py.</footer>
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
