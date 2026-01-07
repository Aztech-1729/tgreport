from telethon import TelegramClient, events, Button
from telethon.tl.functions.messages import ReportRequest
from telethon.tl.types import InputReportReasonSpam, InputReportReasonViolence, InputReportReasonOther
from telethon.sessions import StringSession
import re
from datetime import datetime
import motor.motor_asyncio
import asyncio
import logging
import config

# --- Logging Configuration ---
if config.ENABLE_LOGGING:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config.LOG_FILE),
            logging.StreamHandler()
        ]
    )
else:
    logging.basicConfig(level=logging.WARNING)

# Suppress asyncio task warnings during shutdown
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)

# --- Database Connection ---
client_mongo = motor.motor_asyncio.AsyncIOMotorClient(config.MONGO_URI)
db = client_mongo[config.DB_NAME]
authorized_users_col = db[config.AUTHORIZED_USERS_COLLECTION]
user_sessions_col = db[config.USER_SESSIONS_COLLECTION]

# --- Main Bot Client (will be initialized in main()) ---
main_bot = TelegramClient(config.BOT_SESSION_NAME, config.API_ID, config.API_HASH)

# --- Helper: Check if user is authorized ---
async def is_user_authorized(user_id):
    user = await authorized_users_col.find_one({"user_id": user_id, "is_active": True})
    return user is not None

# --- Command: /start ---
@main_bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    user_id = event.sender_id
    logger.info(f"User {user_id} executed /start")
    
    if not await is_user_authorized(user_id):
        await event.reply("⛔ **Access Denied.**\nYou are not authorized to use this bot.")
        logger.warning(f"Unauthorized access attempt from user {user_id}")
        return
    
    # Get session count for the user
    session_count = await user_sessions_col.count_documents({"user_id": user_id, "is_active": True})
    
    welcome_msg = (
        "🔒 **Admin Mass Reporting Bot**\n\n"
        f"👤 **Your ID:** `{user_id}`\n"
        f"📱 **Active Accounts:** {session_count}\n\n"
        "**Choose an option below:**"
    )
    
    # Create inline keyboard
    is_super_admin = (user_id == config.SUPER_ADMIN_ID)
    
    buttons = [
        [Button.inline("⚠️ Report Post", "menu_report_post"),
         Button.inline("📢 Report Channel", "menu_report_channel")],
        [Button.inline("➕ Add Account", "menu_add_account"),
         Button.inline("📱 My Accounts", "menu_my_sessions")],
    ]
    
    if is_super_admin:
        buttons.append([
            Button.inline("👥 Admin Panel", "menu_admin_panel"),
            Button.inline("ℹ️ Help", "menu_help")
        ])
    else:
        buttons.append([Button.inline("ℹ️ Help", "menu_help")])
    
    await event.reply(welcome_msg, buttons=buttons)

# --- Command: /add_admin ---
@main_bot.on(events.NewMessage(pattern='/add_admin'))
async def add_admin_handler(event):
    user_id = event.sender_id
    
    if user_id != config.SUPER_ADMIN_ID:
        await event.reply("⛔ Only the super admin can add users.")
        logger.warning(f"User {user_id} attempted to add admin without permission")
        return

    args = event.message.text.split()
    if len(args) != 2:
        await event.reply("**Usage:** `/add_admin <telegram_user_id>`\n\n**Example:** `/add_admin 123456789`")
        return

    try:
        new_user_id = int(args[1])
        existing = await authorized_users_col.find_one({"user_id": new_user_id})
        if existing:
            if existing.get("is_active"):
                await event.reply("⚠️ This user is already an active admin.")
            else:
                # Reactivate the user
                await authorized_users_col.update_one(
                    {"user_id": new_user_id},
                    {"$set": {"is_active": True, "reactivated_at": datetime.utcnow()}}
                )
                await event.reply(f"✅ User `{new_user_id}` has been reactivated as an admin.")
                logger.info(f"User {new_user_id} reactivated by {user_id}")
        else:
            await authorized_users_col.insert_one({
                "user_id": new_user_id,
                "added_by": user_id,
                "added_at": datetime.utcnow(),
                "is_active": True
            })
            await event.reply(f"✅ User `{new_user_id}` added as an authorized admin.")
            logger.info(f"User {new_user_id} added as admin by {user_id}")
    except ValueError:
        await event.reply("❌ Invalid user ID. Must be a number.")
    except Exception as e:
        await event.reply(f"❌ Error adding admin: {str(e)}")
        logger.error(f"Error adding admin: {e}")

# --- Command: /list_admins ---
@main_bot.on(events.NewMessage(pattern='/list_admins'))
async def list_admins_handler(event):
    if not await is_user_authorized(event.sender_id):
        return

    admins_cursor = authorized_users_col.find({"is_active": True})
    admins = await admins_cursor.to_list(length=100)
    
    if not admins:
        await event.reply("❌ No authorized admins found.")
        return

    msg = "👥 **Authorized Admins:**\n\n"
    for idx, admin in enumerate(admins, 1):
        added_at = admin.get('added_at', 'Unknown')
        if isinstance(added_at, datetime):
            added_at = added_at.strftime('%Y-%m-%d %H:%M')
        msg += f"{idx}. User ID: `{admin['user_id']}`\n   Added: {added_at}\n"
    
    await event.reply(msg)
    logger.info(f"User {event.sender_id} listed {len(admins)} admins")


# --- Helper: Parse Telegram Post Link ---
def parse_post_link(link):
    """Extract channel username and message ID from a Telegram post link.
       Supports formats like: https://t.me/aztechshub/144 or t.me/aztechshub/144
    """
    pattern = r"(?:https?://)?t\.me/([a-zA-Z0-9_]+)/(\d+)"
    match = re.search(pattern, link)
    if match:
        return match.group(1), int(match.group(2))  # channel_username, message_id
    return None, None

# --- Command: /post <link> [cycles] ---
@main_bot.on(events.NewMessage(pattern='/post'))
async def post_report_handler(event):
    user_id = event.sender_id
    
    if not await is_user_authorized(user_id):
        return

    args = event.message.text.split()
    if len(args) < 2:
        await event.reply(
            "**Usage:** `/post https://t.me/channel/123 [cycles]`\n\n"
            "**Examples:**\n"
            "`/post https://t.me/aztechshub/144` - Report once\n"
            "`/post https://t.me/aztechshub/144 50` - Report 50 times"
        )
        return

    post_link = args[1].strip()
    cycles = 1
    
    # Check if cycles specified
    if len(args) >= 3:
        try:
            cycles = int(args[2])
            if cycles < 1:
                await event.reply("❌ Cycles must be at least 1.")
                return
        except ValueError:
            await event.reply("❌ Cycles must be a number.")
            return
    
    channel_username, message_id = parse_post_link(post_link)

    if not channel_username or not message_id:
        await event.reply("❌ Invalid Telegram post link format.\n\nSupported format: `https://t.me/channel/message_id`")
        return
    
    # Check if user has any sessions
    session_count = await user_sessions_col.count_documents({"user_id": user_id, "is_active": True})
    if session_count == 0:
        await event.reply("❌ You don't have any active accounts added.\n\nUse `/add_account` to add accounts first.")
        return

    # Step 1: Confirm the action
    confirm_msg = (
        f"⚠️ **Confirm Mass Report**\n\n"
        f"**Target:** `{channel_username}`\n"
        f"**Post ID:** `{message_id}`\n"
        f"**Link:** {post_link}\n"
        f"**Active Accounts:** {session_count}\n"
        f"**Cycles:** {cycles}\n"
        f"**Total Reports:** {session_count * cycles}\n\n"
        f"**This will trigger reports from all your authorized accounts.**\n"
        f"Choose a report reason:"
    )

    # Create inline buttons for report reasons
    buttons = [
        [Button.inline("🚫 Spam", f"reason_spam:{channel_username}:{message_id}:{cycles}"),
         Button.inline("⚔️ Violence", f"reason_violence:{channel_username}:{message_id}:{cycles}")],
        [Button.inline("💰 Fraud", f"reason_fraud:{channel_username}:{message_id}:{cycles}"),
         Button.inline("❗ Other", f"reason_other:{channel_username}:{message_id}:{cycles}")],
        [Button.inline("❌ Cancel", "cancel_report")]
    ]

    await event.reply(confirm_msg, buttons=buttons)
    logger.info(f"User {user_id} initiated report for {channel_username}/{message_id} with {cycles} cycles")

