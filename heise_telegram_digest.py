#!/usr/bin/env python3
"""
Heise Newsticker – Daily Telegram Digest
-----------------------------------------
Scrapes https://www.heise.de/newsticker/ and sends all articles
from the *previous* calendar day as a single Telegram message.

Setup
-----
1. Install dependencies:
       pip install requests beautifulsoup4

2. Create a Telegram bot via @BotFather and copy the token.

3. Find your chat / channel ID (send a message to the bot, then
   open https://api.telegram.org/bot<TOKEN>/getUpdates in your
   browser – look for "chat": {"id": ...}).

4. Set the two environment variables (or edit the constants below):
       export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
       export TELEGRAM_CHAT_ID="-1001234567890"

5. Schedule daily execution (example cron – runs every day at 08:00):
       0 8 * * * /usr/bin/python3 /path/to/heise_telegram_digest.py

How it works
------------
* Fetches the Heise Newsticker page and parses every article entry.
* Keeps only entries whose date stamp matches yesterday.
* Formats them as:
      <time>  <headline as clickable URL>
* Sends the result as a single Telegram message (HTML parse mode).
* If there are more than ~50 articles the message is split to stay
  below Telegram's 4 096-character limit.
"""

import os
import re
import sys
import logging
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup

# ── Configuration ────────────────────────────────────────────────────────────

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID",   "YOUR_CHAT_ID_HERE")

HEISE_URL   = "https://www.heise.de/newsticker/"
USER_AGENT  = (
    "Mozilla/5.0 (compatible; HeiseDailyDigestBot/1.0; "
    "+https://github.com/yourname/heise-digest)"
)
REQUEST_TIMEOUT = 15          # seconds
MAX_MSG_LENGTH  = 4096        # Telegram hard limit

# German weekday / month names for the header
WEEKDAYS_DE = [
    "Montag", "Dienstag", "Mittwoch", "Donnerstag",
    "Freitag", "Samstag", "Sonntag",
]

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Scraping ─────────────────────────────────────────────────────────────────

def fetch_page(url: str) -> BeautifulSoup:
    """Download *url* and return a BeautifulSoup tree."""
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def parse_articles(soup: BeautifulSoup, target_date: date) -> list[dict]:
    """
    Extract articles that were published on *target_date*.

    Returns a list of dicts with keys:
        time  – publication time string, e.g. "14:35"
        title – headline text
        url   – absolute URL to the article
    """
    articles = []

    # Heise marks each news item with <article> or a list entry that
    # contains a <time> element with a datetime attribute.
    # We look for <time datetime="YYYY-MM-DDThh:mm…"> anywhere on the page.
    for time_tag in soup.find_all("time", datetime=True):
        raw = time_tag["datetime"]          # e.g. "2026-05-19T14:35:00+02:00"
        try:
            article_date = date.fromisoformat(raw[:10])
        except ValueError:
            continue

        if article_date != target_date:
            continue

        # Extract the human-readable time (hh:mm)
        display_time = raw[11:16] if len(raw) >= 16 else time_tag.get_text(strip=True)

        # Walk up the DOM to find the enclosing article / list item
        # that contains the headline link.
        container = time_tag
        for _ in range(8):                  # max 8 levels up
            container = container.parent
            if container is None:
                break
            link = container.find("a", href=True)
            if link and link.get_text(strip=True):
                break
        else:
            link = None

        if not link:
            continue

        title = link.get_text(strip=True)
        # Remove artefacts that Heise concatenates into the link text:
        #   • leading "HH:MMUhr"  (time + "Uhr")
        #   • trailing "<number>Kommentare"
        title = re.sub(r'^\d{1,2}:\d{2}Uhr', '', title)
        title = re.sub(r'\d+Kommentare$', '', title)
        title = title.strip()
        href  = link["href"]

        # Make relative URLs absolute
        if href.startswith("/"):
            href = "https://www.heise.de" + href
        elif not href.startswith("http"):
            href = HEISE_URL + href

        articles.append({"time": display_time, "title": title, "url": href})

    # De-duplicate (same URL may appear via multiple <time> tags)
    seen = set()
    unique = []
    for a in articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)

    # Sort chronologically
    unique.sort(key=lambda a: a["time"])
    return unique


# ── Formatting ────────────────────────────────────────────────────────────────

def format_message(articles: list[dict], target_date: date) -> list[str]:
    """
    Build one or more Telegram HTML messages.

    The first message starts with a bold date header, e.g.:
        <b>Mittwoch, 20.05.2026</b>

    Each article line:
        14:35  <a href="…">Headline text</a>
    """
    weekday_de = WEEKDAYS_DE[target_date.weekday()]
    header = (
        f"<b>{weekday_de}, "
        f"{target_date.day:02d}.{target_date.month:02d}.{target_date.year}</b>"
    )

    if not articles:
        return [f"{header}\n\n<i>Keine Meldungen für diesen Tag gefunden.</i>"]

    lines = [header, ""]
    for a in articles:
        # Escape HTML special chars in the title
        safe_title = (
            a["title"]
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
        lines.append(f'{a["time"]}  <a href="{a["url"]}">{safe_title}</a>')
        lines.append("")

    # Split into chunks that fit within Telegram's limit
    messages = []
    current = ""
    for line in lines:
        candidate = (current + "\n" + line).lstrip("\n")
        if len(candidate) > MAX_MSG_LENGTH:
            if current:
                messages.append(current)
            current = line
        else:
            current = candidate
    if current:
        messages.append(current)

    return messages


# ── Telegram ──────────────────────────────────────────────────────────────────

def send_telegram(text: str, token: str, chat_id: str) -> None:
    """Send *text* to *chat_id* via the Telegram Bot API."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    result = resp.json()
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result}")
    log.info("Message sent (message_id=%s).", result["result"]["message_id"])


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        log.error(
            "Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID "
            "(environment variables or edit the constants at the top of the script)."
        )
        sys.exit(1)

    yesterday = date.today() - timedelta(days=1)
    log.info("Fetching Heise Newsticker for %s …", yesterday)

    soup     = fetch_page(HEISE_URL)
    articles = parse_articles(soup, yesterday)
    log.info("Found %d article(s).", len(articles))

    messages = format_message(articles, yesterday)
    log.info("Sending %d message chunk(s) to Telegram …", len(messages))

    for i, msg in enumerate(messages, 1):
        send_telegram(msg, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
        log.info("Chunk %d/%d sent.", i, len(messages))

    log.info("Done.")


if __name__ == "__main__":
    main()
