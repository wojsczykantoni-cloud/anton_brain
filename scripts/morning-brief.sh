#!/bin/bash
# Morning brief: tworzy dzisiejszą notatkę, wpisuje wydarzenia z kalendarza do
# sekcji "Plan dnia" i wysyła podsumowanie na Telegram.
# launchd (com.antonbrain.morningbrief) uruchamia go o 7:00, przy logowaniu
# (RunAtLoad) i po wybudzeniu, jeśli 7:00 wypadła we śnie. Wiadomość idzie
# najwyżej raz dziennie i tylko przed 14:00 (chyba że podasz --force).
# Kalendarz czyta scripts/ical-today.command uruchamiany przez `open -a Terminal`
# (`ical` spod launchd dostaje "Calendar access denied", Terminal ma dostęp):
# skrypt czeka do 60 s na wynik w logs/ical/, a po odczycie daje znać, że okno
# Terminala można zamknąć (logs/ical/today.ack).
# Odczyt jest ponawiany do 5 razy co 30 s, a stderr każdej nieudanej próby trafia
# do logu. Jeśli kalendarz dalej nie odpowiada, brief idzie z linią "kalendarz
# chwilowo niedostępny", a skrypt czeka 20 min (z --force 2 min) na jedną
# dodatkową próbę: jeśli się uda, uzupełnia "Plan dnia" w notatce i wysyła samą
# sekcję kalendarza.
set -uo pipefail

LOG_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/logs/morning-brief.log"
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
cd "$PROJECT_DIR"

FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1
FIX="cd ~/anton_brain && scripts/morning-brief.sh --force"
SEND_DEADLINE_HOUR=14
CURL_ATTEMPTS=5
CURL_PAUSE=30
ICAL_COMMAND="$PROJECT_DIR/scripts/ical-today.command"
ICAL_OUT="$PROJECT_DIR/logs/ical"
ICAL_WAIT=60
ICAL_RETRIES=5
ICAL_PAUSE="${ICAL_PAUSE:-30}"
# Z --force (ręczne uruchomienie z terminala) dodatkowa próba po 2 min, nie 20.
if [ $FORCE -eq 1 ]; then
  CAL_RETRY_DELAY="${CAL_RETRY_DELAY:-120}"
else
  CAL_RETRY_DELAY="${CAL_RETRY_DELAY:-1200}"
fi

if ! acquire_lock morningbrief; then
  log "Inny przebieg morning brief trwa - pomijam."
  exit 0
fi

set -a
source .env
set +a

TODAY="$(date +%Y-%m-%d)"
DAILY_DIR="$PROJECT_DIR/daily"
NOTE_PATH="$DAILY_DIR/$TODAY.md"
TEMPLATE_PATH="$PROJECT_DIR/templates/daily.md"

mkdir -p "$DAILY_DIR"

# (a) utwórz dzisiejszą notatkę z szablonu, jeśli jeszcze nie istnieje
if [ ! -f "$NOTE_PATH" ]; then
  sed "s/{{date}}/$TODAY/" "$TEMPLATE_PATH" > "$NOTE_PATH"
  log "Utworzono nową notatkę: $NOTE_PATH"
fi

if [ $FORCE -eq 0 ] && "$PY" "$STATUS" ok-today morning_brief; then
  log "Morning brief już wysłany dziś - pomijam."
  exit 0
fi
if [ $FORCE -eq 0 ] && [ "$(date +%-H)" -ge $SEND_DEADLINE_HOUR ]; then
  log "Po ${SEND_DEADLINE_HOUR}:00 - nie wysyłam porannego briefu (ręcznie: scripts/morning-brief.sh --force)."
  status_set morning_brief skip "Pominięty: przebieg po ${SEND_DEADLINE_HOUR}:00 (brief wysyłany tylko rano)"
  exit 0
fi

CAL_DIR="$(mktemp -d -t morningbrief)"
trap 'rm -rf "$LOCK_DIR" "$CAL_DIR"' EXIT

