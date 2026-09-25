"""Telegram bot for downloading public videos from supported platforms."""

from __future__ import annotations

import logging
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters


BOT_TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
MAX_UPLOAD_BYTES = 49 * 1024 * 1024
SUPPORTED_HOSTS = {
    "instagram.com", "facebook.com", "fb.watch", "pinterest.com", "pin.it",
    "x.com", "twitter.com", "tiktok.com", "reddit.com", "youtube.com",
    "youtu.be", "vimeo.com", "dailymotion.com",
}
URL_PATTERN = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)


class InvalidPublicLink(ValueError):
    """Raised when a URL is not a supported public media link."""


def extract_url(text: str) -> str:
    """Return the first URL from a message."""
    match = URL_PATTERN.search(text.strip())
    if not match:
        raise InvalidPublicLink("Send a public video URL.")
    return match.group(0).rstrip(".,!?;:)")


def validate_public_url(url: str) -> str:
    """Validate URL shape and platform before yt-dlp accesses it."""
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower().removeprefix("www.")
    if parsed.scheme.lower() != "https" or parsed.username or parsed.password:
        raise InvalidPublicLink("Only public HTTPS links are supported.")
    is_supported_host = any(
        hostname == supported_host or hostname.endswith("." + supported_host)
        for supported_host in SUPPORTED_HOSTS
    )
    if not parsed.path or not is_supported_host:
        raise InvalidPublicLink(
            "That link is unsupported. Supported sites: Instagram, Facebook, Pinterest, "
            "X/Twitter, TikTok, Reddit, YouTube, Vimeo, and Dailymotion."
        )
    return url


def download_video(url: str, directory: Path) -> Path:
    """Download one video and return its path, raising for private or invalid media."""
    options = {
        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
        "outtmpl": str(directory / "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "max_filesize": MAX_UPLOAD_BYTES,
    }
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            result = downloader.extract_info(url, download=True)
            requested_downloads = result.get("requested_downloads") or []
            candidates = [
                Path(item["filepath"])
                for item in requested_downloads
                if item.get("filepath")
            ]
            candidates.extend(directory.glob("*"))
    except (yt_dlp.utils.DownloadError, KeyError) as error:
        raise InvalidPublicLink(
            "I could not access that video. It may be private, restricted, invalid, or unavailable."
        ) from error

    files = [path for path in candidates if path.is_file() and path.stat().st_size > 0]
    if not files:
        raise InvalidPublicLink("No downloadable video was found at that link.")
    video = max(files, key=lambda path: path.stat().st_mtime)
    if video.stat().st_size > MAX_UPLOAD_BYTES:
        raise InvalidPublicLink("That video is too large for Telegram (49 MB maximum).")
    return video


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Explain how to use the bot."""
    if update.message:
        await update.message.reply_text(
            "Send a public video link from Instagram, Facebook, Pinterest, X/Twitter, "
            "TikTok, Reddit, YouTube, Vimeo, or Dailymotion."
        )


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Validate, download, send, and automatically remove a video."""
    if not update.message or not update.message.text:
        return
    try:
        url = validate_public_url(extract_url(update.message.text))
    except InvalidPublicLink as error:
        await update.message.reply_text(str(error))
        return

    await update.message.chat.send_action(ChatAction.UPLOAD_VIDEO)
    status = await update.message.reply_text("Checking the link and downloading the video...")
    try:
        with tempfile.TemporaryDirectory(prefix="telegram-video-") as temporary_directory:
            video_path = download_video(url, Path(temporary_directory))
            with video_path.open("rb") as video_file:
                await update.message.reply_video(video=video_file, supports_streaming=True)
    except InvalidPublicLink as error:
        await status.edit_text(str(error))
    except Exception:
        logging.exception("Unexpected download failure")
        await status.edit_text("The download failed. Please try another public video link.")
    else:
        await status.delete()


def main() -> None:
    """Start the polling bot."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    token = os.getenv(BOT_TOKEN_ENV)
    if not token:
        raise SystemExit(f"Set {BOT_TOKEN_ENV} before starting the bot.")
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    application.run_polling()


if __name__ == "__main__":
    main()
