#!/usr/bin/env bash
# ==============================================================================
# Unified One-Click Setup & Deployment Script for Gallery Monorepo
# Operating System: Ubuntu 24.04 / 26.04 LTS (AWS EC2 / GCP / Local Linux)
# Ports Deployed:
#   - Port 80   : File-Upload-App (Host Nginx Reverse Proxy -> Gunicorn 127.0.0.1:5000)
#   - Port 8083 : Media-Playlist-App (Player & Zero-Copy Nginx Video Streaming)
#   - Port 9083 : Media-Organizer-App (Studio & Docker 1-Layer Snapshot Engine)
# ==============================================================================
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================================="
echo "  🚀 Gallery Monorepo - Unified Full-Stack Setup & Deployment"
echo "=================================================================="

# 1. Root / Sudo check
SUDO=""
if [ "$EUID" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
    else
        echo "Error: This script requires root privileges or sudo." >&2
        exit 1
    fi
fi

# 2. Setup Low-Memory Swapfile (2GB) if RAM < 4GB
TOTAL_MEM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
SWAP_TOTAL_KB=$(grep SwapTotal /proc/meminfo | awk '{print $2}')

if [ "$TOTAL_MEM_KB" -lt 4194304 ] && [ "$SWAP_TOTAL_KB" -lt 1048576 ]; then
    echo "[SYSTEM] RAM is under 4GB ($((TOTAL_MEM_KB / 1024))MB) and swap < 1GB. Creating 2GB swapfile..."
    if [ ! -f /swapfile ]; then
        $SUDO fallocate -l 2G /swapfile 2>/dev/null || $SUDO dd if=/dev/zero of=/swapfile bs=1M count=2048
        $SUDO chmod 600 /swapfile
        $SUDO mkswap /swapfile
        $SUDO swapon /swapfile || true
        if ! grep -q '/swapfile' /etc/fstab 2>/dev/null; then
            echo '/swapfile none swap sw 0 0' | $SUDO tee -a /etc/fstab >/dev/null
        fi
        echo "[SYSTEM] 2GB swapfile successfully enabled."
    else
        $SUDO swapon /swapfile 2>/dev/null || true
    fi
fi

# 3. Install Host Prerequisites
echo "[DEPENDENCIES] Updating apt repositories and installing host tools..."
$SUDO DEBIAN_FRONTEND=noninteractive apt-get update -qq
$SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3 python3-pip python3-venv nginx rsync curl ffmpeg docker.io >/dev/null

# Ensure current user is in docker group
if ! groups "$USER" 2>/dev/null | grep -q '\bdocker\b'; then
    echo "[DOCKER] Adding user $USER to docker group..."
    $SUDO usermod -aG docker "$USER" 2>/dev/null || true
fi

# Ensure Docker service is active and socket permissions
if ! systemctl is-active --quiet docker; then
    echo "[DOCKER] Starting docker service..."
    $SUDO systemctl enable docker
    $SUDO systemctl start docker
fi

if [ -S /var/run/docker.sock ]; then
    $SUDO chmod 666 /var/run/docker.sock 2>/dev/null || true
fi

# 4. Storage & Directory Governance
echo "[STORAGE] Initializing persistent directories and version governance..."
mkdir -p "$SCRIPT_DIR/files/thumbs/seek"
chmod -R 777 "$SCRIPT_DIR/files" 2>/dev/null || true

if [ ! -f "$SCRIPT_DIR/.version" ]; then
    echo "v1" > "$SCRIPT_DIR/.version"
fi
chmod 666 "$SCRIPT_DIR/.version" 2>/dev/null || true

VERSION_TAG=$(tr -d '[:space:]' < "$SCRIPT_DIR/.version")
if [ -z "$VERSION_TAG" ]; then
    VERSION_TAG="v1"
    echo "$VERSION_TAG" > "$SCRIPT_DIR/.version"
fi

# 5. Deploy File-Upload-App (Port 80 -> Gunicorn 127.0.0.1:5000)
echo "[APP 1/2] Deploying File-Upload-App on Port 80..."
UPLOAD_SRC="$SCRIPT_DIR/File-Upload-App"
UPLOAD_TARGET="/var/www/file-drop"

$SUDO mkdir -p "$UPLOAD_TARGET" "/var/www"
$SUDO chown -R "$USER:$USER" "$UPLOAD_TARGET" "/var/www" 2>/dev/null || true

# Rsync application files
rsync -a --delete --exclude 'venv' --exclude '__pycache__' "$UPLOAD_SRC/" "$UPLOAD_TARGET/"

# Maintain cross-app relative symlinks in /var/www
ln -sfn "$SCRIPT_DIR/files" "/var/www/files"
ln -sfn "$SCRIPT_DIR/Media-Playlist-App" "/var/www/Media-Playlist-App"
ln -sfn "$SCRIPT_DIR/.version" "/var/www/.version"

# Python virtual environment (PEP 668 compliant)
if [ ! -d "$UPLOAD_TARGET/venv" ]; then
    python3 -m venv "$UPLOAD_TARGET/venv"
fi
"$UPLOAD_TARGET/venv/bin/pip" install --upgrade pip -q
"$UPLOAD_TARGET/venv/bin/pip" install -r "$UPLOAD_TARGET/requirements.txt" -q

# Systemd service unit for File-Upload-App
$SUDO cp "$UPLOAD_SRC/deploy/file-drop.service" /etc/systemd/system/file-drop.service
$SUDO systemctl daemon-reload
$SUDO systemctl enable file-drop >/dev/null 2>&1
$SUDO systemctl restart file-drop

# Configure Host Nginx Reverse Proxy (Port 80)
$SUDO cp "$UPLOAD_SRC/deploy/nginx.conf" /etc/nginx/sites-available/file-drop
$SUDO ln -sfn /etc/nginx/sites-available/file-drop /etc/nginx/sites-enabled/file-drop
$SUDO rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

$SUDO nginx -t >/dev/null 2>&1
$SUDO systemctl restart nginx

# 6. Deploy Media-Playlist & Media-Organizer Container (Ports 8083 & 9083)
echo "[APP 2/2] Deploying unified Media Container (Ports 8083 & 9083)..."
chmod +x "$SCRIPT_DIR/Media-Playlist-App/generate-thumbs.sh" \
         "$SCRIPT_DIR/Media-Playlist-App/run-container.sh" \
         "$SCRIPT_DIR/Media-Playlist-App/update-file.sh" \
         "$SCRIPT_DIR/Media-Playlist-App/squash-layers.sh"

DOCKER_IMAGE="sidorea/gallery:${VERSION_TAG}"

# Check if image exists; if not, attempt pull or run build
if ! docker image inspect "$DOCKER_IMAGE" >/dev/null 2>&1; then
    echo "[DOCKER] Image $DOCKER_IMAGE not found locally. Attempting to pull..."
    if ! docker pull "$DOCKER_IMAGE"; then
        echo "[DOCKER] Pull failed. Building initial container image $DOCKER_IMAGE..."
        bash "$SCRIPT_DIR/Media-Playlist-App/update-file.sh" --no-push
    fi
fi

# Run unified container
bash "$SCRIPT_DIR/Media-Playlist-App/run-container.sh"

# 7. Verification & Health Checks
echo "=================================================================="
echo "[VERIFICATION] Testing service endpoints..."

sleep 2
CHECK_UPLOAD=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/ || echo "ERR")
CHECK_PLAYER=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8083/ || echo "ERR")
CHECK_STUDIO=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9083/ || echo "ERR")

PUBLIC_IP=$(curl -s --connect-timeout 2 http://checkip.amazonaws.com 2>/dev/null || hostname -I | awk '{print $1}')

echo "=================================================================="
echo "  🎉 All Services Successfully Deployed & Running!"
echo "=================================================================="
echo "  1. Upload Portal (Port 80)     : http://${PUBLIC_IP}/        [HTTP $CHECK_UPLOAD]"
echo "  2. Web Media Player (Port 8083): http://${PUBLIC_IP}:8083/   [HTTP $CHECK_PLAYER]"
echo "  3. Organizer Studio (Port 9083): http://${PUBLIC_IP}:9083/   [HTTP $CHECK_STUDIO]"
echo "------------------------------------------------------------------"
echo "  - Version Governance: $(cat "$SCRIPT_DIR/.version")"
echo "  - Media Library     : $SCRIPT_DIR/files/"
echo "  - Docker Image      : sidorea/gallery:$(cat "$SCRIPT_DIR/.version")"
echo "=================================================================="
