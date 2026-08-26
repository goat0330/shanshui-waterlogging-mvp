# syntax=docker/dockerfile:1.7

FROM python:3.11-slim-bookworm AS media
WORKDIR /src

COPY deploy /src/deploy

ARG MEDIA_BUNDLE_URL=""
ARG MEDIA_BUNDLE_SHA256=""
ARG MEDIA_BUNDLE_REQUIRED="false"

ENV MEDIA_BUNDLE_URL="${MEDIA_BUNDLE_URL}" \
    MEDIA_BUNDLE_SHA256="${MEDIA_BUNDLE_SHA256}" \
    MEDIA_BUNDLE_REQUIRED="${MEDIA_BUNDLE_REQUIRED}"

RUN mkdir -p /media \
    && python /src/deploy/download_media.py \
        --manifest /src/deploy/media-manifest.json \
        --output /media


FROM node:20-bookworm-slim AS frontend-builder
WORKDIR /src

COPY frontend/package*.json /src/frontend/
RUN cd /src/frontend \
    && if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY frontend /src/frontend
COPY data /src/data
COPY contracts /src/contracts
COPY deploy /src/deploy
COPY --from=media /media /media

ARG VITE_DATA_SOURCE="api"
ARG VITE_API_BASE_URL=""
ARG VITE_CESIUM_ION_TOKEN=""

ENV VITE_DATA_SOURCE="${VITE_DATA_SOURCE}" \
    VITE_API_BASE_URL="${VITE_API_BASE_URL}" \
    VITE_CESIUM_ION_TOKEN="${VITE_CESIUM_ION_TOKEN}"

# Rewrites only the Docker build copy when bundled same-event historical media exists.
RUN node /src/deploy/rewrite_historical_media.mjs \
    /src/data/historical-cases.json \
    /media

RUN cd /src/frontend \
    && npm run typecheck \
    && npm run build


FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    REPOSITORY_BACKEND=memory \
    DATA_MODE=hybrid \
    PORT=10000

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        nginx \
        gettext-base \
        ca-certificates \
        curl \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt /tmp/backend-requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/backend-requirements.txt

COPY backend /app/backend
COPY contracts /app/contracts
COPY data /app/data
# Use the build-copy data after historical media localization so the API
# returns the same bundled /media URLs that the frontend build expects.
COPY --from=frontend-builder /src/data/historical-cases.json /app/data/historical-cases.json
COPY vision /app/vision
COPY deploy /app/deploy

COPY --from=frontend-builder /src/frontend/dist /app/frontend-dist
COPY --from=media /media /app/media

# If a bundled current-event video exists, update only the image-local runtime
# fixture copy so the public deployment serves it from /media.
RUN python /app/deploy/rewrite_runtime_media.py \
    --repo-root /app \
    --media-root /app/media

RUN rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf \
    && chmod +x /app/deploy/start.sh \
    && mkdir -p /app/backend/.runtime/vision-depth

EXPOSE 10000

CMD ["bash", "/app/deploy/start.sh"]
