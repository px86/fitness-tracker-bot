import os
import logging
import datetime
from enum import IntEnum
import aiosqlite
import typing
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv

load_dotenv()


logging.getLogger("httpx").setLevel(logging.WARNING)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


class BotTokenUnavailableException(Exception):
    """Exception thrown when telegram bot token is not available."""


class GeminiAPIKeyUnavailableException(Exception):
    """Exception thrown when google gemini api token is not available."""


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise BotTokenUnavailableException(
        "TELEGRAM_BOT_TOKEN environment variable is not set"
    )

GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise GeminiAPIKeyUnavailableException(
        "GOOGLE_GEMINI_API_KEY environment variable is not set"
    )

gemini = genai.Client(api_key=GEMINI_API_KEY)


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
                 nutrient_breakdown TEXT
            );"""
    )
    await db.commit()


class MacroNutrient(BaseModel):
    name: typing.Literal["protein", "fat", "carbohydrate"]
    content_in_grams: int


class MealNutrition(BaseModel):
    calories: int
    macro_nutrients: list[MacroNutrient]


async def macro_nutrient_breakdown(meal_description: str) -> str:
    """Get macro nutrient breakdown for given meal as a JSON string."""
    response = await gemini.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Give the total calories (in KCal) and a macro nutrient breakdown (in grams) of the following meal description.\n{meal_description}",
        config={
            "response_mime_type": "application/json",
            "response_schema": MealNutrition,
        },
    )
    return response.text


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
    nutrition_info_json = await macro_nutrient_breakdown(description)
    if nutrition_info_json:
        await db.execute(
            "UPDATE meals SET nutrient_breakdown=? WHERE id=?",
            (nutrition_info_json, meal_id),
        )
        await db.commit()
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