# --- Command: /user <username> [cycles] ---
@main_bot.on(events.NewMessage(pattern='/user'))
async def user_report_handler(event):
    user_id = event.sender_id
    
    if not await is_user_authorized(user_id):
        return

    args = event.message.text.split()
    if len(args) < 2:
        await event.reply(
            "**Usage:** `/user <username> [cycles]`\n\n"
            "**Examples:**\n"
            "`/user johndoe` - Report user once\n"
            "`/user johndoe 50` - Report user 50 times\n\n"
            "Note: Username without @"
        )
        return

    username = args[1].strip().lstrip('@')  # Remove @ if user adds it
    cycles = 1
    
    # Check if cycles specified
    if len(args) >= 3:
        try:
            cycles = int(args[2])
            if cycles < 1:
                await event.reply("❌ Cycles must be at least 1.")
                return
        except ValueError:
            await event.reply("❌ Cycles must be a number.")
            return
    
    # Check if user has any sessions
    session_count = await user_sessions_col.count_documents({"user_id": user_id, "is_active": True})
    if session_count == 0:
        await event.reply("❌ You don't have any active accounts added.\n\nUse `/add` to add accounts first.")
        return

    # Step 1: Confirm the action
    confirm_msg = (
        f"⚠️ **Confirm User Report**\n\n"
        f"**Target User:** `@{username}`\n"
        f"**Active Accounts:** {session_count}\n"
        f"**Cycles:** {cycles}\n"
        f"**Total Reports:** {session_count * cycles}\n\n"
        f"**This will report this user from all your authorized accounts.**\n"
        f"Choose a report reason:"
    )

    # Create inline buttons for report reasons
    buttons = [
        [Button.inline("🚫 Spam", f"reason_user_spam:{username}:{cycles}"),
         Button.inline("⚔️ Violence", f"reason_user_violence:{username}:{cycles}")],
        [Button.inline("💰 Fraud", f"reason_user_fraud:{username}:{cycles}"),
         Button.inline("❗ Other", f"reason_user_other:{username}:{cycles}")],
        [Button.inline("❌ Cancel", "cancel_report")]
    ]

    await event.reply(confirm_msg, buttons=buttons)
    logger.info(f"User {user_id} initiated user report for @{username} with {cycles} cycles")

# --- Command: /channel <link> [cycles] ---
@main_bot.on(events.NewMessage(pattern='/channel'))
async def channel_report_handler(event):
    user_id = event.sender_id
    
    if not await is_user_authorized(user_id):
        return

    args = event.message.text.split()
    if len(args) < 2:
        await event.reply(
            "**Usage:** `/channel https://t.me/ChannelUsername [cycles]`\n\n"
            "**Examples:**\n"
            "`/channel https://t.me/DreamAccountSup` - Report once\n"
            "`/channel https://t.me/DreamAccountSup 50` - Report 50 times\n\n"
            "This will report the entire channel/user."
        )
        return

    channel_link = args[1].strip()
    cycles = 1
    
    # Check if cycles specified
    if len(args) >= 3:
        try:
            cycles = int(args[2])
            if cycles < 1:
                await event.reply("❌ Cycles must be at least 1.")
                return
        except ValueError:
            await event.reply("❌ Cycles must be a number.")
            return
    
    # Extract channel username from link
    pattern = r"(?:https?://)?t\.me/([a-zA-Z0-9_]+)"
    match = re.search(pattern, channel_link)
    
    if not match:
        await event.reply("❌ Invalid Telegram channel link format.\n\nSupported format: `https://t.me/ChannelUsername`")
        return
    
    channel_username = match.group(1)
    
    # Check if user has any sessions
    session_count = await user_sessions_col.count_documents({"user_id": user_id, "is_active": True})
    if session_count == 0:
        await event.reply("❌ You don't have any active accounts added.\n\nUse `/add` to add accounts first.")
        return

    # Step 1: Confirm the action
    confirm_msg = (
        f"⚠️ **Confirm Channel/User Report**\n\n"
        f"**Target:** `@{channel_username}`\n"
        f"**Link:** {channel_link}\n"
        f"**Active Accounts:** {session_count}\n"
        f"**Cycles:** {cycles}\n"
        f"**Total Reports:** {session_count * cycles}\n\n"
        f"**This will report the entire channel/user from all your accounts.**\n"
        f"Choose a report reason:"
    )

    # Create inline buttons for report reasons (use special format for channel reports)
    buttons = [
        [Button.inline("🚫 Spam", f"channelreason_spam:{channel_username}:0:{cycles}"),
         Button.inline("⚔️ Violence", f"channelreason_violence:{channel_username}:0:{cycles}")],
        [Button.inline("💰 Fraud", f"channelreason_fraud:{channel_username}:0:{cycles}"),
         Button.inline("❗ Other", f"channelreason_other:{channel_username}:0:{cycles}")],
        [Button.inline("❌ Cancel", "cancel_report")]
    ]

    await event.reply(confirm_msg, buttons=buttons)
    logger.info(f"User {user_id} initiated channel report for {channel_username} with {cycles} cycles")

