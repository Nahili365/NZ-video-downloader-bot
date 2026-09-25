# Telegram Video Downloader

A Telegram bot that validates public links and downloads videos from Instagram, Facebook, Pinterest, X/Twitter, TikTok, Reddit, YouTube, Vimeo, and Dailymotion.

The bot rejects unsupported, private, restricted, invalid, and oversized videos. Downloaded files are stored in a temporary directory and removed automatically after Telegram receives the video.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create a bot with [@BotFather](https://t.me/BotFather), then set its token:

```powershell
$env:TELEGRAM_BOT_TOKEN = "your-token-from-botfather"
python telegram_video_downloader.py
```

Send `/start` to the bot, then send a public video URL. Telegram bots have upload limits, so videos larger than 49 MB are rejected.
