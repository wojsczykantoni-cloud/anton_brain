#!/usr/bin/env python3
"""Mapa sieci notatek vaulta - pomocnik skilli brain-ingest i brain-review.

  brain_net.py index             JSON: wpisy z inbox/ + istniejące huby (projekty,
                                 obszary, osoby) + nazwy wszystkich notatek
  brain_net.py review [--days N] raport tygodniowy: notatki bez linków, projekty
                                 bez aktywności od N dni (domyślnie 14), osoby bez
                                 kontekstu

Tylko czyta pliki - niczego nie zapisuje i nic nie wysyła.
"""
import argparse
import json
import re
import os
import sys
from datetime import date, datetime
from pathlib import Path

VAULT = Path(os.environ.get("BRAIN_VAULT") or Path(__file__).resolve().parent.parent)

# Foldery techniczne/generowane - nie są "notatkami" sieci.
SKIP_DIRS = {".git", ".obsidian", ".venv", ".claude", "node_modules", "data", "logs",
             "scripts", "templates", "__pycache__"}
GENERATED_DIRS = {"Trening", "Health"}  # generowane skryptami - pomijane w raporcie

HUB_TYPES = {"projects": "projekt", "areas": "obszar", "people": "osoba"}
INACTIVE_STATUSES = {"wstrzymany", "zakonczony", "zakończony"}