# --- Callback Handler for Menu and Report Reason Selection ---
@main_bot.on(events.CallbackQuery)
async def callback_handler(event):
    user_id = event.sender_id
    
    if not await is_user_authorized(user_id):
        await event.answer("Access denied.", alert=True)
        return

    data = event.data.decode('utf-8')
    logger.info(f"Callback received from user {user_id}: {data}")
    
    # Handle menu navigation
    if data == "menu_report_post":
        await event.edit(
            "⚠️ **Report a Post**\n\n"
            "Send me the Telegram post link with optional cycles:\n\n"
            "**Format:**\n"
            "`/post https://t.me/channel/123 [cycles]`\n\n"
            "**Examples:**\n"
            "`/post https://t.me/aztechshub/144`\n"
            "`/post https://t.me/aztechshub/144 50`",
            buttons=[[Button.inline("🔙 Back to Menu", "back_to_menu")]]
        )
        return
    
    if data == "menu_report_channel":
        await event.edit(
            "📢 **Report a Channel**\n\n"
            "Send me the Telegram channel/user link with optional cycles:\n\n"
            "**Format:**\n"
            "`/channel https://t.me/ChannelName [cycles]`\n\n"
            "**Examples:**\n"
            "`/channel https://t.me/DreamAccountSup`\n"
            "`/channel https://t.me/DreamAccountSup 50`",
            buttons=[[Button.inline("🔙 Back to Menu", "back_to_menu")]]
        )
        return
    
    if data == "menu_add_account":
        await event.edit(
            "➕ **Add Telegram Account**\n\n"
            "To add an account for reporting:\n\n"
            "**Format:**\n"
            "`/add <phone_number> [account_name]`\n\n"
            "**Examples:**\n"
            "`/add +1234567890`\n"
            "`/add +1234567890 MyAccount`\n\n"
            "The bot will send an OTP to your number.\n"
            "Just reply with the code directly (no command needed).",
            buttons=[[Button.inline("🔙 Back to Menu", "back_to_menu")]]
        )
        return
    
    if data == "menu_my_sessions":
        sessions_cursor = user_sessions_col.find({"user_id": user_id})
        sessions = await sessions_cursor.to_list(length=100)
        
        if not sessions:
            await event.edit(
                "📱 **No Accounts Found**\n\n"
                "You haven't added any accounts yet.\n"
                "Click 'Add Account' to add your first account.",
                buttons=[[Button.inline("🔙 Back to Menu", "back_to_menu")]]
            )
            return
        
        msg = "📱 **Your Telegram Accounts:**\n\n"
        
        for idx, session in enumerate(sessions[:10], 1):  # Show first 10
            session_id = str(session['_id'])
            account_name = session.get('account_name', 'Unknown')
            username = session.get('account_username', 'N/A')
            phone_last4 = session.get('account_phone', '')[-4:] if session.get('account_phone') else '****'
            status = "✅" if session.get('is_active', True) else "❌"
            
            msg += f"{idx}. {status} ****{phone_last4} - @{username}\n"
        
        msg += f"\n**Total:** {len(sessions)} accounts\n"
        msg += f"**Active:** {sum(1 for s in sessions if s.get('is_active', True))}\n"
        
        buttons = [[Button.inline("🔙 Back to Menu", "back_to_menu")]]
        
        await event.edit(msg, buttons=buttons)
        return
    
    if data == "menu_admin_panel":
        if user_id != config.SUPER_ADMIN_ID:
            await event.answer("⛔ Admin only", alert=True)
            return
        
        await event.edit(
            "👥 **Admin Panel**\n\n"
            "**Available Commands:**\n\n"
            "• `/add_admin <user_id>` - Add new admin\n"
            "• `/remove_admin <user_id>` - Remove admin\n"
            "• `/list_admins` - List all admins",
            buttons=[[Button.inline("🔙 Back to Menu", "back_to_menu")]]
        )
        return
    
    if data == "menu_help":
        await event.edit(
            "ℹ️ **Help & Instructions**\n\n"
            "**📱 Add Accounts:**\n"
            "Use `/add +phone` to add reporting accounts\n\n"
            "**⚠️ Report Posts:**\n"
            "Use `/post <link> [cycles]` to report posts\n\n"
            "**📢 Report Channels:**\n"
            "Use `/channel <link> [cycles]` to report channels\n\n"
            "**💡 Tips:**\n"
            "• Add multiple accounts for more reports\n"
            "• Cycles = how many times each account reports\n"
            "• Default is 1 cycle, no maximum limit",
            buttons=[[Button.inline("🔙 Back to Menu", "back_to_menu")]]
        )
        return
    
    if data == "back_to_menu":
        # Get session count
        session_count = await user_sessions_col.count_documents({"user_id": user_id, "is_active": True})
        
        welcome_msg = (
            "🔒 **Admin Mass Reporting Bot**\n\n"
            f"👤 **Your ID:** `{user_id}`\n"
            f"📱 **Active Accounts:** {session_count}\n\n"
            "**Choose an option below:**"
        )
        
        is_super_admin = (user_id == config.SUPER_ADMIN_ID)
        
        buttons = [
            [Button.inline("⚠️ Report Post", "menu_report_post"),
             Button.inline("📢 Report Channel", "menu_report_channel")],
            [Button.inline("➕ Add Account", "menu_add_account"),
             Button.inline("📱 My Accounts", "menu_my_sessions")],
        ]
        
        if is_super_admin:
            buttons.append([
                Button.inline("👥 Admin Panel", "menu_admin_panel"),
                Button.inline("ℹ️ Help", "menu_help")
            ])
        else:
            buttons.append([Button.inline("ℹ️ Help", "menu_help")])
        
        await event.edit(welcome_msg, buttons=buttons)
        return
    
    if data == "cancel_report":
        await event.edit("❌ Report cancelled.", buttons=[[Button.inline("🔙 Back to Menu", "back_to_menu")]])
        logger.info(f"User {user_id} cancelled report")
        return
    
    if data.startswith("channelreason_"):
        # Parse callback data for channel report: channelreason_spam:channel:0:cycles
        try:
            parts = data.split(":")
            logger.info(f"Channel callback data parts: {parts}")
            
            if len(parts) < 3:
                await event.answer("❌ Invalid callback format", alert=True)
                logger.error(f"Invalid callback data format: {data}")
                return
            
            # Extract: channelreason_spam, channel, 0, cycles (optional)
            reason_part = parts[0]  # "channelreason_spam"
            reason = reason_part.replace("channelreason_", "")  # "spam"
            channel_username = parts[1]  # channel name
            cycles = int(parts[3]) if len(parts) > 3 else 1  # cycles (default 1)
            
            logger.info(f"Parsed - Reason: {reason}, Channel: {channel_username}, Cycles: {cycles}")
            
        except (ValueError, IndexError) as e:
            await event.answer("❌ Invalid callback data", alert=True)
            logger.error(f"Callback parsing error: {e}, Data: {data}")
            return

        reason_map = {
            "spam": InputReportReasonSpam(),
            "violence": InputReportReasonViolence(),
            "fraud": InputReportReasonOther(),
            "other": InputReportReasonOther()
        }
        selected_reason = reason_map.get(reason, InputReportReasonSpam())

        await event.edit(f"🔄 Starting mass report for channel `@{channel_username}`...\n\n**Cycles:** {cycles}\n\nThis may take a few moments...")
        logger.info(f"User {user_id} started channel report for {channel_username} with reason: {reason}, cycles: {cycles}")

        # Start the channel mass reporting process
        await mass_report_channel(
            channel_username=channel_username,
            reason=selected_reason,
            reason_text=reason,
            initiator_id=user_id,
            cycles=cycles
        )
        return
    
    if data.startswith("reason_user_"):
        # Parse callback data for user reports: reason_user_spam:username:cycles
        try:
            parts = data.split(":")
            logger.info(f"User callback data parts: {parts}")
            
            if len(parts) < 3:
                await event.answer("❌ Invalid callback format", alert=True)
                logger.error(f"Invalid callback data format: {data}")
                return
            
            # Extract: reason_user_spam, username, cycles
            reason_part = parts[0]  # "reason_user_spam"
            reason = reason_part.replace("reason_user_", "")  # "spam"
            username = parts[1]  # username
            cycles = int(parts[2]) if len(parts) > 2 else 1  # cycles (default 1)
            
            logger.info(f"Parsed - Reason: {reason}, Username: @{username}, Cycles: {cycles}")
            
        except (ValueError, IndexError) as e:
            await event.answer("❌ Invalid callback data", alert=True)
            logger.error(f"Callback parsing error: {e}, Data: {data}")
            return

        reason_map = {
            "spam": InputReportReasonSpam(),
            "violence": InputReportReasonViolence(),
            "fraud": InputReportReasonOther(),
            "other": InputReportReasonOther()
        }
        selected_reason = reason_map.get(reason, InputReportReasonSpam())

        await event.edit(f"🔄 Starting mass report for user @{username}...\n\n**Cycles:** {cycles}\n\nThis may take a few moments...")
        logger.info(f"User {user_id} started user report for @{username} with reason: {reason}, cycles: {cycles}")

        # Start the mass reporting process for user
        await mass_report_user(
            username=username,
            reason=selected_reason,
            reason_text=reason,
            initiator_id=user_id,
            cycles=cycles
        )
        return
    
    if data.startswith("reason_"):
        # Parse callback data: reason_spam:channel:msg_id:cycles
        try:
            parts = data.split(":")
            logger.info(f"Callback data parts: {parts}")
            
            if len(parts) < 3:
                await event.answer("❌ Invalid callback format", alert=True)
                logger.error(f"Invalid callback data format: {data}")
                return
            
            # Extract: reason_spam, channel, msg_id, cycles (optional)
            reason_part = parts[0]  # "reason_spam"
            reason = reason_part.replace("reason_", "")  # "spam"
            channel_username = parts[1]  # channel name
            msg_id_str = parts[2]  # message ID
            cycles = int(parts[3]) if len(parts) > 3 else 1  # cycles (default 1)
            
            message_id = int(msg_id_str)
            
            logger.info(f"Parsed - Reason: {reason}, Channel: {channel_username}, Message ID: {message_id}, Cycles: {cycles}")
            
        except (ValueError, IndexError) as e:
            await event.answer("❌ Invalid callback data", alert=True)
            logger.error(f"Callback parsing error: {e}, Data: {data}")
            return

        reason_map = {
            "spam": InputReportReasonSpam(),
            "violence": InputReportReasonViolence(),
            "fraud": InputReportReasonOther(),
            "other": InputReportReasonOther()
        }
        selected_reason = reason_map.get(reason, InputReportReasonSpam())

        await event.edit(f"🔄 Starting mass report from all accounts for post `{message_id}`...\n\n**Cycles:** {cycles}\n\nThis may take a few moments...")
        logger.info(f"User {user_id} started mass report for {channel_username}/{message_id} with reason: {reason}, cycles: {cycles}")

        # Start the mass reporting process
        await mass_report_from_all_accounts(
            channel_username=channel_username,
            message_id=message_id,
            reason=selected_reason,
            reason_text=reason,
            initiator_id=user_id,
            cycles=cycles
        )



