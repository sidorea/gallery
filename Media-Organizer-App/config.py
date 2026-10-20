import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PRIMARY_MEDIA_DIR = "/usr/share/nginx/html/files"
FALLBACK_MEDIA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "files"))

# Auto-detect media directory
if os.path.isdir(PRIMARY_MEDIA_DIR) and os.access(PRIMARY_MEDIA_DIR, os.W_OK):
    MEDIA_DIR = PRIMARY_MEDIA_DIR
else:
    MEDIA_DIR = FALLBACK_MEDIA_DIR

THUMBS_DIR = os.path.join(MEDIA_DIR, "thumbs")
SEEK_DIR = os.path.join(MEDIA_DIR, "thumbs", "seek")
BACKUPS_DIR = os.path.join(BASE_DIR, "backups")

os.makedirs(MEDIA_DIR, exist_ok=True)
os.makedirs(THUMBS_DIR, exist_ok=True)
os.makedirs(SEEK_DIR, exist_ok=True)
os.makedirs(BACKUPS_DIR, exist_ok=True)

# Monorepo cross-app references
VERSION_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", ".version"))
MEDIA_PLAYLIST_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "Media-Playlist-App"))
DOCKERFILE_PATH = os.path.join(MEDIA_PLAYLIST_DIR, "Dockerfile")
RUN_SCRIPT_PATH = os.path.join(MEDIA_PLAYLIST_DIR, "run-container.sh")

# Docker container and registry settings
CONTAINER_NAME = "media-playlist"
DOCKER_REPO = "sidorea/gallery"
APP_PORT = 9083
PLAYER_PORT = 8083

SUPPORTED_EXTENSIONS = ('.mp4', '.webm', '.mov', '.mkv', '.jpg', '.jpeg', '.png', '.webp')
