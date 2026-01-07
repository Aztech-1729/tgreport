<div align="center">

# 🚀 Telegram Mass Reporting Bot

<img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python">
<img src="https://img.shields.io/badge/Telethon-1.34+-green.svg" alt="Telethon">
<img src="https://img.shields.io/badge/MongoDB-6.0+-success.svg" alt="MongoDB">
<img src="https://img.shields.io/badge/License-Educational-red.svg" alt="License">

**A powerful, automated Telegram reporting system with multi-account support and advanced features**

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Commands](#-commands) • [Documentation](#-documentation)

---

### ⚠️ **DISCLAIMER**

**This bot is for educational and research purposes only.** Coordinated mass reporting may violate Telegram's Terms of Service. By using this software, you acknowledge that:
- You are solely responsible for any consequences
- The developers assume no liability for misuse
- Always comply with applicable laws and platform policies

---

</div>

## ✨ Features

<table>
<tr>
<td width="50%">

### 🎯 **Core Functionality**
- ⚠️ **Post Reporting** - Target specific messages
- 📢 **Channel Reporting** - Report entire channels
- 👤 **User Reporting** - Report user profiles
- 🔄 **Unlimited Cycles** - No cycle restrictions
- 🤖 **Automated Process** - Set it and forget it

</td>
<td width="50%">

### 💼 **Management**
- 👥 **Multi-Admin System** - Role-based access
- 📱 **Account Management** - Manage multiple Telegram accounts
- 🔐 **Auto OTP/2FA** - Seamless authentication
- 📊 **Live Progress** - Real-time status updates
- 📄 **JSON Export** - Detailed audit logs

</td>
</tr>
<tr>
<td width="50%">

### 🎨 **User Interface**
- 🖱️ **Inline Buttons** - Interactive menu system
- 🔙 **Easy Navigation** - Back buttons everywhere
- 📈 **Live Updates** - Status updates every 1.5s
- 🎯 **One Message** - Clean, non-spammy interface

</td>
<td width="50%">

### 🛡️ **Security & Reliability**
- 🔒 **Secure Sessions** - Encrypted storage
- ⚡ **Efficient** - One connection per account
- 📝 **Comprehensive Logging** - Full audit trail
- 🎛️ **Configurable** - Customizable settings

</td>
</tr>
</table>

## 📋 Prerequisites

<details>
<summary><b>🐍 Python 3.8 or Higher</b></summary>

```bash
# Check your Python version
python --version

# Should output: Python 3.8.x or higher
```
</details>

<details>
<summary><b>🍃 MongoDB Database</b></summary>

**Option A: Local Installation**
- Windows: https://www.mongodb.com/try/download/community
- Linux: `sudo apt-get install mongodb`
- Mac: `brew install mongodb-community`

**Option B: MongoDB Atlas (Free Cloud)**
- Sign up at https://www.mongodb.com/cloud/atlas
- Create a free cluster
- Get your connection string
</details>

<details>
<summary><b>🤖 Telegram Bot Token</b></summary>

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow the instructions
3. Copy your bot token (format: `1234567890:ABCdefGHIjklMNO...`)
</details>

<details>
<summary><b>🔑 Telegram API Credentials</b></summary>

1. Visit https://my.telegram.org/apps
2. Login with your phone number
3. Create a new application
4. Copy your **API ID** (number) and **API Hash** (string)
</details>

## 🚀 Installation

### **Step 1: Clone the Repository**

```bash
git clone <repository-url>
cd "TG REPORT"
```

### **Step 2: Install Dependencies**

```bash
pip install -r requirements.txt
```

**Dependencies installed:**
- `telethon` - Telegram client library
- `motor` - Async MongoDB driver
- `pymongo` - MongoDB Python driver

### **Step 3: Configure the Bot**

Edit `config.py` with your credentials:

```python
# ===== TELEGRAM BOT CONFIGURATION =====
MAIN_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # From @BotFather

# ===== TELEGRAM API CREDENTIALS =====
API_ID = 12345678  # From my.telegram.org
API_HASH = "YOUR_API_HASH_HERE"  # From my.telegram.org

# ===== SUPER ADMIN =====
SUPER_ADMIN_ID = 987654321  # Your user ID from @userinfobot

# ===== MONGODB CONFIGURATION =====
MONGO_URI = "mongodb://localhost:27017"  # Or your MongoDB Atlas URI
DB_NAME = "telegram_report_bot"

# ===== BOT SETTINGS =====
REPORT_DELAY = 2  # Seconds between reports
ENABLE_LOGGING = True
```

<details>
<summary><b>📖 How to Get Each Credential</b></summary>

| Credential | How to Get | Example |
|------------|-----------|---------|
| **Bot Token** | @BotFather → `/newbot` | `1234567890:ABC...` |
| **API ID** | https://my.telegram.org/apps | `12345678` |
| **API Hash** | https://my.telegram.org/apps | `abc123def456...` |
| **User ID** | @userinfobot → `/start` | `987654321` |
| **Mongo URI** | Local or Atlas dashboard | `mongodb://...` |

</details>

## 🎮 Usage

### **Step 1: Start the Bot**

```bash
python bot.py
```

**Expected Output:**
```log
INFO - Starting Telegram Mass Reporting Bot...
INFO - Bot client connected successfully
INFO - Bot is running and ready to receive commands...
INFO - Super Admin ID: 6670166083
```

<details>
<summary><b>🔧 Troubleshooting Startup Issues</b></summary>

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| `Connection Error` | Check MongoDB is running |
| `Invalid Token` | Verify bot token in config.py |
| `API ID Error` | Check API credentials |

</details>

---

### **Step 2: Open Your Bot in Telegram**

1. Search for your bot (name given to @BotFather)
2. Send `/start`
3. You'll see the interactive menu:

```
🔒 Admin Mass Reporting Bot

👤 Your ID: 6670166083
📱 Active Accounts: 0

Choose an option below:
[⚠️ Report Post] [📢 Report Channel]
[➕ Add Account] [📱 My Accounts]
[👥 Admin Panel] [ℹ️ Help]
```

---

### **Step 3: Add Reporting Accounts**

#### **Quick Method:**

1. Click **"➕ Add Account"** or send `/add +1234567890`
2. Bot sends OTP to your phone
3. Just reply with the **5-digit code** (no command needed!)
4. If 2FA enabled, reply with your **password**
5. Done! ✅

#### **Detailed Process:**

```bash
# Send command
/add +1234567890 MyAccount

# Bot responds
📲 OTP Sent to +1234567890
Just send the OTP code (5 digits) directly.

# You send
12345

# If 2FA enabled
🔐 2FA Password Required
Just send your 2FA password directly.

# You send
MyPassword123

# Success!
✅ Account Added Successfully!
Session ID: 507f1f77bcf86cd799439011
Account Name: MyAccount
Username: @johndoe
Phone: +1234567890
```

---

### **Step 4: Start Reporting**

<table>
<tr>
<td width="33%">

#### 📝 **Report Post**
```bash
/post https://t.me/channel/123
```
or
```bash
/post https://t.me/channel/123 50
```
*Reports specific message 50 times*

</td>
<td width="33%">

#### 📢 **Report Channel**
```bash
/channel https://t.me/SomeChannel
```
or
```bash
/channel https://t.me/SomeChannel 100
```
*Reports entire channel 100 times*

</td>
<td width="33%">

#### 👤 **Report User**
```bash
/user username
```
or
```bash
/user username 200
```
*Reports user profile 200 times*

</td>
</tr>
</table>

---

### **Step 5: Choose Report Reason**

After sending a report command, select a reason:

```
⚠️ Confirm Mass Report

Target: @channel
Active Accounts: 28
Cycles: 50
Total Reports: 1,400

Choose a report reason:
[🚫 Spam] [⚔️ Violence]
[💰 Fraud] [❗ Other]
[❌ Cancel]
```

---

### **Step 6: Watch Live Progress**

The bot shows real-time updates:

```
🔄 Report Started

👥 Total Accounts: 28
✅ Success: 456
❌ Failed: 2
📈 Success Rate: 99.6%
🔢 Total Cycles: 50
```

Updates every **1.5 seconds** in the same message!

---

### **Step 7: Get Detailed Report**

After completion, you receive:

1. **Final Status:**
```
✅ Report Complete

👥 Total Accounts: 28
✅ Success: 1,398
❌ Failed: 2
📈 Success Rate: 99.9%
🔢 Total Cycles: 50
```

2. **JSON File:**
- Complete audit trail
- All API requests logged
- Account-wise breakdown
- Error details
- Timestamps

## 📝 Commands

<details open>
<summary><h3>👤 User Commands</h3></summary>

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Show main menu | `/start` |
| `/help` | Show detailed help | `/help` |
| `/add <phone>` | Add Telegram account | `/add +1234567890` |
| `/my_sessions` | View your accounts | `/my_sessions` |
| `/remove_session <id>` | Remove an account | `/remove_session 507f1f...` |
| `/cancel` | Cancel pending login | `/cancel` |

</details>

<details open>
<summary><h3>⚠️ Reporting Commands</h3></summary>

| Command | Description | Example |
|---------|-------------|---------|
| `/post <link> [cycles]` | Report a post | `/post https://t.me/channel/123 50` |
| `/channel <link> [cycles]` | Report a channel | `/channel https://t.me/SomeChannel 100` |
| `/user <username> [cycles]` | Report a user | `/user johndoe 200` |

**Cycles:**
- Default: `1`
- Range: `1` to `unlimited`
- Total Reports: `accounts × cycles`

</details>

<details>
<summary><h3>👥 Admin Commands (Super Admin Only)</h3></summary>

| Command | Description | Example |
|---------|-------------|---------|
| `/add_admin <user_id>` | Add new admin | `/add_admin 987654321` |
| `/remove_admin <user_id>` | Remove admin | `/remove_admin 987654321` |
| `/list_admins` | List all admins | `/list_admins` |

</details>

<details>
<summary><h3>🖱️ Interactive Menu Buttons</h3></summary>

**Main Menu:**
- 🎯 **Report Post** - Instructions for post reporting
- 📢 **Report Channel** - Instructions for channel reporting  
- ➕ **Add Account** - Guide to add accounts
- 📱 **My Accounts** - View account list
- 👥 **Admin Panel** - Admin controls (super admin only)
- ℹ️ **Help** - Detailed help guide

**Report Reasons:**
- 🚫 **Spam** - Unwanted promotional content
- ⚔️ **Violence** - Violent or graphic content
- 💰 **Fraud** - Scams or fraudulent content
- ❗ **Other** - General policy violations

</details>

## 🛡️ Security & Best Practices

<details>
<summary><h3>🔒 Security Considerations</h3></summary>

| Aspect | Best Practice | Why |
|--------|---------------|-----|
| **Bot Token** | Never commit to Git | Full bot control |
| **API Credentials** | Keep in config.py only | Account access |
| **Session Strings** | Auto-deleted messages | Full account control |
| **MongoDB** | Use authentication | Data protection |
| **Private Use** | Bot in private chats only | Prevent exposure |
| **Token Rotation** | Change periodically | Limit compromise |

**🔐 What's Already Secure:**
- ✅ Automatic deletion of credential messages
- ✅ Session strings encrypted in MongoDB
- ✅ No credentials in logs
- ✅ Admin-only access control
- ✅ Secure Telegram API usage

</details>

<details>
<summary><h3>⚡ Performance Optimization</h3></summary>

**Current Optimizations:**
1. **Single Connection** - One connection per account (not per cycle)
2. **Async Operations** - Non-blocking concurrent reports
3. **Smart Updates** - Status updates every 1.5s (not per report)
4. **Efficient Queries** - Indexed MongoDB lookups
5. **Memory Management** - Cleanup after each report

**Recommended Settings:**

| Scenario | Accounts | Cycles | Delay | Est. Time |
|----------|----------|--------|-------|-----------|
| **Quick Test** | 5 | 10 | 2s | ~2 min |
| **Standard** | 28 | 50 | 2s | ~50 min |
| **Heavy** | 28 | 500 | 2s | ~8 hours |
| **Massive** | 28 | 5000 | 2s | ~3 days |

</details>

<details>
<summary><h3>🎯 Rate Limiting & Safety</h3></summary>

**Telegram Rate Limits:**
- **Per Account:** ~30 reports/minute (soft limit)
- **Flood Wait:** Temporary ban if exceeded
- **Detection:** Telegram monitors reporting patterns

**Bot Safety Features:**
- 2-second delay between reports (configurable)
- One connection per account (reduces suspicion)
- Randomized report messages (from config)
- Account health monitoring
- Automatic retry on temporary failures

**⚠️ Warning Signs:**
- Multiple "Flood wait" errors
- Accounts getting restricted
- Reports not going through
- Session expiration

**💡 Solutions:**
- Increase `REPORT_DELAY` in config
- Use fewer accounts per batch
- Space out large report campaigns
- Use aged, active accounts

</details>

## 🗄️ Database Structure

<details>
<summary><h3>📊 MongoDB Collections</h3></summary>

#### **Collection: `authorized_users`**
```json
{
  "_id": ObjectId,
  "user_id": 6670166083,
  "added_by": 6670166083,
  "added_at": "2026-01-07T05:00:00",
  "is_active": true,
  "role": "super_admin"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | Integer | Telegram user ID |
| `added_by` | Integer | Who added this user |
| `added_at` | DateTime | Timestamp |
| `is_active` | Boolean | Active status |
| `role` | String | User role (optional) |

---

#### **Collection: `user_sessions`**
```json
{
  "_id": ObjectId,
  "user_id": 6670166083,
  "api_id": 33428535,
  "api_hash": "c0dbd6f2553e9ed7...",
  "session_string": "AgAAABCdGhI8c9E...",
  "account_name": "MyAccount",
  "account_username": "johndoe",
  "account_phone": "+1234567890",
  "added_at": "2026-01-07T05:00:00",
  "is_active": true
}
```

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | Integer | Owner of session |
| `api_id` | Integer | Telegram API ID |
| `api_hash` | String | Telegram API hash |
| `session_string` | String | Encrypted session |
| `account_name` | String | Friendly name |
| `account_username` | String | Telegram username |
| `account_phone` | String | Phone number |
| `added_at` | DateTime | Timestamp |
| `is_active` | Boolean | Active status |

---

#### **Indexes (Recommended)**

For better performance, create these indexes:

```javascript
// MongoDB Shell
db.authorized_users.createIndex({ "user_id": 1, "is_active": 1 })
db.user_sessions.createIndex({ "user_id": 1, "is_active": 1 })
db.user_sessions.createIndex({ "account_phone": 1 })
```

</details>

## 🔧 Troubleshooting

<details>
<summary><h3>❌ Common Issues & Solutions</h3></summary>

### **Bot Doesn't Start**

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'telethon'` | Run `pip install -r requirements.txt` |
| `Invalid bot token` | Check `MAIN_BOT_TOKEN` in config.py |
| `Connection refused (MongoDB)` | Start MongoDB service |
| `API ID/Hash error` | Verify credentials at my.telegram.org |

---

### **Bot Doesn't Respond**

| Problem | Solution |
|---------|----------|
| No response to `/start` | Check bot is running: `python bot.py` |
| "Access Denied" message | Your user ID not in config.py |
| Commands not working | Restart bot after config changes |
| Inline buttons not showing | Update Telethon: `pip install -U telethon` |

---

### **Account Addition Issues**

| Problem | Solution |
|---------|----------|
| "Session not authorized" | Session expired - generate new one |
| OTP not received | Check phone number format: `+1234567890` |
| 2FA password rejected | Verify password is correct |
| "Invalid API credentials" | Ensure API ID/Hash match from my.telegram.org |

---

### **Reporting Errors**

| Problem | Solution |
|---------|----------|
| "Flood wait" error | Increase `REPORT_DELAY` in config.py |
| "No active accounts" | Add accounts with `/add` command |
| Reports failing | Check account sessions are valid |
| "Rate limit exceeded" | Reduce cycles or use fewer accounts |
| "Channel not found" | Verify channel link is correct |

---

### **Performance Issues**

| Problem | Solution |
|---------|----------|
| Bot running slow | Check MongoDB connection speed |
| High memory usage | Reduce concurrent accounts |
| Status not updating | Check network connection |
| Bot freezing | Restart with fewer active sessions |

</details>

<details>
<summary><h3>📋 Logs & Debugging</h3></summary>

**Check Logs:**
```bash
# View real-time logs
tail -f bot.log

# Search for errors
grep "ERROR" bot.log

# View last 50 lines
tail -n 50 bot.log
```

**Enable Verbose Logging:**
```python
# In config.py
ENABLE_LOGGING = True
LOG_FILE = "bot.log"
```

**Common Log Messages:**

| Log Message | Meaning | Action |
|-------------|---------|--------|
| `Session not authorized` | Invalid session | Re-add account |
| `Flood wait` | Rate limited | Increase delay |
| `Connection timeout` | Network issue | Check internet |
| `MongoDB connection error` | DB offline | Start MongoDB |

</details>

## Logging

The bot creates a `bot.log` file with detailed logs. Check this file for debugging.

To disable logging to file, set in `config.py`:
```python
ENABLE_LOGGING = False
```

## Contributing

This is an educational project. If you find bugs or have suggestions, feel free to improve it.

## ⚖️ Legal & Ethical Use

<div align="center">

### ⚠️ **READ BEFORE USING**

</div>

<details open>
<summary><h3>📜 Terms & Conditions</h3></summary>

By using this software, you agree to:

✅ **DO:**
- Use for research and educational purposes
- Report genuine policy violations
- Respect Telegram's Terms of Service
- Take responsibility for your actions
- Comply with local laws and regulations

❌ **DON'T:**
- Use for harassment or bullying
- Abuse the reporting system
- Target individuals maliciously
- Violate others' rights
- Engage in coordinated attacks

</details>

<details>
<summary><h3>⚠️ Disclaimer</h3></summary>

**THIS SOFTWARE IS PROVIDED "AS IS"**

The developers and contributors of this project:
- Assume **NO LIABILITY** for misuse
- Do **NOT ENCOURAGE** violation of platform policies
- Provide this for **EDUCATIONAL PURPOSES ONLY**
- Are **NOT RESPONSIBLE** for consequences of use
- Do **NOT SUPPORT** malicious activities

**Telegram Terms of Service:**
- Mass reporting may result in account bans
- Coordinated abuse violates TOS
- Use at your own risk

</details>

<details>
<summary><h3>🎯 Intended Use Cases</h3></summary>

**Legitimate Uses:**
- Research on reporting systems
- Educational demonstrations
- Testing platform moderation
- Understanding API functionality
- Security research

**NOT For:**
- Personal vendettas
- Censorship campaigns
- Competitive sabotage
- Harassment operations
- Market manipulation

</details>

---

## 📞 Support & Community

<div align="center">

### Need Help?

</div>

**Before Asking for Help:**
1. ✅ Read the [Troubleshooting](#-troubleshooting) section
2. ✅ Check `bot.log` for error messages
3. ✅ Verify all credentials in `config.py`
4. ✅ Ensure MongoDB is running
5. ✅ Try the [Quick Start Guide](QUICKSTART.md)

---

## 📚 Additional Resources

- 📖 **[Quick Start Guide](QUICKSTART.md)** - Get running in 5 minutes
- 🔧 **[Configuration Guide](config.py)** - All settings explained
- 📊 **[Requirements](requirements.txt)** - Dependencies list
- 🐛 **[Troubleshooting](#-troubleshooting)** - Common issues

---

## 🤝 Contributing

This is an educational project. While we don't actively seek contributions, if you find bugs or have improvements:

1. Test thoroughly
2. Document changes
3. Follow existing code style
4. Consider ethical implications

---

## 📄 License

```
MIT License - Educational Use Only

This software is provided for educational and research purposes.
Users are solely responsible for compliance with applicable laws
and platform terms of service.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
```

---

<div align="center">

### 🌟 Star this repo if you found it helpful!

**Made with ❤️ for educational purposes**

⚠️ **Use Responsibly** | 🔒 **Stay Secure** | 📚 **Keep Learning**

---

**© 2026 | Educational Use Only | No Warranty**

</div>
