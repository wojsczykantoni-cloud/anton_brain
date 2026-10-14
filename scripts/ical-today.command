#!/bin/bash
# Odczyt kalendarza dla morning-brief.sh. Uruchamiany przez `open -a Terminal`,
# bo `ical` spod launchd dostaje "Calendar access denied", a Terminal ma dostęp
# do Kalendarza (jak start-bot.command dla bota).
#
# Zapisuje do logs/ical/: today.json, today.plain (wynik `ical today`),
# today.err (stderr) i today.rc (kody wyjścia "json plain"). Na końcu tworzy
# today.done: dopiero wtedy pozostałe pliki są kompletne.
#
# Okno zamyka się po odczycie: morning-brief.sh po przeczytaniu wyniku tworzy
# today.ack, a ten skrypt (najpóźniej po 120 s) zamyka własne okno przez
# osascript. Zamykanie idzie stąd, bo osascript spod launchd potrzebowałby
# zgody na sterowanie Terminalem (Automatyzacja) i wisiał na niej; procesy
# uruchomione w Terminalu sterują nim bez dodatkowej zgody.
cd "$(dirname "$0")/.." || exit 1

OUT_DIR="logs/ical"
ICAL_BIN="/usr/local/bin/ical"
mkdir -p "$OUT_DIR"

TTY="$(tty)"
: > "$OUT_DIR/today.err"
"$ICAL_BIN" today -o json > "$OUT_DIR/today.json" 2>> "$OUT_DIR/today.err"
rc_json=$?
"$ICAL_BIN" today -o plain > "$OUT_DIR/today.plain" 2>> "$OUT_DIR/today.err"
rc_plain=$?
echo "$rc_json $rc_plain" > "$OUT_DIR/today.rc"

date '+%Y-%m-%d %H:%M:%S' > "$OUT_DIR/today.done.tmp"
mv "$OUT_DIR/today.done.tmp" "$OUT_DIR/today.done"

for _ in $(seq 1 120); do
  [ -f "$OUT_DIR/today.ack" ] && break
  sleep 1
done

# Odłączony od terminala (setsid), żeby karta przestała być "zajęta", gdy ta
# powłoka się skończy; osascript czeka na to i zamyka okno bez pytania.
perl -MPOSIX -e 'fork and exit; POSIX::setsid(); exec @ARGV' osascript - "$TTY" \
  > /dev/null 2>&1 <<'OSA'
on run argv
  set targetTty to item 1 of argv
  delay 1
  tell application "Terminal"
    repeat with w in windows
      repeat with t in tabs of w
        if tty of t is targetTty then
          repeat 20 times
            if not (busy of t) then exit repeat
            delay 0.5
          end repeat
          close w saving no
          return
        end if
      end repeat
    end repeat
  end tell
end run
OSA
exit 0
