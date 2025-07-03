import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, \
    MessageHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio
import os

# Get bot token from environment variable or use placeholder
TOKEN = os.getenv('8071828059:AAEskmZQVoaWEoDgOG8ad8DlCm91w9hkK5U', '8071828059:AAEskmZQVoaWEoDgOG8ad8DlCm91w9hkK5U')
# Conversation states
WAITING_FOR_NAME, WAITING_FOR_DATE, WAITING_FOR_EDIT_NAME, WAITING_FOR_EDIT_DATE, WAITING_FOR_DELETE_NAME = range(5)


# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('birthdays.db')
    c = conn.cursor()

    # Main birthdays table
    c.execute('''CREATE TABLE IF NOT EXISTS birthdays
    (
        chat_id
        INTEGER,
        name
        TEXT,
        birthdate
        TEXT,
        PRIMARY
        KEY
                 (
        chat_id,
        name
                 )
        )''')

    # Settings table for each chat
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (
                     chat_id
                     INTEGER
                     PRIMARY
                     KEY,
                     notifications_enabled
                     INTEGER
                     DEFAULT
                     1,
                     reminder_hour
                     INTEGER
                     DEFAULT
                     8,
                     reminder_minute
                     INTEGER
                     DEFAULT
                     0
                 )''')

    conn.commit()
    conn.close()


# Calculate days until birthday
def days_until_birthday(birthdate_str):
    try:
        birthdate = datetime.strptime(birthdate_str, '%Y-%m-%d')
        today = datetime.now().date()

        # Get this year's birthday
        next_birthday = birthdate.replace(year=today.year).date()

        # If birthday already passed this year, get next year's
        if next_birthday < today:
            next_birthday = birthdate.replace(year=today.year + 1).date()

        days_left = (next_birthday - today).days
        return days_left
    except ValueError:
        return None


# Create main menu keyboard
def get_main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🎂 Add Birthday", callback_data="add_birthday"),
            InlineKeyboardButton("📋 View All", callback_data="list_birthdays")
        ],
        [
            InlineKeyboardButton("🎯 Next Birthday", callback_data="next_birthday"),
            InlineKeyboardButton("📅 Today's Birthdays", callback_data="todays_birthdays")
        ],
        [
            InlineKeyboardButton("🗓️ This Month", callback_data="this_month"),
            InlineKeyboardButton("📊 Statistics", callback_data="stats")
        ],
        [
            InlineKeyboardButton("✏️ Edit Birthday", callback_data="edit_birthday"),
            InlineKeyboardButton("🗑️ Delete Birthday", callback_data="delete_birthday")
        ],
        [
            InlineKeyboardButton("🔔 Notifications", callback_data="notifications_menu"),
            InlineKeyboardButton("📈 Birth Months", callback_data="birth_months")
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="help"),
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# Create notifications menu keyboard
def get_notifications_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🔔 Turn On", callback_data="notifications_on"),
            InlineKeyboardButton("🔕 Turn Off", callback_data="notifications_off")
        ],
        [
            InlineKeyboardButton("⏰ Set Time", callback_data="set_reminder_time"),
            InlineKeyboardButton("ℹ️ Info", callback_data="reminder_info")
        ],
        [
            InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# Create back button keyboard
def get_back_keyboard():
    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
    return InlineKeyboardMarkup(keyboard)


# Create cancel keyboard
def get_cancel_keyboard():
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="cancel")]]
    return InlineKeyboardMarkup(keyboard)


# Handle /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
🎉 **Welcome to Birthday Bot!** 🎂

Your personal birthday reminder assistant! I'll help you keep track of all important birthdays and never miss a special day.

✨ **Features:**
• 🎂 Add & manage birthdays
• 📅 Get daily reminders
• 📊 View statistics
• 🔔 Customize notifications

Choose an option below to get started:
    """

    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=get_main_menu_keyboard()
    )


# Handle callback queries
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "main_menu" or query.data == "refresh_menu":
        await show_main_menu(update, context)
    elif query.data == "add_birthday":
        await start_add_birthday(update, context)
    elif query.data == "list_birthdays":
        await list_birthdays_callback(update, context)
    elif query.data == "next_birthday":
        await next_birthday_callback(update, context)
    elif query.data == "todays_birthdays":
        await todays_birthdays_callback(update, context)
    elif query.data == "this_month":
        await this_month_callback(update, context)
    elif query.data == "stats":
        await stats_callback(update, context)
    elif query.data == "edit_birthday":
        await start_edit_birthday(update, context)
    elif query.data == "delete_birthday":
        await start_delete_birthday(update, context)
    elif query.data == "notifications_menu":
        await show_notifications_menu(update, context)
    elif query.data == "birth_months":
        await birth_months_callback(update, context)
    elif query.data == "help":
        await help_callback(update, context)
    elif query.data == "notifications_on":
        await set_notifications(update, context, True)
    elif query.data == "notifications_off":
        await set_notifications(update, context, False)
    elif query.data == "set_reminder_time":
        await start_set_reminder_time(update, context)
    elif query.data == "reminder_info":
        await reminder_info_callback(update, context)
    elif query.data == "cancel":
        await cancel_operation(update, context)


# Show main menu
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    menu_text = """
🎂 **Birthday Bot Main Menu** 🎉

Choose what you'd like to do:
    """

    if update.callback_query:
        await update.callback_query.edit_message_text(
            menu_text,
            parse_mode='Markdown',
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            menu_text,
            parse_mode='Markdown',
            reply_markup=get_main_menu_keyboard()
        )


# Show notifications menu
async def show_notifications_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.callback_query.message.chat_id

    # Get current settings
    conn = sqlite3.connect('birthdays.db')
    c = conn.cursor()
    c.execute("SELECT notifications_enabled, reminder_hour, reminder_minute FROM settings WHERE chat_id = ?",
              (chat_id,))
    result = c.fetchone()
    conn.close()

    if result:
        enabled, hour, minute = result
        status = "🔔 ON" if enabled else "🔕 OFF"
        time_str = f"{hour:02d}:{minute:02d}"
    else:
        status = "🔔 ON (default)"
        time_str = "08:00 (default)"

    menu_text = f"""
🔔 **Notification Settings**

**Current Status:** {status}
**Reminder Time:** ⏰ {time_str}

Choose an option:
    """

    await update.callback_query.edit_message_text(
        menu_text,
        parse_mode='Markdown',
        reply_markup=get_notifications_menu_keyboard()
    )


# Start add birthday conversation
async def start_add_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        "🎂 **Add New Birthday**\n\nPlease enter the person's name:",
        parse_mode='Markdown',
        reply_markup=get_cancel_keyboard()
    )
    return WAITING_FOR_NAME


# Handle name input for add birthday
async def handle_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['birthday_name'] = update.message.text
    await update.message.reply_text(
        f"📅 **Adding birthday for:** {update.message.text}\n\nNow please enter the birth date in format YYYY-MM-DD\n\n**Example:** 1995-07-15",
        parse_mode='Markdown',
        reply_markup=get_cancel_keyboard()
    )
    return WAITING_FOR_DATE


# Handle date input for add birthday
async def handle_date_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    name = context.user_data.get('birthday_name', '')
    birthdate = update.message.text

    try:
        datetime.strptime(birthdate, '%Y-%m-%d')  # Validate date format
    except ValueError:
        await update.message.reply_text(
            "❌ **Invalid date format!**\n\nPlease use YYYY-MM-DD format\n**Example:** 1995-07-15",
            parse_mode='Markdown',
            reply_markup=get_cancel_keyboard()
        )
        return WAITING_FOR_DATE

    # Save to database
    conn = sqlite3.connect('birthdays.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO birthdays (chat_id, name, birthdate) VALUES (?, ?, ?)",
              (chat_id, name, birthdate))
    conn.commit()
    conn.close()

    days_left = days_until_birthday(birthdate)
    success_text = f"""
✅ **Birthday Added Successfully!**

👤 **Name:** {name}
📅 **Date:** {birthdate}
⏰ **Days until next birthday:** {days_left}

🎉 I'll remind you when it's getting close!
    """

    await update.message.reply_text(
        success_text,
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )

    # Clear user data
    context.user_data.clear()
    return ConversationHandler.END


# List birthdays callback
async def list_birthdays_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.callback_query.message.chat_id
    conn = sqlite3.connect('birthdays.db')
    c = conn.cursor()
    c.execute("SELECT name, birthdate FROM birthdays WHERE chat_id = ? ORDER BY name", (chat_id,))
    birthdays = c.fetchall()
    conn.close()

    if not birthdays:
        message = "📋 **No birthdays found!**\n\nUse '🎂 Add Birthday' to get started."
    else:
        message = "📋 **All Birthdays:**\n\n"
        for name, birthdate in birthdays:
            days_left = days_until_birthday(birthdate)
            if days_left == 0:
                message += f"🎉 **{name}** - TODAY!\n"
            else:
                message += f"🎂 **{name}** - {days_left} days ({birthdate})\n"

    await update.callback_query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )


# Next birthday callback
async def next_birthday_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.callback_query.message.chat_id
    conn = sqlite3.connect('birthdays.db')
    c = conn.cursor()
    c.execute("SELECT name, birthdate FROM birthdays WHERE chat_id = ?", (chat_id,))
    birthdays = c.fetchall()
    conn.close()

    if not birthdays:
        message = "🎯 **No birthdays found!**\n\nAdd some birthdays first."
    else:
        next_bday = None
        min_days = float('inf')

        for name, birthdate in birthdays:
            days_left = days_until_birthday(birthdate)
            if days_left is not None and days_left < min_days:
                min_days = days_left
                next_bday = (name, birthdate, days_left)

        if next_bday:
            name, birthdate, days_left = next_bday
            if days_left == 0:
                message = f"🎉 **Today's Birthday!**\n\n🎂 **{name}** is celebrating today!"
            else:
                message = f"🎯 **Next Birthday:**\n\n🎂 **{name}**\n📅 **Date:** {birthdate}\n⏰ **In {days_left} days**"
        else:
            message = "❌ **No valid birthdays found.**"

    await update.callback_query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )


# Today's birthdays callback
async def todays_birthdays_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.callback_query.message.chat_id
    conn = sqlite3.connect('birthdays.db')
    c = conn.cursor()
    c.execute("SELECT name, birthdate FROM birthdays WHERE chat_id = ?", (chat_id,))
    birthdays = c.fetchall()
    conn.close()

    today_birthdays = []
    for name, birthdate in birthdays:
        days_left = days_until_birthday(birthdate)
        if days_left == 0:
            today_birthdays.append(name)

    if today_birthdays:
        names = '\n🎂 '.join(today_birthdays)
        message = f"🎉 **Today's Birthdays:**\n\n🎂 {names}\n\n🎊 Happy Birthday!"
    else:
        message = "📅 **No birthdays today.**\n\nCheck back tomorrow!"

    await update.callback_query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )


# This month callback
async def this_month_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.callback_query.message.chat_id
    current_month = datetime.now().month
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    conn = sqlite3.connect('birthdays.db')
    c = conn.cursor()
    c.execute("SELECT name, birthdate FROM birthdays WHERE chat_id = ?", (chat_id,))
    birthdays = c.fetchall()
    conn.close()

    month_birthdays = []
    for name, birthdate in birthdays:
        try:
            bday_date = datetime.strptime(birthdate, '%Y-%m-%d')
            if bday_date.month == current_month:
                days_left = days_until_birthday(birthdate)
                month_birthdays.append((name, birthdate, days_left))
        except ValueError:
            continue

    if month_birthdays:
        month_birthdays.sort(key=lambda x: x[2])  # Sort by days left
        message = f"🗓️ **{month_names[current_month - 1]} Birthdays:**\n\n"
        for name, birthdate, days_left in month_birthdays:
            if days_left == 0:
                message += f"🎉 **{name}** - TODAY!\n"
            else:
                message += f"🎂 **{name}** - {days_left} days ({birthdate})\n"
    else:
        message = f"📅 **No birthdays in {month_names[current_month - 1]}.**"

    await update.callback_query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )


# Stats callback
async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.callback_query.message.chat_id
    conn = sqlite3.connect('birthdays.db')
    c = conn.cursor()
    c.execute("SELECT name, birthdate FROM birthdays WHERE chat_id = ?", (chat_id,))
    birthdays = c.fetchall()
    conn.close()

    if not birthdays:
        message = "📊 **No statistics available.**\n\nAdd some birthdays first!"
    else:
        total_count = len(birthdays)
        upcoming_week = 0
        upcoming_month = 0
        today_count = 0

        for name, birthdate in birthdays:
            days_left = days_until_birthday(birthdate)
            if days_left is not None:
                if days_left == 0:
                    today_count += 1
                if days_left <= 7:
                    upcoming_week += 1
                if days_left <= 30:
                    upcoming_month += 1

        message = f"""
📊 **Birthday Statistics**

📝 **Total Birthdays:** {total_count}
🎉 **Today:** {today_count}
📅 **This Week:** {upcoming_week}
🗓️ **This Month:** {upcoming_month}

Keep adding more birthdays to build your network!
        """

    await update.callback_query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )


# Birth months callback
async def birth_months_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.callback_query.message.chat_id
    conn = sqlite3.connect('birthdays.db')
    c = conn.cursor()
    c.execute("SELECT birthdate FROM birthdays WHERE chat_id = ?", (chat_id,))
    birthdays = c.fetchall()
    conn.close()

    if not birthdays:
        message = "📈 **No birth month data available.**\n\nAdd some birthdays first!"
    else:
        months = {}
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        for (birthdate,) in birthdays:
            try:
                bday_date = datetime.strptime(birthdate, '%Y-%m-%d')
                month = bday_date.month
                if month not in months:
                    months[month] = 0
                months[month] += 1
            except ValueError:
                continue

        message = "📈 **Birth Month Distribution:**\n\n"
        for month in sorted(months.keys()):
            count = months[month]
            bars = '█' * min(count, 10)  # Max 10 bars for display
            message += f"**{month_names[month - 1]}:** {bars} ({count})\n"

    await update.callback_query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )


# Help callback
async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
❓ **Birthday Bot Help**

🎂 **Adding Birthdays:**
• Click 'Add Birthday' and follow the prompts
• Date format: YYYY-MM-DD (e.g., 1995-07-15)
• Names can include spaces and special characters

🔔 **Notifications:**
• Get daily reminders for upcoming birthdays
• Customize notification time (24-hour format)
• Turn notifications on/off anytime

📊 **Features:**
• View all birthdays in organized lists
• See next upcoming birthday
• Check today's and this month's birthdays
• View statistics and birth month distribution

💡 **Tips:**
• Works in both private chats and groups
• Each chat has separate birthday lists
• All data is stored securely
• Use the menu buttons for easy navigation

🆘 **Need Help?**
If you encounter any issues, try refreshing the menu or restart with /start
    """

    await update.callback_query.edit_message_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )


# Set notifications
async def set_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE, enabled: bool):
    chat_id = update.callback_query.message.chat_id
    conn = sqlite3.connect('birthdays.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (chat_id, notifications_enabled) VALUES (?, ?)",
              (chat_id, 1 if enabled else 0))
    conn.commit()
    conn.close()

    status = "enabled" if enabled else "disabled"
    icon = "🔔" if enabled else "🔕"

    message = f"{icon} **Notifications {status}!**\n\n"
    if enabled:
        message += "You'll receive daily reminders for upcoming birthdays."
    else:
        message += "You won't receive any birthday reminders."

    await update.callback_query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )


# Reminder info callback
async def reminder_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.callback_query.message.chat_id
    conn = sqlite3.connect('birthdays.db')
    c = conn.cursor()
    c.execute("SELECT notifications_enabled, reminder_hour, reminder_minute FROM settings WHERE chat_id = ?",
              (chat_id,))
    result = c.fetchone()
    conn.close()

    if result:
        enabled, hour, minute = result
        status = "🔔 Enabled" if enabled else "🔕 Disabled"
        time_str = f"{hour:02d}:{minute:02d}"
    else:
        status = "🔔 Enabled (default)"
        time_str = "08:00 (default)"

    message = f"""
ℹ️ **Notification Settings**

**Status:** {status}
**Reminder Time:** ⏰ {time_str}

**How it works:**
• Daily reminders for birthdays within 7 days
• Special messages on birthday days
• Reminders sent at your chosen time
    """

    await update.callback_query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )


# Cancel operation
async def cancel_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.callback_query.edit_message_text(
        "❌ **Operation cancelled.**",
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )
    return ConversationHandler.END


# Placeholder functions for edit and delete (can be expanded similarly)
async def start_edit_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        "✏️ **Edit Birthday**\n\nThis feature is coming soon!\nFor now, you can delete and re-add birthdays.",
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )


async def start_delete_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        "🗑️ **Delete Birthday**\n\nThis feature is coming soon!\nPlease use the command `/deletebirthday Name` for now.",
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )


async def start_set_reminder_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        "⏰ **Set Reminder Time**\n\nThis feature is coming soon!\nPlease use the command `/setremindertime HH:MM` for now.",
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )


# Daily birthday countdown with settings support
async def daily_countdown(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('birthdays.db')
    c = conn.cursor()

    # Get all chats with their notification settings
    c.execute("""SELECT DISTINCT b.chat_id, s.notifications_enabled
                 FROM birthdays b
                          LEFT JOIN settings s ON b.chat_id = s.chat_id""")
    chats = c.fetchall()

    for chat_id, notifications_enabled in chats:
        # Skip if notifications are disabled
        if notifications_enabled == 0:
            continue

        # Get birthdays for this chat
        c.execute("SELECT name, birthdate FROM birthdays WHERE chat_id = ?", (chat_id,))
        birthdays = c.fetchall()

        messages_to_send = []

        for name, birthdate in birthdays:
            days_left = days_until_birthday(birthdate)
            if days_left is not None:
                if days_left == 0:
                    messages_to_send.append(f"🎉 **Happy Birthday, {name}!** 🎂\n\nHave a wonderful day!")
                elif days_left <= 7:  # Only send reminders for upcoming birthdays
                    messages_to_send.append(f"🎂 **Reminder:** {days_left} days until {name}'s birthday!")

        # Send messages if any
        if messages_to_send:
            for message in messages_to_send:
                try:
                    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
                except Exception as e:
                    print(f"Failed to send message to {chat_id}: {e}")

    conn.close()


def main():
    # Initialize database
    init_db()

    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Create conversation handler for adding birthdays
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_birthday, pattern="add_birthday")],
        states={
            WAITING_FOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_input)],
            WAITING_FOR_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date_input)],
        },
        fallbacks=[CallbackQueryHandler(cancel_operation, pattern="cancel")],
    )

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))

    # Start the bot
    print("🎂 Birthday Bot starting...")

    # Start the application and then set up scheduler
    async def run_bot():
        await application.initialize()
        await application.start()

        # Set up scheduler after the application is running
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            daily_countdown,
            CronTrigger(hour=8, minute=0),
            args=[application],
            id='daily_birthday_countdown'
        )
        scheduler.start()

        # Start polling
        await application.updater.start_polling()

        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("🛑 Bot stopping...")
        finally:
            scheduler.shutdown()
            await application.stop()

    # Run the bot
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()