#!/usr/bin/env python3
"""Shared run-status bookkeeping for the automated jobs (data/status.json).

Usage (from repo root, using the project venv):

    .venv/bin/python scripts/status.py set <step> <ok|fail|skip> [message] [--fix CMD]
    .venv/bin/python scripts/status.py ok-today <step>   # exit 0 if <step> succeeded today
    .venv/bin/python scripts/status.py alert             # Telegram alert for failed steps

data/status.json keeps, per step (garmin, waga, dashboard, morning_brief, ...),
the result of the latest run, its message, the time of the last success and a
concrete fix command. ``alert`` sends ONE Telegram message listing every step
whose latest result is "fail" and that has not been alerted about yet today;
a step is only marked as alerted once the message actually went out, so an
alert that failed for lack of network is retried by the next job run.
"""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parent.parent
STATUS_PATH = REPO_ROOT / "data" / "status.json"
LOCK_PATH = REPO_ROOT / "data" / ".status.lock"
ENV_PATH = REPO_ROOT / ".env"
HEVY_CSV_STATE_PATH = REPO_ROOT / "data" / "hevy" / "csv_import.json"
HEVY_CSV_STALE_DAYS = 10

STEP_LABELS = {
    "network": "Sieć",
    "garmin": "Garmin",
    "hevy": "Hevy",
    "hevy_csv": "Hevy CSV",
    "waga": "Waga",
    "dashboard": "Dashboard",
    "morning_brief": "Morning brief",
}


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


@contextmanager
def locked_status() -> Iterator[dict[str, Any]]:
    """Read-modify-write data/status.json under an exclusive file lock."""
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_PATH, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        status = load_status()
        yield status
        status["updated_at"] = now_iso()
        tmp = STATUS_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(STATUS_PATH)


def load_status() -> dict[str, Any]:
    try:
        data = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("steps", {})
            data.setdefault("alerts_sent", {})
            return data
    except (OSError, ValueError):
        pass
    return {"steps": {}, "alerts_sent": {}}


def cmd_set(args: list[str]) -> int:
    fix = None
    if "--fix" in args:
        i = args.index("--fix")
        fix = args[i + 1] if i + 1 < len(args) else None
        args = args[:i] + args[i + 2 :]
    if len(args) < 2 or args[1] not in ("ok", "fail", "skip"):
        print("Użycie: status.py set <step> <ok|fail|skip> [message] [--fix CMD]", file=sys.stderr)
        return 64
    step, result = args[0], args[1]
    message = args[2] if len(args) > 2 else ""

    with locked_status() as status:
        entry = status["steps"].setdefault(step, {})
        entry.update({"result": result, "message": message, "at": now_iso(), "fix": fix})
        if result == "ok":
            entry["last_success"] = entry["at"]
            # A recovered step may alert again on its next failure today.
            status["alerts_sent"].pop(step, None)
    return 0


def cmd_ok_today(args: list[str]) -> int:
    if not args:
        return 64
    entry = load_status()["steps"].get(args[0]) or {}
    last = entry.get("last_success") or ""
    return 0 if last[:10] == datetime.now().strftime("%Y-%m-%d") else 1


def read_env() -> dict[str, str]:
    env: dict[str, str] = {}
    try:
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return env


def send_telegram(text: str, attempts: int = 3, pause: float = 10.0) -> bool:
    env = read_env()
    token = env.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = env.get("TELEGRAM_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Brak TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID - nie wysyłam alertu.", file=sys.stderr)
        return False
    # System curl (Keychain trust store, like morning-brief.sh) rather than
    # urllib, whose bundled CA list can reject the chain. The URL with the
    # token goes in via stdin (-K -) so it never shows up in `ps`.
    config = f'url = "https://api.telegram.org/bot{token}/sendMessage"\n'
    cmd = [
        "curl", "-sS", "--max-time", "20", "-K", "-",
        "--data-urlencode", f"chat_id={chat_id}",
        "--data-urlencode", f"text={text}",
    ]
    for attempt in range(1, attempts + 1):
        try:
            res = subprocess.run(cmd, input=config, capture_output=True, text=True, timeout=30)
            if '"ok":true' in res.stdout:
                return True
            err = (res.stderr or res.stdout).strip().replace(token, "***")[:300]
        except Exception as exc:  # noqa: BLE001 - any failure means "retry"
            err = str(exc)
        print(f"Wysyłka alertu, próba {attempt}/{attempts} nieudana: {err}", file=sys.stderr)
        if attempt < attempts:
            time.sleep(pause)
    return False


def hevy_csv_hint(status: dict[str, Any]) -> str | None:
    """Hint for the alert when Hevy data comes from the CSV fallback and the
    newest export (data/hevy/csv_import.json) is over 10 days old."""
    entry = status["steps"].get("hevy_csv") or {}
    if entry.get("result") not in ("ok", "fail"):
        return None  # API works, or there's no CSV at all
    try:
        csv_state = json.loads(HEVY_CSV_STATE_PATH.read_text(encoding="utf-8"))
        mtime = datetime.strptime(csv_state["newest_mtime"], "%Y-%m-%dT%H:%M:%S")
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if datetime.now() - mtime <= timedelta(days=HEVY_CSV_STALE_DAYS):
        return None
    age = (datetime.now() - mtime).days
    return (
        f"💡 Hevy: najnowszy CSV ({csv_state.get('newest_file')}) ma {age} dni - wyeksportuj "
        "świeży (Hevy → Profil → Ustawienia → Eksportuj dane) do głównego katalogu iCloud Drive."
    )


def cmd_alert(_args: list[str]) -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    status = load_status()
    pending = [
        (step, entry)
        for step, entry in status["steps"].items()
        if entry.get("result") == "fail" and status["alerts_sent"].get(step) != today
    ]
    if not pending:
        return 0

    lines = ["⚠️ anton_brain: awaria automatycznej aktualizacji", ""]
    for step, entry in pending:
        label = STEP_LABELS.get(step, step)
        last_ok = entry.get("last_success")
        last_ok_txt = (
            datetime.strptime(last_ok, "%Y-%m-%dT%H:%M:%S").strftime("%d.%m %H:%M")
            if last_ok
            else "nigdy"
        )
        lines.append(f"• {label}: {entry.get('message') or 'błąd'} (ostatni sukces: {last_ok_txt})")
        if entry.get("fix"):
            lines.append(f"  Naprawa: {entry['fix']}")
    hint = hevy_csv_hint(status)
    if hint:
        lines += ["", hint]
    lines += ["", "Szczegóły: /status w bocie, logi w ~/anton_brain/logs/"]

    if not send_telegram("\n".join(lines)):
        print("Nie udało się wysłać alertu - spróbuję przy następnym przebiegu.", file=sys.stderr)
        return 0
    with locked_status() as fresh:
        for step, _ in pending:
            fresh["alerts_sent"][step] = today
    print(f"Wysłano alert ({', '.join(s for s, _ in pending)}).")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 64
    commands = {"set": cmd_set, "ok-today": cmd_ok_today, "alert": cmd_alert}
    handler = commands.get(sys.argv[1])
    if handler is None:
        print(f"Nieznana komenda: {sys.argv[1]}", file=sys.stderr)
        return 64
    return handler(sys.argv[2:])


if __name__ == "__main__":
    sys.exit(main())
