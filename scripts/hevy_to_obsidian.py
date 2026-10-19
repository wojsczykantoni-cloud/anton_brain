#!/usr/bin/env python3
"""Hevy CSV -> Obsidian notes.

Uzycie:  python3 hevy_to_obsidian.py workout_data.csv "/sciezka/do/vaulta"
Tworzy / nadpisuje w vaultcie folder Trening/:
  Treningi/<data> <nazwa>.md   - jeden plik na trening
  Cwiczenia/<cwiczenie>.md     - historia i progresja na cwiczenie
  Dashboard.md                 - tonaz, serie, najlepsze e1RM
Bezpiecznie odpalac wielokrotnie na nowym eksporcie (pliki sa generowane od nowa).
"""
import csv, re, sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def parse_dt(s):
    d, mon, y, t = re.match(r"(\d+) (\w+) (\d+), (\d+:\d+)", s).groups()
    h, m = map(int, t.split(":"))
    return datetime(int(y), MONTHS[mon], int(d), h, m)


def fmt(x):
    return ("%g" % x).replace(".", ",")


def safe(name):
    return re.sub(r'[\\/:*?"<>|#^\[\]]', "-", name).strip()


def e1rm(w, r):
    return w * (1 + r / 30) if r else 0


def main(csv_path, vault):
    out = Path(vault) / "Trening"
    (out / "Treningi").mkdir(parents=True, exist_ok=True)
    (out / "Cwiczenia").mkdir(parents=True, exist_ok=True)

    workouts = {}
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["set_type"] == "warmup":
                continue
            key = (row["start_time"], row["title"])
            w = workouts.setdefault(key, {
                "title": row["title"],
                "start": parse_dt(row["start_time"]),
                "end": parse_dt(row["end_time"]),
                "ex": defaultdict(list)})
            w["ex"][row["exercise_title"]].append(
                (float(row["weight_kg"] or 0), int(row["reps"] or 0)))

    ordered = sorted(workouts.values(), key=lambda w: w["start"])
    history = defaultdict(list)  # exercise -> [(date, title, sets)]
    dash = []

    for w in ordered:
        date = w["start"].strftime("%Y-%m-%d")
        mins = int((w["end"] - w["start"]).total_seconds() // 60)
        n_sets = sum(len(s) for s in w["ex"].values())
        tonnage = sum(kg * r for s in w["ex"].values() for kg, r in s)
        name = f'{date} {safe(w["title"])}'
        lines = ["---", "type: trening", f"data: {date}", f'nazwa: "{w["title"]}"',
                 f"czas_min: {mins}", f"serie: {n_sets}", f"tonaz_kg: {fmt(tonnage)}",
                 "tags: [trening, hevy]", "---", "",
                 f'# {w["title"]} ({date})', "",
                 f"{mins} min | {n_sets} serii | tonaz {fmt(tonnage)} kg", ""]
        for ex, sets in w["ex"].items():
            lines.append(f"## [[{safe(ex)}]]")
            lines.append("| Seria | kg | powt. |")
            lines.append("|---|---|---|")
            for i, (kg, r) in enumerate(sets, 1):
                lines.append(f"| {i} | {fmt(kg)} | {r} |")
            lines.append("")
            history[ex].append((date, w["title"], sets))
        (out / "Treningi" / f"{name}.md").write_text("\n".join(lines), encoding="utf-8")
        dash.append((date, w["title"], mins, n_sets, tonnage, name))

    for ex, hist in history.items():
        best = max(e1rm(kg, r) for _, _, s in hist for kg, r in s)
        lines = ["---", "type: cwiczenie", f'nazwa: "{ex}"', "tags: [cwiczenie, hevy]", "---", "",
                 f"# {ex}", "", f"Najlepsze e1RM (Epley): **{fmt(round(best, 1))} kg**", "",
                 "| Data | Trening | Serie (kg x powt.) | Tonaz kg | Najlepsze e1RM |",
                 "|---|---|---|---|---|"]
        for date, title, sets in hist:
            sets_s = ", ".join(f"{fmt(kg)}x{r}" for kg, r in sets)
            ton = sum(kg * r for kg, r in sets)
            b = max(e1rm(kg, r) for kg, r in sets)
            lines.append(f"| {date} | {title} | {sets_s} | {fmt(ton)} | {fmt(round(b, 1))} |")
        (out / "Cwiczenia" / f"{safe(ex)}.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["---", "type: dashboard", "tags: [trening, hevy]", "---", "", "# Dashboard treningowy", "",
             "Analiza i wskazówki trenera: [[Analiza trenera]]", "",
             "| Data | Trening | Czas (min) | Serie | Tonaz kg |", "|---|---|---|---|---|"]
    for date, title, mins, n, ton, name in dash:
        lines.append(f"| {date} | [[{name}\\|{title}]] | {mins} | {n} | {fmt(ton)} |")
    lines += ["", "## Najlepsze e1RM per cwiczenie", "", "| Cwiczenie | e1RM kg |", "|---|---|"]
    for ex, hist in sorted(history.items()):
        best = max(e1rm(kg, r) for _, _, s in hist for kg, r in s)
        lines.append(f"| [[{safe(ex)}]] | {fmt(round(best, 1))} |")
    (out / "Dashboard.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"OK: {len(ordered)} treningow, {len(history)} cwiczen -> {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])