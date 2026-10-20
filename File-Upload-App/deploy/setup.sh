#!/usr/bin/env bash
set -eo pipefail

echo "=== Deploying File-Upload-App (Port 80 / 5000) on Ubuntu 26.04 LTS ==="

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_SRC_DIR="${REPO_DIR}/File-Upload-App"
TARGET_DIR="/var/www/file-drop"

# 1. Install prerequisites
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv nginx rsync

# 2. Setup target directories
sudo mkdir -p "$TARGET_DIR" "/var/www"
sudo chown -R ubuntu:ubuntu "$TARGET_DIR" "/var/www"

# 3. Synchronize application source
rsync -av --exclude 'venv' --exclude '__pycache__' "${APP_SRC_DIR}/" "${TARGET_DIR}/"

# 4. Link monorepo dependencies into /var/www for relative path resolution
ln -sfn "${REPO_DIR}/files" "/var/www/files"
ln -sfn "${REPO_DIR}/Media-Playlist-App" "/var/www/Media-Playlist-App"
ln -sfn "${REPO_DIR}/.version" "/var/www/.version"

# 5. Create isolated Python 3 virtual environment (PEP 668 compliant)
if [ ! -d "${TARGET_DIR}/venv" ]; then
    python3 -m venv "${TARGET_DIR}/venv"
fi
"${TARGET_DIR}/venv/bin/pip" install --upgrade pip
"${TARGET_DIR}/venv/bin/pip" install -r "${TARGET_DIR}/requirements.txt"

# 6. Configure Systemd Service
sudo cp "${APP_SRC_DIR}/deploy/file-drop.service" /etc/systemd/system/file-drop.service
sudo systemctl daemon-reload
sudo systemctl enable file-drop
sudo systemctl restart file-drop

# 7. Configure Nginx Reverse Proxy (Port 80)
sudo cp "${APP_SRC_DIR}/deploy/nginx.conf" /etc/nginx/sites-available/file-drop
sudo ln -sfn /etc/nginx/sites-available/file-drop /etc/nginx/sites-enabled/file-drop
sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

sudo nginx -t
sudo systemctl restart nginx

echo "=== File-Upload-App deployment successful! ==="
echo "Access portal at: http://$(curl -s http://checkip.amazonaws.com 2>/dev/null || hostname -I | awk '{print $1}')/"
