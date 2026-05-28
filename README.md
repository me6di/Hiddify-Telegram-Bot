<p align="center">
  <a href="https://github.com/YOUR_GITHUB_USERNAME/Hiddify-Telegram-Bot" target="_blank" rel="noopener noreferrer">
    <img width="200" height="200" src="https://github.com/YOUR_GITHUB_USERNAME/Hiddify-Telegram-Bot/blob/main/Screenshots/icon.png?raw=True" alt="Hidy Bot">
  </a>
</p>

<p align="center">
  <a href="./README.md">English</a> |
  <a href="./README-FA.md">فارسی</a>
</p>

<h1 align="center">Hidy Bot (Custom Edition)</h1>

Hidy Bot is a Telegram bot that allows you to manage your Hiddify panel, build your store, and manage users directly from Telegram. This custom fork includes improvements for modern Linux distributions and separated Subscription/Admin URLs.

## Features

- [x] Multi panel support
- [x] Sell config
- [x] Add users / Remove users / Edit user details
- [x] View users list & Search users (by name, configuration, UUID)
- [x] Show user information (name, traffic, date, etc.)
- [x] **[NEW]** Display user configs with instant QR Code & custom `#name`
- [x] Get a backup of your panel + Auto send
- [x] View server status (RAM, CPU, disk)
- [x] Multi language (English, Persian)
- [x] Client bot
- [x] **[NEW]** Separated Admin API URL and User Subscription URL
- [x] and more...

## Installation

To install the bot, run the following command:

```bash
sudo bash -c "$(curl -Lfo- [https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/Hiddify-Telegram-Bot/main/install.sh](https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/Hiddify-Telegram-Bot/main/install.sh))"

Make sure you have the following information ready before running the installation:

Admin Telegram Number ID : Get it from User info bot (Example: 123456789)

Admin Telegram Bot Token : Get it from BotFather (Example: 1234567890:ABCdEfGhIjKlMnOpQrStUvWxYz)

Client Telegram Bot Token : Get it from BotFather (Example: 1234567890:ABCdEfGhIjKlMnOpQrStUvWxYz)

Admin Panel URL : The URL of your Hiddify panel for API connection (Example: https://panel.example.com/7frgemkvtE0/ADMIN_UUID)

Subscription Base URL : The base URL given to users for their configs (Example: https://sub.example.com/7frgemkvtE0/)

Bot Language : Options are en and fa [default is fa]

Now you can use the bot in Telegram by sending the /start command.

Commands
Update bot
Bash
cd /opt/Hiddify-Telegram-Bot/ && curl -fsSL -o /opt/Hiddify-Telegram-Bot/update.sh [https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/Hiddify-Telegram-Bot/main/update.sh](https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/Hiddify-Telegram-Bot/main/update.sh) && chmod +x /opt/Hiddify-Telegram-Bot/update.sh && bash /opt/Hiddify-Telegram-Bot/update.sh
Restart bot
Bash
cd /opt/Hiddify-Telegram-Bot/ && chmod +x restart.sh && ./restart.sh
Stop bot
Bash
pkill -9 -f hiddifyTelegramBot.py
Get bot logs
Bash
cat /opt/Hiddify-Telegram-Bot/Logs/hidyBot.log
Edit bot configs
Bash
cd /opt/Hiddify-Telegram-Bot/ && python3 config.py && chmod +x restart.sh && ./restart.sh
Reinstall bot
Bash
cd /opt/ && rm -rf /opt/Hiddify-Telegram-Bot/ && sudo bash -c "$(curl -Lfo- [https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/Hiddify-Telegram-Bot/main/install.sh](https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/Hiddify-Telegram-Bot/main/install.sh))"
Uninstall bot
Bash
cd /opt/Hiddify-Telegram-Bot/ && chmod +x uninstall.sh && ./uninstall.sh
```
