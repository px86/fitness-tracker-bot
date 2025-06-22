import os
import logging
import datetime
from enum import IntEnum
import aiosqlite
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
from dotenv import load_dotenv

load_dotenv()


logging.getLogger("httpx").setLevel(logging.WARNING)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


class BotTokenUnavailableException(Exception):
    """Exception thrown when telegram bot token is not available."""


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise BotTokenUnavailableException(
        "TELEGRAM_BOT_TOKEN environment variable is not set"
    )

db: aiosqlite.Connection | None = None


async def db_connect(*args) -> aiosqlite.Connection:
    """Return database connection."""
    global db
    if db is None:
        db = await aiosqlite.connect("fitness-tracker.db")
    return db


async def db_disconnect(*args) -> None:
    """Close the database connection"""
    global db
    if db is not None:
        await db.close()
        db = None


async def db_init(*args) -> None:
    """Create database table if does not exist already."""
    db = await db_connect()
    await db.execute(
        """CREATE TABLE IF NOT EXISTS meals(
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 timestamp TEXT NOT NULL,
                 description TEXT NOT NULL,
                 calories INTEGER,
                 nutrient_breakdown TEXT
            );"""
    )
    await db.commit()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """Hi there! I am here to help you track your fitness. Please select one of the following commands.
        /CaptureMeal - record a meal
        """,
    )


class MealConversationState(IntEnum):
    DESCRIPTION = 0


async def capture_meal(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> MealConversationState | ConversationHandler:
    await update.message.reply_text(text="What did you eat?")
    return MealConversationState.DESCRIPTION


async def description(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> MealConversationState | ConversationHandler:
    db = await db_connect()
    description = update.message.text
    timestamp = datetime.datetime.now().isoformat()
    meal_id = (
        await db.execute_insert(
            "INSERT INTO meals(description, timestamp) VALUES(?, ?)",
            (description, timestamp),
        )
    )[0]
    await db.commit()
    await update.message.reply_text(f"Meal has been recorded. Meal id is {meal_id}.")
    return ConversationHandler.END


async def cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> ConversationHandler.END:
    await update.message.reply_text("Aborted!")
    return ConversationHandler.END


def main():
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(db_connect)
        .post_init(db_init)
        .post_shutdown(db_disconnect)
        .build()
    )

    application.add_handler(CommandHandler("start", start))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("CaptureMeal", capture_meal)],
        states={
            MealConversationState.DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, description)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
