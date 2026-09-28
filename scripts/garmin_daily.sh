#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

.venv/bin/python scripts/garmin_sync.py
# Best-effort: a malformed/unexpected waga.txt shouldn't block the Garmin
# sync's dashboard rebuild below.
.venv/bin/python scripts/import_waga.py || true
.venv/bin/python scripts/build_dashboard.py
