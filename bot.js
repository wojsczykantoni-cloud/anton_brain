require('dotenv').config();

const fs = require('fs');
const path = require('path');
const TelegramBot = require('node-telegram-bot-api');

const TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const CHAT_ID = String(process.env.TELEGRAM_CHAT_ID);

if (!TOKEN || !CHAT_ID) {
  console.error('Brak TELEGRAM_BOT_TOKEN lub TELEGRAM_CHAT_ID w pliku .env');
  process.exit(1);
}

const DAILY_DIR = path.join(__dirname, 'daily');
const TEMPLATE_PATH = path.join(__dirname, 'templates', 'daily.md');
const IDEAS_HEADING = '## 💡 Pomysły / obserwacje';

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

function appendIdea(dateStr, text) {
  const filePath = ensureDailyNote(dateStr);
  const content = fs.readFileSync(filePath, 'utf8');
  const lines = content.split('\n');

  const headingIndex = lines.findIndex((line) => line.trim() === IDEAS_HEADING);
  if (headingIndex === -1) {
    // Sekcja nie istnieje w pliku - dopisz ją na końcu.
    const newLines = content.replace(/\n+$/, '').split('\n');
    newLines.push('', IDEAS_HEADING, `- ${text}`, '');
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

  lines.splice(insertIndex, 0, `- ${text}`);
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

bot.on('message', async (msg) => {
  if (!isAuthorized(msg)) return;
  if (!msg.text) return; // interesują nas tylko wiadomości tekstowe
  if (msg.text.startsWith('/')) return; // komendy obsługujemy osobno

  const dateStr = todayISO();

  try {
    appendIdea(dateStr, msg.text);
    await bot.sendMessage(msg.chat.id, '✅ Dodano do dzisiejszych pomysłów.');
  } catch (err) {
    console.error('Błąd przy zapisie notatki:', err);
    await bot.sendMessage(msg.chat.id, '❌ Nie udało się zapisać notatki.');
  }
});

bot.on('polling_error', (err) => {
  console.error('Polling error:', err.message);
});

console.log('Bot Telegram uruchomiony i nasłuchuje...');
