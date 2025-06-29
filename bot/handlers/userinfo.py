from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.db.db import saveuser
from bot.models.user import User

NAME, GENDER, AGE, HEIGHT, WEIGHT = range(5)


async def recorduserinfo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Please tell me your name.")
    return NAME


async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_name = update.message.text
    if len(user_name) > 120:
        await update.message.reply_text(
            "Your name is too long, please provide a shorter name!"
        )
        return NAME
    context.user_data["user_info"] = {"name": user_name}

    reply_keyboard = [["male", "female", "other"]]

    await update.message.reply_text(
        "Please tell me your gender.",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder="male, female or other?",
        ),
    )
    return GENDER


async def gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_gender = update.message.text
    if user_gender not in ["male", "female", "other"]:
        await update.message.reply_text(
            "Please enter one of the following: male, female, other"
        )
        return GENDER
    context.user_data["user_info"]["gender"] = user_gender

    await update.message.reply_text("Please tell me your age.")
    return AGE


async def age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_age = update.message.text
    if not user_age.isdigit() or not (0 < int(user_age) < 120):
        await update.message.reply_text("Please enter an integer between 0 and 120.")
        return AGE
    context.user_data["user_info"]["age"] = int(user_age)

    await update.message.reply_text("What is your height in centimeters?")
    return HEIGHT


async def height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_height = update.message.text
    try:
        user_height = float(user_height)
        if user_height < 0:
            raise ValueError("invalid height")

        context.user_data["user_info"]["height"] = user_height
        await update.message.reply_text("What is your weight in kilograms?")
        return WEIGHT

    except ValueError:
        await update.message.reply_text("Please enter a valid height.")
        return HEIGHT


async def weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_weight = update.message.text
    try:
        user_weight = float(user_weight)
        if user_weight < 0:
            raise ValueError("invalid weight")

        context.user_data["user_info"]["weight"] = user_weight

        context.user_data["user_info"]["userid"] = update.message.from_user.id
        user = User(**context.user_data["user_info"])
        await saveuser(user)

        await update.message.reply_text("Data recorded.")
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("Please enter a valid weight.")
        return WEIGHT


async def abort(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return ConversationHandler.END


userinfohandler = ConversationHandler(
    entry_points=[CommandHandler("RecordUserInfo", recorduserinfo)],
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
        GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, gender)],
        AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
        HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, height)],
        WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight)],
    },
    fallbacks=[CommandHandler("abort", abort), CommandHandler("cancel", abort)],
)
