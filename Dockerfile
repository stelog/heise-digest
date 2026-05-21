FROM python:3.12-slim

# Install cron and tzdata (for correct timezone handling)
RUN apt-get update && apt-get install -y --no-install-recommends \
        cron \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

# Default timezone – override via TZ env var in docker-compose.yml
ENV TZ=Europe/Berlin

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the scraper script
COPY heise_telegram_digest.py .

# Copy the crontab and entrypoint
COPY crontab /etc/cron.d/heise-digest
COPY entrypoint.sh /entrypoint.sh

# Cron requires specific permissions on the crontab file
RUN chmod 0644 /etc/cron.d/heise-digest \
    && crontab /etc/cron.d/heise-digest \
    && chmod +x /entrypoint.sh

# Log file for cron output
RUN touch /var/log/heise-digest.log

ENTRYPOINT ["/entrypoint.sh"]
