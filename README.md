# Heise Newsticker – Daily Telegram Digest (Docker)

Runs a cron job at **05:00** every morning that scrapes yesterday's
news from [heise.de/newsticker](https://www.heise.de/newsticker/) and
sends them as a formatted Telegram message.

## Prerequisites

- Docker + Docker Compose installed on your server / NAS / Raspberry Pi
- A Telegram bot token (see below)

---

## 1 – Create a Telegram bot

1. Open Telegram and message **@BotFather**
2. Send `/newbot`, follow the prompts, copy the **token**
3. Find your **chat ID**:
   - Send any message to your new bot
   - Open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser
   - Look for `"chat": {"id": <number>}`
   - For a channel, add the bot as admin and use the channel's ID (starts with `-100…`)

---

## 2 – Configure credentials

```bash
cp .env.example .env
# Edit .env and fill in your token and chat ID
nano .env
```

---

## 3 – Build and start

```bash
docker compose up -d --build
```

The container starts immediately, but the first message arrives the
next morning at 05:00 (in the configured timezone).

---

## Useful commands

| Command | What it does |
|---|---|
| `docker compose up -d --build` | Build image and start in background |
| `docker compose down` | Stop and remove the container |
| `docker compose logs -f` | Follow container logs |
| `docker exec heise-digest tail -f /var/log/heise-digest.log` | Follow cron job output |
| `docker exec heise-digest python /app/heise_telegram_digest.py` | Run the script manually right now |

---

## Timezone

The cron schedule uses the `TZ` environment variable in
`docker-compose.yml` (default: `Europe/Berlin`).
Change it to your local timezone if needed – full list at
<https://en.wikipedia.org/wiki/List_of_tz_database_time_zones>.

---

## File structure

```
.
├── Dockerfile
├── docker-compose.yml
├── .env.example            ← copy to .env and fill in credentials
├── crontab                 ← 05:00 daily schedule
├── entrypoint.sh           ← passes env vars to cron, starts crond
├── requirements.txt
└── heise_telegram_digest.py
```

\---

Erstellt mit Claude
