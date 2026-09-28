# launchd agents

Kopie referencyjne plistów launchd używanych do uruchamiania bota Telegram i
morning brief. Trzymane w repo dla historii/backupu — same w sobie nie są
przez macOS wykonywane stąd.

## Gdzie mają leżeć w systemie

```
~/Library/LaunchAgents/com.antonbrain.telegrambot.plist
~/Library/LaunchAgents/com.antonbrain.morningbrief.plist
```

## Instalacja / aktualizacja

Skopiuj plik z repo do `~/Library/LaunchAgents/`, a potem załaduj go w launchd:

```bash
cp scripts/launchd/com.antonbrain.telegrambot.plist ~/Library/LaunchAgents/
cp scripts/launchd/com.antonbrain.morningbrief.plist ~/Library/LaunchAgents/

launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.antonbrain.telegrambot.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.antonbrain.morningbrief.plist
```

## Przeładowanie po zmianie pliku

```bash
launchctl bootout gui/$(id -u)/com.antonbrain.telegrambot
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.antonbrain.telegrambot.plist

launchctl bootout gui/$(id -u)/com.antonbrain.morningbrief
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.antonbrain.morningbrief.plist
```

## Sprawdzenie statusu

```bash
launchctl list | grep antonbrain
```

`com.antonbrain.telegrambot` uruchamia się przez `open -a Terminal` na
`scripts/start-bot.command` (bez `KeepAlive` — nie restartuje się sam po
crashu, tylko przy kolejnym logowaniu przez `RunAtLoad`).

`com.antonbrain.morningbrief` uruchamia się codziennie o 7:00
(`StartCalendarInterval`) przez `scripts/morning-brief.sh`.
