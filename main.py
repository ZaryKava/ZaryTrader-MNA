import logging
import feedparser
import asyncio
from telegram.ext import Application, ApplicationBuilder, ContextTypes
from telegram.constants import ParseMode

# --- НАЛАШТУВАННЯ ---
TOKEN = "7991708926:AAHiMO6q2q2HrW6HI1hCp95rRVksz1VA0wQ"
CHAT_ID = "475384360" # <<<<<<<< ПЕРЕВІРТЕ ТА ВИПРАВТЕ ЦЕЙ CHAT_ID !

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.INFO)

application = ApplicationBuilder().token(TOKEN).build()

FEEDS = [
    "https://www.forexlive.com/feed/",
    "https://www.investing.com/rss/news.rss",
    "https://www.fxstreet.com/rss",
]

seen_links = set()

async def fetch_news_job(context: ContextTypes.DEFAULT_TYPE):
    logging.info("Starting fetch_news_job task...")
    bot = context.bot

    for url in FEEDS:
        logging.info(f"Attempting to fetch feed from: {url}")
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                logging.info(f"Successfully fetched feed from {url}. Found {len(feed.entries)} entries.")
            else:
                logging.warning(f"No entries found in feed from {url}. Possible empty, invalid, or temporarily unavailable feed.")
                continue

            for entry in feed.entries[:5]:
                entry_title = getattr(entry, 'title', 'No Title')
                entry_link = getattr(entry, 'link', 'No Link')

                if entry_link == 'No Link':
                    logging.warning(f"Entry '{entry_title}' from {url} has no link. Skipping this entry.")
                    continue

                if entry_link not in seen_links:
                    seen_links.add(entry_link)
                    text = f"📰 <b>{entry_title}</b>\n{entry_link}"
                    logging.info(f"New link found: '{entry_link}'. Attempting to send message to CHAT_ID: {CHAT_ID}...")
                    try:
                        await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode=ParseMode.HTML)
                        logging.info(f"Message sent successfully for '{entry_title}'.")
                    except Exception as e:
                        logging.error(f"Error sending message for '{entry_title}' to CHAT_ID {CHAT_ID}: {e}", exc_info=True)
                        if "chat not found" in str(e).lower() or "bot was blocked by the user" in str(e).lower() or "not a member" in str(e).lower():
                            logging.critical(f"Critical: Invalid CHAT_ID or bot blocked/not admin. Please check CHAT_ID: {CHAT_ID}")
                else:
                    logging.debug(f"Link '{entry_link}' from {url} already seen. Skipping this entry.")
        except Exception as e:
            logging.error(f"Failed to parse or connect to feed URL {url}: {e}", exc_info=True)
    logging.info("Finished fetch_news_job task.")

if __name__ == '__main__':
    logging.info("Application started. Setting up bot and scheduler.")

    job_queue = application.job_queue
    job_queue.run_repeating(fetch_news_job, interval=60, first=5) # Запускати кожні 60 секунд (1 хв), перший запуск через 5 секунд

    logging.info("fetch_news_job scheduled to run every 1 minute.")

    try:
        logging.info("Starting Telegram bot polling...")
        application.run_polling()
    except KeyboardInterrupt:
        logging.info("Bot stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logging.critical(f"An unhandled error occurred in the bot's main loop: {e}", exc_info=True)
    finally:
        logging.info("Application shutting down.")