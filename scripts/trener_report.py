#!/usr/bin/env python3
"""Writes Health/trener-raport.md: an 8-week training summary for a human
and for Claude (the "trener" skill reads it before every analysis).

Usage (from repo root, using the project venv):

    .venv/bin/python scripts/trener_report.py [--out PATH | --stdout]

Sections: workouts and regularity, progress per exercise (e1RM, trend,
double-progression status), records, working sets per muscle group vs the
target range, weekly volume, steps, average sleep, weight trend and logged
kcal / macros. Data only - no recommendations, and nothing about nutrition
beyond what was logged (targets are set by hand with /cel).

Reuses the loaders of build_dashboard.py and the analytics of
training_analytics.py, so the numbers match the dashboard. The report holds
health data, so Health/trener-raport.md is in .gitignore; this script
prints only the output path.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import build_dashboard as bd
import training_analytics as ta

WEEKS = 8
OUT_PATH = bd.REPO_ROOT / "Health" / "trener-raport.md"


def _d(d: date) -> str:
    return f"{d.day:02d}.{d.month:02d}"


def _kg(v: float | None) -> str:
    return f"{bd._fmt_kg(v)} kg" if v is not None else "—"


def _avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def _weeks(start: date, today: date) -> list[date]:
    """Mondays of every calendar week touching the window (first and last may be partial)."""
    first = bd._week_start(start)
    return [first + timedelta(weeks=i) for i in range((bd._week_start(today) - first).days // 7 + 1)]


def _week_label(wk: date, start: date, today: date) -> str:
    if wk < start:
        return f"{_d(wk)} (od {_d(start)})"
    if wk == bd._week_start(today):
        return f"{_d(wk)} (w toku)"
    return _d(wk)


def _n(n: int, one: str, few: str, many: str) -> str:
    return f"{n} {ta.plural_pl(n, one, few, many)}"


def section_workouts(workouts: list[ta.Workout], start: date, today: date) -> list[str]:
    in_window = [w for w in workouts if start <= w.day <= today]
    lines = ["## Treningi i regularność"]
    if not in_window:
        return lines + [f"- Brak sesji w ostatnich {WEEKS} tygodniach."]
    last = in_window[-1]
    per_week = {wk: 0 for wk in _weeks(start, today)}
    for w in in_window:
        wk = bd._week_start(w.day)
        if wk in per_week:
            per_week[wk] += 1
    titles: dict[str, list[str]] = {}
    for w in in_window:
        titles.setdefault(ta.normalize_title(w.title), []).append(w.title)
    days_sorted = sorted({w.day for w in in_window})
    gaps = [(b - a).days for a, b in zip(days_sorted, days_sorted[1:])]
    ago = {0: "dziś", 1: "wczoraj"}.get((today - last.day).days, f"{(today - last.day).days} dni temu")
    week_cells = " · ".join(f"{_week_label(wk, start, today)}: {n}" for wk, n in per_week.items())
    lines += [
        f"- Sesje: **{len(in_window)}** w {WEEKS} tyg. (śr. {len(in_window) / WEEKS:.1f}/tydz.), "
        f"dni treningowe: {len(days_sorted)}",
        f"- Ostatnia: {last.title}, {_d(last.day)} ({ago}), "
        f"{_n(len(last.exercises), 'ćwiczenie', 'ćwiczenia', 'ćwiczeń')}, "
        f"{_n(last.set_count, 'seria robocza', 'serie robocze', 'serii roboczych')}",
        f"- Sesje na tydzień (od pon.): {week_cells}",
        "- Tytuły: " + ", ".join(f"{v[-1]} ×{len(v)}" for v in titles.values()),
        f"- Najdłuższa przerwa między sesjami: {max(gaps)} dni" if gaps else "- Jedna sesja w oknie - brak przerw do policzenia",
    ]
    return lines


def section_progress(workouts: list[ta.Workout], cfg: ta.Config, start: date, today: date) -> list[str]:
    lines = [
        "## Progres ćwiczeń",
        f"Status wg podwójnej progresji (widełki domyślnie {cfg.rep_range[0]}–{cfg.rep_range[1]}, "
        f"stagnacja = {cfg.stagnation_sessions}+ sesji bez progresu). Trend e1RM liniowy, od "
        f"{ta.TREND_MIN_SESSIONS} sesji w oknie.",
        "",
        "| Ćwiczenie | Partia | Sesje | Ostatnio | Ostatnie serie robocze | e1RM ostatni / max | Zmiana e1RM w oknie | Trend /4 tyg. | Widełki | Status |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    rows = []
    for ex_id, sessions in ta.exercise_history(workouts).items():
        window = [s for s in sessions if start <= s.day <= today]
        if not window:
            continue
        last = window[-1]
        e_pts = [s for s in window if s.best_e1rm is not None]
        e_last = e_pts[-1].best_e1rm if e_pts else None
        e_max = max((s.best_e1rm for s in e_pts), default=None)
        change = "—"
        if len(e_pts) >= 2:
            change = bd._fmt_delta(e_pts[-1].best_e1rm - e_pts[0].best_e1rm) + f" ({_d(e_pts[0].day)}→{_d(e_pts[-1].day)})"
        trend = "—"
        if len(e_pts) >= ta.TREND_MIN_SESSIONS:
            fit = ta.linear_trend([(s.day, s.best_e1rm) for s in e_pts])
            if fit:
                trend = bd._fmt_delta(fit[1] * 28)
        rr = cfg.rep_range_for(ex_id, last.name)
        p = ta.progression(sessions, rr, cfg.stagnation_sessions)
        status = ta.status_label(p) if p else "—"
        if p and p.status == "reps" and p.below_range:
            status += " (poniżej widełek)"
        rows.append((len(window), last.day, (
            f"| {last.name} | {ta.MUSCLE_GROUP_PL.get(last.muscle, last.muscle)} | {len(window)} | {_d(last.day)} | "
            f"{bd._fmt_sets(last.sets)} | {_kg(e_last)} / {_kg(e_max)} | {change} | {trend} | {rr[0]}–{rr[1]} | {status} |"
        )))
    if not rows:
        return lines[:1] + ["- Brak ćwiczeń w oknie."]
    rows.sort(key=lambda r: (-r[0], -r[1].toordinal()))
    return lines + [r[2] for r in rows]


def section_records(workouts: list[ta.Workout], start: date, today: date) -> list[str]:
    recent_from = today - timedelta(days=ta.RECENT_RECORD_DAYS - 1)
    lines = [f"## Rekordy ustanowione w ostatnich {WEEKS} tyg. (★ = ostatnie 4 tyg.)"]
    items = []
    for r in ta.records(workouts):
        parts = []
        if start <= r.best_set_day <= today:
            parts.append(f"najlepsza seria {bd._fmt_set(r.best_set)} ({_d(r.best_set_day)}{' ★' if r.best_set_day >= recent_from else ''})")
        if r.best_e1rm_day and start <= r.best_e1rm_day <= today:
            parts.append(f"e1RM {_kg(r.best_e1rm_set.e1rm)} z {bd._fmt_set(r.best_e1rm_set)} "
                         f"({_d(r.best_e1rm_day)}{' ★' if r.best_e1rm_day >= recent_from else ''})")
        if parts:
            items.append(f"- {r.name}: " + "; ".join(parts))
    first = min((w.day for w in workouts), default=None)
    if first and first >= start:
        lines.append(f"- Uwaga: dane z Hevy zaczynają się {_d(first)} - każda pierwsza sesja ćwiczenia jest rekordem z definicji.")
    return lines + (items or ["- Brak nowych rekordów w oknie."])


def section_sets(workouts: list[ta.Workout], cfg: ta.Config, start: date, today: date) -> list[str]:
    lines = [
        "## Serie robocze na partię vs zakres docelowy",
        "Partia główna ćwiczenia; zakres z data/hevy_config.json.",
        "",
        f"| Partia | Ostatnie 7 dni | Śr./tydz. ({WEEKS} tyg.) | Zakres | Status (7 dni) |",
        "|---|---|---|---|---|",
    ]
    totals: dict[str, int] = {}
    for w in workouts:
        if start <= w.day <= today:
            for ex in w.exercises:
                totals[ex.muscle] = totals.get(ex.muscle, 0) + len(ex.sets)
    groups = {g.muscle: g for g in ta.weekly_muscle_sets(workouts, cfg, today)}
    status_pl = {"low": "poniżej", "ok": "w zakresie", "high": "powyżej"}
    muscles = sorted(set(groups) | set(totals), key=lambda m: -totals.get(m, 0))
    if not muscles:
        return lines[:1] + ["- Brak serii w oknie."]
    for m in muscles:
        lo, hi = cfg.weekly_sets_for(m)
        cur = groups[m].sets if m in groups else 0
        status = status_pl["low" if cur < lo else "high" if cur > hi else "ok"]
        lines.append(f"| {ta.MUSCLE_GROUP_PL.get(m, m)} | {cur} | {totals.get(m, 0) / WEEKS:.1f} | {lo}–{hi} | {status} |")
    return lines


def section_volume(workouts: list[ta.Workout], start: date, today: date) -> list[str]:
    lines = ["## Objętość tygodniowa (ciężar × powtórzenia, serie robocze)"]
    weeks: dict[date, float] = {}
    muscles: dict[str, float] = {}
    for w in workouts:
        if start <= w.day <= today:
            wk = bd._week_start(w.day)
            for ex in w.exercises:
                weeks[wk] = weeks.get(wk, 0.0) + ex.volume
                muscles[ex.muscle] = muscles.get(ex.muscle, 0.0) + ex.volume
    if not weeks:
        return lines + ["- Brak danych."]
    lines.append("- Tygodnie (od pon.): " + " · ".join(
        f"{_week_label(wk, start, today)}: {bd._thousands(weeks.get(wk, 0))} kg" for wk in _weeks(start, today)))
    top = sorted(muscles.items(), key=lambda kv: -kv[1])
    lines.append(f"- Suma {WEEKS} tyg. per partia: " + " · ".join(
        f"{ta.MUSCLE_GROUP_PL.get(m, m)} {bd._thousands(v)} kg" for m, v in top))
    return lines


def section_recovery(records: list[dict[str, Any]], weights: list[tuple[date, float]], start: date, today: date) -> list[str]:
    lines = ["## Aktywność, sen, waga"]
    full_days = _days(start, today - timedelta(days=1))
    by_date = {r["_date"]: r for r in records}
    steps = [by_date[d].get("steps") for d in full_days if d in by_date and isinstance(by_date[d].get("steps"), (int, float))]
    steps_7 = [by_date[d].get("steps") for d in full_days[-7:] if d in by_date and isinstance(by_date[d].get("steps"), (int, float))]
    if steps:
        lines.append(
            f"- Kroki (pełne dni): śr. {bd._thousands(_avg(steps))}/dzień z {len(steps)} dni z danymi; "
            f"ostatnie 7 dni śr. {bd._thousands(_avg(steps_7)) if steps_7 else '—'}; dni ≥ 10 000: {sum(s >= 10000 for s in steps)}"
        )
    else:
        lines.append("- Kroki: brak danych Garmin w oknie.")

    nights = _days(start, today)
    sleep = [bd.dig(by_date[d], "sleep", "total_seconds") for d in nights if d in by_date]
    sleep = [s for s in sleep if isinstance(s, (int, float))]
    sleep_7 = [bd.dig(by_date[d], "sleep", "total_seconds") for d in nights[-7:] if d in by_date]
    sleep_7 = [s for s in sleep_7 if isinstance(s, (int, float))]
    if sleep:
        lines.append(
            f"- Sen: śr. {bd.fmt_hms(_avg(sleep))} z {len(sleep)} nocy; ostatnie 7 nocy śr. "
            f"{bd.fmt_hms(_avg(sleep_7)) if sleep_7 else '—'}; nocy ≥ 7 h: {sum(s >= 7 * 3600 for s in sleep)}"
        )
    else:
        lines.append("- Sen: brak danych Garmin w oknie.")

    in_window = [(d, kg) for d, kg in weights if start <= d <= today]
    if len(in_window) >= 2:
        (d0, w0), (d1, w1) = in_window[0], in_window[-1]
        fit = ta.linear_trend(in_window)
        trend = f"; trend liniowy {bd._fmt_delta(fit[1] * 7)}/tydz." if fit else ""
        lines.append(
            f"- Waga: {_kg(w0)} ({_d(d0)}) → {_kg(w1)} ({_d(d1)}), zmiana {bd._fmt_delta(w1 - w0)}{trend}; "
            f"pomiarów: {len(in_window)}"
        )
    elif in_window:
        lines.append(f"- Waga: jeden pomiar w oknie - {_kg(in_window[0][1])} ({_d(in_window[0][0])}).")
    else:
        lines.append("- Waga: brak pomiarów w oknie.")
    return lines


def section_food(food_by_date: dict[str, dict[str, Any]], targets: dict[str, Any] | None, start: date, today: date) -> list[str]:
    lines = ["## Odżywianie - zalogowane dane (/dzien), bez ocen"]
    days = _days(start, today)
    logged = [(d, food_by_date[d.isoformat()]) for d in days if d.isoformat() in food_by_date]
    if not logged:
        return lines + ["- Brak zalogowanych dni w oknie."]

    def avg_line(items: list[tuple[date, dict[str, Any]]]) -> str:
        parts = []
        for key, label, unit in (("kcal", "kcal", ""), ("protein", "B", " g"), ("carbs", "W", " g"), ("fat", "T", " g")):
            vals = [r[key] for _, r in items if isinstance(r.get(key), (int, float))]
            parts.append(f"{label} {_avg(vals):.0f}{unit}" if vals else f"{label} —")
        return ", ".join(parts)

    last7 = [(d, r) for d, r in logged if d > today - timedelta(days=7)]
    lines.append(f"- Dni zalogowane: {len(logged)} z {len(days)}")
    lines.append(f"- Średnio z dni zalogowanych: {avg_line(logged)}")
    lines.append(f"- Ostatnie 7 dni ({len(last7)} zalogowanych): {avg_line(last7) if last7 else '—'}")
    if targets:
        t = ", ".join(f"{label} {targets[k]:.0f}{unit}" for k, label, unit in (
            ("kcal", "kcal", ""), ("protein", "B", " g"), ("carbs", "W", " g"), ("fat", "T", " g"),
        ) if isinstance(targets.get(k), (int, float)))
        if t:
            lines.append(f"- Cele ustawione przez /cel (kontekst, nie do zmiany przez trenera): {t}")
    return lines


def build_report(today: date | None = None) -> str:
    today = today or date.today()
    start = today - timedelta(days=WEEKS * 7 - 1)
    workouts = ta.load_workouts(bd.HEVY_DIR)
    cfg = ta.load_config(bd.HEVY_CONFIG_PATH)
    records = bd.load_records()
    weights = ta.load_bodyweights(bd.WEIGHT_PATH)
    head = [
        f"# Raport trenera — {WEEKS} tygodni ({_d(start)}–{_d(today)}.{today.year})",
        "",
        f"Wygenerowano {datetime.now():%Y-%m-%d %H:%M}. Źródła: Hevy (data/hevy), Garmin, /dzien, /waga. "
        "Serie robocze = bez rozgrzewek; e1RM = Epley, ciężar × (1 + powt./30). Same dane, bez zaleceń.",
    ]
    sections = [
        section_workouts(workouts, start, today),
        section_progress(workouts, cfg, start, today),
        section_records(workouts, start, today),
        section_sets(workouts, cfg, start, today),
        section_volume(workouts, start, today),
        section_recovery(records, weights, start, today),
        section_food(bd.load_food_records(), bd.load_targets(), start, today),
    ]
    return "\n\n".join(["\n".join(head)] + ["\n".join(s) for s in sections]) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Raport treningowy z ostatnich 8 tygodni (Markdown).")
    out = parser.add_mutually_exclusive_group()
    out.add_argument("--out", type=Path, default=OUT_PATH, help=f"plik wynikowy (domyślnie {OUT_PATH})")
    out.add_argument("--stdout", action="store_true", help="wypisz raport zamiast zapisywać")
    args = parser.parse_args()
    report = build_report()
    if args.stdout:
        print(report, end="")
        return
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(f"Zapisano raport: {args.out}")


if __name__ == "__main__":
    main()
