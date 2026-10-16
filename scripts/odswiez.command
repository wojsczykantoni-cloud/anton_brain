#!/bin/bash
# Ręczne odświeżenie danych z Findera (dwuklik): uruchamia refresh_all.sh,
# pokazuje wynik każdego kroku w oknie Terminala i czeka na klawisz.
cd "$(dirname "$0")/.." || exit 1

echo "Odświeżam dane (Garmin, Hevy, waga, dashboard)…"
echo

if [ -d logs/.lock-refresh ] && [ -z "$(find logs/.lock-refresh -maxdepth 0 -mmin +30 2>/dev/null)" ]; then
  echo "⏳ Odświeżanie już trwa (inny przebieg) - spróbuj za chwilę."
else
  START="$(date '+%Y-%m-%dT%H:%M:%S')"
  scripts/refresh_all.sh
  rc=$?

  # Wynik kroków zapisanych w data/status.json od startu tego przebiegu.
  .venv/bin/python - "$START" <<'PY'
import json, sys
start = sys.argv[1]
labels = {"garmin": "Garmin", "hevy": "Hevy", "hevy_csv": "Hevy CSV",
          "waga": "Waga", "dashboard": "Dashboard"}
icon = {"ok": "✅", "fail": "❌", "skip": "⏭️"}
try:
    steps = json.load(open("data/status.json")).get("steps", {})
except Exception:
    steps = {}
fix = None
shown = 0
for key, label in labels.items():
    st = steps.get(key)
    if not st or st.get("at", "") < start:
        continue
    shown += 1
    print(f"{icon.get(st.get('result'), '▫️')} {label} {st['at'][11:16]}  {st.get('message', '')}")
    if st.get("result") == "fail" and not fix:
        fix = st.get("fix")
if not shown:
    print("❌ Brak wyników kroków - szczegóły w logs/refresh.log")
if fix:
    print(f"\nNaprawa: {fix}")
PY
  echo
  [ "$rc" -eq 0 ] && echo "Gotowe." || echo "Zakończono z błędem (szczegóły: logs/refresh.log)."
fi

echo
read -n 1 -s -r -p "Naciśnij dowolny klawisz, aby zamknąć…"
echo
