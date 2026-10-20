#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VERSION_FILE="../.version"
DOCKER_REPO="sidorea/gallery"

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
BASE_IMAGE="${DOCKER_REPO}:${CURRENT_TAG}"
FULL_IMAGE_NAME="${DOCKER_REPO}:${NEXT_TAG}"

# Push to Docker Hub by default unless --no-push or NO_PUSH=1 is specified
PUSH_TO_HUB=true
for arg in "$@"; do
    case "$arg" in
        --no-push)
            PUSH_TO_HUB=false
            ;;
        --push)
            PUSH_TO_HUB=true
            ;;
    esac
done

if [ "${NO_PUSH:-0}" = "1" ]; then
    PUSH_TO_HUB=false
fi

echo "=========================================="
echo " Modern Docker Buildx Incremental Updater"
echo "=========================================="
echo "Current Version: $CURRENT_TAG"
echo "Target  Version: $NEXT_TAG"
echo "Target  Image  : $FULL_IMAGE_NAME"
echo "Base Cache From: $BASE_IMAGE"
echo "Push to Hub    : $PUSH_TO_HUB"
echo "=========================================="

# Create backups for safety rollback
cp "$VERSION_FILE" "${VERSION_FILE}.bak"
if [ -f "Dockerfile" ]; then
    cp "Dockerfile" "Dockerfile.bak"
fi
if [ -f "run-container.sh" ]; then
    cp "run-container.sh" "run-container.sh.bak"
fi

BUILD_SUCCESS=0

cleanup() {
    local exit_code=$?
    if [ "$BUILD_SUCCESS" -ne 1 ]; then
        echo "[ROLLBACK] Build failed or aborted! Reverting safety backups..." >&2
        if [ -f "${VERSION_FILE}.bak" ]; then
            mv -f "${VERSION_FILE}.bak" "$VERSION_FILE"
        fi
        if [ -f "Dockerfile.bak" ]; then
            mv -f "Dockerfile.bak" "Dockerfile"
        fi
        if [ -f "run-container.sh.bak" ]; then
            mv -f "run-container.sh.bak" "run-container.sh"
        fi
        echo "[ROLLBACK] Revert complete." >&2
    else
        # Remove backup files on success
        rm -f "${VERSION_FILE}.bak" "Dockerfile.bak" "run-container.sh.bak" 2>/dev/null || true
    fi
    exit "$exit_code"
}

trap cleanup EXIT INT TERM HUP

# Ensure generate-thumbs is executable
chmod +x "$SCRIPT_DIR/generate-thumbs.sh"

echo "[BUILDX] Initiating container build with cache..."
# Build with modern Buildx using root context to include both applications
docker buildx build \
    --load \
    --progress=plain \
    --cache-from "$BASE_IMAGE" \
    -t "$FULL_IMAGE_NAME" \
    -t "${DOCKER_REPO}:latest" \
    -f Dockerfile ..

echo "[VERSION] Updating $VERSION_FILE to $NEXT_TAG..."
echo "$NEXT_TAG" > "$VERSION_FILE"

# Update run-container.sh target image tag
if [ -f "run-container.sh" ]; then
    sed -i "s|${DOCKER_REPO}:v[0-9]*|${FULL_IMAGE_NAME}|g" run-container.sh || true
fi

# Deploy/Restart container via run-container.sh ensuring volume mount
if [ -x "$SCRIPT_DIR/run-container.sh" ]; then
    echo "[DEPLOY] Restarting media-playlist container with $FULL_IMAGE_NAME via run-container.sh..."
    "$SCRIPT_DIR/run-container.sh"
fi

if [ "$PUSH_TO_HUB" = true ]; then
    echo "=========================================="
    echo "[PUSH] Pushing $FULL_IMAGE_NAME and ${DOCKER_REPO}:latest to Docker Hub..."
    echo "=========================================="
    docker push "$FULL_IMAGE_NAME"
    docker push "${DOCKER_REPO}:latest"
    echo "[PUSH] Successfully pushed $FULL_IMAGE_NAME to Docker Hub!"
fi

BUILD_SUCCESS=1
echo "=========================================="
echo "Successfully built and deployed $FULL_IMAGE_NAME"
echo "=========================================="
