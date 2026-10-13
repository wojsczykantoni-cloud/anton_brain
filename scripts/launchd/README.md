# launchd agents

Kopie referencyjne plistów launchd. Działające kopie leżą w
`~/Library/LaunchAgents/` - po zmianie pliku tutaj skopiuj go tam i przeładuj.

| Label | Co robi | Kiedy |
|---|---|---|
| `com.antonbrain.garminsync` | `scripts/refresh_all.sh`: Garmin → Hevy → waga → dashboard | 11:20, 15:30, 21:00, przy logowaniu (`RunAtLoad`), po wybudzeniu jeśli termin wypadł we śnie |
| `com.antonbrain.morningbrief` | `scripts/morning-brief.sh`: notatka dnia + brief na Telegram | 7:00, przy logowaniu, po wybudzeniu (wysyła najwyżej raz dziennie, tylko przed 14:00) |
| `com.antonbrain.telegrambot` | `open -a Terminal scripts/start-bot.command` (Terminal ma dostęp do Kalendarza dla `ical`); pętla restartuje `node bot.js` po kodzie ≠ 0 | przy logowaniu |
| `com.antonbrain.botwatchdog` | `scripts/bot_watchdog.sh`: wskrzesza bota, gdy nie działa ani bot, ani pętla restartu | co 3 min i przy logowaniu |

## Instalacja / przeładowanie po zmianie

```bash
cp scripts/launchd/com.antonbrain.*.plist ~/Library/LaunchAgents/
for l in garminsync morningbrief telegrambot botwatchdog; do
  launchctl bootout gui/$(id -u)/com.antonbrain.$l 2>/dev/null
  launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.antonbrain.$l.plist
done
```

## Diagnostyka

- `/status` w bocie: ostatni sukces, wynik kroków, stan zadań launchd, uptime bota.
- `data/status.json`: wynik każdego kroku (`garmin`, `hevy`, `waga`, `dashboard`, `morning_brief`) z komendą naprawczą.
- Logi (każda linia z datą, rotacja przy 1 MB): `logs/refresh.log`, `logs/morning-brief.log`, `logs/bot.log`, `logs/watchdog.log`; `logs/launchd-jobs.log` łapie tylko to, co wymknęło się skryptom.
- `launchctl print gui/$(id -u)/com.antonbrain.garminsync | grep -E "runs|last exit"`.
- Przy awarii kroku idzie alert na Telegram (raz dziennie na krok) z komendą naprawczą.
  Tokeny Garmin nieważne → `cd ~/anton_brain && .venv/bin/python scripts/garmin_login.py && scripts/refresh_all.sh`.