# Sygnał dla ical-today.command, że wynik przeczytany: okno Terminala zamyka
# się wtedy samo (z wnętrza Terminala - osascript spod launchd wisiałby na
# zgodzie na sterowanie Terminalem).
close_ical_window() {
  touch "$ICAL_OUT/today.ack"
}

# Jedna próba odczytu kalendarza przez Terminal: JSON (dla wiadomości) i plain
# (dla notatki). Błąd = brak wyniku po ICAL_WAIT s, kod wyjścia ical różny od 0,
# cokolwiek na stderr albo JSON nie do odczytu; dokładny stderr ical idzie do
# logu, każda linia z datą.
ical_once() {
  local rc_json rc_plain waited=0
  mkdir -p "$ICAL_OUT"
  rm -f "$ICAL_OUT"/today.*
  if ! open -a Terminal "$ICAL_COMMAND" 2> "$CAL_DIR/open.err"; then
    log "open -a Terminal ical-today.command nieudane: $(tr '\n' ' ' < "$CAL_DIR/open.err")"
    return 1
  fi
  while [ ! -f "$ICAL_OUT/today.done" ]; do
    if [ $waited -ge $ICAL_WAIT ]; then
      log "ical-today.command: brak wyniku po ${ICAL_WAIT} s."
      close_ical_window
      return 1
    fi
    sleep 1
    waited=$((waited + 1))
  done
  read -r rc_json rc_plain < "$ICAL_OUT/today.rc"
  cp "$ICAL_OUT/today.json" "$CAL_DIR/events.json"
  cp "$ICAL_OUT/today.plain" "$CAL_DIR/events.plain"
  cp "$ICAL_OUT/today.err" "$CAL_DIR/err"
  close_ical_window
  log "Wynik ical-today.command z Terminala po ${waited} s."
  if [ "${rc_json:-1}" != 0 ] || [ "${rc_plain:-1}" != 0 ] || [ -s "$CAL_DIR/err" ]; then
    log "ical today: kody wyjścia json=${rc_json:-?} plain=${rc_plain:-?}, stderr:"
    ts_pipe < "$CAL_DIR/err"
    return 1
  fi
  if ! "$PY" -c 'import json, sys; json.load(sys.stdin)' < "$CAL_DIR/events.json" 2> /dev/null; then
    log "ical today -o json: kod wyjścia 0, ale wynik nie jest poprawnym JSON-em."
    return 1
  fi
  return 0
}

# Pierwsza próba + do ICAL_RETRIES ponowień co ICAL_PAUSE s.
fetch_calendar() {
  local attempt total=$((ICAL_RETRIES + 1))
  for attempt in $(seq 1 $total); do
    if ical_once; then
      [ "$attempt" -gt 1 ] && log "Kalendarz odczytany w próbie $attempt/$total."
      return 0
    fi
    if [ "$attempt" -lt $total ]; then
      log "Kalendarz, próba $attempt/$total nieudana - ponawiam za ${ICAL_PAUSE} s."
      sleep "$ICAL_PAUSE"
    fi
  done
  log "Kalendarz niedostępny po $total próbach."
  return 1
}

# (b) wstaw tekst do sekcji "## 📅 Plan dnia" (nadpisuje poprzednią zawartość sekcji).
# Tekst idzie przez ENVIRON, nie -v: awk -v nie przyjmuje znaków nowej linii
# ("awk: newline in string") i interpretuje odwrotne ukośniki.
write_plan() {
  if EVENTS="$1" awk '
    /^## .*Plan dnia/ {
      print $0
      print ENVIRON["EVENTS"]
      print ""
      in_section = 1
      next
    }
    in_section && /^## / { in_section = 0 }
    in_section { next }
    { print }
  ' "$NOTE_PATH" > "$NOTE_PATH.tmp" 2> >(ts_pipe); then
    mv "$NOTE_PATH.tmp" "$NOTE_PATH"
    log "Zaktualizowano sekcję Plan dnia w $NOTE_PATH"
  else
    rm -f "$NOTE_PATH.tmp"
    log "Nie udało się zaktualizować sekcji Plan dnia (wysyłam wiadomość mimo to)."
  fi
}

