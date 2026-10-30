# anton_brain — zasady vaulta

Vault Obsidiana Antka (kim jestem: [[o-mnie]]). Wszystko ma tworzyć **jedną sieć**:
każda notatka jest podpięta linkiem `[[...]]` do projektu, obszaru, osoby albo dnia.
Notatki i rozmowy prowadzimy po polsku.

## Struktura folderów

| Folder | Co tu trafia |
|---|---|
| `inbox/` | Surowe wpisy do przetworzenia: wiadomości z bota, `/link`, klipy z Obsidian Web Clipper. Nic tu nie zostaje na stałe — porządkuje to skill `brain-ingest`. |
| `projects/` | Projekty z celem i końcem. Każdy projekt to folder `projects/<Projekt>/` z notatką-hubem `<Projekt>.md` (`type: projekt`) i notatkami, które go dotyczą. |
| `areas/` | Obszary ciągłe, bez końca (studia, finanse, nauka AI…). Tak samo jak projekty: `areas/<Obszar>/<Obszar>.md` (`type: obszar`) + notatki. `areas/Studia/<Przedmiot>/` to hub przedmiotu z notatkami ze studiów. `areas/Trening/` jest **generowany** przez `scripts/hevy_to_obsidian.py` (nie edytuj ręcznie Treningi/ i Cwiczenia/). |
| `people/` | Jedna notatka na osobę: `people/<Imię Nazwisko>.md` (`type: osoba`) — kim jest, skąd ją znam, w jakich projektach się pojawia. |
| `daily/` | Notatki dzienne `YYYY-MM-DD.md` z szablonu `templates/daily.md` (pisze do nich bot i morning brief). |
| `templates/` | Szablony notatek. |

Pozostałe foldery są techniczne albo generowane — nie zakładaj w nich ręcznie notatek:
`Health/` (generują skrypty z Garmin), `Clippings/` (stare klipy sprzed
inboxu), `data/` i `logs/` (poza gitem), `scripts/`, `bot.js` (bot Telegram).

## Frontmatter

Każda notatka poza `daily/` ma frontmatter:

```yaml
---
type: notatka          # wpis | link | clip | notatka | pomysl | projekt | obszar | osoba
tags: [ecommerce, ai]  # małe litery, kebab-case, bez "#"
project: ["[[Sklep sezonowy]]"]   # lista linków do hubów z projects/ lub areas/; [] gdy brak
people: ["[[Jan Kowalski]]"]      # lista linków do people/; [] gdy brak
created: 2026-10-26    # data powstania treści (YYYY-MM-DD), nie data przeniesienia
---
```

Pola dodatkowe, gdy mają sens:
- `status` — w inboxie `nowe` → po przetworzeniu `przetworzone`; w hubach projektów
  `aktywny` | `wstrzymany` | `zakonczony`.
- `source` — URL albo `telegram`; przy linkach i klipach **zawsze zostaje**.
- `title`, `author`, `published`, `description`, `time` — zostawiamy, jeśli przyszły z bota
  lub Web Clippera.

## Nazwy plików

- Nazwa = tytuł notatki po polsku, z wielkiej litery, ze spacjami: `Sklep sezonowy.md`.
- Notatki związane z datą zaczynają się od daty ISO: `2026-10-26 Rozmowa z dostawcą.md`.
  Bot nadaje plikom w inboxie nazwę `YYYY-MM-DD HHmmss <początek treści>.md`.
- Bez znaków `: / \ # ^ [ ] | ? * " < >` (psują pliki albo linki Obsidiana).
- Nazwy muszą być unikalne w całym vaulcie — linkujemy po samej nazwie.

## Linkowanie

- Linkuj po nazwie pliku bez folderu i rozszerzenia: `[[Sklep sezonowy]]`, alias przez
  `|`: `[[Jan Kowalski|Janek]]`.
- Linkuj tylko do notatek, które **istnieją**. Nowy projekt/osobę zakładamy świadomie,
  a nie przez wpisanie linku „na zapas".
- Powiązania z projektem/osobą trzymamy we frontmatterze (`project`, `people`) i
  dodatkowo w treści, gdy coś konkretnego się do nich odnosi.
- Dzień łączymy przez `[[YYYY-MM-DD]]` (np. „ustalone na [[2026-10-26]]").
- Przy porządkowaniu notatek nie dopisujemy faktów, których nie ma w źródle — tylko
  strukturę, tagi i linki.

## Dane zdrowotne nie trafiają do notatek

Waga, kalorie i makro, sen, tętno, kroki, choroby, leki, wyniki badań itp. **nie są
zapisywane w notatkach** (`inbox/`, `projects/`, `areas/`, `people/`, `daily/`).
Trzymają je wyłącznie `data/` (poza gitem) i komendy bota (`/waga`, `/dzien`, `/cel`), a
pokazują generowane widoki w `Health/` i `areas/Trening/`.

Jeśli wpis w inboxie zawiera dane zdrowotne — nie przenosimy go, tylko zgłaszamy i
proponujemy usunięcie (albo zapis przez komendę bota). Nie klipujemy stron zdrowotnych
ani stron po zalogowaniu (bankowość, poczta, panele kont).

## Bot Telegram (`bot.js`)

- Zwykła wiadomość (bez komendy) → nowy plik w `inbox/` (`type: wpis`, data, godzina, treść).
- `/link <url>` → pobiera stronę przez defuddle (`node_modules/defuddle`) i zapisuje w
  `inbox/` tytuł, `source` i pełną treść artykułu w `## Treść` (ucinaną po ~30 000 znaków).
  `## Streszczenie` zostaje „do uzupełnienia (brain-ingest)". Gdy pobranie się nie uda
  albo strona wymaga logowania, zapisuje tylko tytuł i `source`, a bot pisze o tym w odpowiedzi.
- `/note`, `/priorytet`, `/nauka` dalej dopisują do sekcji dzisiejszej notatki w `daily/`.
- Restart: zakończ proces z `data/bot.pid` (`kill $(cat data/bot.pid)`) — pętla w
  `scripts/start-bot.command` uruchomi go ponownie po 10 s.

## Skille

- `brain-ingest` — porządkuje `inbox/` (typ, projekt/osoba, frontmatter, linki, przeniesienie);
  zawsze najpierw pokazuje listę zmian do akceptacji.
- `brain-review` — tygodniowy przegląd sieci: notatki bez linków, projekty bez aktywności,
  osoby bez kontekstu.
