require('dotenv').config();

const fs = require('fs');
const path = require('path');
const { execFile } = require('child_process');
const TelegramBot = require('node-telegram-bot-api');

const TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const CHAT_ID = String(process.env.TELEGRAM_CHAT_ID);

if (!TOKEN || !CHAT_ID) {
  console.error('Brak TELEGRAM_BOT_TOKEN lub TELEGRAM_CHAT_ID w pliku .env');
  process.exit(1);
}

const DAILY_DIR = path.join(__dirname, 'daily');
const TEMPLATE_PATH = path.join(__dirname, 'templates', 'daily.md');

const SECTIONS = {
  note: {
    heading: '## 💡 Pomysły / obserwacje',
    label: 'Pomysły / obserwacje',
    format: (text) => `- ${text}`,
  },
  priorytet: {
    heading: '## 🎯 Priorytety',
    label: 'Priorytety',
    format: (text) => `- [ ] ${text}`,
  },
  nauka: {
    heading: '## 📚 Studia / nauka',
    label: 'Studia / nauka',
    format: (text) => `- ${text}`,
  },
};

// Rozpoznaje proste polskie zwroty czasowe w tekście i sam wylicza z nich
// docelową datę/godzinę w JS (zamiast przekazywać `ical` surowe angielskie
// frazy do złożenia) - dzięki temu kombinacje typu "za 3 dni 9:00" dają
// jednoznaczny wynik, którego sam `ical` nie potrafiłby połączyć.
// To celowo prosty, heurystyczny parser (nie pełne NLP) - wystarczający do
// wyłuskania "jutro 14:00" itp. z końca/środka wiadomości.
// Uwaga: zwykłe \b nie rozpoznaje polskich znaków (ą, ę, ń, ó, ś, ł, ż, ź)
// jako części słowa, więc granice słów budujemy ręcznie przez \p{L}/\p{N}
// (wymaga flagi "u"), zamiast polegać na \b przy wyrazach typu "godzinę".
const NB = '(?<![\\p{L}\\p{N}])';
const NA = '(?![\\p{L}\\p{N}])';

function startOfDay(d) {
  const r = new Date(d);
  r.setHours(0, 0, 0, 0);
  return r;
}

function addDays(base, days) {
  const d = new Date(base);
  d.setDate(d.getDate() + days);
  return d;
}

// Najbliższe wystąpienie danego dnia tygodnia w przyszłości (nigdy "dziś") -
// zgodnie z konwencją "next monday"/"friday" z parsera ical (zawsze do przodu).
function nextWeekday(base, targetDow) {
  const d = new Date(base);
  const diff = ((targetDow - d.getDay()) + 7) % 7 || 7;
  d.setDate(d.getDate() + diff);
  return d;
}