# --- Core: Mass Report Function ---
async def mass_report_from_all_accounts(channel_username, message_id, reason, reason_text, initiator_id, cycles=1):
    """
    1. Fetch all active session strings for the initiating admin.
    2. Log in to each account and send a report for the target post.
    """
    # Get all active sessions for this admin
    sessions_cursor = user_sessions_col.find({"user_id": initiator_id, "is_active": True})
    sessions = await sessions_cursor.to_list(length=None)

    if not sessions:
        logger.warning(f"No active sessions found for user {initiator_id}.")
        await main_bot.send_message(initiator_id, "❌ No active accounts/sessions found. Add an account first with `/add`.")
        return

    report_results = {"success": 0, "failed": 0, "errors": [], "details": []}
    total_sessions = len(sessions)
    total_reports = total_sessions * cycles

    logger.info(f"Starting mass report for user {initiator_id} with {total_sessions} sessions, {cycles} cycles")

    # Send initial status message (will be edited)
    status_msg = await main_bot.send_message(
        initiator_id,
        "🔄 **Report Started**\n\n"
        f"**Count:** 0\n"
        f"✅ **Success:** 0\n"
        f"❌ **Failed:** 0\n"
        f"📈 **Success Rate:** 0%\n"
        f"🔢 **Total Cycles:** {cycles}"
    )
    
    last_update_time = asyncio.get_event_loop().time()
    
    for idx, session_data in enumerate(sessions, 1):
        user_client = None
        session_id = str(session_data.get('_id', 'unknown'))
        account_name = session_data.get('account_name', f'Account #{idx}')
        phone_last4 = session_data.get('account_phone', '')[-4:] if session_data.get('account_phone') else f'#{idx}'
        
        try:
            # Create a client using the stored session string (ONE connection per account)
            user_client = TelegramClient(
                session=StringSession(session_data["session_string"]),
                api_id=session_data["api_id"],
                api_hash=session_data["api_hash"]
            )
            await user_client.connect()

            # Ensure the client is authorized
            if not await user_client.is_user_authorized():
                logger.error(f"Session {session_id} for user_id {initiator_id} is not authorized.")
                report_results["failed"] += cycles
                report_results["details"].append(f"❌ {account_name} (****{phone_last4}): Not authorized")
                await user_client.disconnect()
                continue

            # Resolve the target channel once
            target_entity = await user_client.get_entity(channel_username)
            
            # Get the report message from config
            report_config = config.REPORT_MESSAGES.get(reason_text, config.REPORT_MESSAGES["other"])
            report_message = report_config["message"]
            
            # Report using ReportPeerRequest (works for both channels and posts)
            from telethon.tl.functions.account import ReportPeerRequest
            
            # Send multiple reports from this ONE connection
            account_success = 0
            account_failed = 0
            
            for cycle in range(1, cycles + 1):
                try:
                    # Use ReportPeerRequest which works reliably
                    await user_client(ReportPeerRequest(
                        peer=target_entity,
                        reason=reason,
                        message=report_message
                    ))
                    
                    account_success += 1
                    report_results["success"] += 1
                    logger.info(f"Report {cycle}/{cycles} from {account_name} (****{phone_last4}) succeeded.")
                    
                except Exception as e:
                    account_failed += 1
                    report_results["failed"] += 1
                    logger.error(f"Report {cycle}/{cycles} from {account_name} failed: {e}")
                
                # Update status every 1.5 seconds
                current_time = asyncio.get_event_loop().time()
                if current_time - last_update_time >= 1.5:
                    total_done = report_results["success"] + report_results["failed"]
                    success_rate = (report_results["success"] / total_done * 100) if total_done > 0 else 0
                    
                    try:
                        await status_msg.edit(
                            "🔄 **Report Started**\n\n"
                            f"**Count:** {total_done}\n"
                            f"✅ **Success:** {report_results['success']}\n"
                            f"❌ **Failed:** {report_results['failed']}\n"
                            f"📈 **Success Rate:** {success_rate:.1f}%\n"
                            f"🔢 **Total Cycles:** {cycles}"
                        )
                        last_update_time = current_time
                    except:
                        pass
                
                # Delay between reports (2 seconds)
                await asyncio.sleep(2)
            
            # Summary for this account
            report_results["details"].append(f"✅ ****{phone_last4}: {account_success}/{cycles} reports sent")
            
            # Disconnect client after all cycles
            await user_client.disconnect()
            logger.info(f"Disconnected {account_name} after {cycles} reports")

        except Exception as e:
            report_results["failed"] += cycles
            error_msg = str(e)
            report_results["errors"].append(error_msg)
            report_results["details"].append(f"❌ ****{phone_last4}: {error_msg[:50]}")
            logger.error(f"Report failed for session {session_id} ({account_name}): {e}")
            if user_client:
                try:
                    await user_client.disconnect()
                except:
                    pass
    
    # Final update
    total_done = report_results["success"] + report_results["failed"]
    success_rate = (report_results["success"] / total_done * 100) if total_done > 0 else 0
    
    try:
        await status_msg.edit(
            "✅ **Report Complete**\n\n"
            f"👥 **Total Accounts:** {total_sessions}\n"
            f"✅ **Success:** {report_results['success']}\n"
            f"❌ **Failed:** {report_results['failed']}\n"
            f"📈 **Success Rate:** {success_rate:.1f}%\n"
            f"🔢 **Total Cycles:** {cycles}"
        )
    except:
        pass

    # Create detailed JSON report
    import json
    from datetime import datetime as dt
    
    report_data = {
        "report_type": "post",
        "timestamp": dt.utcnow().isoformat(),
        "target": {
            "channel_username": channel_username,
            "message_id": message_id,
            "full_link": f"https://t.me/{channel_username}/{message_id}"
        },
        "report_reason": {
            "type": reason_text,
            "message": config.REPORT_MESSAGES.get(reason_text, {}).get("message", "")
        },
        "configuration": {
            "total_accounts": total_sessions,
            "cycles_per_account": cycles,
            "total_reports_attempted": total_reports,
            "report_delay_seconds": config.REPORT_DELAY
        },
        "results": {
            "successful_reports": report_results['success'],
            "failed_reports": report_results['failed'],
            "success_rate_percent": round(success_rate, 2)
        },
        "account_details": [],
        "errors": report_results['errors'],
        "api_requests": []
    }
    
    # Add account details
    for detail in report_results['details']:
        report_data["account_details"].append(detail)
    
    # Add API request information
    for idx, session_data in enumerate(sessions, 1):
        phone_last4 = session_data.get('account_phone', '')[-4:] if session_data.get('account_phone') else f'#{idx}'
        account_name = session_data.get('account_name', f'Account #{idx}')
        
        # Get reason type name
        reason_type_name = type(reason).__name__
        
        api_info = {
            "account": f"****{phone_last4}",
            "account_name": account_name,
            "api_endpoint": "account.reportPeer",
            "method": "ReportPeerRequest",
            "parameters": {
                "peer": f"@{channel_username}",
                "message_id": message_id,
                "reason_type": reason_type_name,
                "reason": reason_text,
                "message": config.REPORT_MESSAGES.get(reason_text, {}).get("message", "")[:100] + "..."
            },
            "cycles_sent": cycles,
            "status": "success" if any(phone_last4 in d for d in report_results['details'] if "✅" in d) else "failed"
        }
        report_data["api_requests"].append(api_info)
    
    # Save to file
    filename = f"report_{channel_username}_{message_id}_{dt.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    # Send file to user
    await main_bot.send_file(
        initiator_id,
        filename,
        caption=f"📊 **Detailed Report Log**\n\n"
                f"✅ Success: {report_results['success']}\n"
                f"❌ Failed: {report_results['failed']}\n"
                f"📈 Success Rate: {success_rate:.1f}%"
    )
    
    # Delete local file
    import os
    try:
        os.remove(filename)
    except:
        pass
    
    logger.info(f"Mass report completed for user {initiator_id}: {report_results['success']} success, {report_results['failed']} failed")

