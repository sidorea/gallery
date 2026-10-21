#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VERSION_FILE="../.version"
DOCKER_REPO="sidorea/gallery"
CONTAINER_NAME="media-playlist"
PLAYER_PORT="8083"
ORGANIZER_PORT="9083"

if [ -f "$VERSION_FILE" ]; then
    VERSION_TAG=$(tr -d '[:space:]' < "$VERSION_FILE")
else
    VERSION_TAG="v1"
fi

IMAGE_NAME="${DOCKER_REPO}:${VERSION_TAG}"

echo "Deploying unified $CONTAINER_NAME container with image $IMAGE_NAME..."
echo "  - Player URL   : http://localhost:${PLAYER_PORT}/"
echo "  - Organizer URL: http://localhost:${ORGANIZER_PORT}/"

# Stop and remove existing container
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

# Shared files directory
SHARED_FILES_DIR="$(cd "$SCRIPT_DIR/../files" 2>/dev/null && pwd || true)"

DOCKER_ARGS=(
    --name "$CONTAINER_NAME"
    --restart unless-stopped
    -d
    --entrypoint /entrypoint.sh
    -p "${PLAYER_PORT}:80"
    -p "${ORGANIZER_PORT}:9083"
)

if [ -S "/var/run/docker.sock" ]; then
    DOCKER_ARGS+=(-v "/var/run/docker.sock:/var/run/docker.sock")
fi

# Mount Docker credentials for docker push
DOCKER_CONFIG_SRC=""
if [ -f "$HOME/.docker/config.json" ]; then
    DOCKER_CONFIG_SRC="$HOME/.docker/config.json"
elif [ -f "/home/ubuntu/.docker/config.json" ]; then
    DOCKER_CONFIG_SRC="/home/ubuntu/.docker/config.json"
elif [ -f "/root/.docker/config.json" ]; then
    DOCKER_CONFIG_SRC="/root/.docker/config.json"
fi

if [ -n "$DOCKER_CONFIG_SRC" ]; then
    echo "Mounting Docker credentials: $DOCKER_CONFIG_SRC -> /root/.docker/config.json"
    DOCKER_ARGS+=(-v "${DOCKER_CONFIG_SRC}:/root/.docker/config.json:ro")
fi

if [ -d "$SHARED_FILES_DIR" ]; then
    echo "Mounting shared media folder: $SHARED_FILES_DIR -> /usr/share/nginx/html/files"
    DOCKER_ARGS+=(-v "${SHARED_FILES_DIR}:/usr/share/nginx/html/files")
fi

# Mount version file to keep host and container version truth synchronized
HOST_VERSION_FILE="$(cd "$SCRIPT_DIR/.." 2>/dev/null && pwd)/.version"
if [ -f "$HOST_VERSION_FILE" ]; then
    echo "Mounting version governance: $HOST_VERSION_FILE -> /app/.version"
    DOCKER_ARGS+=(-v "${HOST_VERSION_FILE}:/app/.version")
fi

# Mount Media-Organizer-App and Media-Playlist-App directories for live updates
HOST_ORGANIZER_DIR="$(cd "$SCRIPT_DIR/../Media-Organizer-App" 2>/dev/null && pwd || true)"
if [ -d "$HOST_ORGANIZER_DIR" ]; then
    echo "Mounting Media-Organizer-App: $HOST_ORGANIZER_DIR -> /app/Media-Organizer-App"
    DOCKER_ARGS+=(-v "${HOST_ORGANIZER_DIR}:/app/Media-Organizer-App")
fi

HOST_PLAYLIST_DIR="$(cd "$SCRIPT_DIR" 2>/dev/null && pwd || true)"
if [ -d "$HOST_PLAYLIST_DIR" ]; then
    echo "Mounting Media-Playlist-App: $HOST_PLAYLIST_DIR -> /app/Media-Playlist-App"
    DOCKER_ARGS+=(-v "${HOST_PLAYLIST_DIR}:/app/Media-Playlist-App")
fi

if [ -f "$SCRIPT_DIR/entrypoint.sh" ]; then
    echo "Mounting custom entrypoint: $SCRIPT_DIR/entrypoint.sh -> /entrypoint.sh"
    DOCKER_ARGS+=(-v "${SCRIPT_DIR}/entrypoint.sh:/entrypoint.sh")
fi

docker run "${DOCKER_ARGS[@]}" "$IMAGE_NAME"

echo "Container $CONTAINER_NAME successfully started."
echo "Player:    http://localhost:${PLAYER_PORT}/"
echo "Organizer: http://localhost:${ORGANIZER_PORT}/"
