require('dotenv').config();

const fs = require('fs');
const os = require('os');
const path = require('path');
const util = require('util');
const { execFile, execFileSync } = require('child_process');
const TelegramBot = require('node-telegram-bot-api');

// Każda linia logu z datą i godziną: na konsolę (okno Terminala) i do
// logs/bot.log, rotowanego (jedna kopia .1) po przekroczeniu 1 MB.
const BOT_LOG_PATH = path.join(__dirname, 'logs', 'bot.log');
const LOG_MAX_BYTES = 1024 * 1024;

function timestamp(d = new Date()) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
    `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function appendBotLog(text) {
  try {
    fs.mkdirSync(path.dirname(BOT_LOG_PATH), { recursive: true });
    try {
      if (fs.statSync(BOT_LOG_PATH).size > LOG_MAX_BYTES) {
        fs.renameSync(BOT_LOG_PATH, `${BOT_LOG_PATH}.1`);
      }
    } catch (_) { /* brak pliku - nic do rotacji */ }
    fs.appendFileSync(BOT_LOG_PATH, text);
  } catch (_) { /* logowanie nie może wywrócić bota */ }
}

for (const level of ['log', 'error']) {
  const original = console[level].bind(console);
  console[level] = (...args) => {
    const line = `${timestamp()} ${level === 'error' ? 'ERROR ' : ''}${util.format(...args)}`;
    original(line);
    appendBotLog(`${line}\n`);
  };
}

process.on('unhandledRejection', (err) => {
  console.error('Nieobsłużony błąd (promise):', err && err.message ? err.message : err);
});

const TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const CHAT_ID = String(process.env.TELEGRAM_CHAT_ID);

if (!TOKEN || !CHAT_ID) {
  console.error('Brak TELEGRAM_BOT_TOKEN lub TELEGRAM_CHAT_ID w pliku .env');
  process.exit(1);
}

// --- Jedna instancja ---------------------------------------------------------
// Dwa procesy na tym samym tokenie kradną sobie getUpdates (409 Conflict)
// i oba odpowiadają na wiadomości. Blokada: data/bot.pid z PID działającego
// bota. Druga kopia kończy się kodem 0 - start-bot.command nie restartuje jej
// w pętli. Plik po martwym procesie (albo po PID zajętym już przez inny
// program) jest przejmowany.
const PID_PATH = path.join(__dirname, 'data', 'bot.pid');

function isBotProcess(pid) {
  try {
    process.kill(pid, 0);
  } catch (err) {
    if (err.code !== 'EPERM') return false;
  }
  try {
    const command = execFileSync('ps', ['-p', String(pid), '-o', 'command='], { encoding: 'utf8' });
    return /\bbot\.js\b/.test(command);
  } catch (_) {
    return false;
  }
}

function readPidFile() {
  try {
    return parseInt(fs.readFileSync(PID_PATH, 'utf8'), 10) || null;
  } catch (_) {
    return null;
  }
}

function acquireSingleInstanceLock() {
  fs.mkdirSync(path.dirname(PID_PATH), { recursive: true });
  // Plik tymczasowy + link: blokada powstaje atomowo i od razu z PID w środku,
  // więc równoległy start nigdy nie zobaczy pustego pliku.
  const tmpPath = `${PID_PATH}.${process.pid}.tmp`;
  fs.writeFileSync(tmpPath, `${process.pid}\n`);
  try {
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        fs.linkSync(tmpPath, PID_PATH);
        return readPidFile() === process.pid;
      } catch (err) {
        if (err.code !== 'EEXIST') throw err;
      }
      const otherPid = readPidFile();
      if (otherPid && otherPid !== process.pid && isBotProcess(otherPid)) {
        console.error(`Bot już działa (PID ${otherPid}, blokada ${PID_PATH}) - ta kopia (PID ${process.pid}) kończy pracę.`);
        return false;
      }
      console.log(`Nieaktualna blokada ${PID_PATH} (PID ${otherPid || 'brak'} nie działa) - przejmuję.`);
      if (readPidFile() === otherPid) {
        try { fs.unlinkSync(PID_PATH); } catch (_) { /* ktoś usunął pierwszy */ }
      }
    }
    console.error(`Nie udało się przejąć blokady ${PID_PATH} - kończę.`);
    return false;
  } finally {
    try { fs.unlinkSync(tmpPath); } catch (_) { /* już usunięty */ }
  }
}

if (!acquireSingleInstanceLock()) {
  process.exit(0);
}

process.on('exit', () => {
  if (readPidFile() === process.pid) {
    try { fs.unlinkSync(PID_PATH); } catch (_) { /* już usunięty */ }
  }
});

// Bez własnych handlerów sygnały zabijają proces z pominięciem 'exit' (i
// sprzątania blokady). Kody 128+N jak przy domyślnej obsłudze, więc
// start-bot.command reaguje tak samo jak wcześniej.
for (const [signal, number] of [['SIGHUP', 1], ['SIGINT', 2], ['SIGTERM', 15]]) {
  process.on(signal, () => {
    console.log(`Otrzymano ${signal} - kończę.`);
    process.exit(128 + number);
  });
}

const DAILY_DIR = path.join(__dirname, 'daily');
const TEMPLATE_PATH = path.join(__dirname, 'templates', 'daily.md');

const FOOD_DIR = path.join(__dirname, 'data', 'food');
const WEIGHT_PATH = path.join(__dirname, 'data', 'weight.json');
const TARGETS_PATH = path.join(__dirname, 'data', 'targets.json');
const GOALS_PATH = path.join(__dirname, 'data', 'goals.json');
const PYTHON_BIN = path.join(__dirname, '.venv', 'bin', 'python');
const BUILD_DASHBOARD_SCRIPT = path.join(__dirname, 'scripts', 'build_dashboard.py');
const TRAINING_SCRIPT = path.join(__dirname, 'scripts', 'training_analytics.py');
const STATUS_PATH = path.join(__dirname, 'data', 'status.json');
const GARMIN_DIR = path.join(__dirname, 'data', 'garmin');
const HEVY_CSV_STATE_PATH = path.join(__dirname, 'data', 'hevy', 'csv_import.json');
const HEVY_CSV_STALE_DAYS = 10;
const LAUNCHD_LABELS = ['garminsync', 'morningbrief', 'telegrambot', 'botwatchdog'];
const STEP_LABELS = {
  garmin: 'Garmin',
  hevy: 'Hevy',
  hevy_csv: 'Hevy CSV',
  waga: 'Waga',
  dashboard: 'Dashboard',
  morning_brief: 'Morning brief',
};
const BOT_STARTED_AT = new Date();

const KCAL_MIN = 300;
const KCAL_MAX = 8000;
const WEIGHT_MIN = 30;
const WEIGHT_MAX = 250;

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
    // DD.MM.RRRR (np. "01.10.2026"). Musi poprzedzać wzorzec 'time' w tej
    // tablicy: przy tym samym indeksie startowym rozstrzyganie nakładających
    // się dopasowań w resolveEventDateTime zachowuje pierwsze w kolejności
    // tablicy, a chcemy, żeby dłuższe dopasowanie daty ("01.10.2026") wygrało
    // z krótszym, przypadkowym dopasowaniem wzorca godziny do "01.10".
    kind: 'day',
    re: new RegExp(`${NB}(\\d{1,2})\\.(\\d{1,2})\\.(\\d{4})${NA}`, 'gu'),
    resolve: (m, d, mo, y) => new Date(Number(y), Number(mo) - 1, Number(d)),
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
    title,
    startIso: formatIcalDateTime(target),
    startDate: target,
    hasTime: Boolean(timeSpan),
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

// Porównania w lokalnej strefie czasowej (jak formatLocalDateTime) - używane
// przez /usun do filtrowania wyników wyszukiwania po dacie/godzinie podanej
// przez użytkownika, zamiast po surowym UTC ze start_date.
function sameLocalDate(isoUtc, targetDate) {
  const d = new Date(isoUtc);
  return (
    d.getFullYear() === targetDate.getFullYear() &&
    d.getMonth() === targetDate.getMonth() &&
    d.getDate() === targetDate.getDate()
  );
}

function sameLocalTime(isoUtc, targetDate) {
  const d = new Date(isoUtc);
  return d.getHours() === targetDate.getHours() && d.getMinutes() === targetDate.getMinutes();
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

// Polling startuje dopiero na końcu pliku, po zarejestrowaniu wszystkich
// handlerów.
const bot = new TelegramBot(TOKEN, { polling: { autoStart: false } });

// --- Deduplikacja wiadomości ------------------------------------------------
// Ta sama wiadomość (chat + message_id) przechodzi przez handlery tylko raz,
// nawet jeśli Telegram dostarczy ją ponownie (np. po restarcie przed
// potwierdzeniem offsetu). Ostatnie identyfikatory są w data/, żeby przetrwać
// restart procesu.
const SEEN_MESSAGES_PATH = path.join(__dirname, 'data', 'bot-seen-messages.json');
const SEEN_MESSAGES_MAX = 200;

function loadSeenMessages() {
  try {
    const list = JSON.parse(fs.readFileSync(SEEN_MESSAGES_PATH, 'utf8'));
    return Array.isArray(list) ? list.slice(-SEEN_MESSAGES_MAX) : [];
  } catch (_) {
    return [];
  }
}

const seenMessageKeys = loadSeenMessages();
const seenMessageSet = new Set(seenMessageKeys);

function markMessageSeen(key) {
  seenMessageKeys.push(key);
  seenMessageSet.add(key);
  while (seenMessageKeys.length > SEEN_MESSAGES_MAX) {
    seenMessageSet.delete(seenMessageKeys.shift());
  }
  try {
    fs.writeFileSync(SEEN_MESSAGES_PATH, JSON.stringify(seenMessageKeys));
  } catch (err) {
    console.error('Nie udało się zapisać listy przetworzonych wiadomości:', err.message);
  }
}

const processUpdateOnce = bot.processUpdate.bind(bot);
bot.processUpdate = (update) => {
  const msg = update && update.message;
  if (msg && msg.chat && msg.message_id !== undefined) {
    const key = `${msg.chat.id}:${msg.message_id}`;
    if (seenMessageSet.has(key)) {
      console.log(`Pominięto duplikat wiadomości ${msg.message_id} (update ${update.update_id}).`);
      return;
    }
    markMessageSeen(key);
  }
  processUpdateOnce(update);
};

function isoDateFor(d) {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function todayISO() {
  return isoDateFor(new Date());
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

// Parsuje 4 tokeny w stałej kolejności: "<kcal> b<białko> w<węgle> t<tłuszcze>"
// (np. ["2450", "b160", "w300", "t70"]). Akceptuje przecinek jako separator
// dziesiętny. Zwraca null przy złym formacie albo nierozsądnych wartościach -
// wywołujący odpowiada za pokazanie podpowiedzi formatu.
function parseMacros(tokens) {
  if (tokens.length !== 4) return null;

  const numRe = /^\d+(?:[.,]\d+)?$/;
  if (!numRe.test(tokens[0])) return null;
  const kcal = parseFloat(tokens[0].replace(',', '.'));

  const macroDefs = [['b', 'protein'], ['w', 'carbs'], ['t', 'fat']];
  const result = { kcal };
  for (let i = 0; i < macroDefs.length; i++) {
    const [prefix, key] = macroDefs[i];
    const m = tokens[i + 1].match(new RegExp(`^${prefix}(\\d+(?:[.,]\\d+)?)$`, 'i'));
    if (!m) return null;
    result[key] = parseFloat(m[1].replace(',', '.'));
  }

  if (!(result.kcal > 0) || !(result.protein > 0) || !(result.carbs > 0) || !(result.fat > 0)) {
    return null;
  }
  if (result.kcal < KCAL_MIN || result.kcal > KCAL_MAX) {
    return null;
  }

  return result;
}

function saveFoodDay(dateStr, macros) {
  fs.mkdirSync(FOOD_DIR, { recursive: true });
  const filePath = path.join(FOOD_DIR, `${dateStr}.json`);
  const record = { date: dateStr, ...macros, logged_at: new Date().toISOString() };
  fs.writeFileSync(filePath, JSON.stringify(record, null, 2), 'utf8');
}

function loadWeightEntries() {
  if (!fs.existsSync(WEIGHT_PATH)) return [];
  try {
    const data = JSON.parse(fs.readFileSync(WEIGHT_PATH, 'utf8'));
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

// Jeden wpis na dzień - nadpisuje istniejący wpis dla tej daty zamiast dopisywać kolejny.
function saveWeightEntry(dateStr, kg) {
  const entries = loadWeightEntries();
  const idx = entries.findIndex((e) => e.date === dateStr);
  const entry = { date: dateStr, kg };
  if (idx === -1) {
    entries.push(entry);
  } else {
    entries[idx] = entry;
  }
  entries.sort((a, b) => a.date.localeCompare(b.date));
  fs.mkdirSync(path.dirname(WEIGHT_PATH), { recursive: true });
  fs.writeFileSync(WEIGHT_PATH, JSON.stringify(entries, null, 2), 'utf8');
}

function saveTargets(macros) {
  fs.mkdirSync(path.dirname(TARGETS_PATH), { recursive: true });
  const record = { ...macros, updated_at: new Date().toISOString() };
  fs.writeFileSync(TARGETS_PATH, JSON.stringify(record, null, 2), 'utf8');
}

// Cele kroków / wagi / snu (linie celu w dashboardzie) - osobno od makr z
// data/targets.json; zapis scala z istniejącymi celami.
function saveGoal(key, value) {
  let goals = {};
  try {
    const data = JSON.parse(fs.readFileSync(GOALS_PATH, 'utf8'));
    if (data && typeof data === 'object' && !Array.isArray(data)) goals = data;
  } catch (_) { /* brak pliku albo uszkodzony - zaczynamy od pustego */ }
  goals[key] = value;
  fs.mkdirSync(path.dirname(GOALS_PATH), { recursive: true });
  fs.writeFileSync(GOALS_PATH, JSON.stringify(goals, null, 2), 'utf8');
}

function execFileP(cmd, args, options) {
  return new Promise((resolve, reject) => {
    execFile(cmd, args, options || {}, (error, stdout) => {
      if (error) {
        reject(error);
        return;
      }
      resolve(stdout);
    });
  });
}

// Odświeża dashboard po każdym zapisie /dzien, /waga, /cel. Błąd tu nie
// powinien cofać już zapisanych danych ani zawierać ich treści w logu.
async function rebuildDashboardSafe() {
  try {
    await execFileP(PYTHON_BIN, [BUILD_DASHBOARD_SCRIPT], { cwd: __dirname });
    return true;
  } catch (err) {
    console.error('Błąd przebudowy dashboardu:', err.message);
    return false;
  }
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
      '❌ Nie rozpoznałem daty. Np. „jutro 14:00”, „za 2 dni”, „piątek 10:00”, 2026-03-15 14:00.'
    );
    return;
  }

  const title = parsed.title || 'Wydarzenie';

  try {
    await icalAdd(title, parsed.startIso);
    const event = await findCreatedEvent(title);
    const whenLabel = event ? formatLocalDateTime(event.start_date) : parsed.recognizedText;
    await bot.sendMessage(msg.chat.id, `✅ Dodano wydarzenie „${title}” — ${whenLabel}.`);
  } catch (err) {
    console.error('Błąd przy tworzeniu wydarzenia:', err);
    await bot.sendMessage(msg.chat.id, `❌ Nie udało się utworzyć wydarzenia: ${err.message}`);
  }
});

const USUN_USAGE =
  'Format: /usun <fragment tytułu> [data] [godzina], np. /usun kawa jutro 10:00 albo /usun New Event 01.10.2026 09:00.';

bot.onText(/^\/usun(?:@\w+)?(?:\s+([\s\S]+))?$/, async (msg, match) => {
  if (!isAuthorized(msg)) return;

  const raw = match[1] && match[1].trim();
  if (!raw) {
    await bot.sendMessage(msg.chat.id, USUN_USAGE);
    return;
  }

  // Ten sam parser co /event: wyłuskuje datę/godzinę z tekstu (gdziekolwiek
  // by nie była) i zwraca resztę jako fragment tytułu. Brak dopasowania
  // (parsed === null) oznacza po prostu, że cały tekst to fragment tytułu -
  // dokładnie jak w starym zachowaniu /usun.
  const parsed = resolveEventDateTime(raw);
  const titleQuery = (parsed ? parsed.title : raw).trim();
  if (!titleQuery) {
    await bot.sendMessage(msg.chat.id, USUN_USAGE);
    return;
  }

  try {
    let events = await icalSearch(titleQuery);

    if (parsed) {
      const target = parsed.startDate;
      events = events.filter((e) => sameLocalDate(e.start_date, target));
      if (parsed.hasTime) {
        events = events.filter((e) => sameLocalTime(e.start_date, target));
      }
    }

    if (events.length === 0) {
      const suffix = parsed ? ' w podanym terminie' : '';
      await bot.sendMessage(msg.chat.id, `Nie znaleziono wydarzenia pasującego do „${titleQuery}”${suffix}.`);
      return;
    }

    if (events.length > 1) {
      const list = events
        .map((e) => `• ${e.title} — ${formatLocalDateTime(e.start_date)}`)
        .join('\n');
      const hint = parsed
        ? 'podaj dokładniejszą datę/godzinę'
        : 'podaj dokładniejszy fragment tytułu albo datę i godzinę';
      await bot.sendMessage(msg.chat.id, `Znaleziono ${events.length} pasujących wydarzeń, ${hint}:\n${list}`);
      return;
    }

    // Dokładnie jedno trafienie - jedyny przypadek, w którym w ogóle usuwamy.
    // icalDeleteById nie przekazuje --span, więc ical stosuje domyślne
    // --span this: dla wydarzenia cyklicznego kasuje tylko to wystąpienie,
    // nigdy całą serię.
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

const DZIEN_USAGE =
  'Format: /dzien [wczoraj|DD.MM[.RRRR]] <kcal> b<białko> w<węgle> t<tłuszcze>, ' +
  'np. /dzien 2450 b160 w300 t70 albo /dzien 07.10 2594 b208 w290 t62.';

// Parsuje jawną datę "DD.MM" lub "DD.MM.RRRR" na "RRRR-MM-DD". Bez roku
// przyjmuje bieżący; poprzedni tylko na przełomie roku (np. 30.12 wpisane
// w styczniu), gdy daje to datę z ostatnich 90 dni - literówka typu "jutro"
// nie ląduje wtedy cicho rok wcześniej. Zwraca null dla nieistniejącej daty
// (np. 31.02) albo daty z przyszłości - zaległości wpisujemy tylko wstecz.
function parseFoodDate(token, now = new Date()) {
  const m = token.match(/^(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?$/);
  if (!m) return null;
  const day = Number(m[1]);
  const month = Number(m[2]);
  const today = startOfDay(now);

  let year = m[3] ? Number(m[3]) : today.getFullYear();
  let d = new Date(year, month - 1, day);
  if (!m[3] && d > today) {
    const prev = new Date(year - 1, month - 1, day);
    if (prev >= addDays(today, -90)) {
      year -= 1;
      d = prev;
    }
  }
  if (d.getFullYear() !== year || d.getMonth() !== month - 1 || d.getDate() !== day) return null;
  if (d > today) return null;
  return isoDateFor(d);
}

bot.onText(/^\/dzien(?:@\w+)?(?:\s+([\s\S]+))?$/, async (msg, match) => {
  if (!isAuthorized(msg)) return;

  const raw = match[1] && match[1].trim();
  if (!raw) {
    await bot.sendMessage(msg.chat.id, DZIEN_USAGE);
    return;
  }

  const tokens = raw.split(/\s+/).filter(Boolean);
  let dateStr = todayISO();
  if (tokens.length && /^wczoraj$/i.test(tokens[0])) {
    dateStr = isoDateFor(addDays(new Date(), -1));
    tokens.shift();
  } else if (tokens.length && /^\d{1,2}\.\d{1,2}(?:\.\d{4})?$/.test(tokens[0])) {
    const parsedDate = parseFoodDate(tokens[0]);
    if (!parsedDate) {
      await bot.sendMessage(msg.chat.id, `❌ Nieprawidłowa data „${tokens[0]}” (nie może być z przyszłości). ${DZIEN_USAGE}`);
      return;
    }
    dateStr = parsedDate;
    tokens.shift();
  }

  const macros = parseMacros(tokens);
  if (!macros) {
    await bot.sendMessage(msg.chat.id, DZIEN_USAGE);
    return;
  }

  try {
    saveFoodDay(dateStr, macros);
    await rebuildDashboardSafe();
    await bot.sendMessage(
      msg.chat.id,
      `✅ Zapisano dzień ${dateStr}: ${macros.kcal} kcal, B ${macros.protein}g, W ${macros.carbs}g, T ${macros.fat}g.`
    );
  } catch (err) {
    console.error('Błąd przy zapisie dnia:', err.message);
    await bot.sendMessage(msg.chat.id, '❌ Nie udało się zapisać dnia.');
  }
});

const WAGA_USAGE = 'Format: /waga <kg>, np. /waga 72.4 (lub 72,4). Zakres 30-250.';

bot.onText(/^\/waga(?:@\w+)?(?:\s+([\s\S]+))?$/, async (msg, match) => {
  if (!isAuthorized(msg)) return;

  const raw = match[1] && match[1].trim();
  if (!raw) {
    await bot.sendMessage(msg.chat.id, WAGA_USAGE);
    return;
  }

  const m = raw.match(/^(\d+(?:[.,]\d+)?)$/);
  if (!m) {
    await bot.sendMessage(msg.chat.id, WAGA_USAGE);
    return;
  }

  const kg = parseFloat(m[1].replace(',', '.'));
  if (!(kg >= WEIGHT_MIN && kg <= WEIGHT_MAX)) {
    await bot.sendMessage(msg.chat.id, WAGA_USAGE);
    return;
  }

  const dateStr = todayISO();

  try {
    saveWeightEntry(dateStr, kg);
    await rebuildDashboardSafe();
    await bot.sendMessage(msg.chat.id, `✅ Zapisano wagę: ${kg} kg (${dateStr}).`);
  } catch (err) {
    console.error('Błąd przy zapisie wagi:', err.message);
    await bot.sendMessage(msg.chat.id, '❌ Nie udało się zapisać wagi.');
  }
});

const CEL_USAGE =
  'Format: /cel <kcal> b<białko> w<węgle> t<tłuszcze> (np. /cel 2400 b150 w280 t70), ' +
  '/cel kroki 10000, /cel waga 83,5 albo /cel sen 7,5.';

// /cel kroki|waga|sen <liczba>: klucz w data/goals.json, zakres i format odpowiedzi.
const GOAL_KINDS = {
  kroki: { key: 'steps', min: 1000, max: 50000, integer: true, reply: (v) => `✅ Cel kroków: ${v} dziennie.` },
  waga: { key: 'weight', min: WEIGHT_MIN, max: WEIGHT_MAX, reply: (v) => `✅ Cel wagi: ${v} kg.` },
  sen: { key: 'sleep', min: 4, max: 12, reply: (v) => `✅ Cel snu: ${v} h.` },
};

// Zwraca { kind, value }, { error } dla złej liczby / zakresu albo null, gdy
// to nie jest wariant kroki/waga/sen (wtedy działa dotychczasowe /cel makr).
function parseGoal(raw) {
  const m = raw.match(/^(kroki|waga|sen)(?:\s+(\S+))?$/i);
  if (!m) return null;
  const kind = GOAL_KINDS[m[1].toLowerCase()];
  const num = m[2] && m[2].match(/^\d+(?:[.,]\d+)?$/) ? parseFloat(m[2].replace(',', '.')) : NaN;
  if (!(num >= kind.min && num <= kind.max) || (kind.integer && !Number.isInteger(num))) {
    const unit = kind.integer ? ', liczba całkowita' : '';
    return { error: `❌ Cel ${m[1].toLowerCase()}: podaj liczbę z zakresu ${kind.min}-${kind.max}${unit}.` };
  }
  return { kind, value: num };
}

bot.onText(/^\/cel(?:@\w+)?(?:\s+([\s\S]+))?$/, async (msg, match) => {
  if (!isAuthorized(msg)) return;

  const raw = match[1] && match[1].trim();
  if (!raw) {
    await bot.sendMessage(msg.chat.id, CEL_USAGE);
    return;
  }

  const goal = parseGoal(raw);
  if (goal) {
    if (goal.error) {
      await bot.sendMessage(msg.chat.id, goal.error);
      return;
    }
    try {
      saveGoal(goal.kind.key, goal.value);
      await rebuildDashboardSafe();
      await bot.sendMessage(msg.chat.id, goal.kind.reply(goal.value));
    } catch (err) {
      console.error('Błąd przy zapisie celu:', err.message);
      await bot.sendMessage(msg.chat.id, '❌ Nie udało się zapisać celu.');
    }
    return;
  }

  const tokens = raw.split(/\s+/).filter(Boolean);
  const macros = parseMacros(tokens);
  if (!macros) {
    await bot.sendMessage(msg.chat.id, CEL_USAGE);
    return;
  }

  try {
    saveTargets(macros);
    await rebuildDashboardSafe();
    await bot.sendMessage(
      msg.chat.id,
      `✅ Zapisano cele: ${macros.kcal} kcal, B ${macros.protein}g, W ${macros.carbs}g, T ${macros.fat}g.`
    );
  } catch (err) {
    console.error('Błąd przy zapisie celów:', err.message);
    await bot.sendMessage(msg.chat.id, '❌ Nie udało się zapisać celów.');
  }
});

// --- /przenies ----------------------------------------------------------------
// Przenosi dzisiejszy wpis jedzenia na wczoraj (np. gdy /dzien wysłano po
// północy). Nic nie jest kasowane: dzisiejszy plik i ewentualny nadpisywany
// wpis wczorajszy zostają jako kopie .bak (których dashboard nie czyta).
const PRZENIES_USAGE = 'Format: /przenies (albo /przenies tak, żeby nadpisać istniejący wpis z wczoraj).';

function fmtDayMonth(dateStr) {
  const [, m, d] = dateStr.split('-');
  return `${d}.${m}`;
}

function fmtMacros(rec) {
  return `${rec.kcal} kcal, B ${rec.protein}, W ${rec.carbs}, T ${rec.fat}`;
}

// Wolna nazwa kopii: plik.json.bak, a gdy zajęta - plik.json.bak.1, .2 ...
function backupPathFor(filePath) {
  let candidate = `${filePath}.bak`;
  for (let i = 1; fs.existsSync(candidate); i++) candidate = `${filePath}.bak.${i}`;
  return candidate;
}

bot.onText(/^\/przenies(?:@\w+)?(?:\s+([\s\S]+))?$/, async (msg, match) => {
  if (!isAuthorized(msg)) return;

  const arg = match[1] && match[1].trim();
  if (arg && !/^tak$/i.test(arg)) {
    await bot.sendMessage(msg.chat.id, PRZENIES_USAGE);
    return;
  }
  const overwrite = Boolean(arg);

  const todayStr = todayISO();
  const yesterdayStr = isoDateFor(addDays(new Date(), -1));
  const srcPath = path.join(FOOD_DIR, `${todayStr}.json`);
  const dstPath = path.join(FOOD_DIR, `${yesterdayStr}.json`);

  try {
    if (!fs.existsSync(srcPath)) {
      await bot.sendMessage(msg.chat.id, `Brak wpisu jedzenia z dziś (${fmtDayMonth(todayStr)}).`);
      return;
    }
    const record = JSON.parse(fs.readFileSync(srcPath, 'utf8'));

    if (fs.existsSync(dstPath)) {
      if (!overwrite) {
        let existing = null;
        try {
          existing = JSON.parse(fs.readFileSync(dstPath, 'utf8'));
        } catch (_) { /* uszkodzony plik - pokażemy bez wartości */ }
        const values = existing ? `: ${fmtMacros(existing)}` : '';
        await bot.sendMessage(
          msg.chat.id,
          `⚠️ Wczoraj (${fmtDayMonth(yesterdayStr)}) już ma wpis${values}. ` +
          'Wyślij /przenies tak, żeby go nadpisać (stary wpis zostanie jako kopia .bak).'
        );
        return;
      }
      fs.renameSync(dstPath, backupPathFor(dstPath));
    }

    record.date = yesterdayStr;
    fs.writeFileSync(dstPath, JSON.stringify(record, null, 2), 'utf8');
    fs.renameSync(srcPath, backupPathFor(srcPath));

    await rebuildDashboardSafe();
    await bot.sendMessage(msg.chat.id, `✅ Przeniesiono: ${fmtMacros(record)} → ${fmtDayMonth(yesterdayStr)}`);
  } catch (err) {
    console.error('Błąd /przenies:', err.message);
    await bot.sendMessage(msg.chat.id, '❌ Nie udało się przenieść wpisu.');
  }
});

// --- /odswiez -----------------------------------------------------------------
// Ręczny przebieg scripts/refresh_all.sh (to samo co launchd o 11:20/15:30/21:00).
// Wynik czytamy z data/status.json: kroki zapisane od startu tego przebiegu.
const REFRESH_SCRIPT = path.join(__dirname, 'scripts', 'refresh_all.sh');
const REFRESH_LOCK_DIR = path.join(__dirname, 'logs', '.lock-refresh');
const REFRESH_LOCK_STALE_MS = 30 * 60 * 1000; // jak acquire_lock w scripts/lib.sh
const REFRESH_COOLDOWN_MS = 60 * 1000;
const REFRESH_TIMEOUT_MS = 20 * 60 * 1000;
const REFRESH_STEPS = ['garmin', 'hevy', 'hevy_csv', 'waga', 'dashboard'];

const refreshState = { running: false, lastStartedAt: 0 };

// Przebieg uruchomiony przez launchd trzyma blokadę logs/.lock-refresh -
// refresh_all.sh by się wtedy po cichu pominął, więc sprawdzamy ją wcześniej.
function refreshLockHeld() {
  try {
    return Date.now() - fs.statSync(REFRESH_LOCK_DIR).mtimeMs < REFRESH_LOCK_STALE_MS;
  } catch (_) {
    return false;
  }
}

function fmtTime(value) {
  const d = new Date(value);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

// Najwyżej 5 linii (po jednej na krok) + jedna komenda naprawcza przy błędzie.
// Celowo bez treści komunikatów kroków - mogą zawierać wartości zdrowotne.
function buildRefreshSummary(startedAt, runError) {
  const steps = readStatusFile().steps || {};
  const startedSec = Math.floor(startedAt / 1000) * 1000;
  const icon = { ok: '✅', fail: '❌', skip: '⏭️' };
  const lines = [];
  let fix = null;

  for (const key of REFRESH_STEPS) {
    const st = steps[key];
    if (!st || !st.at || new Date(st.at).getTime() < startedSec) continue;
    lines.push(`${icon[st.result] || '▫️'} ${STEP_LABELS[key] || key} ${fmtTime(st.at)}`);
    if (st.result === 'fail' && !fix && st.fix) fix = st.fix;
  }

  if (!lines.length) {
    const reason = runError && runError.killed ? 'przekroczony limit czasu' : 'brak wyników kroków';
    lines.push(`❌ Odświeżanie ${fmtTime(Date.now())}: ${reason}`);
    fix = 'cd ~/anton_brain && scripts/refresh_all.sh';
  }
  if (fix) lines.push(`Naprawa: ${fix}`);
  return lines.join('\n');
}

bot.onText(/^\/odswiez(?:@\w+)?$/, async (msg) => {
  if (!isAuthorized(msg)) return;

  if (refreshState.running || refreshLockHeld()) {
    await bot.sendMessage(msg.chat.id, '⏳ Odświeżanie już trwa.');
    return;
  }
  const sinceLast = Date.now() - refreshState.lastStartedAt;
  if (sinceLast < REFRESH_COOLDOWN_MS) {
    const wait = Math.ceil((REFRESH_COOLDOWN_MS - sinceLast) / 1000);
    await bot.sendMessage(msg.chat.id, `⏳ Kolejne odświeżanie za ${wait} s.`);
    return;
  }

  refreshState.running = true;
  const startedAt = Date.now();
  refreshState.lastStartedAt = startedAt;
  console.log('/odswiez: start refresh_all.sh');

  try {
    await bot.sendMessage(msg.chat.id, 'Odświeżam…');
  } catch (err) {
    console.error('Błąd wysyłki /odswiez:', err.message);
  }

  execFile(REFRESH_SCRIPT, [], { cwd: __dirname, timeout: REFRESH_TIMEOUT_MS, maxBuffer: 10 * 1024 * 1024 }, async (error) => {
    refreshState.running = false;
    console.log(`/odswiez: koniec (${error ? `kod ${error.code ?? error.signal}` : 'OK'})`);
    try {
      await bot.sendMessage(msg.chat.id, buildRefreshSummary(startedAt, error));
    } catch (err) {
      console.error('Błąd wysyłki wyniku /odswiez:', err.message);
    }
  });
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

// --- Odporność na utratę sieci ---------------------------------------------
// Po uśpieniu Maca / zmianie Wi-Fi polling sypie ENOTFOUND/ECONNRESET/
// AggregateError w pętli. Zamiast zalewać log: wstrzymujemy polling i
// sprawdzamy połączenie (getMe) z wykładniczo rosnącym odstępem (5 s ... 5 min).
// Jeśli połączenia nie ma przez 15 min, kończymy proces kodem 75 -
// scripts/start-bot.command uruchamia bota od nowa (kontrolowany restart).
const POLL_BACKOFF_MIN_MS = 5 * 1000;
const POLL_BACKOFF_MAX_MS = 5 * 60 * 1000;
const POLL_STABLE_MS = 2 * 60 * 1000;
const OFFLINE_RESTART_MS = 15 * 60 * 1000;
const EXIT_CODE_RESTART = 75;

const connection = {
  offlineSince: null, // pierwszy błąd bieżącej serii
  lastError: null,
  recovering: false,
  backoffMs: POLL_BACKOFF_MIN_MS,
  stableTimer: null,
};

bot.on('polling_error', (err) => {
  connection.lastError = { at: new Date(), message: err.message };
  if (connection.recovering) return;
  connection.recovering = true;
  clearTimeout(connection.stableTimer);
  if (!connection.offlineSince) connection.offlineSince = Date.now();
  console.error(`Polling error: ${err.message} - wstrzymuję polling, próba za ${connection.backoffMs / 1000} s`);
  // Bez { cancel: true }: w node-telegram-bot-api 0.66 stop z cancel nie
  // ustawia flagi _abort, więc przerwana pętla getUpdates planuje kolejne
  // zapytanie, a startPolling dokłada drugą. Każdy błąd sieci dodawał pętlę -
  // stąd 409 Conflict w jednym procesie i kilka odpowiedzi na jedną wiadomość
  // (18.10: 7x "Zapisano dzień"). Zwykły stop kończy pętlę po bieżącym zapytaniu.
  bot.stopPolling()
    .catch(() => {})
    .finally(scheduleReconnect);
});

function scheduleReconnect() {
  setTimeout(async () => {
    try {
      await bot.getMe();
    } catch (err) {
      connection.lastError = { at: new Date(), message: err.message };
      const offlineMs = Date.now() - connection.offlineSince;
      if (offlineMs >= OFFLINE_RESTART_MS) {
        console.error(`Brak połączenia z Telegramem od ${Math.round(offlineMs / 60000)} min - kontrolowany restart bota.`);
        process.exit(EXIT_CODE_RESTART);
      }
      connection.backoffMs = Math.min(connection.backoffMs * 2, POLL_BACKOFF_MAX_MS);
      console.error(`Telegram nadal niedostępny (${err.message}) - kolejna próba za ${connection.backoffMs / 1000} s`);
      scheduleReconnect();
      return;
    }
    console.log(`Połączenie z Telegramem jest - wznawiam polling (przerwa ${Math.round((Date.now() - connection.offlineSince) / 1000)} s).`);
    connection.recovering = false;
    // Seria błędów kończy się dopiero, gdy polling działa stabilnie przez 2 min -
    // inaczej "migająca" sieć resetowałaby licznik 15 min w nieskończoność.
    connection.stableTimer = setTimeout(() => {
      connection.offlineSince = null;
      connection.backoffMs = POLL_BACKOFF_MIN_MS;
    }, POLL_STABLE_MS);
    checkHandlersRegisteredOnce();
    if (bot.isPolling()) {
      console.error('Polling nadal działa - nie uruchamiam drugiej pętli getUpdates.');
      return;
    }
    // restart: false - restart w bibliotece też przerywa przez cancel (patrz wyżej).
    bot.startPolling({ restart: false }).catch((err) => {
      console.error('Nie udało się wznowić pollingu:', err.message);
    });
  }, connection.backoffMs);
}

// --- /status -----------------------------------------------------------------
function fmtDateTime(value) {
  if (!value) return 'nigdy';
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  const pad = (n) => String(n).padStart(2, '0');
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// --- Waga w /status ----------------------------------------------------------
// Ostatni wpis w weight.json vs data modyfikacji waga.txt w iCloud (Skrót
// iOS) i ślad ostatniego importu (data/waga_import.json z import_waga.py).
// Ostrzeżenie, gdy plik jest nowszy niż ostatni wpis, a import go nie wziął -
// czyli ostatni przebieg nie przetworzył z sukcesem właśnie tej wersji pliku.
const WAGA_TXT_PATH = path.join(os.homedir(), 'Library', 'Mobile Documents', 'com~apple~CloudDocs', 'waga.txt');
const WAGA_IMPORT_STATE_PATH = path.join(__dirname, 'data', 'waga_import.json');

function fmtDay(dateStr) {
  return `${dateStr.slice(8, 10)}.${dateStr.slice(5, 7)}`;
}

function weightStatusLines() {
  const dates = loadWeightEntries().map((e) => e && e.date).filter((d) => typeof d === 'string').sort();
  const lastDate = dates.length ? dates[dates.length - 1] : null;
  let state = null;
  try {
    state = JSON.parse(fs.readFileSync(WAGA_IMPORT_STATE_PATH, 'utf8'));
  } catch (_) { /* jeszcze nie było importu */ }

  let fileText;
  let mtime = null;
  try {
    mtime = fs.statSync(WAGA_TXT_PATH).mtime;
    fileText = fmtDateTime(mtime);
  } catch (_) {
    const placeholder = path.join(path.dirname(WAGA_TXT_PATH), '.waga.txt.icloud');
    fileText = fs.existsSync(placeholder) ? 'w iCloud, niepobrany na dysk' : 'brak pliku';
  }
  const lines = [`⚖️ Waga: ostatni wpis ${lastDate ? fmtDay(lastDate) : 'brak'} · waga.txt w iCloud: ${fileText}`];

  if (mtime && (!lastDate || isoDateFor(mtime) > lastDate)) {
    const tookThisFile = state && state.result === 'ok'
      && state.file_mtime_epoch === Math.floor(mtime.getTime() / 1000);
    if (!tookThisFile) {
      const why = state
        ? `ostatni import ${fmtDateTime(state.checked_at)}: ${state.reason || state.result}`
        : 'brak śladu importu';
      lines.push(`⚠️ waga.txt jest nowszy niż ostatni wpis, a import go nie wziął (${why})`);
    }
  }
  return lines;
}

function fmtDuration(ms) {
  const min = Math.floor(ms / 60000);
  const d = Math.floor(min / 1440);
  const h = Math.floor((min % 1440) / 60);
  const m = min % 60;
  return [d && `${d} d`, h && `${h} h`, `${m} min`].filter(Boolean).join(' ');
}

function readStatusFile() {
  try {
    return JSON.parse(fs.readFileSync(STATUS_PATH, 'utf8'));
  } catch (_) {
    return { steps: {} };
  }
}

function newestGarminFetch() {
  let newest = null;
  try {
    for (const name of fs.readdirSync(GARMIN_DIR)) {
      if (!name.endsWith('.json')) continue;
      try {
        const rec = JSON.parse(fs.readFileSync(path.join(GARMIN_DIR, name), 'utf8'));
        if (rec.fetched_at && (!newest || rec.fetched_at > newest)) newest = rec.fetched_at;
      } catch (_) { /* uszkodzony plik pomijamy */ }
    }
  } catch (_) { /* brak katalogu */ }
  return newest;
}

// Import CSV z Hevy (scripts/hevy_csv_import.py) - data ostatniego importu
// i wiek najnowszego pliku CSV w iCloud Drive.
function hevyCsvLines() {
  let st;
  try {
    st = JSON.parse(fs.readFileSync(HEVY_CSV_STATE_PATH, 'utf8'));
  } catch (_) {
    return ['Ostatni import CSV z Hevy: nigdy'];
  }
  const lines = [`Ostatni import CSV z Hevy: ${fmtDateTime(st.last_import)}${st.last_import_file ? ` (${st.last_import_file})` : ''}`];
  const mtime = st.newest_mtime ? new Date(st.newest_mtime) : null;
  if (mtime && !Number.isNaN(mtime.getTime())) {
    const ageDays = (Date.now() - mtime.getTime()) / 86400000;
    lines.push(ageDays > HEVY_CSV_STALE_DAYS
      ? `⚠️ Najnowszy CSV (${st.newest_file}) z ${fmtDateTime(mtime)}, ma ${Math.floor(ageDays)} dni - wyeksportuj świeży z Hevy do iCloud Drive`
      : `Najnowszy CSV (${st.newest_file}) z ${fmtDateTime(mtime)}`);
  }
  return lines;
}

async function launchdJobLine(label) {
  const uid = process.getuid();
  try {
    const out = await execFileP('launchctl', ['print', `gui/${uid}/com.antonbrain.${label}`]);
    const runs = (out.match(/\n\s*runs = (\d+)/) || [])[1] || '?';
    const exit = (out.match(/last exit code = ([^\n]+)/) || [])[1] || '?';
    const state = (out.match(/\n\s*state = ([^\n]+)/) || [])[1] || "?";
    const ok = exit === '0' || exit.startsWith('(never exited)') || state === 'running';
    return `${ok ? '✅' : '⚠️'} ${label}: załadowane, ${state}, uruchomień ${runs}, ostatni kod wyjścia ${exit}`;
  } catch (_) {
    return `❌ ${label}: NIEZAŁADOWANE (launchctl bootstrap gui/${uid} ~/Library/LaunchAgents/com.antonbrain.${label}.plist)`;
  }
}

async function buildStatusText() {
  const status = readStatusFile();
  const steps = status.steps || {};
  const lines = ['📊 Status anton_brain', ''];

  const newest = newestGarminFetch();
  const staleMs = newest ? Date.now() - new Date(newest).getTime() : Infinity;
  lines.push(`Ostatnia udana synchronizacja Garmin: ${fmtDateTime((steps.garmin || {}).last_success || newest)}`);
  lines.push(staleMs > 24 * 3600 * 1000
    ? `⚠️ Dane w dashboardzie nieaktualne (najnowsze z ${fmtDateTime(newest)})`
    : `Dane w dashboardzie aktualne (pobrane ${fmtDateTime(newest)})`);
  lines.push(...hevyCsvLines());
  lines.push(...weightStatusLines());
  lines.push('');

  lines.push('Kroki (ostatni przebieg):');
  const icon = { ok: '✅', fail: '❌', skip: '⏭️' };
  for (const key of [...Object.keys(STEP_LABELS), ...Object.keys(steps).filter((k) => !STEP_LABELS[k])]) {
    const st = steps[key];
    if (!st) {
      lines.push(`▫️ ${STEP_LABELS[key] || key}: brak danych`);
      continue;
    }
    lines.push(`${icon[st.result] || '▫️'} ${STEP_LABELS[key] || key} (${fmtDateTime(st.at)}): ${st.message || st.result}`);
    if (st.result === 'fail') {
      lines.push(`   ostatni sukces: ${fmtDateTime(st.last_success)}`);
      if (st.fix) lines.push(`   naprawa: ${st.fix}`);
    }
  }
  lines.push('');

  lines.push('Zadania launchd:');
  for (const label of LAUNCHD_LABELS) {
    lines.push(await launchdJobLine(label));
  }
  lines.push('');

  lines.push(`Bot działa od ${fmtDateTime(BOT_STARTED_AT)} (${fmtDuration(Date.now() - BOT_STARTED_AT.getTime())}).`);
  if (connection.offlineSince) {
    lines.push(`⚠️ Problemy z połączeniem od ${fmtDateTime(new Date(connection.offlineSince))}`);
  }
  if (connection.lastError) {
    lines.push(`Ostatni błąd pollingu: ${fmtDateTime(connection.lastError.at)} - ${connection.lastError.message}`);
  }
  return lines.join('\n');
}

// --- /nawyk ------------------------------------------------------------------
// Odhacza ręczny nawyk w sekcji "## 🔁 Nawyki" dzisiejszej (albo wczorajszej)
// notatki. Nawyki z data/habits.json (te same, które czyta scripts/habits.py);
// nawyki automatyczne liczy tylko dashboard - tu ich nie zapisujemy. Tylko fs,
// żadnego shella.
const HABITS_PATH = path.join(__dirname, 'data', 'habits.json');
const HABITS_HEADING = '## 🔁 Nawyki';
const HABITS_HEADING_RE = /^##\s+.*\bNawyki\b/;
const HABIT_CHECKBOX_RE = /^(\s*[-*]\s+\[)([ xX])(\]\s+)(\S.*?)\s*$/;
// Te same domyślne nawyki ręczne co w scripts/habits.py i templates/daily.md.
const DEFAULT_MANUAL_HABITS = [
  { id: 'nauka', name: 'Nauka' },
  { id: 'czytanie', name: 'Czytanie' },
  { id: 'cardio', name: 'Cardio 20 min' },
];
const NAWYK_USAGE = 'Format: /nawyk <nazwa> albo /nawyk wczoraj <nazwa>, np. /nawyk czyt.';

function normalizeHabitText(text) {
  return String(text)
    .toLowerCase()
    .replace(/ł/g, 'l')
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function loadHabits() {
  try {
    const data = JSON.parse(fs.readFileSync(HABITS_PATH, 'utf8'));
    const list = Array.isArray(data && data.habits) ? data.habits : [];
    const valid = list.filter((h) => h && String(h.id || '').trim() && String(h.name || '').trim());
    return {
      manual: valid.filter((h) => h.type === 'manual').map((h) => ({ id: String(h.id).trim(), name: String(h.name).trim() })),
      auto: valid.filter((h) => h.type === 'auto').map((h) => ({ id: String(h.id).trim(), name: String(h.name).trim() })),
    };
  } catch (_) {
    return { manual: DEFAULT_MANUAL_HABITS, auto: [] };
  }
}

// Fragment pasuje do nazwy albo id; dokładne trafienie wygrywa z częściowymi.
function matchHabits(habits, fragment) {
  const q = normalizeHabitText(fragment);
  const keys = (h) => [normalizeHabitText(h.name), normalizeHabitText(h.id)];
  const exact = habits.filter((h) => keys(h).includes(q));
  return exact.length ? exact : habits.filter((h) => keys(h).some((k) => k.includes(q)));
}

// Etykieta checkboxa należy do nawyku, gdy zaczyna się od jego nazwy albo id
// (jak label_matches w scripts/habits.py), np. "Czytanie - 30 stron".
function labelMatchesHabit(habit, label) {
  const n = normalizeHabitText(label);
  return [habit.name, habit.id].map(normalizeHabitText).some((k) =>
    n === k || (n.startsWith(k) && !/[a-z0-9]/.test(n[k.length])));
}

function habitSectionBounds(lines) {
  const start = lines.findIndex((line) => HABITS_HEADING_RE.test(line));
  if (start === -1) return null;
  let end = lines.length;
  for (let i = start + 1; i < lines.length; i++) {
    if (lines[i].startsWith('## ')) { end = i; break; }
  }
  return { start, end };
}

// Zwraca 'checked' albo 'already'. Brakującą sekcję (starsze notatki) wstawia
// przed "Recap wieczorny" albo na końcu; brakującą linię nawyku dopisuje.
function checkHabitInNote(dateStr, habit, manualHabits) {
  const filePath = ensureDailyNote(dateStr);
  const lines = fs.readFileSync(filePath, 'utf8').split('\n');
  let bounds = habitSectionBounds(lines);
  if (!bounds) {
    const section = [HABITS_HEADING, ...manualHabits.map((h) => `- [ ] ${h.name}`), ''];
    const recap = lines.findIndex((line) => line.startsWith('## ') && line.includes('Recap wieczorny'));
    if (recap === -1) {
      while (lines.length && lines[lines.length - 1].trim() === '') lines.pop();
      lines.push('', ...section);
    } else {
      lines.splice(recap, 0, ...section);
    }
    bounds = habitSectionBounds(lines);
  }

  for (let i = bounds.start + 1; i < bounds.end; i++) {
    const m = lines[i].match(HABIT_CHECKBOX_RE);
    if (m && labelMatchesHabit(habit, m[4])) {
      if (m[2] !== ' ') return 'already';
      lines[i] = `${m[1]}x${m[3]}${m[4]}`;
      fs.writeFileSync(filePath, lines.join('\n'), 'utf8');
      return 'checked';
    }
  }
  let insertAt = bounds.end;
  while (insertAt > bounds.start + 1 && lines[insertAt - 1].trim() === '') insertAt--;
  lines.splice(insertAt, 0, `- [x] ${habit.name}`);
  fs.writeFileSync(filePath, lines.join('\n'), 'utf8');
  return 'checked';
}

function habitStatusLine(dateStr, manualHabits) {
  const note = readDailyNote(dateStr);
  const lines = note ? note.split('\n') : [];
  const bounds = habitSectionBounds(lines);
  const checked = (h) => !!bounds && lines.slice(bounds.start + 1, bounds.end).some((line) => {
    const m = line.match(HABIT_CHECKBOX_RE);
    return m && m[2] !== ' ' && labelMatchesHabit(h, m[4]);
  });
  return manualHabits.map((h) => `${checked(h) ? '☑' : '☐'} ${h.name}`).join('\n');
}

bot.onText(/^\/nawyk(?:@\w+)?(?:\s+([\s\S]+))?$/, async (msg, match) => {
  if (!isAuthorized(msg)) return;
  const { manual, auto } = loadHabits();
  const tokens = (match[1] || '').trim().split(/\s+/).filter(Boolean);
  let dateStr = todayISO();
  let dayLabel = 'dziś';
  if (tokens.length && normalizeHabitText(tokens[0]) === 'wczoraj') {
    dateStr = isoDateFor(addDays(new Date(), -1));
    dayLabel = `wczoraj, ${dateStr.slice(8, 10)}.${dateStr.slice(5, 7)}`;
    tokens.shift();
  }

  if (!tokens.length) {
    const list = manual.length ? habitStatusLine(dateStr, manual) : 'Brak nawyków ręcznych w data/habits.json.';
    await bot.sendMessage(msg.chat.id, `Nawyki (${dayLabel}):\n${list}\n\n${NAWYK_USAGE}`);
    return;
  }

  const fragment = tokens.join(' ');
  const found = matchHabits(manual, fragment);
  if (found.length !== 1) {
    let reply;
    if (found.length > 1) {
      reply = `Pasuje kilka nawyków: ${found.map((h) => h.name).join(', ')} - doprecyzuj.`;
    } else if (matchHabits(auto, fragment).length) {
      reply = `„${matchHabits(auto, fragment)[0].name}” liczy się automatycznie w dashboardzie - nie trzeba go odhaczać.`;
    } else {
      reply = `Nie znam nawyku „${fragment}”. Ręczne: ${manual.map((h) => h.name).join(', ') || 'brak'}.`;
    }
    await bot.sendMessage(msg.chat.id, reply);
    return;
  }

  const habit = found[0];
  try {
    const result = checkHabitInNote(dateStr, habit, manual);
    await bot.sendMessage(
      msg.chat.id,
      result === 'already' ? `„${habit.name}” było już odhaczone (${dayLabel}).` : `✅ Odhaczono „${habit.name}” (${dayLabel}).`
    );
  } catch (err) {
    console.error('Błąd /nawyk:', err.message);
    await bot.sendMessage(msg.chat.id, '❌ Nie udało się zapisać nawyku.');
  }
});

// --- /trening ----------------------------------------------------------------
// Podsumowanie z scripts/training_analytics.py (te same wyliczenia co zakładka
// Trening w dashboardzie): ostatnia sesja, ćwiczenia do podniesienia ciężaru,
// partie z za małą liczbą serii. Skrypt nie podaje ciężarów; do logu trafia
// tylko kod wyjścia, nie stdout/stderr.
const TRENING_MAX_LINES = 8;

bot.onText(/^\/trening(?:@\w+)?$/, async (msg) => {
  if (!isAuthorized(msg)) return;
  try {
    const stdout = await execFileP(PYTHON_BIN, [TRAINING_SCRIPT, '--telegram'], { cwd: __dirname, timeout: 60 * 1000 });
    const text = stdout.trim().split('\n').slice(0, TRENING_MAX_LINES).join('\n');
    await bot.sendMessage(msg.chat.id, text || 'Brak danych treningowych.');
  } catch (err) {
    console.error(`Błąd /trening: training_analytics.py zakończył się kodem ${err.code ?? err.signal ?? '?'}`);
    await bot.sendMessage(msg.chat.id, '❌ Nie udało się przygotować podsumowania treningu.');
  }
});

bot.onText(/^\/status(?:@\w+)?$/, async (msg) => {
  if (!isAuthorized(msg)) return;
  try {
    await sendLong(msg.chat.id, await buildStatusText());
  } catch (err) {
    console.error('Błąd /status:', err.message);
    await bot.sendMessage(msg.chat.id, '❌ Nie udało się zebrać statusu.');
  }
});

// Lista komend w menu Telegrama - ustawiana przy każdym starcie, żeby nie
// rozjeżdżała się z kodem.
const BOT_COMMANDS = [
  { command: 'priorytet', description: 'Dodaj priorytet na dziś' },
  { command: 'nauka', description: 'Dodaj notatkę ze studiów' },
  { command: 'note', description: 'Dodaj pomysł lub obserwację' },
  { command: 'event', description: 'Dodaj wydarzenie do kalendarza' },
  { command: 'usun', description: 'Usuń wydarzenie z kalendarza' },
  { command: 'brief', description: 'Pokaż dzisiejszą notatkę' },
  { command: 'dzien', description: 'Zapisz podsumowanie dnia (kcal, B, W, T)' },
  { command: 'przenies', description: 'Przenieś dzisiejszy wpis jedzenia na wczoraj' },
  { command: 'waga', description: 'Zapisz wagę' },
  { command: 'cel', description: 'Ustaw cele: makra, kroki, waga, sen' },
  { command: 'odswiez', description: 'Odśwież dane (Garmin, Hevy, waga, dashboard)' },
  { command: 'trening', description: 'Podsumowanie treningu (progresja, serie)' },
  { command: 'nawyk', description: 'Odhacz nawyk (np. /nawyk czytanie, /nawyk wczoraj nauka)' },
  { command: 'status', description: 'Pokaż stan synchronizacji i zadań' },
];

bot.setMyCommands(BOT_COMMANDS).catch((err) => {
  console.error('Nie udało się ustawić listy komend:', err.message);
});

// Handlery są rejestrowane raz, przy ładowaniu pliku; wznowienie pollingu ich
// nie dotyka. Liczniki z tej chwili są sprawdzane przy każdym wznowieniu, żeby
// ewentualne podwójne rejestrowanie od razu było widać w logu.
// (_textRegexpCallbacks to wewnętrzna lista onText biblioteki.)
function handlerCounts() {
  return {
    onText: bot._textRegexpCallbacks.length,
    message: bot.listenerCount('message'),
    polling_error: bot.listenerCount('polling_error'),
  };
}

const HANDLER_COUNTS = handlerCounts();

function checkHandlersRegisteredOnce() {
  const now = handlerCounts();
  if (JSON.stringify(now) !== JSON.stringify(HANDLER_COUNTS)) {
    console.error(`Liczba handlerów zmieniła się: ${JSON.stringify(HANDLER_COUNTS)} -> ${JSON.stringify(now)}`);
  }
}

bot.startPolling({ restart: false }).catch((err) => {
  console.error('Nie udało się uruchomić pollingu:', err.message);
});

console.log(`Bot Telegram uruchomiony i nasłuchuje... (PID ${process.pid}, handlery: ${JSON.stringify(HANDLER_COUNTS)})`);
