from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from dotenv import load_dotenv
import requests
import os
import re

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# States for ConversationHandler
ASK_VIN, ASK_AGAIN = range(2)

# VIN format validation function
def is_valid_vin(vin: str) -> bool:
    vin = vin.upper()
    return bool(re.fullmatch(r"^[A-HJ-NPR-Z0-9]{17}$", vin))

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! 🚗\nPlease enter your VIN (17 characters) to check vehicle details:")
    return ASK_VIN

# Handle VIN input
async def handle_vin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vin = update.message.text.strip().upper()

    if not is_valid_vin(vin):
        await update.message.reply_text("❌ Invalid VIN. A VIN must be 17 characters (letters & numbers, no I, O, Q).\nPlease try again:")
        return ASK_VIN

    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}?format=json"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        results = data.get("Results", [])
        make = next((item['Value'] for item in results if item['Variable'] == "Make"), "N/A")
        model = next((item['Value'] for item in results if item['Variable'] == "Model"), "N/A")
        year = next((item['Value'] for item in results if item['Variable'] == "Model Year"), "N/A")
        reply = f"🔎 VIN Details:\nMake: {make}\nModel: {model}\nYear: {year}"
    else:
        reply = "❌ Failed to fetch data from API."

    await update.message.reply_text(reply)
    await update.message.reply_text("Do you want to check another VIN? (yes/no)")
    return ASK_AGAIN

# Handle yes/no response
async def handle_yes_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text.strip().lower()
    if answer in ['yes', 'y']:
        await update.message.reply_text("Please enter the next VIN:")
        return ASK_VIN
    elif answer in ['no', 'n']:
        await update.message.reply_text("Okay, bye! 👋")
        return ConversationHandler.END
    else:
        await update.message.reply_text("❓ Please reply with 'yes' or 'no'.")
        return ASK_AGAIN

# Cancel command
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Conversation ended. Bye 👋")
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_VIN: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_vin)],
            ASK_AGAIN: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_yes_no)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)
    print("✅ Bot is running...")
    app.run_polling()
