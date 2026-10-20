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
    -p "${PLAYER_PORT}:80"
    -p "${ORGANIZER_PORT}:9083"
)

if [ -S "/var/run/docker.sock" ]; then
    DOCKER_ARGS+=(-v "/var/run/docker.sock:/var/run/docker.sock")
fi

if [ -d "$SHARED_FILES_DIR" ]; then
    echo "Mounting shared media folder: $SHARED_FILES_DIR -> /usr/share/nginx/html/files"
    DOCKER_ARGS+=(-v "${SHARED_FILES_DIR}:/usr/share/nginx/html/files")
fi

docker run "${DOCKER_ARGS[@]}" "$IMAGE_NAME"

echo "Container $CONTAINER_NAME successfully started."
echo "Player:    http://localhost:${PLAYER_PORT}/"
echo "Organizer: http://localhost:${ORGANIZER_PORT}/"
