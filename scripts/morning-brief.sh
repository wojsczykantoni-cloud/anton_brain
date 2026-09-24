#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

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
  echo "Utworzono nową notatkę: $NOTE_PATH"
fi

EVENTS="$(/usr/local/bin/ical today -o plain 2>/dev/null || true)"
if [ -z "$EVENTS" ]; then
  EVENTS="Brak wydarzeń w kalendarzu na dziś."
fi

# (b) wstaw wydarzenia do sekcji "## 📅 Plan dnia" (nadpisuje poprzednią zawartość sekcji)
awk -v events="$EVENTS" '
  /^## .*Plan dnia/ {
    print $0
    print events
    print ""
    in_section = 1
    next
  }
  in_section && /^## / { in_section = 0 }
  in_section { next }
  { print }
' "$NOTE_PATH" > "$NOTE_PATH.tmp" && mv "$NOTE_PATH.tmp" "$NOTE_PATH"

echo "Zaktualizowano sekcję Plan dnia w $NOTE_PATH"

# (c) wyślij podsumowanie na Telegram
MESSAGE="☀️ Dzień dobry! Plan na dziś ($TODAY):

$EVENTS

🎯 Pamiętaj, żeby ustawić priorytety na dziś w notatce."

RESPONSE="$(curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
  --data-urlencode "text=${MESSAGE}")"

if echo "$RESPONSE" | grep -q '"ok":true'; then
  echo "Wiadomość wysłana na Telegram."
else
  echo "Błąd wysyłki na Telegram: $RESPONSE" >&2
  exit 1
fi
