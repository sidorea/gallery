#!/usr/bin/env bash
set -eo pipefail

# Determine directories
FILES_DIR="${1:-}"
if [ -z "$FILES_DIR" ]; then
    if [ -d "/usr/share/nginx/html/files" ]; then
        FILES_DIR="/usr/share/nginx/html/files"
    elif [ -d "../files" ]; then
        FILES_DIR="../files"
    elif [ -d "./files" ]; then
        FILES_DIR="./files"
    elif [ -d "/tmp/new_files" ]; then
        FILES_DIR="/tmp/new_files"
    else
        FILES_DIR="$(pwd)"
    fi
fi

STAGING_DIR="/tmp/new_files"
THUMBS_DIR="${FILES_DIR}/thumbs"
SEEK_DIR="${FILES_DIR}/thumbs/seek"

mkdir -p "$THUMBS_DIR" "$SEEK_DIR"

echo "=== Media Processor & Storyboard Generator ==="
echo "Target media directory: $FILES_DIR"

# Multicore concurrency setup (clamped between 2 and 8 workers)
NPROC=$(nproc 2>/dev/null || echo 2)
WORKERS=$(( NPROC < 2 ? 2 : (NPROC > 8 ? 8 : NPROC) ))
echo "Processing concurrency: $WORKERS parallel workers (nproc: $NPROC)"

# If staging directory exists and is distinct, move new files into FILES_DIR
if [ -d "$STAGING_DIR" ] && [ "$STAGING_DIR" != "$FILES_DIR" ]; then
    echo "Importing new files from staging directory: $STAGING_DIR"
    find "$STAGING_DIR" -maxdepth 1 -type f \( -iname "*.mp4" -o -iname "*.webm" -o -iname "*.mov" -o -iname "*.mkv" -o -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) -exec mv -n {} "$FILES_DIR/" \; || true
fi

# Function to process an individual file
process_media_file() {
    local file_path="$1"
    local filename
    filename=$(basename "$file_path")
    local thumbs_dir="$2"
    local seek_dir="$3"

    # Skip thumbs folder itself
    if [[ "$file_path" == *"/thumbs/"* ]]; then
        return 0
    fi

    local ext="${filename##*.}"
    local ext_lower
    ext_lower=$(echo "$ext" | tr '[:upper:]' '[:lower:]')
    local thumb_file="${thumbs_dir}/${filename}.jpg"
    local seek_file="${seek_dir}/${filename}.jpg"

    # 1. Image handling
    if [[ "$ext_lower" =~ ^(jpg|jpeg|png|webp)$ ]]; then
        if [ ! -f "$thumb_file" ]; then
            echo "[IMAGE] Generating 320px thumbnail: $filename"
            ffmpeg -v error -y -i "$file_path" -vf "scale=320:-1" -vframes 1 -q:v 2 "$thumb_file" 2>/dev/null || cp "$file_path" "$thumb_file" 2>/dev/null || true
        fi
        return 0
    fi

    # 2. Video handling
    if [[ "$ext_lower" =~ ^(mp4|webm|mov|mkv)$ ]]; then
        # Probe duration for thumbnail and storyboard timing (read-only)
        local probe_info
        probe_info=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 "$file_path" 2>/dev/null || true)
        local duration
        duration=$(echo "$probe_info" | grep '^duration=' | cut -d= -f2 || echo 0)
        duration=${duration%.*} # integer seconds
        if [ -z "$duration" ] || [ "$duration" -le 0 ]; then
            duration=60
        fi

        # 320px Playlist Thumbnail (Read-only from original file)
        if [ ! -f "$thumb_file" ]; then
            local seek_sec=$(( duration > 3 ? 2 : 0 ))
            echo "[THUMB] Creating 320px preview: $filename"
            ffmpeg -v error -y -ss "$seek_sec" -i "$file_path" -vf "scale=320:-1" -vframes 1 -q:v 2 "$thumb_file" 2>/dev/null || true
        fi

        # Adaptive Storyboard Sprite Sheet
        if [ ! -f "$seek_file" ]; then
            local grid=10
            local total_frames=100
            if [ "$duration" -gt 1200 ]; then
                grid=20
                total_frames=400
            elif [ "$duration" -gt 180 ]; then
                grid=15
                total_frames=225
            fi

            # Compute fps for ffmpeg tile filter
            # fps = total_frames / duration
            local fps
            fps=$(awk -v tf="$total_frames" -v dur="$duration" 'BEGIN { if (dur <= 0) dur = 1; printf "%.4f", tf / dur }')

            echo "[SEEK SPRITE] Generating ${grid}x${grid} storyboard (${total_frames} frames) for $filename (dur: ${duration}s)"
            ffmpeg -v error -y -i "$file_path" -vf "fps=${fps},scale=160:90,tile=${grid}x${grid}" -frames:v 1 -q:v 3 "$seek_file" 2>/dev/null || true
        fi
    fi
}

export -f process_media_file

# Collect all media files
find "$FILES_DIR" -maxdepth 1 -type f \( -iname "*.mp4" -o -iname "*.webm" -o -iname "*.mov" -o -iname "*.mkv" -o -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) \
  | sort \
  | xargs -I {} -P "$WORKERS" bash -c 'process_media_file "$@"' _ "{}" "$THUMBS_DIR" "$SEEK_DIR"

echo "=== Media processing complete ==="
