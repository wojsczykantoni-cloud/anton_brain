#!/bin/bash
# Wspólne funkcje dla skryptów zadań launchd (source "$(dirname "$0")/lib.sh").
# Przed source ustaw LOG_FILE. Każda linia logu dostaje datę i godzinę,
# a log jest rotowany (jedna kopia .1) po przekroczeniu 1 MB.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$PROJECT_DIR/.venv/bin/python"
STATUS="$PROJECT_DIR/scripts/status.py"
LOG_MAX_BYTES=1048576

mkdir -p "$PROJECT_DIR/logs"

rotate_log() {
  local f="$1" size
  [ -f "$f" ] || return 0
  size=$(stat -f %z "$f" 2>/dev/null || echo 0)
  if [ "$size" -gt "$LOG_MAX_BYTES" ]; then
    mv -f "$f" "$f.1"
  fi
}

ts() { date '+%Y-%m-%d %H:%M:%S'; }

log() {
  rotate_log "$LOG_FILE"
  echo "$(ts) $*" >> "$LOG_FILE"
}

# Prefiksuje każdą linię stdin datą i godziną i dopisuje do LOG_FILE.
ts_pipe() {
  local line
  while IFS= read -r line || [ -n "$line" ]; do
    printf '%s %s\n' "$(ts)" "$line" >> "$LOG_FILE"
  done
}

# run_logged <plik_na_wyjście> <komenda...>
# Uruchamia komendę, loguje jej stdout+stderr z czasem, kopię wyjścia zapisuje
# do pliku (żeby wyciągnąć komunikat błędu) i zwraca kod wyjścia komendy.
run_logged() {
  local out="$1"; shift
  rotate_log "$LOG_FILE"
  "$@" 2>&1 | tee "$out" | ts_pipe
  return "${PIPESTATUS[0]}"
}

# Ostatnia niepusta linia pliku - krótki opis błędu do status.json.
last_line() {
  grep -v '^[[:space:]]*$' "$1" 2>/dev/null | tail -1 | cut -c1-300
}

# Po wybudzeniu Maca sieć/DNS bywa niegotowa przez kilkadziesiąt sekund.
# Czeka do $1 sekund (domyślnie 120) na odpowiedź api.telegram.org.
wait_for_network() {
  local max="${1:-120}" waited=0
  while ! curl -sI --max-time 10 https://api.telegram.org >/dev/null 2>&1; do
    if [ "$waited" -ge "$max" ]; then
      log "Brak sieci/DNS po ${max} s."
      return 1
    fi
    sleep 10
    waited=$((waited + 10))
  done
  [ "$waited" -gt 0 ] && log "Sieć gotowa po ${waited} s."
  return 0
}

status_set() { "$PY" "$STATUS" set "$@" 2>&1 | ts_pipe; }
status_alert() { "$PY" "$STATUS" alert 2>&1 | ts_pipe; }

# Blokada przed równoległym przebiegiem tego samego zadania (np. RunAtLoad
# zbiegające się z terminem). Przeterminowana po 30 min.
acquire_lock() {
  LOCK_DIR="$PROJECT_DIR/logs/.lock-$1"
  if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    if [ -n "$(find "$LOCK_DIR" -maxdepth 0 -mmin +30 2>/dev/null)" ]; then
      rm -rf "$LOCK_DIR"
      mkdir "$LOCK_DIR" 2>/dev/null || return 1
    else
      return 1
    fi
  fi
  trap 'rm -rf "$LOCK_DIR"' EXIT
  return 0
}
