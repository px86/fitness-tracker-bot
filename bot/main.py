import os
import logging
import datetime
from enum import IntEnum
import aiosqlite
import typing
from telegram import Update
from telegram.constants import ParseMode
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
import bot.db as db
from bot.handlers.userinfo import userinfohandler
from bot.db.db import getuser

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


class MacroNutrients(BaseModel):
    calories: int
    protein: int
    fat: int
    carbohydrate: int


async def macro_nutrient_breakdown(meal_description: str) -> str | None:
    """Get macro nutrient breakdown for given meal as a JSON string."""

    try:
        response = await gemini.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Give the total calories (in KCal) and a macro nutrient breakdown (in grams) of the following meal description.\n{meal_description}",
            config={
                "response_mime_type": "application/json",
                "response_schema": MacroNutrients,
            },
        )
        return response.text
    except Exception:
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    userid = update.message.from_user.id
    user = await getuser(userid)
    if user is not None:
        await update.message.reply_text(
            "\n".join(
                [
                    f"Hi <b>{user.name}</b>, I'm glad to see you again. How may I help you?",
                    "",
                    "/CaptureMeal     record a meal",
                    "/RecordUserInfo  update your information by re-recording them",
                ]
            ),
            parse_mode=ParseMode.HTML,
        )

    else:
        await update.message.reply_text(
            "\n".join(
                [
                    "Hi there! you are new here.",
                    "I am here to help you in your fitness journey.",
                    "Let's start by recording some of your basic information like age, height, weight etc.",
                    "Please send /RecordUserInfo to get started.",
                ]
            )
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
    conn = await db.connect()
    description = update.message.text
    timestamp = datetime.datetime.now().isoformat()
    meal_id = (
        await conn.execute_insert(
            "INSERT INTO meals(description, timestamp) VALUES(?, ?)",
            (description, timestamp),
        )
    )[0]
    await conn.commit()
    await update.message.reply_text(f"Meal has been recorded. Meal id is {meal_id}.")
    nutrition_info_json = await macro_nutrient_breakdown(description)
    if nutrition_info_json:
        await conn.execute(
            "UPDATE meals SET nutrient_breakdown=? WHERE id=?",
            (nutrition_info_json, meal_id),
        )
        await conn.commit()
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
        .post_init(db.connect)
        .post_init(db.init)
        .post_shutdown(db.disconnect)
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

    application.add_handler(userinfohandler)

    application.run_polling()


if __name__ == "__main__":
    main()
