from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackQueryHandler
)
from dotenv import load_dotenv
import requests
import os
import re
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

ASK_VIN, ASK_AGAIN = range(2)

# Cache to store previously shown VINs to avoid repeats
shown_vins = set()
MAX_CACHE_SIZE = 1000  # Prevent memory issues by limiting cache size

def is_valid_vin(vin: str) -> bool:
    vin = vin.upper()
    return bool(re.fullmatch(r"^[A-HJ-NPR-Z0-9]{17}$", vin))

def get_detailed_vin_info(results: list) -> dict:
    """Extract comprehensive VIN information"""
    info = {}
    
    # Basic vehicle info
    info['make'] = next((i['Value'] for i in results if i['Variable'] == "Make"), "N/A")
    info['model'] = next((i['Value'] for i in results if i['Variable'] == "Model"), "N/A")
    info['year'] = next((i['Value'] for i in results if i['Variable'] == "Model Year"), "N/A")
    
    # Additional details
    info['body_class'] = next((i['Value'] for i in results if i['Variable'] == "Body Class"), "N/A")
    info['vehicle_type'] = next((i['Value'] for i in results if i['Variable'] == "Vehicle Type"), "N/A")
    info['fuel_type'] = next((i['Value'] for i in results if i['Variable'] == "Fuel Type - Primary"), "N/A")
    info['engine_info'] = next((i['Value'] for i in results if i['Variable'] == "Engine Number of Cylinders"), "N/A")
    info['transmission'] = next((i['Value'] for i in results if i['Variable'] == "Transmission Style"), "N/A")
    info['drive_type'] = next((i['Value'] for i in results if i['Variable'] == "Drive Type"), "N/A")
    info['manufacturer'] = next((i['Value'] for i in results if i['Variable'] == "Manufacturer Name"), "N/A")
    info['plant_country'] = next((i['Value'] for i in results if i['Variable'] == "Plant Country"), "N/A")
    
    # Fuel capacity information - try multiple field names
    fuel_fields = [
        "Fuel Tank Capacity (gallons)",
        "Fuel Tank Capacity",
        "Tank Capacity",
        "Fuel Capacity",
        "Tank Size"
    ]
    
    info['fuel_capacity'] = "N/A"
    for field in fuel_fields:
        value = next((i['Value'] for i in results if i['Variable'] == field), None)
        if value and value != "N/A" and value.strip():
            info['fuel_capacity'] = value
            break
    
    # Liters version
    fuel_fields_liters = [
        "Fuel Tank Capacity (liters)",
        "Fuel Tank Capacity (L)",
        "Tank Capacity (liters)"
    ]
    
    info['fuel_capacity_liters'] = "N/A"
    for field in fuel_fields_liters:
        value = next((i['Value'] for i in results if i['Variable'] == field), None)
        if value and value != "N/A" and value.strip():
            info['fuel_capacity_liters'] = value
            break
    
    # Engine details
    info['displacement'] = next((i['Value'] for i in results if i['Variable'] == "Displacement (L)"), "N/A")
    info['displacement_ci'] = next((i['Value'] for i in results if i['Variable'] == "Displacement (CI)"), "N/A")
    
    # Safety ratings
    info['ncap_rating'] = next((i['Value'] for i in results if i['Variable'] == "NCAP Body Type"), "N/A")
    
    # Validation
    info['error_code'] = next((i['Value'] for i in results if i['Variable'] == "Error Code"), "0")
    info['error_text'] = next((i['Value'] for i in results if i['Variable'] == "Error Text"), "")
    
    return info

