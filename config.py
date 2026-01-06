# Configuration File for Telegram Mass Reporting Bot
# Fill in your credentials below

# ===== TELEGRAM BOT CONFIGURATION =====
# Get your bot token from @BotFather on Telegram
MAIN_BOT_TOKEN = "8571232771:AAEXzWlA86e1qZkLtdKPLECxjGHUjnreGq8"

# Get API_ID and API_HASH from https://my.telegram.org/apps
API_ID = 33428535  # Replace with your API ID (integer)
API_HASH = "c0dbd6f2553e9ed7ab51db2c6cd3360e"  # Replace with your API hash (string)

# ===== SUPER ADMIN CONFIGURATION =====
# Your Telegram User ID - Get it from @userinfobot
SUPER_ADMIN_ID = 6670166083  # Replace with your Telegram user ID

# ===== MONGODB CONFIGURATION =====
# MongoDB connection string
# Local: "mongodb://localhost:27017"
# Atlas: "mongodb+srv://username:password@cluster.mongodb.net/"
MONGO_URI = "mongodb+srv://aztech:ayazahmed1122@cluster0.mhuaw3q.mongodb.net/tgreport_db?retryWrites=true&w=majority"

# Database name
DB_NAME = "tgreport_db"

# Collection names (you can keep these as default)
AUTHORIZED_USERS_COLLECTION = "authorized_users"
USER_SESSIONS_COLLECTION = "user_sessions"

# ===== BOT SETTINGS =====
# Delay between reports (in seconds) to avoid rate limiting
REPORT_DELAY = 2

# Enable logging
ENABLE_LOGGING = True
LOG_FILE = "bot.log"

# Session file name for the main bot
BOT_SESSION_NAME = "main_bot_session"

# ===== REPORT MESSAGES CONFIGURATION =====
# Customize the report messages for each reason
REPORT_MESSAGES = {
    "spam": {
        "title": "Spam Report",
        "message": "This content is spam. It contains unsolicited advertisements, fake engagement schemes, or repetitive content that violates Telegram's Terms of Service. This is clearly promotional spam that disrupts the platform."
    },
    "violence": {
        "title": "Violence Report",
        "message": "This content promotes violence or contains graphic violent material. It violates Telegram's community guidelines by depicting or encouraging harmful acts, threats, or dangerous behavior that could cause harm to individuals or groups."
    },
    "fraud": {
        "title": "Fraud/Scam Report",
        "message": "This content is fraudulent and attempts to scam users. It contains deceptive practices, fake offers, phishing attempts, or financial fraud schemes designed to steal money or personal information from unsuspecting victims."
    },
    "other": {
        "title": "Policy Violation Report",
        "message": "This content violates Telegram's Terms of Service and community guidelines. It contains inappropriate material, misinformation, or other policy violations that make the platform unsafe or unpleasant for users."
    }
}
