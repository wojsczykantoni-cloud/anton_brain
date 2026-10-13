#!/bin/bash
# Jeden przebieg aktualizacji: Garmin -> waga -> dashboard.
# Wywoływany przez launchd (com.antonbrain.garminsync) o 11:20, 15:30, 21:00,
# przy logowaniu (RunAtLoad) i po wybudzeniu Maca, jeśli termin wypadł we śnie.
# Wynik każdego kroku trafia do data/status.json; przy awarii idzie alert na
# Telegram (najwyżej raz dziennie na krok) z komendą naprawczą.
set -uo pipefail

LOG_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/logs/refresh.log"
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
cd "$PROJECT_DIR"

if ! acquire_lock refresh; then
  log "Inny przebieg refresh_all trwa - pomijam."
  exit 0
fi
OUT="$(mktemp -t refresh_all)"
trap 'rm -rf "$LOCK_DIR" "$OUT"' EXIT

FIX_RUN="cd ~/anton_brain && scripts/refresh_all.sh"
FIX_LOGIN="cd ~/anton_brain && .venv/bin/python scripts/garmin_login.py && scripts/refresh_all.sh"
FAILED=0

log "=== Start refresh_all"

# 1. Garmin (nadrabia brakujące i niepełne dni z ostatnich 30+).
if wait_for_network 120; then
  run_logged "$OUT" "$PY" scripts/garmin_sync.py
  rc=$?
  case $rc in
    0) status_set garmin ok "$(last_line "$OUT")" ;;
    2) status_set garmin fail "Tokeny Garmin nieważne: $(last_line "$OUT")" --fix "$FIX_LOGIN"; FAILED=1 ;;
    *) status_set garmin fail "$(last_line "$OUT")" --fix "$FIX_RUN"; FAILED=1 ;;
  esac
else
  status_set garmin fail "Brak sieci/DNS przez 2 min (Mac w trybie uśpienia/bez Wi-Fi?)" --fix "$FIX_RUN"
  FAILED=1
fi

# 2. Waga - pusty lub niepoprawny waga.txt to "brak pomiaru", nie błąd (exit 0).
run_logged "$OUT" "$PY" scripts/import_waga.py
if [ $? -eq 0 ]; then
  status_set waga ok "$(last_line "$OUT")"
else
  status_set waga fail "$(last_line "$OUT")" --fix "cd ~/anton_brain && .venv/bin/python scripts/import_waga.py"
  FAILED=1
fi

# 3. Dashboard - zawsze, także po awarii Garmina (pokaże pasek "Dane nieaktualne").
run_logged "$OUT" "$PY" scripts/build_dashboard.py
if [ $? -eq 0 ]; then
  status_set dashboard ok "$(last_line "$OUT")"
else
  status_set dashboard fail "$(last_line "$OUT")" --fix "cd ~/anton_brain && .venv/bin/python scripts/build_dashboard.py"
  FAILED=1
fi

status_alert
log "=== Koniec refresh_all: $([ $FAILED -eq 0 ] && echo OK || echo 'BŁĄD (szczegóły wyżej)')"
exit $FAILED