# --- Core: Mass Report User Function ---
async def mass_report_user(username, reason, reason_text, initiator_id, cycles=1):
    """
    Report a user profile.
    """
    from telethon.tl.functions.account import ReportPeerRequest
    
    # Get all active sessions for this admin
    sessions_cursor = user_sessions_col.find({"user_id": initiator_id, "is_active": True})
    sessions = await sessions_cursor.to_list(length=None)

    if not sessions:
        logger.warning(f"No active sessions found for user {initiator_id}.")
        await main_bot.send_message(initiator_id, "❌ No active accounts/sessions found. Add an account first with `/add`.")
        return

    report_results = {"success": 0, "failed": 0, "errors": [], "details": []}
    total_sessions = len(sessions)
    total_reports = total_sessions * cycles

    logger.info(f"Starting user report for {initiator_id} with {total_sessions} sessions, {cycles} cycles")

    # Send initial status message (will be edited)
    status_msg = await main_bot.send_message(
        initiator_id,
        "🔄 **Report Started**\n\n"
        f"👥 **Total Accounts:** {total_sessions}\n"
        f"✅ **Success:** 0\n"
        f"❌ **Failed:** 0\n"
        f"📈 **Success Rate:** 0%\n"
        f"🔢 **Total Cycles:** {cycles}"
    )
    
    last_update_time = asyncio.get_event_loop().time()
    
    for idx, session_data in enumerate(sessions, 1):
        user_client = None
        session_id = str(session_data.get('_id', 'unknown'))
        account_name = session_data.get('account_name', f'Account #{idx}')
        phone_last4 = session_data.get('account_phone', '')[-4:] if session_data.get('account_phone') else f'#{idx}'
        
        try:
            # Create a client using the stored session string (ONE connection per account)
            user_client = TelegramClient(
                session=StringSession(session_data["session_string"]),
                api_id=session_data["api_id"],
                api_hash=session_data["api_hash"]
            )
            await user_client.connect()

            # Ensure the client is authorized
            if not await user_client.is_user_authorized():
                logger.error(f"Session {session_id} for user_id {initiator_id} is not authorized.")
                report_results["failed"] += cycles
                report_results["details"].append(f"❌ {account_name} (****{phone_last4}): Not authorized")
                await user_client.disconnect()
                continue

            # Resolve the target user once
            target_entity = await user_client.get_entity(username)
            
            # Get the report message from config
            report_config = config.REPORT_MESSAGES.get(reason_text, config.REPORT_MESSAGES["other"])
            report_message = report_config["message"]
            
            # Send multiple reports from this ONE connection
            account_success = 0
            account_failed = 0
            
            for cycle in range(1, cycles + 1):
                try:
                    # Report the user
                    await user_client(ReportPeerRequest(
                        peer=target_entity,
                        reason=reason,
                        message=report_message
                    ))
                    
                    account_success += 1
                    report_results["success"] += 1
                    logger.info(f"User report {cycle}/{cycles} from {account_name} (****{phone_last4}) succeeded.")
                    
                except Exception as e:
                    account_failed += 1
                    report_results["failed"] += 1
                    logger.error(f"User report {cycle}/{cycles} from {account_name} failed: {e}")
                
                # Update status every 1.5 seconds
                current_time = asyncio.get_event_loop().time()
                if current_time - last_update_time >= 1.5:
                    total_done = report_results["success"] + report_results["failed"]
                    success_rate = (report_results["success"] / total_done * 100) if total_done > 0 else 0
                    
                    try:
                        await status_msg.edit(
                            "🔄 **Report Started**\n\n"
                            f"👥 **Total Accounts:** {total_sessions}\n"
                            f"✅ **Success:** {report_results['success']}\n"
                            f"❌ **Failed:** {report_results['failed']}\n"
                            f"📈 **Success Rate:** {success_rate:.1f}%\n"
                            f"🔢 **Total Cycles:** {cycles}"
                        )
                        last_update_time = current_time
                    except:
                        pass
                
                # Delay between reports (2 seconds)
                await asyncio.sleep(2)
            
            # Summary for this account
            report_results["details"].append(f"✅ ****{phone_last4}: {account_success}/{cycles} reports sent")
            
            # Disconnect client after all cycles
            await user_client.disconnect()
            logger.info(f"Disconnected {account_name} after {cycles} user reports")

        except Exception as e:
            report_results["failed"] += cycles
            error_msg = str(e)
            report_results["errors"].append(error_msg)
            report_results["details"].append(f"❌ ****{phone_last4}: {error_msg[:50]}")
            logger.error(f"User report failed for session {session_id} ({account_name}): {e}")
            if user_client:
                try:
                    await user_client.disconnect()
                except:
                    pass
    
    # Final update
    total_done = report_results["success"] + report_results["failed"]
    success_rate = (report_results["success"] / total_done * 100) if total_done > 0 else 0
    
    try:
        await status_msg.edit(
            "✅ **Report Complete**\n\n"
            f"👥 **Total Accounts:** {total_sessions}\n"
            f"✅ **Success:** {report_results['success']}\n"
            f"❌ **Failed:** {report_results['failed']}\n"
            f"📈 **Success Rate:** {success_rate:.1f}%\n"
            f"🔢 **Total Cycles:** {cycles}"
        )
    except:
        pass

    # Create detailed JSON report
    import json
    from datetime import datetime as dt
    
    report_data = {
        "report_type": "user",
        "timestamp": dt.utcnow().isoformat(),
        "target": {
            "username": username,
            "full_link": f"https://t.me/{username}"
        },
        "report_reason": {
            "type": reason_text,
            "message": config.REPORT_MESSAGES.get(reason_text, {}).get("message", "")
        },
        "configuration": {
            "total_accounts": total_sessions,
            "cycles_per_account": cycles,
            "total_reports_attempted": total_reports,
            "report_delay_seconds": config.REPORT_DELAY
        },
        "results": {
            "successful_reports": report_results['success'],
            "failed_reports": report_results['failed'],
            "success_rate_percent": round(success_rate, 2)
        },
        "account_details": [],
        "errors": report_results['errors'],
        "api_requests": []
    }
    
    # Add account details
    for detail in report_results['details']:
        report_data["account_details"].append(detail)
    
    # Add API request information
    reason_type_name = type(reason).__name__
    for idx, session_data in enumerate(sessions, 1):
        phone_last4 = session_data.get('account_phone', '')[-4:] if session_data.get('account_phone') else f'#{idx}'
        account_name = session_data.get('account_name', f'Account #{idx}')
        
        api_info = {
            "account": f"****{phone_last4}",
            "account_name": account_name,
            "api_endpoint": "account.reportPeer",
            "method": "ReportPeerRequest",
            "parameters": {
                "peer": f"@{username}",
                "reason_type": reason_type_name,
                "reason": reason_text,
                "message": config.REPORT_MESSAGES.get(reason_text, {}).get("message", "")[:100] + "..."
            },
            "cycles_sent": cycles,
            "status": "success" if any(phone_last4 in d for d in report_results['details'] if "✅" in d) else "failed"
        }
        report_data["api_requests"].append(api_info)
    
    # Save to file
    filename = f"report_user_{username}_{dt.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    # Send file to user
    await main_bot.send_file(
        initiator_id,
        filename,
        caption=f"📊 **Detailed Report Log**\n\n"
                f"✅ Success: {report_results['success']}\n"
                f"❌ Failed: {report_results['failed']}\n"
                f"📈 Success Rate: {success_rate:.1f}%"
    )
    
    # Delete local file
    import os
    try:
        os.remove(filename)
    except:
        pass
    
    logger.info(f"User report completed for {initiator_id}: {report_results['success']} success, {report_results['failed']} failed")

