# Stage 1: build the Vue frontend
FROM node:22-alpine AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime on the Home Assistant base image
FROM ghcr.io/home-assistant/base-python:3.14-alpine3.24

ARG BUILD_ARCH
ARG BUILD_VERSION

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RENO_DATA_DIR=/data \
    RENO_STATIC_DIR=/app/static \
    RENO_VERSION=${BUILD_VERSION}

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

COPY backend/alembic.ini /app/alembic.ini
COPY backend/alembic /app/alembic
COPY backend/app /app/app
COPY --from=frontend /src/dist /app/static
COPY run.sh /run.sh
RUN chmod a+x /run.sh

LABEL \
    io.hass.type="app" \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.arch="${BUILD_ARCH}" \
    org.opencontainers.image.title="Renovation Budget" \
    org.opencontainers.image.source="https://github.com/nielssteyaert/reno-base"

CMD ["/run.sh"]
