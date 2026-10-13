#!/bin/bash
# Co 3 min (launchd com.antonbrain.botwatchdog): jeśli nie działa ani bot, ani
# pętla restartu w start-bot.command, wskrzesza bota przez launchd.
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$PROJECT_DIR/logs/watchdog.log"
PLIST="$HOME/Library/LaunchAgents/com.antonbrain.telegrambot.plist"

if pgrep -f "node bot.js" >/dev/null || pgrep -f "scripts/start-bot.command" >/dev/null; then
    exit 0
fi

mkdir -p "$PROJECT_DIR/logs"
if [ -f "$LOG_FILE" ] && [ "$(stat -f %z "$LOG_FILE")" -gt 1048576 ]; then
    mv -f "$LOG_FILE" "$LOG_FILE.1"
fi

launchctl bootout "gui/$(id -u)" "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "$(date '+%Y-%m-%d %H:%M:%S') - bot nie działał, zrestartowano przez watchdog" >> "$LOG_FILE"
