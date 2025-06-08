import asyncio
import logging
import sys
import os
import requests # Для отримання новин
from bs4 import BeautifulSoup # Для парсингу RSS-стрічок
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler # Для планування завдань

# Імпортуємо keep_alive з background.py
from background import keep_alive #

# aiogram v3 імпорти
from aiogram import Bot, Dispatcher, html #
from aiogram.client.default import DefaultBotProperties #
from aiogram.enums import ParseMode #
from aiogram.filters import CommandStart #
from aiogram.types import Message #

# ----- Налаштування Логування -----
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout) # Виводимо логи в stdout для Scalingo
    ]
)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ----- Отримання токена бота та ID чату зі змінних середовища -----
# Встановіть ці змінні у налаштуваннях вашого додатка на Scalingo!
# Ваш токен бота має бути ЗНАЧЕННЯМ змінної оточення TELEGRAM_BOT_TOKEN
# а не її назвою.
TOKEN = os.getenv('7991708926:AAHiMO6q2q2HrW6HI1hCp95rRVksz1VA0wQ') # Тут має бути назва змінної, а не сам токен.
# ID чату, куди надсилати новини. Може бути один або кілька, розділені комами.
# Наприклад: "123456789,987654321"
TARGET_CHAT_IDS_STR = os.getenv('475384360') # Тут має бути назва змінної, а не сам ID.

if not TOKEN:
    logging.critical("TELEGRAM_BOT_TOKEN environment variable not set. Exiting.")
    sys.exit(1)

if not TARGET_CHAT_IDS_STR:
    logging.warning("TARGET_CHAT_IDS environment variable not set. News won't be sent.")
    TARGET_CHAT_IDS = []
else:
    try:
        TARGET_CHAT_IDS = [int(chat_id.strip()) for chat_id in TARGET_CHAT_IDS_STR.split(',')]
    except ValueError:
        logging.critical("Invalid TARGET_CHAT_IDS format. Please provide comma-separated integers. Exiting.")
        sys.exit(1)

# ----- Ініціалізація Бота та Диспетчера -----
# bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)) # Цей рядок у вас вже був, це ОК
# dp = Dispatcher(bot) # (виправлено до dp = Dispatcher())
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)) #
dp = Dispatcher() # Диспетчер в aiogram v3 ініціалізується без аргументів

# ----- Список RSS-стрічок для новин -----
FEEDS = [
    "https://www.forexlive.com/feed/",
    "https://www.investing.com/rss/news.rss",
    "https://www.fxstreet.com/rss",
]

# Зберігаємо вже надіслані заголовки новин, щоб уникнути дублікатів
# У реальному проєкті це має бути база даних або Redis для стійкості
SENT_NEWS_TITLES = set()

# ----- Функція для отримання та парсингу новин -----
async def fetch_news_job():
    logging.info("Fetching news...")
    new_articles_count = 0
    for feed_url in FEEDS:
        try:
            response = requests.get(feed_url, timeout=10)
            response.raise_for_status() # Перевіряємо на HTTP помилки
            soup = BeautifulSoup(response.content, 'xml') # Парсимо як XML

            items = soup.find_all('item') # Для RSS 2.0
            if not items:
                items = soup.find_all('entry') # Для Atom

            for item in items:
                title = item.find('title').text.strip() if item.find('title') else 'No title'
                link = item.find('link').text.strip() if item.find('link') else 'No link'
                description = item.find('description').text.strip() if item.find('description') else 'No description'

                # Обмежуємо довжину опису
                if len(description) > 200:
                    description = description[:200] + "..."

                # Перевіряємо, чи новина вже була надіслана
                if title not in SENT_NEWS_TITLES:
                    SENT_NEWS_TITLES.add(title)
                    news_message = (
                        f"<b>НОВА НОВИНА:</b>\n"
                        f"{html.bold(title)}\n"
                        f"{description}\n"
                        f"Посилання: {html.link('Читати далі', link)}"
                    )

                    for chat_id in TARGET_CHAT_IDS:
                        try:
                            await bot.send_message(chat_id, news_message, disable_web_page_preview=True)
                            new_articles_count += 1
                        except Exception as e:
                            logging.error(f"Failed to send news to chat {chat_id}: {e}")
                else:
                    logging.debug(f"News '{title}' already sent. Skipping.")

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching RSS feed {feed_url}: {e}")
        except Exception as e:
            logging.error(f"Error parsing RSS feed {feed_url}: {e}")

    if new_articles_count > 0:
        logging.info(f"Sent {new_articles_count} new articles.")
    else:
        logging.info("No new articles found.")

# ----- Обробник команди /start -----
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    Цей обробник відповідає на команду /start
    """
    user_name = message.from_user.full_name if message.from_user else "Гість"
    await message.answer(f"Привіт, {html.bold(user_name)}! Я бот, який надсилає новини з ринку Форекс. "
                         f"Щоб отримати допомогу, напиши /help.\n"
                         f"Щоб я надсилав новини у цей чат, ваш Chat ID: {message.chat.id}. "
                         f"Попросіть власника бота додати його до TARGET_CHAT_IDS.")

# ----- Обробник для інших повідомлень (ECHO) -----
@dp.message()
async def echo_handler(message: Message) -> None:
    """
    Цей обробник копіює отримане повідомлення.
    Якщо повідомлення не може бути скопійоване (наприклад, стикер), він відповідає "Nice try!".
    """
    try:
        await message.send_copy(chat_id=message.chat.id)
    except TypeError:
        await message.answer("Nice try!")

# ----- Основна асинхронна функція запуску -----
async def main() -> None:
    # Запускаємо Flask сервер у фоновому режимі для підтримки активності на хостингу.
    # Цей сервер буде відповідати на HTTP-запити Scalingo для "health check".
    keep_alive() #
    logging.info("Flask keep-alive server started in background.")

    # Ініціалізуємо планувальник
    scheduler = AsyncIOScheduler()
    # Додаємо завдання для отримання новин: запускати кожні 5 хвилин
    scheduler.add_job(fetch_news_job, 'interval', minutes=5)
    # Запускаємо планувальник
    scheduler.start()
    logging.info("News fetching scheduler started.")

    # Запускаємо опитування Telegram API.
    # skip_updates=True дозволяє ігнорувати повідомлення, які були надіслані, поки бот був офлайн.
    logging.info("Starting aiogram bot polling...")
    await dp.start_polling(bot, skip_updates=True) # (виправлено синтаксис для v3)
    logging.info("aiogram bot polling stopped.")


# ----- Точка входу в програму -----
if __name__ == "__main__":
    asyncio.run(main())
