# Telegram Mass Reporting Bot

A Telegram bot that allows authorized users to perform mass reporting of posts using multiple accounts.

## ⚠️ Disclaimer

This bot is for educational purposes only. Mass reporting and coordinated reporting may violate Telegram's Terms of Service. Use at your own risk.

## Features

- 👥 Multi-user authorization system
- 📱 Multiple account management per user
- ⚠️ Mass reporting with multiple accounts simultaneously
- 📊 Detailed reporting statistics
- 🔐 Secure credential handling
- 📝 Comprehensive logging
- 🎯 Multiple report reasons (Spam, Violence, Fraud, Other)

## Prerequisites

1. **Python 3.8+**
2. **MongoDB** (local or cloud instance)
3. **Telegram Bot Token** (from @BotFather)
4. **Telegram API credentials** (from https://my.telegram.org/apps)

## Installation

### 1. Clone or Download

Download this repository to your local machine.

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup MongoDB

**Option A: Local MongoDB**
- Install MongoDB on your system
- Start MongoDB service
- Use default URI: `mongodb://localhost:27017`

**Option B: MongoDB Atlas (Cloud)**
- Create a free account at https://www.mongodb.com/cloud/atlas
- Create a cluster
- Get your connection string
- Replace in `config.py`

### 4. Configure the Bot

Edit `config.py` and fill in your credentials:

```python
# Bot token from @BotFather
MAIN_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"

# API credentials from my.telegram.org
API_ID = 12345678
API_HASH = "abc123def456ghi789jkl012mno345pq"

# Your Telegram User ID (get from @userinfobot)
SUPER_ADMIN_ID = 987654321

# MongoDB connection
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "telegram_report_bot"
```

## Usage

### 1. Start the Bot

```bash
python bot.py
```

### 2. Initialize Super Admin

When you first run the bot, send `/start` to your bot on Telegram. If you're the super admin (configured in `config.py`), you'll have full access.

### 3. Add Accounts for Reporting

To use the mass reporting feature, you need to add Telegram accounts:

1. Go to https://my.telegram.org/apps
2. Create an app and note your API ID and API Hash
3. Use @StringSessionBot on Telegram to generate a session string
4. In your reporting bot, send `/add_account`
5. Follow the instructions and send:
   ```
   /provide_credentials <api_id> <api_hash> <session_string> [account_name]
   ```

### 4. Report a Post

```
/post https://t.me/channel/message_id
```

Select the report reason and confirm. All your added accounts will report the post.

## Commands

### Admin Management (Super Admin Only)
- `/add_admin <user_id>` - Add new authorized user
- `/remove_admin <user_id>` - Remove an authorized user
- `/list_admins` - List all authorized users

### Account Management
- `/add_account` - Get instructions to add account
- `/provide_credentials` - Add account with credentials
- `/my_sessions` - View your added accounts
- `/remove_session <session_id>` - Remove an account

### Reporting
- `/post <link>` - Start mass report on a post

### General
- `/start` - Show welcome message and commands
- `/help` - Show detailed help

## Security Notes

⚠️ **Important Security Considerations:**

1. **Never share your bot token or API credentials**
2. **Session strings are sensitive** - they give full access to accounts
3. **Use the bot in private chats only**
4. **The bot automatically deletes credential messages** for security
5. **Consider encrypting session strings in production**
6. **Keep your MongoDB database secure**
7. **Regularly rotate your bot token**

## Database Structure

### Collections

1. **authorized_users**
   - `user_id`: Telegram user ID
   - `added_by`: Who added this user
   - `added_at`: When added
   - `is_active`: Active status

2. **user_sessions**
   - `user_id`: Owner of this session
   - `api_id`: Telegram API ID
   - `api_hash`: Telegram API hash
   - `session_string`: Session string
   - `account_name`: Friendly name
   - `account_username`: Telegram username
   - `account_phone`: Phone number
   - `added_at`: When added
   - `is_active`: Active status

## Troubleshooting

### Bot doesn't respond
- Check if bot token is correct
- Ensure bot is running
- Check internet connection

### "Session not authorized" error
- Session string might be expired
- Generate a new session string
- Make sure API ID and Hash match the session

### MongoDB connection error
- Check if MongoDB is running
- Verify connection string in config.py
- Check firewall settings

### Rate limiting errors
- Telegram has rate limits
- Increase `REPORT_DELAY` in config.py
- Reduce number of accounts used simultaneously

## Logging

The bot creates a `bot.log` file with detailed logs. Check this file for debugging.

To disable logging to file, set in `config.py`:
```python
ENABLE_LOGGING = False
```

## Contributing

This is an educational project. If you find bugs or have suggestions, feel free to improve it.

## Legal & Ethics

⚠️ **This tool can be misused. Please use responsibly:**

- Don't use for harassment or bullying
- Don't abuse Telegram's reporting system
- Only report genuine violations
- Respect Telegram's Terms of Service
- Mass reporting may get your accounts banned

## License

This project is provided as-is for educational purposes. Use at your own risk.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the logs in `bot.log`
3. Ensure all credentials are correct
4. Check MongoDB connection

---

**Made for educational purposes only. Use responsibly.**
