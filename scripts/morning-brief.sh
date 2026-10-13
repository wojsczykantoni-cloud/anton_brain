#!/bin/bash
# Morning brief: tworzy dzisiejszą notatkę, wpisuje wydarzenia z kalendarza do
# sekcji "Plan dnia" i wysyła podsumowanie na Telegram.
# launchd (com.antonbrain.morningbrief) uruchamia go o 7:00, przy logowaniu
# (RunAtLoad) i po wybudzeniu, jeśli 7:00 wypadła we śnie. Wiadomość idzie
# najwyżej raz dziennie i tylko przed 14:00 (chyba że podasz --force).
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

EVENTS="$(/usr/local/bin/ical today -o plain 2>/dev/null || true)"
if [ -z "$EVENTS" ]; then
  EVENTS="Brak wydarzeń w kalendarzu na dziś."
fi

# (b) wstaw wydarzenia do sekcji "## 📅 Plan dnia" (nadpisuje poprzednią zawartość sekcji).
# Wydarzenia idą przez ENVIRON, nie -v: awk -v nie przyjmuje znaków nowej linii
# ("awk: newline in string") i interpretuje odwrotne ukośniki.
if EVENTS="$EVENTS" awk '
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

# (c) wyślij podsumowanie na Telegram
MESSAGE="☀️ Dzień dobry! Plan na dziś ($TODAY):

$EVENTS

🎯 Pamiętaj, żeby ustawić priorytety na dziś w notatce."
# Limit Telegrama to 4096 znaków.
if [ "${#MESSAGE}" -gt 4000 ]; then
  MESSAGE="${MESSAGE:0:3950}
… (pełna lista w notatce dnia)"
fi

if ! wait_for_network 120; then
  status_set morning_brief fail "Brak sieci/DNS przez 2 min - brief niewysłany" --fix "$FIX"
  exit 1
fi

for attempt in $(seq 1 $CURL_ATTEMPTS); do
  RESPONSE="$(curl -sS --max-time 20 -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=${MESSAGE}" 2>&1)"
  if echo "$RESPONSE" | grep -q '"ok":true'; then
    log "Wiadomość wysłana na Telegram (próba $attempt)."
    status_set morning_brief ok "Wysłano (próba $attempt)"
    status_alert
    exit 0
  fi
  ERR="$(echo "$RESPONSE" | sed "s/${TELEGRAM_BOT_TOKEN}/***/g" | tr '\n' ' ' | cut -c1-300)"
  log "Wysyłka na Telegram, próba $attempt/$CURL_ATTEMPTS nieudana: $ERR"
  [ "$attempt" -lt $CURL_ATTEMPTS ] && sleep $CURL_PAUSE
done

status_set morning_brief fail "Telegram nie przyjął wiadomości po $CURL_ATTEMPTS próbach: $ERR" --fix "$FIX"
status_alert
exit 1
