from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
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
    await update.message.reply_text("Welcome! 🚗 Enter your VIN (17 characters):")
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
        reply = f"🔎 VIN Details:\nMake: {make}\nModel: {model}\nYear: {year}"
    else:
        reply = "❌ API Error. Please try later."

    await update.message.reply_text(reply)
    await update.message.reply_text("Do you want to check another VIN? (yes/no)")
    return ASK_AGAIN

async def handle_yes_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text.strip().lower()
    if answer in ['yes', 'y']:
        await update.message.reply_text("Please enter the next VIN:")
        return ASK_VIN
    elif answer in ['no', 'n']:
        await update.message.reply_text("Goodbye 👋")
        return ConversationHandler.END
    else:
        await update.message.reply_text("❓ Reply 'yes' or 'no'.")
        return ASK_AGAIN

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Session ended. Bye 👋")
    return ConversationHandler.END

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
    print("✅ Bot is running...")
    app.run_polling()



