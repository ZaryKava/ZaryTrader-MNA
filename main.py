import os # ДОДАНО ЦЕЙ ІМПОРТ
import logging
import feedparser
import asyncio # Для асинхронних операцій

# Імпорти для python-telegram-bot
from telegram import Bot
from telegram.ext import Application, ApplicationBuilder, ContextTypes
from telegram.constants import ParseMode

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logging.getLogger("httpx").setLevel(logging.WARNING) # Зменшити логування для httpx
logging.getLogger("telegram.ext").setLevel(logging.INFO) # Зменшити логування для telegram.ext

# --- КОНФІГУРАЦІЯ БОТА ---
# Токен отримується з змінних оточення (Secrets на Replit, Environment Variables на Render)
TOKEN = os.environ.get("TOKEN") # ТЕПЕР ПРАВИЛЬНО ЧИТАЄ ТОКЕН ЗІ ЗМІННИХ ОТОЧЕННЯ
# Ваш ID чату. Переконайтеся, що він правильний (для групи може бути від'ємним)
CHAT_ID = "475384360" # <<<<<<<< ПЕРЕВІРТЕ ТА ВИПРАВТЕ ЦЕЙ CHAT_ID, ЯКЩО ВІН НЕПРАВИЛЬНИЙ!

# Список RSS-стрічок
FEEDS = [
    "https://www.forexlive.com/feed/",
    "https://www.investing.com/rss/news.rss",
    "https://www.fxstreet.com/rss",
    "https://www.forexfactory.com/calendar.php?week=thisweek&format=rss",
]

# Набір для зберігання вже надісланих посилань
seen_links = set()

# Асинхронна функція для отримання та надсилання новин
async def fetch_news_job(context: ContextTypes.DEFAULT_TYPE):
    logging.info("Починаю перевірку новин...")
    bot = context.bot # Отримуємо об'єкт бота з контексту

    for url in FEEDS:
        logging.info(f"Намагаюсь отримати стрічку з: {url}")
        try:
            feed = feedparser.parse(url)
            if not feed.entries:
                logging.warning(f"Не знайдено записів у стрічці з {url}. Можливо, стрічка порожня або тимчасово недоступна.")
                continue

            for entry in feed.entries[:5]: # Обмежуємо до 5 останніх, щоб уникнути спаму під час тестування
                entry_title = getattr(entry, 'title', 'Без заголовка')
                entry_link = getattr(entry, 'link', 'Без посилання')

                if entry_link == 'Без посилання':
                    logging.warning(f"Запис '{entry_title}' з {url} не має посилання. Пропускаю цей запис.")
                    continue

                if entry_link not in seen_links:
                    seen_links.add(entry_link)
                    text = f"📰 <b>{entry_title}</b>\n{entry_link}"
                    logging.info(f"Знайдено нове посилання: '{entry_link}'. Намагаюсь надіслати повідомлення до CHAT_ID: {CHAT_ID}...")
                    try:
                        # Перевіряємо, чи CHAT_ID встановлений
                        if not CHAT_ID:
                            logging.error("CHAT_ID не встановлений! Не можу надіслати повідомлення.")
                            continue
                        await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
                        logging.info(f"Повідомлення успішно надіслано для '{entry_title}'.")
                    except Exception as e:
                        logging.error(f"Помилка надсилання повідомлення для '{entry_title}' до CHAT_ID {CHAT_ID}: {e}", exc_info=True)
                        if "chat not found" in str(e).lower() or "bot was blocked by the user" in str(e).lower() or "not a member" in str(e).lower():
                            logging.critical(f"Критична помилка: Неправильний CHAT_ID або бот заблокований/не є адміністратором. Будь ласка, перевірте CHAT_ID: {CHAT_ID}")
                else:
                    logging.debug(f"Посилання '{entry_link}' зі стрічки {url} вже було надіслано. Пропускаю цей запис.")
        except Exception as e:
            logging.error(f"Не вдалося розібрати або підключитися до URL стрічки {url}: {e}", exc_info=True)
    logging.info("Перевірку новин завершено.")

# --- Основна асинхронна функція для запуску бота та планувальника ---
async def main():
    # Важливо: TOKEN має бути встановлений в змінних оточення Replit/Render.
    if not TOKEN:
        logging.critical("TOKEN не встановлений. Будь ласка, встановіть TOKEN як змінну оточення.")
        return

    logging.info("Application started. Setting up bot and scheduler.")

    # Створення Application для Telegram бота
    application = ApplicationBuilder().token(TOKEN).build()

    # Додаємо завдання до job_queue
    job_queue = application.job_queue
    # Запускати fetch_news_job кожні 60 секунд (1 хв), перший запуск через 5 секунд
    job_queue.run_repeating(fetch_news_job, interval=60, first=5)
    logging.info("fetch_news_job заплановано на запуск кожну 1 хвилину.")

    try:
        logging.info("Запускаю Telegram bot polling...")
        await application.run_polling()
        logging.info("Telegram bot polling запущено.")
    except KeyboardInterrupt:
        logging.info("Бот зупинено користувачем (KeyboardInterrupt).")
    except Exception as e:
        logging.critical(f"Виникла необроблена помилка в основному циклі бота: {e}", exc_info=True)
    finally:
        logging.info("Застосунок вимикається.")

# Запуск головної асинхронної функції
if __name__ == '__main__':
    asyncio.run(main())
