import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Target upload directory (shared files folder)
DEFAULT_UPLOAD_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "files"))
CONTAINER_FILES_DIR = "/usr/share/nginx/html/files"

if os.path.isdir(CONTAINER_FILES_DIR) and os.access(CONTAINER_FILES_DIR, os.W_OK):
    UPLOAD_FOLDER = CONTAINER_FILES_DIR
else:
    UPLOAD_FOLDER = DEFAULT_UPLOAD_DIR

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, "thumbs"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, "thumbs", "seek"), exist_ok=True)

# Path to Media-Playlist-App containing update-file.sh
DOCKER_SCRIPT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "Media-Playlist-App"))
UPDATE_SCRIPT_PATH = os.path.join(DOCKER_SCRIPT_DIR, "update-file.sh")

# Central version governance file
VERSION_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", ".version"))

# Unlimited file size
MAX_FILE_SIZE_MB = 0
MAX_CONTENT_LENGTH = None  # Flask unlimited upload body

ALLOWED_EXTENSIONS = {
    'mp4', 'webm', 'mov', 'mkv', 'avi',
    'jpg', 'jpeg', 'png', 'webp', 'gif',
    'tar', 'gz', 'zip'
}