# --- Core: Mass Report Channel Function ---
async def mass_report_channel(channel_username, reason, reason_text, initiator_id, cycles=1):
    """
    Report an entire channel/user (not a specific post).
    """
    from telethon.tl.functions.account import ReportPeerRequest
    
    # Get all active sessions for this admin
    sessions_cursor = user_sessions_col.find({"user_id": initiator_id, "is_active": True})
    sessions = await sessions_cursor.to_list(length=None)

    if not sessions:
        logger.warning(f"No active sessions found for user {initiator_id}.")
        await main_bot.send_message(initiator_id, "❌ No active accounts/sessions found. Add an account first with `/add`.")
        return

    report_results = {"success": 0, "failed": 0, "errors": [], "details": []}
    total_sessions = len(sessions)
    total_reports = total_sessions * cycles

    logger.info(f"Starting channel report for user {initiator_id} with {total_sessions} sessions, {cycles} cycles")

    # Send initial status message (will be edited)
    status_msg = await main_bot.send_message(
        initiator_id,
        "🔄 **Report Started**\n\n"
        f"**Count:** 0\n"
        f"✅ **Success:** 0\n"
        f"❌ **Failed:** 0\n"
        f"📈 **Success Rate:** 0%\n"
        f"🔢 **Total Cycles:** {cycles}"
    )
    
    last_update_time = asyncio.get_event_loop().time()
    
    for idx, session_data in enumerate(sessions, 1):
        user_client = None
        session_id = str(session_data.get('_id', 'unknown'))
        account_name = session_data.get('account_name', f'Account #{idx}')
        phone_last4 = session_data.get('account_phone', '')[-4:] if session_data.get('account_phone') else f'#{idx}'
        
        try:
            # Create a client using the stored session string (ONE connection per account)
            user_client = TelegramClient(
                session=StringSession(session_data["session_string"]),
                api_id=session_data["api_id"],
                api_hash=session_data["api_hash"]
            )
            await user_client.connect()

            # Ensure the client is authorized
            if not await user_client.is_user_authorized():
                logger.error(f"Session {session_id} for user_id {initiator_id} is not authorized.")
                report_results["failed"] += cycles
                report_results["details"].append(f"❌ {account_name} (****{phone_last4}): Not authorized")
                await user_client.disconnect()
                continue

            # Resolve the target channel once
            target_entity = await user_client.get_entity(channel_username)
            
            # Get the report message from config
            report_config = config.REPORT_MESSAGES.get(reason_text, config.REPORT_MESSAGES["other"])
            report_message = report_config["message"]
            
            # Send multiple reports from this ONE connection
            account_success = 0
            account_failed = 0
            
            for cycle in range(1, cycles + 1):
                try:
                    # Report the peer (channel/user)
                    await user_client(ReportPeerRequest(
                        peer=target_entity,
                        reason=reason,
                        message=report_message
                    ))
                    
                    account_success += 1
                    report_results["success"] += 1
                    logger.info(f"Channel report {cycle}/{cycles} from {account_name} (****{phone_last4}) succeeded.")
                    
                except Exception as e:
                    account_failed += 1
                    report_results["failed"] += 1
                    logger.error(f"Channel report {cycle}/{cycles} from {account_name} failed: {e}")
                
                # Update status every 1.5 seconds
                current_time = asyncio.get_event_loop().time()
                if current_time - last_update_time >= 1.5:
                    total_done = report_results["success"] + report_results["failed"]
                    success_rate = (report_results["success"] / total_done * 100) if total_done > 0 else 0
                    
                    try:
                        await status_msg.edit(
                            "🔄 **Report Started**\n\n"
                            f"👥 **Total Accounts:** {total_sessions}\n"
                            f"✅ **Success:** {report_results['success']}\n"
                            f"❌ **Failed:** {report_results['failed']}\n"
                            f"📈 **Success Rate:** {success_rate:.1f}%\n"
                            f"🔢 **Total Cycles:** {cycles}"
                        )
                        last_update_time = current_time
                    except:
                        pass
                
                # Delay between reports (2 seconds)
                await asyncio.sleep(2)
            
            # Summary for this account
            report_results["details"].append(f"✅ ****{phone_last4}: {account_success}/{cycles} reports sent")
            
            # Disconnect client after all cycles
            await user_client.disconnect()
            logger.info(f"Disconnected {account_name} after {cycles} channel reports")

        except Exception as e:
            report_results["failed"] += cycles
            error_msg = str(e)
            report_results["errors"].append(error_msg)
            report_results["details"].append(f"❌ ****{phone_last4}: {error_msg[:50]}")
            logger.error(f"Channel report failed for session {session_id} ({account_name}): {e}")
            if user_client:
                try:
                    await user_client.disconnect()
                except:
                    pass
    
    # Final update
    total_done = report_results["success"] + report_results["failed"]
    success_rate = (report_results["success"] / total_done * 100) if total_done > 0 else 0
    
    try:
        await status_msg.edit(
            "✅ **Report Complete**\n\n"
            f"👥 **Total Accounts:** {total_sessions}\n"
            f"✅ **Success:** {report_results['success']}\n"
            f"❌ **Failed:** {report_results['failed']}\n"
            f"📈 **Success Rate:** {success_rate:.1f}%\n"
            f"🔢 **Total Cycles:** {cycles}"
        )
    except:
        pass

    # Create detailed JSON report
    import json
    from datetime import datetime as dt
    
    report_data = {
        "report_type": "channel",
        "timestamp": dt.utcnow().isoformat(),
        "target": {
            "channel_username": channel_username,
            "full_link": f"https://t.me/{channel_username}"
        },
        "report_reason": {
            "type": reason_text,
            "message": config.REPORT_MESSAGES.get(reason_text, {}).get("message", "")
        },
        "configuration": {
            "total_accounts": total_sessions,
            "cycles_per_account": cycles,
            "total_reports_attempted": total_reports,
            "report_delay_seconds": config.REPORT_DELAY
        },
        "results": {
            "successful_reports": report_results['success'],
            "failed_reports": report_results['failed'],
            "success_rate_percent": round(success_rate, 2)
        },
        "account_details": [],
        "errors": report_results['errors'],
        "api_requests": []
    }
    
    # Add account details
    for detail in report_results['details']:
        report_data["account_details"].append(detail)
    
    # Add API request information
    for idx, session_data in enumerate(sessions, 1):
        phone_last4 = session_data.get('account_phone', '')[-4:] if session_data.get('account_phone') else f'#{idx}'
        account_name = session_data.get('account_name', f'Account #{idx}')
        
        # Get reason type name
        reason_type_name = type(reason).__name__
        
        api_info = {
            "account": f"****{phone_last4}",
            "account_name": account_name,
            "api_endpoint": "account.reportPeer",
            "method": "ReportPeerRequest",
            "parameters": {
                "peer": f"@{channel_username}",
                "reason_type": reason_type_name,
                "reason": reason_text,
                "message": config.REPORT_MESSAGES.get(reason_text, {}).get("message", "")[:100] + "..."
            },
            "cycles_sent": cycles,
            "status": "success" if any(phone_last4 in d for d in report_results['details'] if "✅" in d) else "failed"
        }
        report_data["api_requests"].append(api_info)
    
    # Save to file
    filename = f"report_channel_{channel_username}_{dt.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    # Send file to user
    await main_bot.send_file(
        initiator_id,
        filename,
        caption=f"📊 **Detailed Report Log**\n\n"
                f"✅ Success: {report_results['success']}\n"
                f"❌ Failed: {report_results['failed']}\n"
                f"📈 Success Rate: {success_rate:.1f}%"
    )
    
    # Delete local file
    import os
    try:
        os.remove(filename)
    except:
        pass
    
    logger.info(f"Channel report completed for user {initiator_id}: {report_results['success']} success, {report_results['failed']} failed")



# Store for pending login sessions
pending_logins = {}

# --- Command: /add (simplified from /add_account) ---
@main_bot.on(events.NewMessage(pattern='/add'))
async def add_account_handler(event):
    user_id = event.sender_id
    
    if not await is_user_authorized(user_id):
        return

    args = event.message.text.split()
    
    if len(args) < 2:
        await event.reply(
            "📱 **Add Telegram Account for Reporting**\n\n"
            "**Usage:**\n"
            "`/add <phone_number> [account_name]`\n\n"
            "**Examples:**\n"
            "`/add +1234567890`\n"
            "`/add +1234567890 MyAccount`\n\n"
            "The bot will send an OTP to this number.\n"
            "⚠️ Make sure you can receive SMS/Telegram code on this number!"
        )
        return
    
    phone = args[1].strip()
    account_name = args[2] if len(args) > 2 else f"Account_{phone[-4:]}"
    
    # Validate phone format
    if not phone.startswith('+'):
        await event.reply("❌ Phone number must start with '+' and country code.\n\n**Example:** `+1234567890`")
        return
    
    try:
        await event.reply("🔄 Initiating login process...\n\nPlease wait...")
        
        # Create a new client for this phone number
        session_name = f"session_{user_id}_{phone.replace('+', '')}"
        user_client = TelegramClient(session_name, config.API_ID, config.API_HASH)
        
        await user_client.connect()
        
        # Send code request
        await user_client.send_code_request(phone)
        
        # Store the client temporarily
        pending_logins[user_id] = {
            'client': user_client,
            'phone': phone,
            'account_name': account_name,
            'session_name': session_name,
            'step': 'otp'
        }
        
        await event.reply(
            f"📲 **OTP Sent to {phone}**\n\n"
            f"Just send the OTP code (5 digits) directly.\n"
            f"No command needed!\n\n"
            f"⏱ You have 3 minutes to verify."
        )
        logger.info(f"User {user_id} initiated login for {phone}")
        
    except Exception as e:
        await event.reply(f"❌ **Error sending OTP:**\n{str(e)}")
        logger.error(f"Error in add_account for user {user_id}: {e}")
        if user_id in pending_logins:
            try:
                await pending_logins[user_id]['client'].disconnect()
            except:
                pass
            del pending_logins[user_id]