// kind 'day'    -> data bazowa o północy, chyba że dopisano też godzinę
// kind 'offset' -> data bazowa liczona od "teraz" (zachowuje bieżącą godzinę,
//                  jak "za 3 dni" bez podanej godziny), chyba że dopisano godzinę
// kind 'time'   -> sama godzina, nadpisuje godzinę/minuty daty bazowej
const DATE_PATTERNS = [
  { kind: 'offset', re: new RegExp(`${NB}za\\s+(\\d+)\\s+dni\\p{L}*${NA}`, 'giu'), resolve: (m, n, now) => addDays(now, Number(n)) },
  { kind: 'offset', re: new RegExp(`${NB}za\\s+(\\d+)\\s+godzin\\p{L}*${NA}`, 'giu'), resolve: (m, n, now) => new Date(now.getTime() + Number(n) * 3600000) },
  { kind: 'offset', re: new RegExp(`${NB}za\\s+(\\d+)\\s+minut\\p{L}*${NA}`, 'giu'), resolve: (m, n, now) => new Date(now.getTime() + Number(n) * 60000) },
  { kind: 'offset', re: new RegExp(`${NB}za\\s+(\\d+)\\s+tyg\\p{L}*${NA}`, 'giu'), resolve: (m, n, now) => addDays(now, Number(n) * 7) },
  { kind: 'offset', re: new RegExp(`${NB}za\\s+p[oó][lł]\\s+godzin\\p{L}*${NA}`, 'giu'), resolve: (m, now) => new Date(now.getTime() + 30 * 60000) },
  { kind: 'offset', re: new RegExp(`${NB}za\\s+kwadrans${NA}`, 'giu'), resolve: (m, now) => new Date(now.getTime() + 15 * 60000) },
  { kind: 'offset', re: new RegExp(`${NB}za\\s+godzin[eę]${NA}`, 'giu'), resolve: (m, now) => new Date(now.getTime() + 3600000) },
  { kind: 'offset', re: new RegExp(`${NB}za\\s+tydzie[nń]${NA}`, 'giu'), resolve: (m, now) => addDays(now, 7) },
  { kind: 'day', re: new RegExp(`${NB}pojutrze${NA}`, 'giu'), resolve: (m, now) => startOfDay(addDays(now, 2)) },
  { kind: 'day', re: new RegExp(`${NB}(?:dzisiaj|dziś)${NA}`, 'giu'), resolve: (m, now) => startOfDay(now) },
  { kind: 'day', re: new RegExp(`${NB}jutro${NA}`, 'giu'), resolve: (m, now) => startOfDay(addDays(now, 1)) },
  { kind: 'day', re: new RegExp(`${NB}wczoraj${NA}`, 'giu'), resolve: (m, now) => startOfDay(addDays(now, -1)) },
  { kind: 'day', re: new RegExp(`${NB}poniedzia[lł]ek${NA}`, 'giu'), resolve: (m, now) => startOfDay(nextWeekday(now, 1)) },
  { kind: 'day', re: new RegExp(`${NB}wtorek${NA}`, 'giu'), resolve: (m, now) => startOfDay(nextWeekday(now, 2)) },
  { kind: 'day', re: new RegExp(`${NB}[sś]rod[eęya]${NA}`, 'giu'), resolve: (m, now) => startOfDay(nextWeekday(now, 3)) },
  { kind: 'day', re: new RegExp(`${NB}czwartek${NA}`, 'giu'), resolve: (m, now) => startOfDay(nextWeekday(now, 4)) },
  { kind: 'day', re: new RegExp(`${NB}pi[aą]tek${NA}`, 'giu'), resolve: (m, now) => startOfDay(nextWeekday(now, 5)) },
  { kind: 'day', re: new RegExp(`${NB}sobot[eęya]${NA}`, 'giu'), resolve: (m, now) => startOfDay(nextWeekday(now, 6)) },
  { kind: 'day', re: new RegExp(`${NB}niedziel[eęia]${NA}`, 'giu'), resolve: (m, now) => startOfDay(nextWeekday(now, 0)) },
  {
    kind: 'day',
    re: new RegExp(`${NB}(\\d{4})-(\\d{2})-(\\d{2})${NA}`, 'gu'),
    resolve: (m, y, mo, d) => new Date(Number(y), Number(mo) - 1, Number(d)),
  },
  {
    kind: 'time',
    re: new RegExp(`${NB}([01]?\\d|2[0-3])[:.]([0-5]\\d)${NA}`, 'gu'),
    resolve: (m, hh, mm) => ({ hour: Number(hh), minute: Number(mm) }),
  },
];

function pad2(n) {
  return String(n).padStart(2, '0');
}

