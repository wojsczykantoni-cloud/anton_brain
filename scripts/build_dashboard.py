#!/usr/bin/env python3
"""Builds a self-contained Health Dashboard.html from data/garmin/*.json.

Usage (from repo root, using the project venv):

    .venv/bin/python scripts/build_dashboard.py

Reads every daily JSON file written by scripts/garmin_sync.py, and
generates a single standalone HTML file at "Health/Health Dashboard.html"
with inline SVG charts (no external libraries or fonts, no network
requests). Dark theme by default, switching to a light theme when the
system prefers light (prefers-color-scheme). Days with missing data are
rendered as gaps, never errors.

Tiles: last night's sleep (duration, phase bar, score), 14-night sleep
duration bars, and 14-night HRV line with a baseline band.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "garmin"
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


def pl_word(value_pl_map: dict[str, str], raw: Any) -> str:
    if not raw:
        return "brak danych"
    return value_pl_map.get(raw, str(raw).replace("_", " ").title())


# --------------------------------------------------------------------------
# SVG chart builders
# --------------------------------------------------------------------------

CHART_W = 560
CHART_H = 180
PAD_L = 42
PAD_R = 14
PAD_T = 16
PAD_B = 26


def _scale_points(
    labels: list[str],
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

    points = _scale_points(labels, values, y_min, y_max)
    inner_w = CHART_W - PAD_L - PAD_R

    parts: list[str] = [
        f'<svg viewBox="0 0 {CHART_W} {CHART_H}" class="chart" role="img" '
        f'aria-label="Wykres liniowy">'
    ]

    # gridlines + y-axis labels (min/mid/max)
    for frac in (0.0, 0.5, 1.0):
        gy = PAD_T + (CHART_H - PAD_T - PAD_B) * (1 - frac)
        gv = y_min + (y_max - y_min) * frac
        parts.append(
            f'<line x1="{PAD_L}" y1="{gy:.1f}" x2="{CHART_W - PAD_R}" y2="{gy:.1f}" '
            f'class="grid-line" />'
        )
        parts.append(
            f'<text x="{PAD_L - 6}" y="{gy + 3:.1f}" class="axis-label" text-anchor="end">'
            f'{y_fmt.format(gv)}{unit}</text>'
        )

    # baseline band (e.g. HRV balanced range)
    if baseline_band:
        lo, hi = baseline_band
        y_lo = PAD_T + (CHART_H - PAD_T - PAD_B) * (1 - (lo - y_min) / (y_max - y_min))
        y_hi = PAD_T + (CHART_H - PAD_T - PAD_B) * (1 - (hi - y_min) / (y_max - y_min))
        parts.append(
            f'<rect x="{PAD_L}" y="{min(y_lo, y_hi):.1f}" width="{inner_w:.1f}" '
            f'height="{abs(y_lo - y_hi):.1f}" class="baseline-band" />'
        )

    # line segments, broken across gaps (None values)
    segment: list[str] = []
    for x, y in points:
        if y is None:
            if len(segment) > 1:
                parts.append(
                    f'<polyline points="{" ".join(segment)}" fill="none" '
                    f'stroke="{color}" stroke-width="2.5" stroke-linejoin="round" '
                    f'stroke-linecap="round" />'
                )
            segment = []
        else:
            segment.append(f"{x:.1f},{y:.1f}")
    if len(segment) > 1:
        parts.append(
            f'<polyline points="{" ".join(segment)}" fill="none" '
            f'stroke="{color}" stroke-width="2.5" stroke-linejoin="round" '
            f'stroke-linecap="round" />'
        )

    # dots
    for x, y in points:
        if y is not None:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}" />')

    # x-axis labels (thin out if many points)
    n = len(labels)
    step = max(1, round(n / 7))
    for i, label in enumerate(labels):
        if i % step != 0 and i != n - 1:
            continue
        x = points[i][0]
        parts.append(
            f'<text x="{x:.1f}" y="{CHART_H - 6}" class="axis-label" text-anchor="middle">'
            f"{esc(label)}</text>"
        )

    parts.append("</svg>")
    return "".join(parts)


def svg_bar_chart(
    labels: list[str],
    values: list[float | None],
    color: str,
    unit: str = "",
    y_fmt: str = "{:.0f}",
) -> str:
    non_null = [v for v in values if v is not None]
    if not non_null:
        return '<p class="empty-msg">Brak danych do wykresu.</p>'

    y_max = max(non_null) * 1.15 or 1.0
    n = len(values)
    inner_w = CHART_W - PAD_L - PAD_R
    inner_h = CHART_H - PAD_T - PAD_B
    slot_w = inner_w / n
    bar_w = slot_w * 0.6

    parts = [
        f'<svg viewBox="0 0 {CHART_W} {CHART_H}" class="chart" role="img" '
        f'aria-label="Wykres słupkowy">'
    ]

    for frac in (0.0, 0.5, 1.0):
        gy = PAD_T + inner_h * (1 - frac)
        gv = y_max * frac
        parts.append(
            f'<line x1="{PAD_L}" y1="{gy:.1f}" x2="{CHART_W - PAD_R}" y2="{gy:.1f}" '
            f'class="grid-line" />'
        )
        parts.append(
            f'<text x="{PAD_L - 6}" y="{gy + 3:.1f}" class="axis-label" text-anchor="end">'
            f'{y_fmt.format(gv)}{unit}</text>'
        )

    step = max(1, round(n / 7))
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
                f'<text x="{x + bar_w / 2:.1f}" y="{CHART_H - 6}" class="axis-label" '
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
    total = sum(v for _, v, _ in segments if isinstance(v, (int, float)))
    width = 640
    height = 28

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


# --------------------------------------------------------------------------
# Tile builders
# --------------------------------------------------------------------------

def build_last_night_tile(records: list[dict[str, Any]]) -> str:
    with_sleep = [r for r in records if dig(r, "sleep", "total_seconds") is not None]
    if not with_sleep:
        return _card("Ostatnia noc", '<p class="empty-msg">Brak danych o śnie.</p>', extra_class="hero")

    r = with_sleep[-1]
    sleep = r.get("sleep") or {}
    d: date = r["_date"]

    total = fmt_hms(sleep.get("total_seconds"))
    score = sleep.get("score")
    qualifier = pl_word(SLEEP_QUALIFIER_PL, sleep.get("score_qualifier"))
    score_text = f"{int(score)}/100 &middot; {esc(qualifier)}" if score is not None else "brak danych"

    body = f'''
<div class="stat-row">
  <div class="stat-big">{total}</div>
  <div class="stat-sub">Ocena snu: <b>{score_text}</b></div>
</div>
{svg_phase_bar(sleep.get("deep_seconds"), sleep.get("light_seconds"), sleep.get("rem_seconds"), sleep.get("awake_seconds"))}
'''
    return _card(f"Ostatnia noc ({fmt_short_date(d)})", body, extra_class="hero")


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
    sub = (
        f'Ostatnia noc: <b>{latest:.0f} ms</b> &middot; {esc(pl_word(HRV_STATUS_PL, latest_status))}'
        if latest is not None
        else "Ostatnia noc: brak danych"
    )

    chart = svg_line_chart(labels, values, "var(--c-hrv)", unit=" ms", baseline_band=baseline_band)
    body = f'<p class="tile-sub">{sub}</p>{chart}'
    return _card("HRV — ostatnie 14 nocy", body)


def build_sleep_duration_tile(records: list[dict[str, Any]]) -> str:
    trend = records[-TREND_DAYS:]
    labels = [fmt_short_date(r["_date"]) for r in trend]
    values_sec = [dig(r, "sleep", "total_seconds") for r in trend]
    values_h = [v / 3600 if v is not None else None for v in values_sec]

    chart = svg_bar_chart(labels, values_h, "var(--c-sleep-bar)", unit="h", y_fmt="{:.1f}")
    return _card("Czas snu — ostatnie 14 nocy", chart)


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

  --c-deep: #7c6fe0;
  --c-light: #5fb3d9;
  --c-rem: #f2b84b;
  --c-awake: #5b6472;

  --c-hrv: #5b9dd9;
  --c-sleep-bar: #43c6ac;
}

@media (prefers-color-scheme: light) {
  :root {
    --bg: #f4f5f7;
    --bg-card: #ffffff;
    --text: #1a1d24;
    --text-dim: #5b6472;
    --border: #e2e5ea;
    --grid-line: #edeff3;
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
  padding: 28px 24px 8px;
  max-width: 1200px;
  margin: 0 auto;
}

header h1 {
  margin: 0 0 4px;
  font-size: 1.6rem;
  font-weight: 650;
}

header .meta {
  margin: 0;
  color: var(--text-dim);
  font-size: 0.85rem;
}

main.layout {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px 24px 48px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chart-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
  gap: 16px;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 18px 20px 14px;
}

.card h2 {
  margin: 0 0 10px;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.stat-row { margin-bottom: 10px; }

.stat-big {
  font-size: 2.4rem;
  font-weight: 650;
  line-height: 1.1;
}

.stat-sub, .tile-sub {
  color: var(--text-dim);
  font-size: 0.9rem;
  margin: 2px 0 10px;
}

.stat-sub b, .tile-sub b { color: var(--text); font-weight: 600; }

.dim { color: var(--text-dim); }

.chart { width: 100%; height: auto; display: block; }

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
  gap: 10px 16px;
  margin-top: 10px;
  font-size: 0.82rem;
}

.legend-item { display: inline-flex; align-items: center; gap: 6px; color: var(--text-dim); }

.legend-item i {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
}

.legend-item b { color: var(--text); font-weight: 600; }

.empty-msg { color: var(--text-dim); font-size: 0.9rem; padding: 20px 0; }

footer {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px 32px;
  color: var(--text-dim);
  font-size: 0.78rem;
}
"""


def build_html(records: list[dict[str, Any]]) -> str:
    if not records:
        layout = '<section class="card"><h2>Brak danych</h2><p class="empty-msg">' \
                 'Uruchom scripts/garmin_sync.py, aby pobrać dane z Garmin Connect.</p></section>'
    else:
        hero = build_last_night_tile(records)
        chart_row = (
            f'<div class="chart-row">'
            f"{build_sleep_duration_tile(records)}"
            f"{build_hrv_tile(records)}"
            f"</div>"
        )
        layout = hero + chart_row

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
    html = build_html(records)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Zapisano dashboard: {OUT_PATH} ({len(records)} dni danych, {len(html)} znaków).")


if __name__ == "__main__":
    main()