# Wysyła $1 na Telegram (CURL_ATTEMPTS prób co CURL_PAUSE s). Ustawia
# SENT_ATTEMPT przy sukcesie, ERR przy porażce.
send_message() {
  local attempt response
  for attempt in $(seq 1 $CURL_ATTEMPTS); do
    response="$(curl -sS --max-time 20 -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
      --data-urlencode "text=$1" 2>&1)"
    if echo "$response" | grep -q '"ok":true'; then
      SENT_ATTEMPT=$attempt
      return 0
    fi
    ERR="$(echo "$response" | sed "s/${TELEGRAM_BOT_TOKEN}/***/g" | tr '\n' ' ' | cut -c1-300)"
    log "Wysyłka na Telegram, próba $attempt/$CURL_ATTEMPTS nieudana: $ERR"
    [ "$attempt" -lt $CURL_ATTEMPTS ] && sleep $CURL_PAUSE
  done
  return 1
}

# Jedna dodatkowa próba kalendarza CAL_RETRY_DELAY s po wysłaniu briefu.
# Czeka według zegara ściennego, więc uśpienie Maca nie wydłuża odstępu.
calendar_followup() {
  local target=$(( $(date +%s) + CAL_RETRY_DELAY )) msg
  log "Dodatkowa próba kalendarza o $(date -r "$target" '+%H:%M')."
  while [ "$(date +%s)" -lt "$target" ]; do
    sleep 30
  done
  if ! ical_once; then
    log "Dodatkowa próba kalendarza nieudana - sekcja kalendarza nie zostanie dosłana."
    return 1
  fi
  write_plan "$(cat "$CAL_DIR/events.plain")"
  if ! msg="$("$PY" scripts/brief_message.py "$NOTE_PATH" --events-json "$CAL_DIR/events.json" --calendar-only 2> >(ts_pipe))"; then
    log "Nie udało się złożyć sekcji kalendarza."
    return 1
  fi
  if wait_for_network 120 && send_message "$msg"; then
    log "Dosłano sekcję kalendarza na Telegram (próba $SENT_ATTEMPT)."
    return 0
  fi
  log "Nie udało się dosłać sekcji kalendarza."
  return 1
}

if fetch_calendar; then
  CAL_OK=1
  EVENTS="$(cat "$CAL_DIR/events.plain")"
  [ -z "$EVENTS" ] && EVENTS="Brak wydarzeń w kalendarzu na dziś."
  BRIEF_ARGS=(--events-json "$CAL_DIR/events.json")
else
  CAL_OK=0
  EVENTS="Kalendarz chwilowo niedostępny - spróbuję ponownie za $((CAL_RETRY_DELAY / 60)) min."
  BRIEF_ARGS=(--calendar-unavailable)
fi

write_plan "$EVENTS"

# (c) wyślij podsumowanie na Telegram (treść składa scripts/brief_message.py)
if ! MESSAGE="$("$PY" scripts/brief_message.py "$NOTE_PATH" "${BRIEF_ARGS[@]}" 2> >(ts_pipe))"; then
  status_set morning_brief fail "Nie udało się złożyć treści briefu (szczegóły w logs/morning-brief.log)" --fix "$FIX"
  status_alert
  exit 1
fi
# Limit Telegrama to 4096 znaków.
if [ "${#MESSAGE}" -gt 4000 ]; then
  MESSAGE="${MESSAGE:0:3950}
… (pełna lista w notatce dnia)"
fi

if ! wait_for_network 120; then
  status_set morning_brief fail "Brak sieci/DNS przez 2 min - brief niewysłany" --fix "$FIX"
  exit 1
fi

if send_message "$MESSAGE"; then
  log "Wiadomość wysłana na Telegram (próba $SENT_ATTEMPT)."
  status_set morning_brief ok "Wysłano (próba $SENT_ATTEMPT)"
  status_alert
  [ $CAL_OK -eq 0 ] && calendar_followup
  exit 0
fi

status_set morning_brief fail "Telegram nie przyjął wiadomości po $CURL_ATTEMPTS próbach: $ERR" --fix "$FIX"
status_alert
exit 1
