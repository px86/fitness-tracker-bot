import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from dotenv import load_dotenv

load_dotenv()


class BotTokenUnavailableException(Exception):
    """Exception thrown when telegram bot token is not available."""


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise BotTokenUnavailableException(
        "TELEGRAM_BOT_TOKEN environment variable is not set"
    )


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!"
    )


if __name__ == "__main__":
    application = ApplicationBuilder().token(TOKEN).build()

    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)

    application.run_polling()
