#!/bin/bash
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$PROJECT_DIR/logs/watchdog.log"
PLIST="$HOME/Library/LaunchAgents/com.antonbrain.telegrambot.plist"

if ps aux | grep "[n]ode bot.js" >/dev/null; then
    exit 0
fi

mkdir -p "$PROJECT_DIR/logs"

launchctl bootout "gui/$(id -u)" "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "$(date '+%Y-%m-%d %H:%M:%S') - bot nie działał, zrestartowano przez watchdog" >> "$LOG_FILE"
