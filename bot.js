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

// Rozpoznaje proste polskie zwroty czasowe w tekście i tłumaczy je na
// angielskie wyrażenia zrozumiałe dla parsera dat w `ical` (go-eventkit).
// To celowo prosty, heurystyczny parser (nie pełne NLP) - wystarczający do
// wyłuskania "jutro 14:00" itp. z końca/środka wiadomości.
// Uwaga: zwykłe \b nie rozpoznaje polskich znaków (ą, ę, ń, ó, ś, ł, ż, ź)
// jako części słowa, więc granice słów budujemy ręcznie przez \p{L}/\p{N}
// (wymaga flagi "u"), zamiast polegać na \b przy wyrazach typu "godzinę".
const NB = '(?<![\\p{L}\\p{N}])';
const NA = '(?![\\p{L}\\p{N}])';
const DATE_PATTERNS = [
  { re: new RegExp(`${NB}za\\s+(\\d+)\\s+dni\\p{L}*${NA}`, 'giu'), translate: (m, n) => `in ${n} days` },
  { re: new RegExp(`${NB}za\\s+(\\d+)\\s+godzin\\p{L}*${NA}`, 'giu'), translate: (m, n) => `in ${n} hours` },
  { re: new RegExp(`${NB}za\\s+(\\d+)\\s+minut\\p{L}*${NA}`, 'giu'), translate: (m, n) => `in ${n} minutes` },
  { re: new RegExp(`${NB}za\\s+(\\d+)\\s+tyg\\p{L}*${NA}`, 'giu'), translate: (m, n) => `in ${n} weeks` },
  { re: new RegExp(`${NB}za\\s+p[oó][lł]\\s+godzin\\p{L}*${NA}`, 'giu'), translate: () => 'in 30 minutes' },
  { re: new RegExp(`${NB}za\\s+kwadrans${NA}`, 'giu'), translate: () => 'in 15 minutes' },
  { re: new RegExp(`${NB}za\\s+godzin[eę]${NA}`, 'giu'), translate: () => 'in 1 hour' },
  { re: new RegExp(`${NB}za\\s+tydzie[nń]${NA}`, 'giu'), translate: () => 'in 1 week' },
  { re: new RegExp(`${NB}pojutrze${NA}`, 'giu'), translate: () => 'in 2 days' },
  { re: new RegExp(`${NB}(dzisiaj|dziś)${NA}`, 'giu'), translate: () => 'today' },
  { re: new RegExp(`${NB}jutro${NA}`, 'giu'), translate: () => 'tomorrow' },
  { re: new RegExp(`${NB}wczoraj${NA}`, 'giu'), translate: () => 'yesterday' },
  { re: new RegExp(`${NB}poniedzia[lł]ek${NA}`, 'giu'), translate: () => 'monday' },
  { re: new RegExp(`${NB}wtorek${NA}`, 'giu'), translate: () => 'tuesday' },
  { re: new RegExp(`${NB}[sś]rod[eęya]${NA}`, 'giu'), translate: () => 'wednesday' },
  { re: new RegExp(`${NB}czwartek${NA}`, 'giu'), translate: () => 'thursday' },
  { re: new RegExp(`${NB}pi[aą]tek${NA}`, 'giu'), translate: () => 'friday' },
  { re: new RegExp(`${NB}sobot[eęya]${NA}`, 'giu'), translate: () => 'saturday' },
  { re: new RegExp(`${NB}niedziel[eęia]${NA}`, 'giu'), translate: () => 'sunday' },
  { re: new RegExp(`${NB}\\d{4}-\\d{2}-\\d{2}${NA}`, 'gu'), translate: (m) => m },
  { re: new RegExp(`${NB}([01]?\\d|2[0-3])[:.]([0-5]\\d)${NA}`, 'gu'), translate: (m, hh, mm) => `${hh}:${mm}` },
];

// Znajduje w tekście fragmenty pasujące do DATE_PATTERNS, wycina je z tekstu
// (dając tytuł wydarzenia) i składa z nich wyrażenie czasu dla `ical --start`.
function extractDateTime(text) {
  const matches = [];
  for (const { re, translate } of DATE_PATTERNS) {
    re.lastIndex = 0;
    let m;
    while ((m = re.exec(text)) !== null) {
      matches.push({
        start: m.index,
        end: m.index + m[0].length,
        original: m[0],
        translated: translate(...m),
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

  const minStart = spans[0].start;
  const maxEnd = spans[spans.length - 1].end;

  const title = (text.slice(0, minStart) + ' ' + text.slice(maxEnd))
    .replace(/\s+(w|we|o|na)\s*$/i, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  return {
    title: title || 'Wydarzenie',
    startExpr: spans.map((s) => s.translated).join(' '),
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

  const parsed = extractDateTime(raw);
  if (!parsed) {
    await bot.sendMessage(
      msg.chat.id,
      '❌ Nie rozpoznałem daty/godziny w treści. Spróbuj np. „jutro 14:00”, „za 2 dni”, „piątek 10:00” albo daty ISO (2026-03-15 14:00).'
    );
    return;
  }

  try {
    await icalAdd(parsed.title, parsed.startExpr);
    const event = await findCreatedEvent(parsed.title);
    const whenLabel = event ? formatLocalDateTime(event.start_date) : parsed.recognizedText;
    await bot.sendMessage(msg.chat.id, `✅ Dodano wydarzenie „${parsed.title}” — ${whenLabel}.`);
  } catch (err) {
    console.error('Błąd przy tworzeniu wydarzenia:', err);
    await bot.sendMessage(msg.chat.id, `❌ Nie udało się utworzyć wydarzenia: ${err.message}`);
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
