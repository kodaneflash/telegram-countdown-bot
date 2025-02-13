import os
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ChatMemberStatus

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store countdown data (in production, consider using a database)
countdown_data = {}

def format_time_delta(time_delta: timedelta) -> str:
    """Format timedelta into human readable string."""
    total_seconds = int(time_delta.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    return ", ".join(parts) if parts else "0 seconds"

async def check_admin(update: Update) -> bool:
    """Check if the user is an admin in the group."""
    user = update.effective_user
    chat = update.effective_chat
    
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("This command can only be used in groups!")
        return False
    
    member = await chat.get_member(user.id)
    return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]

async def set_countdown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set a countdown timer (admin only)."""
    if not await check_admin(update):
        await update.message.reply_text("Only administrators can set the countdown!")
        return

    try:
        hours = float(context.args[0])
        if hours <= 0:
            await update.message.reply_text("Please provide a positive number of hours!")
            return

        current_time = datetime.now(ZoneInfo('US/Eastern'))
        end_time = current_time + timedelta(hours=hours)

        chat_id = update.effective_chat.id
        countdown_data[chat_id] = {
            'end_time': end_time,
            'total_hours': hours
        }

        await update.message.reply_text(
            f"Countdown timer set for {hours} hours!\n"
            f"The countdown will end at {end_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
        )

        # Schedule hourly updates
        job_name = f"countdown_{chat_id}"
        context.job_queue.run_repeating(
            send_countdown_update,
            interval=3600,  # 1 hour in seconds
            first=0,  # Start immediately
            chat_id=chat_id,
            name=job_name,
            data=end_time
        )

    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /setcountdown <hours>")

async def get_countdown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check remaining time in the countdown."""
    chat_id = update.effective_chat.id
    
    if chat_id not in countdown_data:
        await update.message.reply_text("No countdown is currently set!")
        return

    current_time = datetime.now(ZoneInfo('US/Eastern'))
    end_time = countdown_data[chat_id]['end_time']
    
    if current_time >= end_time:
        await update.message.reply_text("Countdown has ended!")
        del countdown_data[chat_id]
        return

    time_left = end_time - current_time
    formatted_time_left = format_time_delta(time_left)

    await update.message.reply_text(
        f"Time remaining: {formatted_time_left}\n"
        f"Countdown will end at: {end_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
    )

async def send_countdown_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send automated countdown updates."""
    job = context.job
    chat_id = job.chat_id
    end_time = job.data

    current_time = datetime.now(ZoneInfo('US/Eastern'))
    
    if current_time >= end_time:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Countdown has ended!"
        )
        del countdown_data[chat_id]
        job.schedule_removal()
        return

    time_left = end_time - current_time
    formatted_time_left = format_time_delta(time_left)

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"⏰ Countdown Update ⏰\n"
             f"Time remaining: {formatted_time_left}\n"
             f"Countdown will end at: {end_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors."""
    logger.error(f"Update {update} caused error {context.error}")

def main() -> None:
    """Start the bot."""
    # Get token from environment variable
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("No token provided!")
        return

    # Create application
    application = Application.builder().token(token).build()

    # Add command handlers
    application.add_handler(CommandHandler("setcountdown", set_countdown))
    application.add_handler(CommandHandler("countdown", get_countdown))

    # Add error handler
    application.add_error_handler(error_handler)

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