# --- Auto OTP/2FA Handler (no command needed) ---
@main_bot.on(events.NewMessage)
async def auto_verify_handler(event):
    user_id = event.sender_id
    
    if not await is_user_authorized(user_id):
        return
    
    # Skip if it's a command
    if event.message.text and event.message.text.startswith('/'):
        return
    
    # Check if user has pending login
    if user_id not in pending_logins:
        return
    
    message_text = event.message.text.strip()
    
    # Delete the message for security
    try:
        await event.delete()
    except:
        pass
    
    login_data = pending_logins[user_id]
    
    try:
        user_client = login_data['client']
        phone = login_data['phone']
        
        if login_data['step'] == 'otp':
            try:
                # Try to sign in with the code
                await user_client.sign_in(phone, message_text)
                
                # Success! Get account info
                me = await user_client.get_me()
                username = me.username or "No username"
                
                # Get session string
                session_string = StringSession.save(user_client.session)
                
                # Store in database
                session_doc = {
                    "user_id": user_id,
                    "api_id": config.API_ID,
                    "api_hash": config.API_HASH,
                    "session_string": session_string,
                    "account_name": login_data['account_name'],
                    "account_username": username,
                    "account_phone": phone,
                    "added_at": datetime.utcnow(),
                    "is_active": True
                }
                
                result = await user_sessions_col.insert_one(session_doc)
                session_id = str(result.inserted_id)
                
                await main_bot.send_message(
                    user_id,
                    f"✅ **Account Added Successfully!**\n\n"
                    f"**Session ID:** `{session_id}`\n"
                    f"**Account Name:** {login_data['account_name']}\n"
                    f"**Username:** @{username}\n"
                    f"**Phone:** {phone}\n\n"
                    f"You can now use this account for reporting.\n"
                    f"Use `/my_sessions` to view all your accounts."
                )
                logger.info(f"User {user_id} successfully added account {phone}")
                
                # Cleanup
                await user_client.disconnect()
                del pending_logins[user_id]
                
                # Delete session file
                import os
                try:
                    os.remove(f"{login_data['session_name']}.session")
                except:
                    pass
                
            except Exception as e:
                error_str = str(e)
                
                # Check if 2FA is required
                if "Two-steps verification" in error_str or "password" in error_str.lower():
                    login_data['step'] = '2fa'
                    await main_bot.send_message(
                        user_id,
                        "🔐 **2FA Password Required**\n\n"
                        "This account has Two-Factor Authentication enabled.\n\n"
                        "Just send your 2FA password directly (no command needed)."
                    )
                else:
                    await main_bot.send_message(
                        user_id,
                        f"❌ **Invalid OTP Code**\n\n"
                        f"Error: {error_str}\n\n"
                        f"Please send the correct code."
                    )
                    logger.error(f"OTP verification failed for user {user_id}: {e}")
        
        elif login_data['step'] == '2fa':
            try:
                # Try to sign in with 2FA password
                await user_client.sign_in(password=message_text)
                
                # Success! Get account info
                me = await user_client.get_me()
                username = me.username or "No username"
                
                # Get session string
                session_string = StringSession.save(user_client.session)
                
                # Store in database
                session_doc = {
                    "user_id": user_id,
                    "api_id": config.API_ID,
                    "api_hash": config.API_HASH,
                    "session_string": session_string,
                    "account_name": login_data['account_name'],
                    "account_username": username,
                    "account_phone": phone,
                    "added_at": datetime.utcnow(),
                    "is_active": True
                }
                
                result = await user_sessions_col.insert_one(session_doc)
                session_id = str(result.inserted_id)
                
                await main_bot.send_message(
                    user_id,
                    f"✅ **Account Added Successfully!**\n\n"
                    f"**Session ID:** `{session_id}`\n"
                    f"**Account Name:** {login_data['account_name']}\n"
                    f"**Username:** @{username}\n"
                    f"**Phone:** {phone}\n\n"
                    f"You can now use this account for reporting.\n"
                    f"Use `/my_sessions` to view all your accounts."
                )
                logger.info(f"User {user_id} successfully added account {phone} with 2FA")
                
                # Cleanup
                await user_client.disconnect()
                del pending_logins[user_id]
                
                # Delete session file
                import os
                try:
                    os.remove(f"{login_data['session_name']}.session")
                except:
                    pass
                
            except Exception as e:
                await main_bot.send_message(
                    user_id,
                    f"❌ **Invalid 2FA Password**\n\n"
                    f"Error: {str(e)}\n\n"
                    f"Please send the correct password."
                )
                logger.error(f"2FA verification failed for user {user_id}: {e}")
    
    except Exception as e:
        await main_bot.send_message(
            user_id,
            f"❌ **Verification Error:**\n{str(e)}\n\n"
            f"Please start over with `/add <phone>`"
        )
        logger.error(f"Verification error for user {user_id}: {e}")
        if user_id in pending_logins:
            try:
                await pending_logins[user_id]['client'].disconnect()
            except:
                pass
            del pending_logins[user_id]

# --- Old /verify command (kept for compatibility) ---
@main_bot.on(events.NewMessage(pattern='/verify'))
async def verify_command_handler(event):
    user_id = event.sender_id
    
    if not await is_user_authorized(user_id):
        return
    
    # Delete the message for security
    try:
        await event.delete()
    except:
        pass
    
    if user_id not in pending_logins:
        await main_bot.send_message(
            user_id,
            "❌ No pending login found.\n\nUse `/add_account <phone>` first."
        )
        return
    
    args = event.message.text.split()
    if len(args) < 2:
        await main_bot.send_message(
            user_id,
            "❌ **Invalid format!**\n\n"
            "Please use:\n"
            "`/verify <code>`\n\n"
            "**Example:** `/verify 12345`"
        )
        return
    
    code = args[1].strip()
    login_data = pending_logins[user_id]
    
    try:
        user_client = login_data['client']
        phone = login_data['phone']
        
        if login_data['step'] == 'otp':
            try:
                # Try to sign in with the code
                await user_client.sign_in(phone, code)
                
                # Success! Get account info
                me = await user_client.get_me()
                username = me.username or "No username"
                
                # Get session string
                session_string = StringSession.save(user_client.session)
                
                # Store in database
                session_doc = {
                    "user_id": user_id,
                    "api_id": config.API_ID,
                    "api_hash": config.API_HASH,
                    "session_string": session_string,
                    "account_name": login_data['account_name'],
                    "account_username": username,
                    "account_phone": phone,
                    "added_at": datetime.utcnow(),
                    "is_active": True
                }
                
                result = await user_sessions_col.insert_one(session_doc)
                session_id = str(result.inserted_id)
                
                await main_bot.send_message(
                    user_id,
                    f"✅ **Account Added Successfully!**\n\n"
                    f"**Session ID:** `{session_id}`\n"
                    f"**Account Name:** {login_data['account_name']}\n"
                    f"**Username:** @{username}\n"
                    f"**Phone:** {phone}\n\n"
                    f"You can now use this account for reporting.\n"
                    f"Use `/my_sessions` to view all your accounts."
                )
                logger.info(f"User {user_id} successfully added account {phone}")
                
                # Cleanup
                await user_client.disconnect()
                del pending_logins[user_id]
                
                # Delete session file
                import os
                try:
                    os.remove(f"{login_data['session_name']}.session")
                except:
                    pass
                
            except Exception as e:
                error_str = str(e)
                
                # Check if 2FA is required
                if "Two-steps verification" in error_str or "password" in error_str.lower():
                    login_data['step'] = '2fa'
                    await main_bot.send_message(
                        user_id,
                        "🔐 **2FA Password Required**\n\n"
                        "This account has Two-Factor Authentication enabled.\n\n"
                        "Please send your 2FA password:\n"
                        "`/verify <password>`\n\n"
                        "**Example:** `/verify MyPassword123`"
                    )
                else:
                    await main_bot.send_message(
                        user_id,
                        f"❌ **Invalid OTP Code**\n\n"
                        f"Error: {error_str}\n\n"
                        f"Please try again with `/verify <code>`"
                    )
                    logger.error(f"OTP verification failed for user {user_id}: {e}")
        
        elif login_data['step'] == '2fa':
            try:
                # Try to sign in with 2FA password
                await user_client.sign_in(password=code)
                
                # Success! Get account info
                me = await user_client.get_me()
                username = me.username or "No username"
                
                # Get session string
                session_string = StringSession.save(user_client.session)
                
                # Store in database
                session_doc = {
                    "user_id": user_id,
                    "api_id": config.API_ID,
                    "api_hash": config.API_HASH,
                    "session_string": session_string,
                    "account_name": login_data['account_name'],
                    "account_username": username,
                    "account_phone": phone,
                    "added_at": datetime.utcnow(),
                    "is_active": True
                }
                
                result = await user_sessions_col.insert_one(session_doc)
                session_id = str(result.inserted_id)
                
                await main_bot.send_message(
                    user_id,
                    f"✅ **Account Added Successfully!**\n\n"
                    f"**Session ID:** `{session_id}`\n"
                    f"**Account Name:** {login_data['account_name']}\n"
                    f"**Username:** @{username}\n"
                    f"**Phone:** {phone}\n\n"
                    f"You can now use this account for reporting.\n"
                    f"Use `/my_sessions` to view all your accounts."
                )
                logger.info(f"User {user_id} successfully added account {phone} with 2FA")
                
                # Cleanup
                await user_client.disconnect()
                del pending_logins[user_id]
                
                # Delete session file
                import os
                try:
                    os.remove(f"{login_data['session_name']}.session")
                except:
                    pass
                
            except Exception as e:
                await main_bot.send_message(
                    user_id,
                    f"❌ **Invalid 2FA Password**\n\n"
                    f"Error: {str(e)}\n\n"
                    f"Please try again with `/verify <password>`"
                )
                logger.error(f"2FA verification failed for user {user_id}: {e}")
    
    except Exception as e:
        await main_bot.send_message(
            user_id,
            f"❌ **Verification Error:**\n{str(e)}\n\n"
            f"Please start over with `/add_account <phone>`"
        )
        logger.error(f"Verification error for user {user_id}: {e}")
        if user_id in pending_logins:
            try:
                await pending_logins[user_id]['client'].disconnect()
            except:
                pass
            del pending_logins[user_id]

