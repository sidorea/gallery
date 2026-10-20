#!/usr/bin/env bash
set -e

echo "=================================================="
echo " 🚀 Unified Gallery Multi-App Container Startup"
echo "=================================================="

# Ensure directories exist
mkdir -p /usr/share/nginx/html/files/thumbs/seek \
         /app/Media-Organizer-App/backups

chmod -R 777 /app/Media-Organizer-App/backups 2>/dev/null || true
chmod -R 777 /usr/share/nginx/html/files 2>/dev/null || true

# 1. Start Media Organizer App WSGI service (Gunicorn) on port 9083
echo "[INIT] Starting Media-Organizer-App (Gunicorn) on 0.0.0.0:9083..."
cd /app/Media-Organizer-App
gunicorn --bind 0.0.0.0:9083 \
         --workers 2 \
         --timeout 3600 \
         --access-logfile - \
         --error-logfile - \
         app:app &
ORGANIZER_PID=$!

# 2. Start Nginx Media Player service on port 80
echo "[INIT] Starting Nginx Media Player on port 80..."
nginx -g 'daemon off;' &
NGINX_PID=$!

echo "[INIT] Both applications successfully started."
echo "  -> Player (Nginx)   : Port 80 (PID: $NGINX_PID)"
echo "  -> Organizer Studio : Port 9083 (PID: $ORGANIZER_PID)"
echo "=================================================="

# Graceful termination handler
cleanup() {
    echo ""
    echo "[SHUTDOWN] Signal received. Terminating all container services..."
    kill -TERM "$ORGANIZER_PID" 2>/dev/null || true
    nginx -s quit 2>/dev/null || true
    wait "$ORGANIZER_PID" 2>/dev/null || true
    wait "$NGINX_PID" 2>/dev/null || true
    echo "[SHUTDOWN] Container shutdown cleanly complete."
    exit 0
}

trap cleanup SIGTERM SIGINT SIGQUIT

# Wait for either process to terminate
wait -n "$ORGANIZER_PID" "$NGINX_PID"
EXIT_CODE=$?

echo "[WARNING] A process exited unexpectedly with code $EXIT_CODE."
cleanup
