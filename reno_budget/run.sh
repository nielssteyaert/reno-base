#!/usr/bin/with-contenv bashio
# shellcheck shell=bash
set -e

bashio::log.info "Starting Renovation Budget..."

cd /app
# Database migrations run inside the app on startup; options are read from /data/options.json.
exec /opt/venv/bin/uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8099 \
    --no-proxy-headers \
    --no-server-header \
    --log-level warning
