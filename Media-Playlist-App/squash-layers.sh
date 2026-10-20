#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VERSION_FILE="../.version"
DOCKER_REPO="sidorea/gallery"
CONTAINER_NAME="media-playlist"
SHARED_FILES_DIR="$(cd "$SCRIPT_DIR/../files" && pwd)"

if [ ! -f "$VERSION_FILE" ]; then
    echo "Error: Version file $VERSION_FILE not found!" >&2
    exit 1
fi

CURRENT_TAG=$(tr -d '[:space:]' < "$VERSION_FILE")
CURRENT_NUM="${CURRENT_TAG#v}"
if ! [[ "$CURRENT_NUM" =~ ^[0-9]+$ ]]; then
    CURRENT_NUM=1
fi
NEXT_NUM=$((CURRENT_NUM + 1))
NEXT_TAG="v${NEXT_NUM}"
TARGET_IMAGE="${DOCKER_REPO}:${NEXT_TAG}"

echo "=========================================="
echo " Container Layer Squashing & Consolidation"
echo "=========================================="
echo "Active Container : $CONTAINER_NAME"
echo "Current Version  : $CURRENT_TAG"
echo "New Target Tag   : $NEXT_TAG ($TARGET_IMAGE)"
echo "=========================================="

# Create safety backups
cp "$VERSION_FILE" "${VERSION_FILE}.bak"
if [ -f "Dockerfile" ]; then
    cp "Dockerfile" "Dockerfile.bak"
fi
if [ -f "run-container.sh" ]; then
    cp "run-container.sh" "run-container.sh.bak"
fi

SUCCESS=0
TEMP_EXPORT_CONTAINER="media-squash-export-${NEXT_NUM}"

cleanup() {
    local exit_code=$?
    docker rm -f "$TEMP_EXPORT_CONTAINER" 2>/dev/null || true
    if [ "$SUCCESS" -ne 1 ]; then
        echo "[ROLLBACK] Layer squashing failed or aborted! Reverting backups..." >&2
        [ -f "${VERSION_FILE}.bak" ] && mv -f "${VERSION_FILE}.bak" "$VERSION_FILE"
        [ -f "Dockerfile.bak" ] && mv -f "Dockerfile.bak" "Dockerfile"
        [ -f "run-container.sh.bak" ] && mv -f "run-container.sh.bak" "run-container.sh"
    else
        rm -f "${VERSION_FILE}.bak" "Dockerfile.bak" "run-container.sh.bak" 2>/dev/null || true
    fi
    exit "$exit_code"
}

trap cleanup EXIT INT TERM HUP

echo "[EXPORT] Preparing consolidated filesystem including all media assets..."
# Create temporary export container and populate /usr/share/nginx/html/files
docker create --name "$TEMP_EXPORT_CONTAINER" "${DOCKER_REPO}:${CURRENT_TAG}"
if [ -d "$SHARED_FILES_DIR" ]; then
    docker cp "$SHARED_FILES_DIR/." "${TEMP_EXPORT_CONTAINER}:/usr/share/nginx/html/files/"
fi

echo "[EXPORT] Streaming container filesystem and importing into 1 single layer..."
docker export "$TEMP_EXPORT_CONTAINER" | docker import \
    --change "EXPOSE 80 9083" \
    --change 'CMD ["/entrypoint.sh"]' \
    - "$TARGET_IMAGE"

docker rm -f "$TEMP_EXPORT_CONTAINER" 2>/dev/null || true

# Tag latest
docker tag "$TARGET_IMAGE" "${DOCKER_REPO}:latest"

echo "[VERIFY] Checking filesystem layer count..."
LAYER_COUNT=$(docker inspect --format '{{len .RootFS.Layers}}' "$TARGET_IMAGE" 2>/dev/null || echo 0)
echo "RootFS Layers Count: $LAYER_COUNT"

if [ "$LAYER_COUNT" -ne 1 ]; then
    echo "Error: Expected exactly 1 layer, but got $LAYER_COUNT!" >&2
    exit 1
fi

echo "[VERSION] Updating $VERSION_FILE to $NEXT_TAG..."
echo "$NEXT_TAG" > "$VERSION_FILE"

# Update Dockerfile FROM line to point to squashed base
if [ -f "Dockerfile" ]; then
    sed -i "s|^FROM .*|FROM ${TARGET_IMAGE}|g" Dockerfile
fi

# Update run-container.sh
if [ -f "run-container.sh" ]; then
    sed -i "s|${DOCKER_REPO}:v[0-9]*|${TARGET_IMAGE}|g" run-container.sh || true
fi

# Restart container with newly squashed image
"$SCRIPT_DIR/run-container.sh"

SUCCESS=1
echo "=========================================="
echo "Successfully squashed layers into $TARGET_IMAGE (1 layer)"
echo "=========================================="
