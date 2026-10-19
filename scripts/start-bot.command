#!/bin/bash
# Uruchamiany przez launchd (com.antonbrain.telegrambot) przez `open -a Terminal`,
# bo `ical` w bocie potrzebuje uprawnień Terminala do Kalendarza.
cd ~/anton_brain || exit 1

export NVM_DIR="$HOME/.nvm"
export PATH="$NVM_DIR/versions/node/v24.15.0/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Kontrolowany restart: bot kończy się kodem != 0 (np. 75 po 15 min bez sieci
# albo po crashu) - uruchamiamy go ponownie po 10 s. Kod 0 kończy pętlę -
# także gdy bot już działa (blokada data/bot.pid): druga kopia wychodzi od
# razu z komunikatem w logs/bot.log, zamiast działać obok pierwszej.
while true; do
  node bot.js
  code=$?
  [ "$code" -eq 0 ] && break
  echo "$(date '+%Y-%m-%d %H:%M:%S') bot zakończył się kodem $code - restart za 10 s" | tee -a logs/bot.log
  sleep 10
done
