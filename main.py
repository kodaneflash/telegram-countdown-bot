import os
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ChatMemberStatus

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration constants
DEBUG_MODE = False  # Changed to False for production (1-hour updates)
UPDATE_INTERVAL = 60 if DEBUG_MODE else 3600  # 60 seconds (1 min) in debug, 3600 (1 hour) in production

# Store countdown data (in production, consider using a database)
countdown_data = {}

def format_time_delta(time_delta: timedelta) -> str:
    """Format timedelta into human readable string with days, hours, minutes."""
    total_seconds = int(time_delta.total_seconds())
    days, remainder = divmod(total_seconds, 86400)  # 86400 seconds in a day
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if not parts:  # If less than a minute remaining
        parts.append("less than a minute")
    return ", ".join(parts)

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
    """Set a countdown timer for AgentAxis token launch (admin only)."""
    if not await check_admin(update):
        await update.message.reply_text(
            "⚠️ Only administrators can set the launch countdown!\n"
            "Use /countdown to check the remaining time."
        )
        return

    try:
        datetime_str = ' '.join(context.args)
        
        try:
            target_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
        except ValueError:
            await update.message.reply_text(
                "Invalid date/time format!\n"
                "Please use: /setcountdown YYYY-MM-DD HH:MM\n"
                "Example: /setcountdown 2024-12-31 23:59"
            )
            return

        est_tz = ZoneInfo('US/Eastern')
        current_time = datetime.now(est_tz)
        target_datetime = target_datetime.replace(tzinfo=est_tz)

        if target_datetime <= current_time:
            await update.message.reply_text("Please set a future launch date and time!")
            return

        chat_id = update.effective_chat.id
        
        # Remove existing countdown job if any
        if chat_id in countdown_data and 'job' in countdown_data[chat_id]:
            countdown_data[chat_id]['job'].schedule_removal()

        # Store countdown data
        countdown_data[chat_id] = {
            'end_time': target_datetime,
            'set_by': update.effective_user.id
        }

        # Schedule updates
        job = context.job_queue.run_repeating(
            send_countdown_update,
            interval=UPDATE_INTERVAL,
            first=0,
            chat_id=chat_id,
            name=f"countdown_{chat_id}",
            data=target_datetime
        )
        
        countdown_data[chat_id]['job'] = job

        time_remaining = target_datetime - current_time
        formatted_time = format_time_delta(time_remaining)

        update_interval_text = "minute" if DEBUG_MODE else "hour"
        await update.message.reply_text(
            f"✅ AgentAxis Solana Token Launch Countdown Set! 🚀\n\n"
            f"🗓 Launch Date: {target_datetime.strftime('%Y-%m-%d %H:%M %Z')}\n"
            f"⏰ Time until launch: {formatted_time}\n\n"
            f"Updates will be sent every {update_interval_text}\n"
            f"Stay tuned!\n\n"
            f"Use /countdown anytime to check remaining time!"
        )

    except Exception as e:
        logger.error(f"Error setting countdown: {e}")
        await update.message.reply_text(
            "Error setting launch countdown!\n"
            "Please use: /setcountdown YYYY-MM-DD HH:MM\n"
            "Example: /setcountdown 2024-12-31 23:59"
        )

async def get_countdown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check remaining time until token launch."""
    chat_id = update.effective_chat.id
    
    if chat_id not in countdown_data:
        await update.message.reply_text(
            "No launch countdown is currently set! ⏰\n"
            "Stay tuned for the upcoming AgentAxis token launch! 🚀"
        )
        return

    est_tz = ZoneInfo('US/Eastern')
    current_time = datetime.now(est_tz)
    end_time = countdown_data[chat_id]['end_time']
    
    time_remaining = end_time - current_time
    seconds_remaining = time_remaining.total_seconds()

    if seconds_remaining <= 0:
        await update.message.reply_text(
            "🎉 AgentAxis Solana Token is LIVE! 🚀\n\n"
            "The wait is over! Join the action now! 🔥\n"
            f"Launch time: {end_time.strftime('%Y-%m-%d %H:%M %Z')}"
        )
        # Clean up countdown data
        if 'job' in countdown_data[chat_id]:
            countdown_data[chat_id]['job'].schedule_removal()
        del countdown_data[chat_id]
        return

    formatted_time = format_time_delta(time_remaining)
    
    if seconds_remaining <= 300:  # Last 5 minutes
        message = (
            "🚨 FINAL COUNTDOWN - LAUNCH IMMINENT! 🚨\n\n"
            f"AgentAxis Token Launch in: {formatted_time}\n"
            "Get ready! 🚀🔥\n\n"
            f"Launch time: {end_time.strftime('%Y-%m-%d %H:%M %Z')}"
        )
    else:
        message = (
            "⏳ AgentAxis Token Launch Countdown\n\n"
            f"Time until launch: {formatted_time}\n"
            f"Launch time: {end_time.strftime('%Y-%m-%d %H:%M %Z')}\n\n"
            "Stay tuned!"
        )

    await update.message.reply_text(message)

async def send_countdown_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send automated countdown updates."""
    job = context.job
    chat_id = job.chat_id
    target_time = job.data

    est_tz = ZoneInfo('US/Eastern')
    current_time = datetime.now(est_tz)
    
    time_remaining = target_time - current_time
    seconds_remaining = time_remaining.total_seconds()

    if seconds_remaining <= 0:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "🎉 AgentAxis Solana Token is LIVE! 🚀🔥\n\n"
                "The wait is over! Join the action now!\n"
                f"Launch time: {target_time.strftime('%Y-%m-%d %H:%M %Z')}"
            )
        )
        # Clean up countdown data
        if chat_id in countdown_data:
            if 'job' in countdown_data[chat_id]:
                countdown_data[chat_id]['job'].schedule_removal()
            del countdown_data[chat_id]
        return

    # If less than 2 minutes remaining, send more frequent updates
    if seconds_remaining <= 120 and DEBUG_MODE:
        next_interval = 10  # Update every 10 seconds for last 2 minutes
        job.interval = next_interval
    
    formatted_time = format_time_delta(time_remaining)

    if seconds_remaining <= 300:  # Last 5 minutes
        message = (
            "🚨 FINAL COUNTDOWN - LAUNCH IMMINENT! 🚨\n\n"
            f"⏰ AgentAxis Token Launch in: {formatted_time}\n"
            "Get ready for liftoff! 🚀\n"
            f"Launch time: {target_time.strftime('%Y-%m-%d %H:%M %Z')}"
        )
    else:
        message = (
            "⏳ AgentAxis Token Launch Incoming! 🚀\n\n"
            f"Only {formatted_time} left until liftoff! 💎\n"
            f"Launch time: {target_time.strftime('%Y-%m-%d %H:%M %Z')}"
        )

    await context.bot.send_message(
        chat_id=chat_id,
        text=message
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
