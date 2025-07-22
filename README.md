# 🚗 Professional VIN Decoder Bot

A comprehensive Telegram bot that decodes Vehicle Identification Numbers (VINs) and provides detailed vehicle information using the official NHTSA database.

## ✨ Features

- **🔍 VIN Analysis**: Decode any 17-character VIN
- **🎲 Random VIN Generator**: Get sample VINs for testing
- **🔒 Real vs Fake Detection**: Smart algorithm to detect authentic vehicles
- **⛽ Fuel Capacity Information**: Always shows fuel tank capacity in gallons
- **📊 Comprehensive Reports**: Detailed technical specifications on request
- **🚫 Duplicate Prevention**: Never shows the same random VIN twice
- **💬 Professional Interface**: Clean, intuitive user experience
- **🔧 Error Handling**: Graceful handling of API failures and edge cases

## 🚀 Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/vin-checker-bot.git
   cd vin-checker-bot
   ```

2. **Set up environment**
   ```bash
   # Copy environment template
   cp .env.example .env
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Configure bot token**
   - Message [@BotFather](https://t.me/botfather) on Telegram
   - Create a new bot and get your token
   - Edit `.env` file and replace `your_telegram_bot_token_here` with your actual token

4. **Run the bot**
   ```bash
   python bot.py
   ```

### Deploy to Render

1. **Connect Repository**
   - Fork/clone this repository to your GitHub
   - Connect your GitHub account to [Render](https://render.com)
   - Create a new Web Service from your repository

2. **Configure Render Settings**
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   
3. **Set Environment Variables in Render Dashboard**
   - Go to your service → Environment
   - Add: `BOT_TOKEN` = `your_actual_bot_token_here`

4. **Deploy**
   - Click "Deploy Latest Commit"
   - Your bot will be live in minutes!

## 🔧 Bot Commands

- `/start` - Start the bot and see main menu
- `/randomvin` - Generate a random VIN for testing
- `/help` - Show detailed help information
- `/cancel` - End current session

## 🎯 How It Works

1. **VIN Validation**: Checks format and authenticity using NHTSA database
2. **Data Analysis**: Extracts vehicle specifications and technical details
3. **Smart Detection**: Determines if VIN corresponds to real manufactured vehicle
4. **Fuel Capacity**: Always provides fuel tank information (exact or estimated)
5. **Professional Reports**: Comprehensive technical specifications on demand

## 🔍 VIN Analysis Results

- **✅ REAL VIN**: Authentic vehicle found in official database
- **🔸 FAKE VIN**: Valid format but synthetic/test data
- **❌ INVALID VIN**: Format errors or database rejection

## 📊 Information Provided

### Basic Analysis
- Vehicle Make, Model, and Year
- Manufacturer details
- Fuel tank capacity (gallons)
- Country of origin
- Real vs fake detection

### Comprehensive Report
- Complete technical specifications
- Engine details (cylinders, displacement, power)
- Transmission and drivetrain information
- Body style and vehicle type
- Dimensions and weight data
- Manufacturing plant details
- Safety ratings and certifications

## 🛡️ Security & Privacy

- Environment variables for sensitive data
- No VIN data stored or logged
- Official NHTSA database only
- Secure deployment practices

## 📚 Tech Stack

- **Python 3.8+**
- **python-telegram-bot**: Telegram Bot API wrapper
- **NHTSA API**: Official vehicle database
- **Render**: Cloud deployment platform
- **GitHub**: Version control and CI/CD

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- Create an issue for bug reports or feature requests
- Check existing issues before creating new ones
- Provide detailed information for faster resolution

## 🔗 Links

- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [NHTSA VIN Decoder API](https://vpic.nhtsa.dot.gov/api/)
- [Render Deployment Guide](https://render.com/docs)

---

**Made with ❤️ for the automotive community**
