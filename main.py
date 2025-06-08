import asyncio
import logging
import sys
import os # Додаємо імпорт os для роботи зі змінними середовища

# Імпортуємо keep_alive з background.py
# Переконайтеся, що background.py знаходиться в тому ж каталозі
from background import keep_alive 

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message

# ----- Налаштування Логування -----
# Рекомендується встановити рівень INFO для aiogram, щоб бачити, що бот працює
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout) # Виводимо логи в stdout для Scalingo
    ]
)
# Зменшуємо рівень логування для деяких бібліотек, щоб не засмічувати логи
logging.getLogger("httpx").setLevel(logging.WARNING)
# Прибрано "telegram.ext", оскільки ми використовуємо aiogram, а не python-telegram-bot
# logging.getLogger("telegram.ext").setLevel(logging.INFO) 

# ----- Отримання токена бота -----
# ЗАВЖДИ отримуйте токен зі змінних середовища для безпеки
# У Scalingo, ви додаєте TELEGRAM_BOT_TOKEN у налаштуваннях вашого додатку
TOKEN = os.getenv('7991708926:AAHiMO6q2q2HrW6HI1hCp95rRVksz1VA0wQ') 

# Перевірка, чи токен встановлено
if not TOKEN:
    logging.critical("TELEGRAM_BOT_TOKEN environment variable not set. Exiting.")
    sys.exit(1)

# ----- Ініціалізація Бота та Диспетчера -----
# Ініціалізуємо Bot та Dispatcher на глобальному рівні (або в main(), але так простіше для початку)
# DefaultBotProperties дозволяє задати parse_mode для всіх відповідей бота
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ----- Обробник команди /start -----
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    Цей обробник відповідає на команду /start
    """
    user_name = message.from_user.full_name if message.from_user else "Гість"
    await message.answer(f"Привіт, {html.bold(user_name)}! Я бот, який надсилає новини з ринку Форекс. Щоб отримати допомогу, напиши /help.")


# ----- Обробник для інших повідомлень (ECHO) -----
@dp.message()
async def echo_handler(message: Message) -> None:
    """
    Цей обробник копіює отримане повідомлення.
    Якщо повідомлення не може бути скопійоване (наприклад, стикер), він відповідає "Nice try!".
    """
    try:
        # Відправляємо копію отриманого повідомлення
        await message.send_copy(chat_id=message.chat.id)
    except TypeError:
        # Обробляємо випадки, коли тип повідомлення не підтримується для копіювання
        await message.answer("Nice try!")


# ----- Основна асинхронна функція запуску -----
async def main() -> None:
    # Запускаємо Flask сервер у фоновому режимі для підтримки активності на хостингу
    # Цей сервер буде відповідати на HTTP-запити Scalingo для "health check"
    keep_alive() 
    logging.info("Flask keep-alive server started in background.")

    # Запускаємо опитування Telegram API
    logging.info("Starting aiogram bot polling...")
    # skip_updates=True дозволяє ігнорувати повідомлення, які були надіслані, поки бот був офлайн
    await dp.start_polling(bot, skip_updates=True) 
    logging.info("aiogram bot polling stopped.")


# ----- Точка входу в програму -----
if __name__ == "__main__":
    # Запускаємо основну асинхронну функцію
    asyncio.run(main())
