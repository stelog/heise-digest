#!/bin/bash
set -e

# Cron runs in a minimal environment and does not inherit Docker env vars.
# We export them to /etc/environment so the crontab can source them.
echo "TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}" >> /etc/environment
echo "TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}"     >> /etc/environment
echo "TZ=${TZ}"                                 >> /etc/environment

echo "[entrypoint] Timezone  : ${TZ}"
echo "[entrypoint] Chat ID   : ${TELEGRAM_CHAT_ID}"
echo "[entrypoint] Cron job  : daily at 05:00 ${TZ}"
echo "[entrypoint] Starting cron daemon …"

# Start cron in the foreground so Docker keeps the container alive
exec cron -f