// Format bez strefy czasowej ("YYYY-MM-DD HH:MM"), który `ical` interpretuje
// jako czas lokalny - jednoznaczny, w przeciwieństwie do angielskich fraz
// łączonych przez sam `ical` (stąd cała reszta liczenia dzieje się tutaj).
function formatIcalDateTime(d) {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

// Znajduje w tekście fragmenty pasujące do DATE_PATTERNS, wycina je z tekstu
// (dając tytuł wydarzenia) i wylicza z nich konkretną datę/godzinę.
function resolveEventDateTime(text, now = new Date()) {
  const matches = [];
  for (const pattern of DATE_PATTERNS) {
    pattern.re.lastIndex = 0;
    let m;
    while ((m = pattern.re.exec(text)) !== null) {
      matches.push({
        start: m.index,
        end: m.index + m[0].length,
        original: m[0],
        kind: pattern.kind,
        args: m,
        resolve: pattern.resolve,
      });
    }
  }

  if (matches.length === 0) {
    return null;
  }

  matches.sort((a, b) => a.start - b.start);

  // Usuń nakładające się dopasowania, zachowując pierwsze (po pozycji).
  const spans = [];
  let lastEnd = -1;
  for (const m of matches) {
    if (m.start >= lastEnd) {
      spans.push(m);
      lastEnd = m.end;
    }
  }

  const dayOrOffset = spans.find((s) => s.kind === 'day' || s.kind === 'offset');
  const timeSpan = spans.find((s) => s.kind === 'time');

  let target = dayOrOffset ? dayOrOffset.resolve(...dayOrOffset.args, now) : startOfDay(now);
  if (timeSpan) {
    const { hour, minute } = timeSpan.resolve(...timeSpan.args);
    target = new Date(target);
    target.setHours(hour, minute, 0, 0);
  }

  const minStart = spans[0].start;
  const maxEnd = spans[spans.length - 1].end;

  const title = (text.slice(0, minStart) + ' ' + text.slice(maxEnd))
    .replace(/\s+(w|we|o|na)\s*$/i, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  return {
    title: title || 'Wydarzenie',
    startIso: formatIcalDateTime(target),
    recognizedText: spans.map((s) => s.original).join(' '),
  };
}

// Bezpiecznie wywołuje `ical add` - execFile przekazuje argumenty jako
// tablicę bez powłoki, więc treść od użytkownika nie może wstrzyknąć
// dodatkowych poleceń ani flag interpretowanych przez shell.
function icalAdd(title, startExpr) {
  return new Promise((resolve, reject) => {
    execFile('ical', ['add', title, '--start', startExpr], (error, stdout, stderr) => {
      if (error) {
        const firstLine = (stderr || error.message).split('\n')[0].replace(/^Error:\s*/, '');
        reject(new Error(firstLine || 'nieznany błąd'));
        return;
      }
      resolve(stdout);
    });
  });
}

// Po utworzeniu wydarzenia doszukuje się go po tytule, żeby potwierdzić
// dokładny czas rozpoznany przez `ical` (a nie tylko nasze przypuszczenie).
function findCreatedEvent(title) {
  return new Promise((resolve) => {
    execFile(
      'ical',
      ['search', title, '--from', 'today', '--to', 'in 90 days', '-o', 'json'],
      (error, stdout) => {
        if (error) {
          resolve(null);
          return;
        }
        try {
          const events = JSON.parse(stdout);
          if (!Array.isArray(events) || events.length === 0) {
            resolve(null);
            return;
          }
          events.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
          resolve(events[0]);
        } catch {
          resolve(null);
        }
      }
    );
  });
}

function formatLocalDateTime(isoUtc) {
  const d = new Date(isoUtc);
  const pad = (n) => String(n).padStart(2, '0');
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// Szuka wydarzeń pasujących do fragmentu tytułu - execFile z argumentami
// jako tablicą, więc treść od użytkownika nie trafia do powłoki.
function icalSearch(query) {
  return new Promise((resolve, reject) => {
    execFile(
      'ical',
      ['search', query, '--from', '365 days ago', '--to', 'in 365 days', '-o', 'json'],
      (error, stdout, stderr) => {
        if (error) {
          const firstLine = (stderr || error.message).split('\n')[0].replace(/^Error:\s*/, '');
          reject(new Error(firstLine || 'nieznany błąd'));
          return;
        }
        try {
          const events = JSON.parse(stdout || '[]');
          resolve(Array.isArray(events) ? events : []);
        } catch {
          reject(new Error('Nie udało się odczytać wyniku wyszukiwania.'));
        }
      }
    );
  });
}

// Usuwa wydarzenie po pełnym ID (--id = dokładne dopasowanie, jedno
// wydarzenie) i bez interaktywnego potwierdzenia (--force), bo działamy
// z bota, nie z terminala.
function icalDeleteById(id) {
  return new Promise((resolve, reject) => {
    execFile('ical', ['delete', '--id', id, '--force'], (error, stdout, stderr) => {
      if (error) {
        const firstLine = (stderr || error.message).split('\n')[0].replace(/^Error:\s*/, '');
        reject(new Error(firstLine || 'nieznany błąd'));
        return;
      }
      resolve(stdout);
    });
  });
}

const bot = new TelegramBot(TOKEN, { polling: true });

function todayISO() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function dailyPathFor(dateStr) {
  return path.join(DAILY_DIR, `${dateStr}.md`);
}

function ensureDailyNote(dateStr) {
  const filePath = dailyPathFor(dateStr);
  if (!fs.existsSync(filePath)) {
    const template = fs.readFileSync(TEMPLATE_PATH, 'utf8');
    const content = template.replace('{{date}}', dateStr);
    fs.mkdirSync(DAILY_DIR, { recursive: true });
    fs.writeFileSync(filePath, content, 'utf8');
  }
  return filePath;
}

function appendToSection(dateStr, sectionKey, text) {
  const section = SECTIONS[sectionKey];
  const filePath = ensureDailyNote(dateStr);
  const content = fs.readFileSync(filePath, 'utf8');
  const lines = content.split('\n');
  const newLine = section.format(text);

  const headingIndex = lines.findIndex((line) => line.trim() === section.heading);
  if (headingIndex === -1) {
    // Sekcja nie istnieje w pliku - dopisz ją na końcu.
    const newLines = content.replace(/\n+$/, '').split('\n');
    newLines.push('', section.heading, newLine, '');
    fs.writeFileSync(filePath, newLines.join('\n'), 'utf8');
    return;
  }

  // Znajdź koniec sekcji: kolejny nagłówek "## " albo koniec pliku.
  let insertIndex = lines.length;
  for (let i = headingIndex + 1; i < lines.length; i++) {
    if (lines[i].startsWith('## ')) {
      insertIndex = i;
      break;
    }
  }

  // Wstaw nową linię tuż przed kolejnym nagłówkiem (lub na końcu pliku),
  // pomijając puste linie na końcu sekcji, żeby nie mnożyć odstępów.
  while (insertIndex > headingIndex + 1 && lines[insertIndex - 1].trim() === '') {
    insertIndex--;
  }

  lines.splice(insertIndex, 0, newLine);
  fs.writeFileSync(filePath, lines.join('\n'), 'utf8');
}

function readDailyNote(dateStr) {
  const filePath = dailyPathFor(dateStr);
  if (!fs.existsSync(filePath)) {
    return null;
  }
  return fs.readFileSync(filePath, 'utf8');
}

function isAuthorized(msg) {
  return String(msg.chat.id) === CHAT_ID;
}

// Telegram ogranicza wiadomości do 4096 znaków - dzielimy dłuższe treści.
async function sendLong(chatId, text) {
  const CHUNK_SIZE = 4000;
  if (text.length <= CHUNK_SIZE) {
    await bot.sendMessage(chatId, text);
    return;
  }
  for (let i = 0; i < text.length; i += CHUNK_SIZE) {
    await bot.sendMessage(chatId, text.slice(i, i + CHUNK_SIZE));
  }
}

bot.onText(/^\/brief$/, async (msg) => {
  if (!isAuthorized(msg)) return;

  const dateStr = todayISO();
  const content = readDailyNote(dateStr);

  if (!content) {
    await bot.sendMessage(msg.chat.id, `Brak notatki na dziś (${dateStr}).`);
    return;
  }

  await sendLong(msg.chat.id, content);
});

// Rejestruje komendę /<name> <tekst>, dopisującą tekst do danej sekcji.
function registerSectionCommand(name, sectionKey) {
  const regex = new RegExp(`^\\/${name}(?:@\\w+)?(?:\\s+([\\s\\S]+))?$`);
  bot.onText(regex, async (msg, match) => {
    if (!isAuthorized(msg)) return;

    const text = match[1] && match[1].trim();
    if (!text) {
      await bot.sendMessage(msg.chat.id, `Podaj treść, np. /${name} treść wiadomości.`);
      return;
    }

    const dateStr = todayISO();
    const section = SECTIONS[sectionKey];

    try {
      appendToSection(dateStr, sectionKey, text);
      await bot.sendMessage(msg.chat.id, `✅ Dodano do sekcji „${section.label}”.`);
    } catch (err) {
      console.error('Błąd przy zapisie notatki:', err);
      await bot.sendMessage(msg.chat.id, '❌ Nie udało się zapisać notatki.');
    }
  });
}

registerSectionCommand('priorytet', 'priorytet');
registerSectionCommand('nauka', 'nauka');
registerSectionCommand('note', 'note');

bot.onText(/^\/event(?:@\w+)?(?:\s+([\s\S]+))?$/, async (msg, match) => {
  if (!isAuthorized(msg)) return;

  const raw = match[1] && match[1].trim();
  if (!raw) {
    await bot.sendMessage(msg.chat.id, 'Podaj treść, np. /event Spotkanie z promotorem jutro 14:00.');
    return;
  }

  const parsed = resolveEventDateTime(raw);
  if (!parsed) {
    await bot.sendMessage(
      msg.chat.id,
      '❌ Nie rozpoznałem daty/godziny w treści. Spróbuj np. „jutro 14:00”, „za 2 dni”, „piątek 10:00” albo daty ISO (2026-03-15 14:00).'
    );
    return;
  }

  try {
    await icalAdd(parsed.title, parsed.startIso);
    const event = await findCreatedEvent(parsed.title);
    const whenLabel = event ? formatLocalDateTime(event.start_date) : parsed.recognizedText;
    await bot.sendMessage(msg.chat.id, `✅ Dodano wydarzenie „${parsed.title}” — ${whenLabel}.`);
  } catch (err) {
    console.error('Błąd przy tworzeniu wydarzenia:', err);
    await bot.sendMessage(msg.chat.id, `❌ Nie udało się utworzyć wydarzenia: ${err.message}`);
  }
});

bot.onText(/^\/usun(?:@\w+)?(?:\s+([\s\S]+))?$/, async (msg, match) => {
  if (!isAuthorized(msg)) return;

  const query = match[1] && match[1].trim();
  if (!query) {
    await bot.sendMessage(msg.chat.id, 'Podaj fragment tytułu, np. /usun spotkanie z promotorem.');
    return;
  }

  try {
    const events = await icalSearch(query);

    if (events.length === 0) {
      await bot.sendMessage(msg.chat.id, `Nie znaleziono wydarzenia pasującego do „${query}”.`);
      return;
    }

    if (events.length > 1) {
      const list = events
        .map((e) => `• ${e.title} — ${formatLocalDateTime(e.start_date)}`)
        .join('\n');
      await bot.sendMessage(
        msg.chat.id,
        `Znaleziono ${events.length} pasujących wydarzeń, podaj dokładniejszy fragment tytułu:\n${list}`
      );
      return;
    }

    const event = events[0];
    await icalDeleteById(event.id);
    await bot.sendMessage(
      msg.chat.id,
      `🗑️ Usunięto wydarzenie „${event.title}” — ${formatLocalDateTime(event.start_date)}.`
    );
  } catch (err) {
    console.error('Błąd przy usuwaniu wydarzenia:', err);
    await bot.sendMessage(msg.chat.id, `❌ Nie udało się usunąć wydarzenia: ${err.message}`);
  }
});

bot.on('message', async (msg) => {
  if (!isAuthorized(msg)) return;
  if (!msg.text) return; // interesują nas tylko wiadomości tekstowe
  if (msg.text.startsWith('/')) return; // komendy obsługujemy osobno

  const dateStr = todayISO();

  try {
    appendToSection(dateStr, 'note', msg.text);
    await bot.sendMessage(msg.chat.id, `✅ Dodano do sekcji „${SECTIONS.note.label}”.`);
  } catch (err) {
    console.error('Błąd przy zapisie notatki:', err);
    await bot.sendMessage(msg.chat.id, '❌ Nie udało się zapisać notatki.');
  }
});

bot.on('polling_error', (err) => {
  console.error('Polling error:', err.message);
});

console.log('Bot Telegram uruchomiony i nasłuchuje...');
