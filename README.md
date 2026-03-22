# Automated-NASDAQ-VSA-Trading-Bot
Built a Python script to trade NASDAQ small-cap stocks using Volume Spread Analysis (VSA). The script can be run manually at anytime for the bot to monitor and trade however youe device must be online for it to function.

If you prefer a cloud hosted service than can run the bot in the background 24/7 then you can host the script through Oracle cloude.

Server Deployment: Hosted on an Oracle Cloud Ubuntu VPS for 24/7 uptime

Remote Access: Connection established via SSH using a private .key file for security.

Environment Setup:

Update system packages using sudo dnf update.

Create a Python Virtual Environment to isolate trading libraries.

Install dependencies: pip install -r requirements.txt.

Session Management: Utilises tmux to maintain the trading session during NASDAQ hours (09:00–13:30 UK) even after disconnecting from the server.

Security: API credentials are managed via a local .env file (excluded from GitHub via .gitignore).