def format_vin_response(vin: str, info: dict, is_random: bool = False) -> str:
    """Format the VIN response with essential details only"""
    # Enhanced VIN authenticity detection
    is_real_vin = detect_real_vin(info)
    
    # Determine validation status with real/fake detection
    if info['error_code'] == "0" or "VIN decoded clean" in str(info['error_code']):
        if is_real_vin:
            status = "✅ REAL VIN - Authentic vehicle found"
        else:
            status = "🔸 FAKE VIN - Synthetic/Test VIN (valid format only)"
    else:
        status = f"❌ INVALID VIN - {info['error_text']}" if info['error_text'] else "❌ INVALID VIN"
    
    # Header
    header = f"🔑 Random VIN: {vin}" if is_random else f"🔎 VIN Analysis: {vin}"
    
    # Basic info
    basic_info = f"\n{status}\n\n📋 **Vehicle Details:**\n🚗 Make: {info['make']}\n🚙 Model: {info['model']}\n📅 Year: {info['year']}"
    
    # Additional details (only essential info)
    additional = ""
    if info['make'] != "N/A" and info['make']:
        details = []
        if info['manufacturer'] != "N/A": details.append(f"🏭 Manufacturer: {info['manufacturer']}")
        
        # Fuel capacity - prioritize gallons, show liters as backup, add estimated capacity if no data
        fuel_added = False
        if info['fuel_capacity'] != "N/A" and info['fuel_capacity'].strip():
            details.append(f"⛽ Fuel Capacity: {info['fuel_capacity']} gallons")
            fuel_added = True
        elif info['fuel_capacity_liters'] != "N/A" and info['fuel_capacity_liters'].strip():
            # Convert liters to gallons if only liters available (1 gallon ≈ 3.785 liters)
            try:
                liters = float(info['fuel_capacity_liters'])
                gallons = round(liters / 3.785, 1)
                details.append(f"⛽ Fuel Capacity: ~{gallons} gallons ({info['fuel_capacity_liters']} L)")
                fuel_added = True
            except:
                details.append(f"⛽ Fuel Capacity: {info['fuel_capacity_liters']} liters")
                fuel_added = True
        
        # If no fuel capacity data available, add estimated range based on vehicle type
        if not fuel_added:
            # Provide estimated fuel capacity based on common vehicle types
            estimated_capacity = "12-20 gallons (estimated)"
            if info['body_class'] != "N/A":
                body_type = info['body_class'].lower()
                if "truck" in body_type or "suv" in body_type:
                    estimated_capacity = "15-25 gallons (estimated)"
                elif "compact" in body_type or "subcompact" in body_type:
                    estimated_capacity = "10-14 gallons (estimated)"
                elif "sedan" in body_type:
                    estimated_capacity = "12-18 gallons (estimated)"
            details.append(f"⛽ Fuel Capacity: {estimated_capacity}")
        
        if info['plant_country'] != "N/A": details.append(f"🌍 Origin: {info['plant_country']}")
        
        if details:
            additional = f"\n\n🔍 **Essential Details:**\n" + "\n".join(details)
    
    return header + basic_info + additional

