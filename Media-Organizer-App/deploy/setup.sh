#!/usr/bin/env bash
set -eo pipefail

echo "=== Deploying Media-Organizer-App (Port 9083) on Ubuntu 26.04 LTS ==="

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_SRC_DIR="${REPO_DIR}/Media-Organizer-App"
TARGET_DIR="/var/www/media-organizer"

# 1. Install prerequisites
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv rsync

# 2. Setup target directories
sudo mkdir -p "$TARGET_DIR" "/var/www"
sudo chown -R ubuntu:ubuntu "$TARGET_DIR" "/var/www"

# 3. Synchronize application source
rsync -av --exclude 'venv' --exclude '__pycache__' --exclude 'backups/*.json' "${APP_SRC_DIR}/" "${TARGET_DIR}/"

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
sudo cp "${APP_SRC_DIR}/deploy/media-organizer.service" /etc/systemd/system/media-organizer.service
sudo systemctl daemon-reload
sudo systemctl enable media-organizer
sudo systemctl restart media-organizer

echo "=== Media-Organizer-App deployment successful! ==="
echo "Access studio at: http://$(curl -s http://checkip.amazonaws.com 2>/dev/null || hostname -I | awk '{print $1}'):9083/"