# --- Command: /cancel (Cancel pending login) ---
@main_bot.on(events.NewMessage(pattern='/cancel'))
async def cancel_login_handler(event):
    user_id = event.sender_id
    
    if not await is_user_authorized(user_id):
        return
    
    if user_id in pending_logins:
        try:
            await pending_logins[user_id]['client'].disconnect()
        except:
            pass
        del pending_logins[user_id]
        await event.reply("✅ Login process cancelled.")
        logger.info(f"User {user_id} cancelled login")
    else:
        await event.reply("❌ No pending login to cancel.")

# --- Command: /my_sessions ---
@main_bot.on(events.NewMessage(pattern='/my_sessions'))
async def my_sessions_handler(event):
    user_id = event.sender_id
    
    if not await is_user_authorized(user_id):
        return
    
    sessions_cursor = user_sessions_col.find({"user_id": user_id})
    sessions = await sessions_cursor.to_list(length=100)
    
    if not sessions:
        await event.reply(
            "📱 **No Accounts Found**\n\n"
            "You haven't added any accounts yet.\n"
            "Use `/add_account` to add your first account."
        )
        return
    
    msg = "📱 **Your Telegram Accounts:**\n\n"
    
    for idx, session in enumerate(sessions, 1):
        session_id = str(session['_id'])
        account_name = session.get('account_name', 'Unknown')
        username = session.get('account_username', 'N/A')
        status = "✅ Active" if session.get('is_active', True) else "❌ Inactive"
        added_at = session.get('added_at', 'Unknown')
        
        if isinstance(added_at, datetime):
            added_at = added_at.strftime('%Y-%m-%d %H:%M')
        
        msg += (
            f"{idx}. **{account_name}**\n"
            f"   ID: `{session_id}`\n"
            f"   Username: @{username}\n"
            f"   Status: {status}\n"
            f"   Added: {added_at}\n\n"
        )
    
    msg += f"**Total Accounts:** {len(sessions)}\n"
    msg += f"**Active:** {sum(1 for s in sessions if s.get('is_active', True))}\n\n"
    msg += "Use `/remove_session <session_id>` to remove an account."
    
    await event.reply(msg)
    logger.info(f"User {user_id} viewed their {len(sessions)} sessions")

# --- Command: /remove_session ---
@main_bot.on(events.NewMessage(pattern='/remove_session'))
async def remove_session_handler(event):
    user_id = event.sender_id
    
    if not await is_user_authorized(user_id):
        return
    
    args = event.message.text.split()
    if len(args) != 2:
        await event.reply("**Usage:** `/remove_session <session_id>`")
        return
    
    session_id = args[1]
    
    try:
        from bson import ObjectId
        result = await user_sessions_col.delete_one({
            "_id": ObjectId(session_id),
            "user_id": user_id
        })
        
        if result.deleted_count > 0:
            await event.reply(f"✅ Session `{session_id}` removed successfully.")
            logger.info(f"User {user_id} removed session {session_id}")
        else:
            await event.reply(f"❌ Session not found or you don't have permission to remove it.")
    except Exception as e:
        await event.reply(f"❌ Error removing session: {str(e)}")
        logger.error(f"Error removing session for user {user_id}: {e}")

# --- Command: /remove_admin ---
@main_bot.on(events.NewMessage(pattern='/remove_admin'))
async def remove_admin_handler(event):
    user_id = event.sender_id
    
    if user_id != config.SUPER_ADMIN_ID:
        await event.reply("⛔ Only the super admin can remove users.")
        return
    
    args = event.message.text.split()
    if len(args) != 2:
        await event.reply("**Usage:** `/remove_admin <user_id>`")
        return
    
    try:
        target_user_id = int(args[1])
        
        if target_user_id == config.SUPER_ADMIN_ID:
            await event.reply("❌ Cannot remove the super admin!")
            return
        
        result = await authorized_users_col.update_one(
            {"user_id": target_user_id},
            {"$set": {"is_active": False, "deactivated_at": datetime.utcnow()}}
        )
        
        if result.modified_count > 0:
            await event.reply(f"✅ Admin `{target_user_id}` has been removed.")
            logger.info(f"User {user_id} removed admin {target_user_id}")
        else:
            await event.reply(f"❌ Admin not found.")
    except ValueError:
        await event.reply("❌ Invalid user ID. Must be a number.")
    except Exception as e:
        await event.reply(f"❌ Error removing admin: {str(e)}")
        logger.error(f"Error removing admin: {e}")

# --- Command: /help ---
@main_bot.on(events.NewMessage(pattern='/help'))
async def help_handler(event):
    if not await is_user_authorized(event.sender_id):
        return
    
    help_msg = (
        "📚 **Detailed Help Guide**\n\n"
        "**Admin Management:**\n"
        "• `/add_admin <user_id>` - Add a new authorized admin (super admin only)\n"
        "• `/remove_admin <user_id>` - Remove an admin (super admin only)\n"
        "• `/list_admins` - View all authorized admins\n\n"
        "**Account Management:**\n"
        "• `/add_account` - Get instructions to add a Telegram account\n"
        "• `/provide_credentials` - Add account with credentials\n"
        "• `/my_sessions` - View all your added accounts\n"
        "• `/remove_session <id>` - Remove a specific account\n\n"
        "**Reporting:**\n"
        "• `/post <link>` - Start mass report on a post\n"
        "  Example: `/post https://t.me/channel/123`\n\n"
        "**How to get Session String:**\n"
        "1. Go to https://my.telegram.org/apps\n"
        "2. Get your API ID and API Hash\n"
        "3. Use @StringSessionBot on Telegram\n"
        "4. Follow the bot's instructions\n"
        "5. Copy the session string\n"
        "6. Use `/add_account` command here\n\n"
        "⚠️ **Important:** Never share your credentials with anyone!"
    )
    await event.reply(help_msg)

# --- Main Bot Startup ---
async def main():
    """Initialize the bot and start polling."""
    logger.info("Starting Telegram Mass Reporting Bot...")
    
    try:
        # Start the bot client
        await main_bot.start(bot_token=config.MAIN_BOT_TOKEN)
        logger.info("Bot client connected successfully")
        
        # Ensure super admin is in the database
        super_admin = await authorized_users_col.find_one({"user_id": config.SUPER_ADMIN_ID})
        if not super_admin:
            await authorized_users_col.insert_one({
                "user_id": config.SUPER_ADMIN_ID,
                "added_by": config.SUPER_ADMIN_ID,
                "added_at": datetime.utcnow(),
                "is_active": True,
                "role": "super_admin"
            })
            logger.info(f"Super admin {config.SUPER_ADMIN_ID} added to database")
        
        logger.info("Bot is running and ready to receive commands...")
        logger.info(f"Super Admin ID: {config.SUPER_ADMIN_ID}")
        
        # Keep the bot running
        await main_bot.run_until_disconnected()
    
    except KeyboardInterrupt:
        logger.info("Shutting down bot...")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        raise
    finally:
        # Graceful shutdown
        if main_bot:
            logger.info("Disconnecting bot...")
            if main_bot.is_connected():
                await main_bot.disconnect()
            logger.info("Bot stopped successfully")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")

