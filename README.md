# Token Launch Countdown Bot

A Telegram bot that manages countdown timers for token launches, operating in Eastern Standard Time (EST). The bot provides admin controls for setting countdowns and allows all users to check the remaining time until launch.

## Features

- **EST Timezone Support**: All times are handled in Eastern Standard Time
- **Admin Controls**: Only group administrators can set countdowns
- **Hourly Updates**: Automatic status messages about remaining time
- **Launch Announcements**: Special messages for launch time
- **User-Friendly**: Any user can check the countdown status

## Commands

- `/setcountdown YYYY-MM-DD HH:MM` - Set launch time (admin only)
  - Example: `/setcountdown 2024-12-31 14:30`
- `/countdown` - Check remaining time (all users)

## Setup

1. **Prerequisites**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment Variables**
   Create a `.env` file:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```

3. **Local Development**
   ```bash
   python main.py
   ```

## Deployment to Heroku

1. **Install Heroku CLI**
   ```bash
   brew install heroku    # On macOS
   heroku login
   ```

2. **Create Heroku App**
   ```bash
   heroku create your-app-name
   ```

3. **Configure Environment**
   ```bash
   heroku config:set TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```

4. **Deploy**
   ```bash
   git push heroku main
   ```

5. **Start Worker**
   ```bash
   heroku ps:scale worker=1
   ```

## Message Types

- **Setup Confirmation**
  ```
  ✅ Token Launch Countdown Set! 🚀
  Launch Date: [DATE] [TIME] EST
  ```

- **Regular Updates**
  ```
  ⏳ Token Launch Incoming! 🚀
  Only [TIME] left until liftoff!
  ```

- **Launch Announcement**
  ```
  🎉 Token is LIVE! 🚀
  The wait is over! Join the action now!
  ```

## Technical Details

- Built with `python-telegram-bot` v20+
- Uses `APScheduler` for job scheduling
- Implements timezone handling with `zoneinfo`
- Supports Heroku deployment with worker dyno

## Requirements

- Python 3.9+
- python-telegram-bot>=20.0
- python-dotenv
- pytz
- APScheduler>=3.6.3

## Development

To run in debug mode (1-minute updates):
1. Set `DEBUG_MODE = True` in main.py
2. Restart the bot

For production (1-hour updates):
1. Set `DEBUG_MODE = False` in main.py
2. Restart the bot

## Monitoring

Check Heroku logs: