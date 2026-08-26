#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-10000}"
export PORT

if [[ -z "${VISION_WATER_SEGMENTATION_CHECKPOINT:-}" ]] \
   && [[ -f /app/media/models/candidate-water-segmentation.joblib ]]; then
  export VISION_WATER_SEGMENTATION_CHECKPOINT=/app/media/models/candidate-water-segmentation.joblib
fi

envsubst '${PORT}' \
  < /app/deploy/nginx.conf.template \
  > /etc/nginx/conf.d/default.conf

python -m uvicorn backend.app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --proxy-headers \
  --forwarded-allow-ips='*' &
BACKEND_PID=$!

cleanup() {
  kill -TERM "${BACKEND_PID}" 2>/dev/null || true
  nginx -s quit 2>/dev/null || true
  wait "${BACKEND_PID}" 2>/dev/null || true
}
trap cleanup TERM INT EXIT

# Do not accept public traffic before the application has at least booted.
for _ in $(seq 1 40); do
  if curl -fsS --max-time 2 \
      http://127.0.0.1:8000/api/v1/dashboard/overview >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "${BACKEND_PID}" 2>/dev/null; then
    echo "FastAPI exited before readiness" >&2
    wait "${BACKEND_PID}"
    exit 1
  fi
  sleep 0.5
done

nginx -t
nginx -g 'daemon off;' &
NGINX_PID=$!

set +e
wait -n "${BACKEND_PID}" "${NGINX_PID}"
STATUS=$?
set -e

kill -TERM "${BACKEND_PID}" "${NGINX_PID}" 2>/dev/null || true
wait "${BACKEND_PID}" 2>/dev/null || true
wait "${NGINX_PID}" 2>/dev/null || true
trap - TERM INT EXIT

exit "${STATUS}"