LINK_RE = re.compile(r"!?\[\[([^\]\n]+)\]\]")
FENCE_RE = re.compile(r"```.*?```", re.S)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_frontmatter(text):
    """Prosty parser YAML-owego frontmattera (klucz: wartość, [listy], - listy)."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw, body = text[4:end], text[end + 4:].lstrip("\n")
    data, key = {}, None
    for line in raw.splitlines():
        item = re.match(r"^\s+-\s*(.*)$", line)
        if item and key:
            if not isinstance(data.get(key), list):
                data[key] = []
            data[key].append(unquote(item.group(1)))
            continue
        kv = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not kv:
            continue
        key, value = kv.group(1), kv.group(2).strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            data[key] = [unquote(v) for v in split_list(inner)] if inner else []
        else:
            data[key] = unquote(value) if value else None
    return data, body


def split_list(inner):
    parts, buf, depth, quote = [], "", 0, None
    for ch in inner:
        if quote:
            buf += ch
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf += ch
        elif ch == "[":
            depth += 1
            buf += ch
        elif ch == "]":
            depth -= 1
            buf += ch
        elif ch == "," and depth == 0:
            parts.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        parts.append(buf.strip())
    return parts


def unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def link_target(raw):
    target = raw.split("|", 1)[0].split("#", 1)[0].strip()
    return Path(target).name.removesuffix(".md")


def links_in(text):
    return {link_target(m) for m in LINK_RE.findall(FENCE_RE.sub("", text))} - {""}


def words(text):
    text = FENCE_RE.sub("", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"^#+\s.*$", "", text, flags=re.M)
    return len(re.findall(r"\w+", text))


def as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def to_date(value):
    if isinstance(value, str) and DATE_RE.match(value[:10]):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def load_notes():
    notes = {}
    for path in sorted(VAULT.rglob("*.md")):
        rel = path.relative_to(VAULT)
        if set(rel.parts[:-1]) & SKIP_DIRS or rel.as_posix() == "CLAUDE.md":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        fm, body = parse_frontmatter(text)
        notes[rel.as_posix()] = {
            "path": rel.as_posix(),
            "name": path.stem,
            "top": rel.parts[0] if len(rel.parts) > 1 else "",
            "fm": fm,
            "body": body,
            "links": links_in(text),
            "mtime": date.fromtimestamp(path.stat().st_mtime),
        }
    return notes


def hubs(notes):
    result = {key: [] for key in HUB_TYPES}
    for note in notes.values():
        for folder, hub_type in HUB_TYPES.items():
            if note["top"] == folder and note["fm"].get("type") == hub_type:
                result[folder].append({
                    "name": note["name"],
                    "path": note["path"],
                    "status": note["fm"].get("status"),
                    "tags": as_list(note["fm"].get("tags")),
                    "aliases": as_list(note["fm"].get("aliases")),
                })
    return result


def cmd_index(notes):
    inbox = []
    for note in notes.values():
        if note["top"] != "inbox":
            continue
        inbox.append({
            "path": note["path"],
            "frontmatter": note["fm"],
            "words": words(note["body"]),
            "preview": re.sub(r"\s+", " ", note["body"])[:300],
        })
    print(json.dumps({
        "inbox": inbox,
        "hubs": hubs(notes),
        "notes": sorted({n["name"] for n in notes.values()}),
    }, ensure_ascii=False, indent=2, default=str))


def cmd_review(notes, days):
    today = date.today()
    names = {}
    for note in notes.values():
        names.setdefault(note["name"], note)

    backlinks = {name: set() for name in names}
    for note in notes.values():
        for target in note["links"]:
            if target in backlinks and target != note["name"]:
                backlinks[target].add(note["path"])

    # inbox/ czeka na brain-ingest - liczony osobno na końcu raportu.
    scope = [n for n in notes.values()
             if n["top"] not in GENERATED_DIRS | {"daily", "inbox"}]

    print(f"# Przegląd sieci — {today.isoformat()}\n")

    # 1. Notatki bez linków
    orphans, no_out = [], []
    for note in scope:
        out = {t for t in note["links"] if t in names and t != note["name"]}
        if out:
            continue
        (no_out if backlinks[note["name"]] else orphans).append(note)
    print(f"## Notatki bez linków ({len(orphans) + len(no_out)})")
    if not orphans and not no_out:
        print("- brak — wszystkie notatki są podpięte")
    for note in orphans:
        print(f"- 🔴 [[{note['name']}]] (`{note['path']}`) — żadnych linków, nikt tu nie linkuje")
    for note in no_out:
        print(f"- 🟡 [[{note['name']}]] (`{note['path']}`) — brak linków wychodzących "
              f"(linkuje tu {len(backlinks[note['name']])})")

    # 2. Projekty bez ostatniej aktywności
    print(f"\n## Projekty bez aktywności od {days} dni")
    projects = [n for n in notes.values()
                if n["top"] == "projects" and n["fm"].get("type") == "projekt"]
    stale = []
    for hub in projects:
        status = (hub["fm"].get("status") or "").lower()
        if status in INACTIVE_STATUSES:
            continue
        folder = str(Path(hub["path"]).parent)
        candidates = []  # (data, skąd)
        for note in notes.values():
            in_folder = folder != "projects" and note["path"].startswith(folder + "/")
            if in_folder or note is hub:
                candidates.append((note["mtime"], f"zmiana {note['name']}"))
            if hub["name"] in {link_target(p) for p in as_list(note["fm"].get("project"))}:
                d = to_date(note["fm"].get("created")) or note["mtime"]
                candidates.append((d, f"notatka {note['name']}"))
            if note["top"] == "daily" and hub["name"] in note["links"]:
                d = to_date(note["name"]) or note["mtime"]
                candidates.append((d, f"wzmianka w [[{note['name']}]]"))
        last, source = max(candidates, key=lambda c: c[0])
        idle = (today - last).days
        if idle >= days:
            stale.append((idle, hub, last, source))
    if not projects:
        print("- brak hubów projektów (`projects/<Projekt>/<Projekt>.md`, `type: projekt`)")
    elif not stale:
        print("- brak — każdy aktywny projekt ruszył się w tym okresie")
    for idle, hub, last, source in sorted(stale, key=lambda s: -s[0]):
        print(f"- [[{hub['name']}]] — ostatnio {last.isoformat()} ({idle} dni temu, {source})")

    # 3. Osoby bez kontekstu
    print("\n## Osoby bez kontekstu")
    people = [n for n in notes.values()
              if n["top"] == "people" and n["fm"].get("type") == "osoba"]
    lacking = []
    for person in people:
        reasons = []
        if words(person["body"]) < 8:
            reasons.append("pusty opis (kim jest, skąd znam)")
        refs = {p for p in backlinks[person["name"]] if not p.startswith("daily/")}
        if not as_list(person["fm"].get("project")) and not refs:
            reasons.append("brak projektu i notatek, które o niej wspominają")
        if reasons:
            lacking.append((person, reasons))
    if not people:
        print("- brak notatek osób (`people/<Imię Nazwisko>.md`, `type: osoba`)")
    elif not lacking:
        print("- brak — każda osoba ma opis i powiązania")
    for person, reasons in lacking:
        print(f"- [[{person['name']}]] — {'; '.join(reasons)}")

    # Kontekst: zaległości w inboxie
    pending = [n for n in notes.values()
               if n["top"] == "inbox" and (n["fm"].get("status") or "nowe") == "nowe"]
    print(f"\n## Inbox\n- {len(pending)} nieprzetworzonych wpisów"
          + (" — uruchom brain-ingest" if pending else ""))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("index")
    review = sub.add_parser("review")
    review.add_argument("--days", type=int, default=14)
    args = parser.parse_args()

    notes = load_notes()
    if args.cmd == "index":
        cmd_index(notes)
    else:
        cmd_review(notes, args.days)


if __name__ == "__main__":
    sys.exit(main())
