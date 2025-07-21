from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackQueryHandler
)
from dotenv import load_dotenv
import requests
import os
import re

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

ASK_VIN, ASK_AGAIN = range(2)

def is_valid_vin(vin: str) -> bool:
    vin = vin.upper()
    return bool(re.fullmatch(r"^[A-HJ-NPR-Z0-9]{17}$", vin))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🔄 Get Random VIN", callback_data="get_random_vin")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome! 🚗\nSend me a VIN (17 characters) to decode it or tap below:",
        reply_markup=reply_markup
    )
    return ASK_VIN

async def handle_vin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vin = update.message.text.strip().upper()
    if not is_valid_vin(vin):
        await update.message.reply_text("❌ Invalid VIN. Must be 17 characters (no I, O, Q). Try again:")
        return ASK_VIN

    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}?format=json"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        results = data.get("Results", [])
        make = next((i['Value'] for i in results if i['Variable'] == "Make"), "N/A")
        model = next((i['Value'] for i in results if i['Variable'] == "Model"), "N/A")
        year = next((i['Value'] for i in results if i['Variable'] == "Model Year"), "N/A")
        reply = f"🔎 VIN Details:\n🚗 Make: {make}\n🚙 Model: {model}\n📅 Year: {year}"
    else:
        reply = "❌ Failed to decode VIN."

    keyboard = [[InlineKeyboardButton("🔄 Get Random VIN", callback_data="get_random_vin")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(reply, reply_markup=reply_markup)
    return ASK_AGAIN

async def handle_yes_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text.strip().lower()
    if answer in ['yes', 'y']:
        await update.message.reply_text("Please enter the next VIN:")
        return ASK_VIN
    elif answer in ['no', 'n']:
        await update.message.reply_text("Okay, goodbye! 👋")
        return ConversationHandler.END
    else:
        await update.message.reply_text("❓ Reply with 'yes' or 'no'.")
        return ASK_AGAIN

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Session ended. Bye 👋")
    return ConversationHandler.END

async def random_vin_logic():
    """Separate function to handle the VIN fetching logic"""
    try:
        vin_response = requests.get("https://randomvin.com/getvin.php?type=random")
        random_vin = vin_response.text.strip()
        
        url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{random_vin}?format=json"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            results = data.get("Results", [])
            make = next((i['Value'] for i in results if i['Variable'] == "Make"), "N/A")
            model = next((i['Value'] for i in results if i['Variable'] == "Model"), "N/A")
            year = next((i['Value'] for i in results if i['Variable'] == "Model Year"), "N/A")
            reply = f"🔑 Random VIN: {random_vin}\n🚗 Make: {make}\n🚙 Model: {model}\n📅 Year: {year}"
        else:
            reply = f"🔑 Random VIN: {random_vin}\n❌ Failed to decode VIN."

    except Exception as e:
        reply = f"❌ Error fetching VIN: {e}"
    
    return reply

async def random_vin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = await random_vin_logic()
    keyboard = [[InlineKeyboardButton("🔄 Get Another VIN", callback_data="get_random_vin")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(reply, reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "get_random_vin":
        reply = await random_vin_logic()
        keyboard = [[InlineKeyboardButton("🔄 Get Another VIN", callback_data="get_random_vin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # Use query.edit_message_text or query.message.reply_text for callback queries
        await query.message.reply_text(reply, reply_markup=reply_markup)

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_VIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_vin)],
            ASK_AGAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_yes_no)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("randomvin", random_vin))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("✅ Bot is running...")
    app.run_polling()