def detect_real_vin(info: dict) -> bool:
    """Enhanced detection to determine if VIN corresponds to a real manufactured vehicle"""
    # Criteria for real VIN detection
    real_indicators = 0
    total_checks = 0
    
    # Check 1: Has meaningful vehicle data
    if info['make'] != "N/A" and info['make'].strip():
        real_indicators += 1
    total_checks += 1
    
    # Check 2: Has model information
    if info['model'] != "N/A" and info['model'].strip():
        real_indicators += 1
    total_checks += 1
    
    # Check 3: Has valid year (not future or too old)
    if info['year'] != "N/A" and info['year'].strip():
        try:
            year = int(info['year'])
            if 1980 <= year <= 2025:  # Reasonable vehicle year range
                real_indicators += 1
        except:
            pass
    total_checks += 1
    
    # Check 4: Has manufacturer details
    if info['manufacturer'] != "N/A" and info['manufacturer'].strip():
        real_indicators += 1
    total_checks += 1
    
    # Check 5: Has plant/origin information
    if info['plant_country'] != "N/A" and info['plant_country'].strip():
        real_indicators += 1
    total_checks += 1
    
    # Check 6: Has body class or vehicle type info
    if (info['body_class'] != "N/A" and info['body_class'].strip()) or \
       (info['vehicle_type'] != "N/A" and info['vehicle_type'].strip()):
        real_indicators += 1
    total_checks += 1
    
    # Check 7: Error code indicates valid VIN
    if info['error_code'] == "0" or "VIN decoded clean" in str(info['error_code']):
        real_indicators += 1
    total_checks += 1
    
    # VIN is considered "real" if it passes at least 5 out of 7 checks
    return real_indicators >= 5

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"User {user.id} ({user.first_name}) started the bot")
    
    keyboard = [
        [InlineKeyboardButton("🔄 Get Random VIN", callback_data="get_random_vin")],
        [InlineKeyboardButton("ℹ️ About VINs", callback_data="about_vin"),
         InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_msg = (
        "🚗 **Professional VIN Decoder Bot** 🔍\n\n"
        "Welcome! I can decode Vehicle Identification Numbers (VINs) and provide comprehensive vehicle information.\n\n"
        "📝 **How to use:**\n"
        "• Send me any 17-character VIN to decode\n"
        "• Use buttons below for random VINs or help\n"
        "• Get detailed vehicle specifications and validation\n\n"
        "🔒 **Powered by NHTSA Official Database**"
    )
    
    await update.message.reply_text(welcome_msg, reply_markup=reply_markup, parse_mode='Markdown')
    return ASK_VIN

async def handle_vin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vin = update.message.text.strip().upper()
    user = update.effective_user
    logger.info(f"User {user.id} submitted VIN: {vin}")
    
    if not is_valid_vin(vin):
        await update.message.reply_text(
            "❌ **Invalid VIN Format**\n\n"
            "VIN must be exactly 17 characters and cannot contain I, O, or Q.\n"
            "Please try again:", 
            parse_mode='Markdown'
        )
        return ASK_VIN

    # Show processing message
    processing_msg = await update.message.reply_text("🔄 Analyzing VIN... Please wait.")
    
    # Decode the VIN
    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}?format=json"
    try:
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("Results", [])
            info = get_detailed_vin_info(results)
            reply = format_vin_response(vin, info, is_random=False)
        else:
            reply = f"🔎 VIN: {vin}\n❌ NHTSA API error (HTTP {response.status_code})"
    
    except requests.exceptions.Timeout:
        reply = f"🔎 VIN: {vin}\n❌ Request timeout. Server may be busy, please try again."
    except Exception as e:
        logger.error(f"Error decoding VIN {vin}: {str(e)}")
        reply = f"🔎 VIN: {vin}\n❌ Unexpected error occurred."

    # Delete processing message and send result
    await processing_msg.delete()
    
    keyboard = [
        [InlineKeyboardButton("🔄 Get Random VIN", callback_data="get_random_vin")],
        [InlineKeyboardButton("🔍 Search Another VIN", callback_data="search_manual"), 
         InlineKeyboardButton("📊 VIN Report", callback_data=f"report_{vin}")],
        [InlineKeyboardButton("❌ End Search", callback_data="end_search")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(reply, reply_markup=reply_markup, parse_mode='Markdown')
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
    """Separate function to handle the VIN fetching logic with duplicate prevention"""
    global shown_vins
    
    max_attempts = 10  # Prevent infinite loops
    attempts = 0
    
    while attempts < max_attempts:
        try:
            # Fetch random VIN from randomvin.com
            vin_response = requests.get("https://randomvin.com/getvin.php?type=random", timeout=15)
            if vin_response.status_code != 200:
                return "❌ Failed to fetch random VIN from service."
            
            random_vin = vin_response.text.strip()
            
            # Validate the VIN format
            if not is_valid_vin(random_vin):
                attempts += 1
                continue
            
            # Check if we've seen this VIN before
            if random_vin in shown_vins:
                attempts += 1
                logger.info(f"Skipping duplicate VIN: {random_vin}")
                continue
            
            # Add to cache (manage cache size)
            shown_vins.add(random_vin)
            if len(shown_vins) > MAX_CACHE_SIZE:
                # Remove oldest 100 VINs to keep cache manageable
                shown_vins = set(list(shown_vins)[100:])
            
            # Decode the VIN using NHTSA API
            url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{random_vin}?format=json"
            response = requests.get(url, timeout=15)

            if response.status_code == 200:
                data = response.json()
                results = data.get("Results", [])
                info = get_detailed_vin_info(results)
                return format_vin_response(random_vin, info, is_random=True)
            else:
                # If API fails for this VIN, try another one
                attempts += 1
                continue

        except requests.exceptions.Timeout:
            return "❌ Request timed out. Server may be busy, please try again."
        except requests.exceptions.RequestException as e:
            return f"❌ Network error: Service temporarily unavailable."
        except Exception as e:
            logger.error(f"Random VIN error: {str(e)}")
            attempts += 1
            continue
    
    # If we've exhausted all attempts
    return "❌ Unable to generate a unique VIN after multiple attempts. Please try again."

async def random_vin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    processing_msg = await update.message.reply_text("🔄 Generating random VIN... Please wait.")
    reply = await random_vin_logic()
    await processing_msg.delete()
    
    keyboard = [
        [InlineKeyboardButton("🔄 Get Another VIN", callback_data="get_random_vin")],
        [InlineKeyboardButton("🔍 Search Manually", callback_data="search_manual"), 
         InlineKeyboardButton("📊 Clear Cache", callback_data="clear_cache")],
        [InlineKeyboardButton("❌ End Search", callback_data="end_search")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(reply, reply_markup=reply_markup, parse_mode='Markdown')

async def show_help(update, context, is_callback=False):
    help_text = (
        "❓ **VIN Decoder Bot Help**\n\n"
        "🔍 **What is a VIN?**\n"
        "A Vehicle Identification Number is a unique 17-character code that identifies every motor vehicle.\n\n"
        "📝 **How to use this bot:**\n"
        "• Send any 17-character VIN to get detailed analysis\n"
        "• Use 'Get Random VIN' for testing with sample data\n"
        "• All data comes from the official NHTSA database\n\n"
        "✅ **Features:**\n"
        "• VIN format validation\n"
        "• Comprehensive vehicle specifications\n"
        "• Real vs. synthetic VIN detection\n"
        "• Technical details and safety information\n\n"
        "🆘 **Commands:**\n"
        "/start - Start the bot\n"
        "/randomvin - Get a random VIN\n"
        "/help - Show this help\n"
        "/cancel - End current session"
    )
    
    if is_callback:
        await update.callback_query.message.reply_text(help_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(help_text, parse_mode='Markdown')

async def show_about_vin(query):
    about_text = (
        "ℹ️ **About Vehicle Identification Numbers**\n\n"
        "🔢 **VIN Structure (17 characters):**\n"
        "• Positions 1-3: World Manufacturer Identifier\n"
        "• Positions 4-8: Vehicle Descriptor Section\n"
        "• Position 9: Check Digit\n"
        "• Position 10: Model Year\n"
        "• Position 11: Assembly Plant\n"
        "• Positions 12-17: Vehicle Identifier Section\n\n"
        "🚫 **Excluded Characters:**\n"
        "Letters I, O, and Q are never used to avoid confusion with numbers 1, 0, and 0.\n\n"
        "🔒 **Data Source:**\n"
        "This bot uses the official NHTSA (National Highway Traffic Safety Administration) database for accurate and up-to-date vehicle information."
    )
    
    await query.message.reply_text(about_text, parse_mode='Markdown')

async def generate_vin_report(vin: str):
    """Generate a comprehensive VIN report with all technical details"""
    try:
        url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}?format=json"
        response = requests.get(url, timeout=15)
        
        if response.status_code != 200:
            return "❌ Unable to generate report. Please try again."
        
        data = response.json()
        results = data.get("Results", [])
        
        # Extract comprehensive information for detailed report
        report_data = {}
        comprehensive_fields = [
            "Make", "Model", "Model Year", "Body Class", "Vehicle Type",
            "Fuel Type - Primary", "Engine Number of Cylinders", "Displacement (L)", "Displacement (CI)",
            "Fuel Tank Capacity (gallons)", "Fuel Tank Capacity (liters)",
            "Transmission Style", "Drive Type", "Manufacturer Name",
            "Plant Country", "Plant State", "NCAP Body Type", "Safety Rating",
            "Series", "Trim", "Vehicle Descriptor", "Engine Model", "Engine Power (kW)",
            "Gross Vehicle Weight Rating", "Curb Weight (pounds)", "Wheelbase (inches)",
            "Track Width (inches)", "Overall Length (inches)", "Overall Width (inches)", "Overall Height (inches)"
        ]
        
        for field in comprehensive_fields:
            value = next((i['Value'] for i in results if i['Variable'] == field), "N/A")
            if value and value != "N/A" and value.strip():
                report_data[field] = value
        
        # Get authenticity info
        info = get_detailed_vin_info(results)
        is_real = detect_real_vin(info)
        authenticity = "🟢 REAL VEHICLE" if is_real else "🔸 SYNTHETIC/TEST VIN"
        
        # Format the comprehensive report
        report = f"📊 **Comprehensive VIN Report**\n"
        report += f"🔑 VIN: `{vin}`\n"
        report += f"🔍 Authenticity: {authenticity}\n"
        report += f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        
        if report_data:
            # Group data by categories
            basic_info = {}
            technical_specs = {}
            dimensions = {}
            manufacturing = {}
            
            for field, value in report_data.items():
                if field in ["Make", "Model", "Model Year", "Series", "Trim"]:
                    basic_info[field] = value
                elif field in ["Engine Number of Cylinders", "Displacement (L)", "Displacement (CI)", 
                              "Engine Model", "Engine Power (kW)", "Transmission Style", "Drive Type",
                              "Fuel Type - Primary", "Fuel Tank Capacity (gallons)", "Fuel Tank Capacity (liters)"]:
                    technical_specs[field] = value
                elif field in ["Overall Length (inches)", "Overall Width (inches)", "Overall Height (inches)",
                              "Wheelbase (inches)", "Track Width (inches)", "Gross Vehicle Weight Rating", "Curb Weight (pounds)"]:
                    dimensions[field] = value
                elif field in ["Manufacturer Name", "Plant Country", "Plant State", "Body Class", "Vehicle Type"]:
                    manufacturing[field] = value
            
            # Basic Vehicle Information
            if basic_info:
                report += "🚗 **Basic Information:**\n"
                for field, value in basic_info.items():
                    emoji = {"Make": "🏭", "Model": "🚙", "Model Year": "📅", "Series": "📋", "Trim": "✨"}.get(field, "📋")
                    report += f"{emoji} {field}: {value}\n"
                report += "\n"
            
            # Technical Specifications
            if technical_specs:
                report += "🔧 **Technical Specifications:**\n"
                for field, value in technical_specs.items():
                    emoji = {
                        "Engine Number of Cylinders": "🔧", "Displacement (L)": "🏎️", "Displacement (CI)": "🏎️",
                        "Engine Model": "🔧", "Engine Power (kW)": "⚡", "Transmission Style": "⚙️",
                        "Drive Type": "🛣️", "Fuel Type - Primary": "⛽", 
                        "Fuel Tank Capacity (gallons)": "⛽", "Fuel Tank Capacity (liters)": "⛽"
                    }.get(field, "📋")
                    report += f"{emoji} {field}: {value}\n"
                report += "\n"
            
            # Dimensions & Weight
            if dimensions:
                report += "📏 **Dimensions & Weight:**\n"
                for field, value in dimensions.items():
                    emoji = "📏"
                    if "Weight" in field:
                        emoji = "⚖️"
                    report += f"{emoji} {field}: {value}\n"
                report += "\n"
            
            # Manufacturing Details
            if manufacturing:
                report += "🏭 **Manufacturing Details:**\n"
                for field, value in manufacturing.items():
                    emoji = {
                        "Manufacturer Name": "🏢", "Plant Country": "🌍", "Plant State": "🌍",
                        "Body Class": "🚘", "Vehicle Type": "🚙"
                    }.get(field, "📋")
                    report += f"{emoji} {field}: {value}\n"
        else:
            report += "⚠️ Limited data available for this VIN"
        
        report += f"\n🔒 **Data provided by NHTSA Official Database**"
        return report
        
    except Exception as e:
        logger.error(f"Error generating report for VIN {vin}: {str(e)}")
        return "❌ Error generating report. Please try again later."

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "get_random_vin":
        processing_msg = await query.message.reply_text("🔄 Generating random VIN... Please wait.")
        reply = await random_vin_logic()
        await processing_msg.delete()
        
        keyboard = [
            [InlineKeyboardButton("🔄 Get Another VIN", callback_data="get_random_vin")],
            [InlineKeyboardButton("🔍 Search Manually", callback_data="search_manual"), 
             InlineKeyboardButton("📊 Clear Cache", callback_data="clear_cache")],
            [InlineKeyboardButton("❌ End Search", callback_data="end_search")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(reply, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif query.data == "search_manual":
        await query.message.reply_text("✍️ **Please enter a VIN manually**\n\nSend me any 17-character VIN to analyze:", parse_mode='Markdown')
    
    elif query.data == "end_search":
        await query.message.reply_text("👋 **Session ended successfully!**\n\nType /start to begin a new VIN analysis session.", parse_mode='Markdown')
        return ConversationHandler.END
    
    elif query.data == "help":
        await show_help(update, context, is_callback=True)
    
    elif query.data == "about_vin":
        await show_about_vin(query)
    
    elif query.data.startswith("report_"):
        vin = query.data.replace("report_", "")
        processing_msg = await query.message.reply_text("📊 Generating comprehensive report... Please wait.")
        report = await generate_vin_report(vin)
        await processing_msg.delete()
        await query.message.reply_text(report, parse_mode='Markdown')
    
    elif query.data == "clear_cache":
        global shown_vins
        cache_size = len(shown_vins)
        shown_vins.clear()
        await query.message.reply_text(
            f"🗑️ **Cache Cleared Successfully!**\n\n"
            f"Removed {cache_size} previously shown VINs from memory.\n"
            f"You can now get those VINs again with 'Get Random VIN'.",
            parse_mode='Markdown'
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_help(update, context)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors gracefully"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ **An unexpected error occurred**\n\n"
            "Please try again or use /start to restart the bot.",
            parse_mode='Markdown'
        )

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

    # Add handlers
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("randomvin", random_vin))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Add error handler
    app.add_error_handler(error_handler)

    print("✅ Professional VIN Decoder Bot is running...")
    print("📊 Features: Advanced validation, detailed reports, comprehensive analysis")
    print("🔒 Data source: NHTSA Official Database")
    
    # Clear any pending updates to avoid conflicts
    app.run_polling(drop_pending_updates=True)