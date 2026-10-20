# 🚀 MASTER ARCHITECTURE SPECIFICATION & DEPLOYMENT BLUEPRINT
**Target GitHub Repository**: `https://github.com/sidorea/gallery`  
**Target Host Operating System**: Ubuntu 26.04 LTS ("Resolute Raccoon") (AWS EC2 / GCP Compute Engine VM)  

---

## 📌 CRITICAL INSTRUCTIONS FOR ANTIGRAVITY AI (ON CLONED AWS VM)
When you clone `https://github.com/sidorea/gallery` onto the AWS EC2 VM and run Antigravity inside it:
1. **Strict Monorepo Folder Separation**: You **MUST** organize and maintain each application inside its own dedicated, separate directory within this same repository:
   - **`Media-Playlist-App/`**: The core Nginx media streaming container & player (Port 8083).
   - **`File-Upload-App/`**: The web upload drop-box & Buildx build orchestration portal (Port 80 / 5000).
   - **`Media-Organizer-App/`**: The visual drag-and-drop media sequencer, safe renamer & Docker snapshot studio (Port 9083).
   - **`files/`**: Shared media storage folder containing active media, `thumbs/`, and `thumbs/seek/`.
   - **`.version`**: Root-level version governance file (e.g. `v1`).
2. **Zero Root Clutter**: Do NOT dump application scripts, configs, or source files into the repository root. All application code lives strictly within its corresponding folder.
3. **Cross-App Path Discipline**: All configs and scripts reference shared media and versioning via relative paths:
   - Shared media: `../files/` (or container path `/usr/share/nginx/html/files/`)
   - Central version file: `../.version`
   - Build trigger from upload app: `../Media-Playlist-App/update-file.sh`
   - Dockerfile reference from organizer: `../Media-Playlist-App/Dockerfile`
   - Run script reference from organizer: `../Media-Playlist-App/run-container.sh`
4. **UI Design Standard**: Both web applications (`File-Upload-App` and `Media-Organizer-App`) must use the **Modern Minimalist Light Theme** (pure white `#ffffff` surfaces, soft `#f8fafc` canvas, generous rounded corners `border-radius: 16px-24px`, soft elevation shadows, and crisp slate typography).

```text
/home/ubuntu/gallery/ (Repository Root: https://github.com/sidorea/gallery)
├── .version                          # Single source of truth for version tags (e.g. "v1")
├── .gitignore                        # Global ignore (.venv, __pycache__, .bak, *.log)
├── README.md                         # Monorepo deployment & orchestration guide
│
├── files/                            # Shared media library (/usr/share/nginx/html/files/)
│   ├── thumbs/                       # 320px playlist preview thumbnails
│   └── thumbs/seek/                  # NxN storyboard seek sprite sheets
│
├── Media-Playlist-App/               # APP 1: Gallery Player & Nginx Streaming Container (Port 8083)
│   ├── Dockerfile                    # Hardened Alpine Nginx Dockerfile
│   ├── nginx.conf                    # Zero-copy HTTP 206 byte-range streaming config
│   ├── index.html                    # Single-Page Web Player (Vanilla JS, 100dvh, Web Audio 300% boost)
│   ├── generate-thumbs.sh            # Parallel media processor & seek sprite sheet generator
│   ├── run-container.sh              # Local/server container deployment script (-p 8083:80)
│   ├── squash-layers.sh              # 1-layer filesystem consolidation utility
│   ├── update-file.sh                # Modern Docker Buildx incremental updater
│   └── .dockerignore                 # Container build context filter
│
├── File-Upload-App/                  # APP 2: Automated Drop-Box & Build Portal (Port 80 / 5000)
│   ├── app.py                        # Flask API & upload router
│   ├── config.py                     # Path config pointing to ../files and ../Media-Playlist-App/
│   ├── docker_service.py             # Docker build orchestration, streaming & safety rollback
│   ├── requirements.txt              # Flask, gunicorn, python-dotenv
│   ├── static/
│   │   ├── css/style.css             # Modern rounded-corner white background styling
│   │   └── js/upload.js              # Multi-file chunked upload, progress, SSE live terminal
│   ├── templates/
│   │   └── index.html                # Modern white-background upload portal
│   └── deploy/
│       ├── file-drop.service         # Systemd service unit for Gunicorn
│       ├── nginx.conf                # Reverse proxy config (Port 80 -> 127.0.0.1:5000)
│       └── setup.sh                  # One-click Ubuntu 26.04 deployment script
│
└── Media-Organizer-App/              # APP 3: Visual Sequencer, Safe Renumber & Docker Studio (Port 9083)
    ├── app.py                        # Flask REST API & SSE streaming server
    ├── config.py                     # Config pointing to ../files and container media-playlist
    ├── reorder_service.py            # 2-phase collision-free renamer, backup & rollback engine
    ├── docker_snapshot_service.py    # Docker container export/import, .version updater & SSE streamer
    ├── requirements.txt              # Flask, gunicorn, python-dotenv
    ├── backups/                      # Timestamped JSON rollback journals
    ├── static/
    │   ├── css/style.css             # Modern rounded-corner white background styling
    │   └── js/organizer.js           # SortableJS 1.15+ grid, popup modal, SSE terminal
    ├── templates/
    │   └── index.html                # Modern white-background drag-and-drop sequencing UI
    └── deploy/
        ├── media-organizer.service   # Systemd service unit on port 9083
        └── setup.sh                  # One-click Ubuntu 26.04 deployment script
```

---

# 📋 PROMPT 1: The Media-Playlist App (Folder: `Media-Playlist-App/`, Port: 8083)

```markdown
Build a self-contained, high-performance web media streaming and gallery application deployed in a Docker container using Nginx. The application serves large local video libraries (e.g., hundreds of sequential files like "insta vid (1).mp4", "insta vid (2).mp4", ..., "insta vid (841).mp4", images, and webm files) without requiring a backend database. It auto-discovers files from the Nginx directory index, provides smooth HTTP 206 byte-range video streaming, pre-generates adaptive seek storyboard preview sprite sheets, and delivers an Instagram/YouTube-grade mobile and desktop user experience.

### 1. HOST & CONTAINER ENVIRONMENT (LATEST 2026 STANDARDS)
- **Repository Folder**: `Media-Playlist-App/`
- **Host Operating System**: Ubuntu 26.04 LTS ("Resolute Raccoon") (AWS EC2 / GCP Compute Engine VM). All build and deployment scripts (`update-file.sh`, `squash-layers.sh`, `run-container.sh`) execute natively on the host using standard Ubuntu 26.04 Bash.
- **Low-Memory Host Setup (AWS t2.micro / GCP e2-micro with 2 CPU & 2GB RAM)**:
  Before running media processing or Docker layer builds on 2GB RAM cloud VMs, allocate a 2GB swapfile to prevent Out-Of-Memory (OOM) kills during `ffmpeg` processing:
  ```bash
  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile && echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  ```
- **Container Base OS**: Latest official minimal Alpine Linux (`nginx:alpine-slim` or `nginx:alpine` latest stable release on Alpine 3.24+).
- **Alpine Container Hardening Standards (In Dockerfile)**:
  - Immediately patch all container packages to the latest security baseline:
    ```dockerfile
    RUN apk update && apk upgrade --no-cache
    ```
  - Strip unnecessary SUID/SGID permissions to eliminate privilege escalation vectors:
    ```dockerfile
    RUN find / -xdev -perm /6000 -type f -exec chmod a-s {} + 2>/dev/null || true
    ```
  - Install ffmpeg only during the build stage; completely remove ffmpeg and clean package caches in the same RUN layer to leave zero attack surface in production.
  - Enforce strict least-privilege permissions:
    ```dockerfile
    RUN chown -R nginx:nginx /usr/share/nginx/html && chmod -R 755 /usr/share/nginx/html
    ```

### 2. NETWORKING, PORTS & TOPOLOGY
- **Container Name**: `media-playlist`
- **Docker Image Repository**: `sidorea/my-media-app`
- **Target Version Tag**: Dictated strictly by `../.version` (e.g., `sidorea/my-media-app:v2`)
- **Port Mapping**:
  - Container Internal Port: `80` (HTTP)
  - Host Public/External Port: `8083` (Docker flag: `-p 8083:80`)
  - Web Access URL: `http://localhost:8083` or `http://<SERVER_PUBLIC_IP>:8083`
- **Container Run Command**:
  ```bash
  docker rm -f media-playlist 2>/dev/null || true
  docker run --name media-playlist --restart unless-stopped -d -p 8083:80 sidorea/my-media-app:v2
  ```

### 3. DIRECTORY STRUCTURE & FILESYSTEM
- **Inside Container**:
  - Web Root: `/usr/share/nginx/html/`
  - Media Folder: `/usr/share/nginx/html/files/`
  - Playlist Thumbnails (320px): `/usr/share/nginx/html/files/thumbs/`
  - Storyboard Preview Sprites: `/usr/share/nginx/html/files/thumbs/seek/`
  - Build Staging Directory: `/tmp/new_files/`
- **In Dedicated Folder `Media-Playlist-App/`**:
  ```text
  Media-Playlist-App/
  ├── index.html                    # Single-Page Web Player (Vanilla JS, CSS3, zero dependencies)
  ├── nginx.conf                    # Nginx streaming & security caching configuration
  ├── generate-thumbs.sh            # Automated media processor & seek thumbnail generator
  ├── Dockerfile                    # Container build file (Hardened Alpine Nginx)
  ├── update-file.sh                # Automated Docker Buildx incremental updater
  ├── squash-layers.sh              # 1-layer filesystem consolidation utility
  ├── run-container.sh              # Local/server container deployment script
  └── .dockerignore                 # Strict build context exclusion file
  ```
- **Shared at Root**:
  - `../.version`: Single source of truth for version tag (e.g. `v1`)
  - `../files/`: Shared folder containing uploaded media, `thumbs/`, and `thumbs/seek/`

### 4. NGINX STREAMING & SECURITY CONFIGURATION (nginx.conf)
- High-performance streaming configuration:
  - `sendfile on; tcp_nopush on; tcp_nodelay on; keepalive_timeout 65;`
  - Gzip enabled for HTML/CSS/JS only. **Never gzip video/image files** (breaks HTTP 206 byte-range seek).
  - Dynamic media folder listing: `autoindex on;` under `/files/` with `add_header Cache-Control "no-cache, no-store, must-revalidate";`.
  - Static media streaming: `output_buffers 2 512k; add_header Accept-Ranges bytes always;`.
  - Thumbnails and seek sprites: `expires 30d; add_header Accept-Ranges bytes always; access_log off;`.

### 5. SERVER-SIDE MEDIA PROCESSOR & ADAPTIVE STORYBOARDS (generate-thumbs.sh)
- Staged processing: Processes newly added media from `/tmp/new_files/`, 100% skipping existing base image files.
- FastStart & Codec Normalization:
  - If video is already H.264, width <= 1920, and bitrate <= 4Mbps: executes stream copy with `-movflags +faststart` in < 1 second.
  - If non-H.264 (.mov, .mkv, .webm, 4K): transcodes to web-compatible 1080p H.264 with AAC audio.
- Adaptive Seek Storyboard Sprite Sheets:
  - <= 180s (3m): 10x10 grid (100 frames).
  - 181s - 1200s (20m): 15x15 grid (225 frames).
  - > 1200s: 20x20 grid (400 frames).
- Multi-core concurrency: Clamped between 2 and 8 workers based on `nproc`.
- Zero attack surface cleanup: installs ffmpeg at start, purges ffmpeg and package caches before layer completion.

### 6. WEB PLAYER UI, UX & ENGINE (index.html)
- Pure Vanilla JavaScript, HTML5, CSS3 with zero external runtime dependencies.
- Layout: 100dvh viewport, safe area insets, full-screen containment.
- Streaming: HTTP 206 continuous auto-buffering, real-time buffered range display.
- Seek Scrubbing: Hover (desktop) / touch drag (mobile) live frame canvas tooltip rendered instantly from seek sprite sheets with zero CPU decode lag.
- Web Audio Volume Booster: Boosts audio volume up to 300% (3.0x gain) for quiet phone recordings with soft-clipping limiter.
- Mobile Touch Gestures: Swipe Up/Down (next/prev), Swipe Left/Right (10s seek), Double-Tap, Long-Press 2x speed boost with haptic feedback.
- State Persistence: `localStorage` tracks last played file, playback mode, speed, volume, and video resume positions.

### 7. MODERN DOCKER BUILDX & SCRIPTING (update-file.sh, squash-layers.sh)
- Governed strictly by `../.version`. Next version = `v$((VERSION_NUM + 1))`.
- Safety Rollback: Traps `EXIT INT TERM HUP` to restore `.bak` files if build fails or is aborted.
- Modern Buildx: `docker buildx build --load --progress=plain --cache-from "$BASE_IMAGE" -t "$FULL_IMAGE_NAME" -f Dockerfile .`
- ❌ No legacy builder (`DOCKER_BUILDKIT=1`).
- ❌ No cache pruning (`docker builder prune` is strictly forbidden).
- Layer Squashing (`squash-layers.sh`): Stream exports container filesystem to 1 single clean layer via `docker export | docker import ...`.
```

---

# 📋 PROMPT 2: The File-Upload-App (Folder: `File-Upload-App/`, Port: 80 / 5000)

```markdown
Build a secure, responsive, full-featured Python Flask companion web application designed for mobile and laptop browsers to upload large media files (videos, photos, archives) directly to an Nginx server's media folder, and automatically trigger the modern Docker Buildx build and deployment pipeline (`bash ../Media-Playlist-App/update-file.sh`) with real-time live terminal streaming and one-click rollback.

### 1. NETWORKING, PORTS & REVERSE PROXY TOPOLOGY
- **Repository Folder**: `File-Upload-App/`
- **Host Environment**: Ubuntu 26.04 LTS ("Resolute Raccoon") (AWS EC2 / GCP Compute Engine).
- **Gunicorn Backend**:
  - Bind Address: `127.0.0.1:5000` (Internal only)
  - Workers: `2`
  - Timeout: `3600` seconds (1 hour for large transfers)
  - Executable: `/var/www/file-drop/venv/bin/gunicorn`
- **Nginx Frontend Reverse Proxy**:
  - Bind: `listen 80 default_server;` (Public HTTP port)
  - Public Access URL: `http://<SERVER_PUBLIC_IP>/`
  - Static Asset Route: `location /static/ { alias /var/www/file-drop/static/; expires 30d; }`
  - Proxy Pass Target: `proxy_pass http://127.0.0.1:5000;`
  - Unlimited streaming headers: `client_max_body_size 0; proxy_request_buffering off; proxy_buffering off;`

### 2. FILESYSTEM & DIRECTORY PATHS
- **In Dedicated Folder `File-Upload-App/`**:
  ```text
  File-Upload-App/
  ├── app.py                        # Flask application & API routes
  ├── config.py                     # Environment & path configuration
  ├── docker_service.py             # Docker build orchestration, streaming & rollback service
  ├── requirements.txt              # Flask==3.0.3, gunicorn==22.0.0, python-dotenv==1.0.1
  ├── deploy/
  │   ├── file-drop.service         # Systemd unit file for Gunicorn service
  │   ├── nginx.conf                # Reverse proxy config (Port 80, unlimited upload, no buffering)
  │   └── setup.sh                  # One-click Ubuntu 26.04 deployment script
  ├── static/
  │   ├── css/style.css             # Modern rounded-corner white background styling
  │   └── js/upload.js              # Multi-file upload, progress, SSE live terminal & abort logic
  └── templates/
      └── index.html                # Modern white-background web upload portal
  ```
- **Target Media Upload Destination**: `../files/` (or `/usr/share/nginx/html/files/`)
- **Target Docker Script Directory**: `../Media-Playlist-App/` (Directory holding `update-file.sh`)
- **Version File**: `../.version`

### 3. BACKEND SPECIFICATIONS (app.py, config.py, docker_service.py)
- `config.py`: Resolves `UPLOAD_FOLDER` to `../files`, `DOCKER_SCRIPT_DIR` to `../Media-Playlist-App`, `MAX_FILE_SIZE_MB = 0` (unlimited).
- `POST /upload`: Handles multi-part file uploads, sanitizes filenames, auto-overwrites duplicates, and triggers background build if `docker_build=true`.
- `POST /api/docker-build/start`: Asynchronously starts `bash update-file.sh` with mutex locking (`threading.Lock`).
- `GET /api/docker-build/stream`: Server-Sent Events (SSE) streaming terminal output line-by-line with 15s heartbeats.
- `POST /api/docker-build/abort`: Sends `SIGINT` to the process group (`os.killpg`) so the script's bash trap cleanly rolls back all `.bak` files.
- `rollback_safety_backups`: Direct Python safety fallback ensuring `Dockerfile`, `run-container.sh`, and `.version` are reverted if `.bak` files exist.

### 4. FRONTEND UI & DESIGN SYSTEM (MODERN ROUNDED-CORNER WHITE THEME)
- **Theme**: Modern Minimalist Light Theme:
  - Background: Crisp pure white surfaces (`#ffffff`) on a clean `#f8fafc` canvas.
  - Geometry: Generous rounded corners (`border-radius: 16px-24px` for cards/panels, `12px` for buttons, `9999px` for badges).
  - Elevation: Soft layered shadows (`box-shadow: 0 4px 20px -2px rgba(0,0,0,0.05)`), subtle borders (`1px solid #e2e8f0`).
  - Typography: High-contrast slate typography (`#0f172a`, `#334155`).
- **Upload Queue & Progress**:
  - Drag-and-drop zone with click-to-browse fallback.
  - Queue cards showing filename, formatted size (MB/GB), remove buttons, and aggregate size.
  - Switch toggle: "Build & Push to Docker Hub (bash update-file.sh) automatically after upload".
  - Two primary buttons: "Upload Files Only" and "Upload & Trigger Build".
  - Real-time `XMLHttpRequest.upload.onprogress`: percentage (0-100%), transfer speed in MB/s, and ETA.
  - "Abort Upload" button cancels active network requests immediately.
- **Live Terminal & Real-Time Log Streaming**:
  - Terminal modal window with dark console styling (`#0f172a`, monospace font, glowing status dot) inside a rounded white modal shell.
  - Auto-scroll checkbox, line counter badge, "Copy Logs" button, and "Abort Build" button.

### 5. AUTOMATED SETUP SCRIPT FOR UBUNTU 26.04 (deploy/setup.sh)
- Deploys application to `/var/www/file-drop/` with isolated virtual environment (`python3-venv`, PEP 668 compliant).
- Configures and enables `/etc/systemd/system/file-drop.service`.
- Configures Nginx reverse proxy on Port 80 and restarts services.
```

---

# 📋 PROMPT 3: The Media-Organizer-App (Folder: `Media-Organizer-App/`, Port: 9083)

```markdown
Build a modern, high-performance web-based media organizer and re-sequencing studio running on port 9083 on Ubuntu 26.04 LTS ("Resolute Raccoon"). The application provides an interactive drag-and-drop grid to visually arrange, preview, and batch-renumber hundreds of media files stored in `/usr/share/nginx/html/files/`, features a collision-proof 2-phase atomic renaming engine with 1-click instant rollback, keeps preview thumbnails in lockstep with video renames, seamlessly integrates with the media-playlist player on port 8083, and allows one-click creation and layer squashing of a new Docker image from the active running container governed strictly by the `.version` file.

### 1. HOST, CONTAINER & NETWORK ENVIRONMENT (2026 STANDARDS)
- **Repository Folder**: `Media-Organizer-App/`
- **Host Operating System**: Ubuntu 26.04 LTS ("Resolute Raccoon") (AWS EC2 / GCP Compute Engine).
- **Backend Application Port**: `9083` (Standalone Gunicorn WSGI server bound to `0.0.0.0:9083`).
- **Target Media Filesystem**:
  - Primary Media Folder: `/usr/share/nginx/html/files/`
  - Playlist Thumbnails: `/usr/share/nginx/html/files/thumbs/`
  - Storyboard Seek Sprites: `/usr/share/nginx/html/files/thumbs/seek/`
  - Fallback/Dev Mode: Automatic fallback to `../files` when executing locally outside Docker.
- **Companion Media Player**:
  - Running Container: `media-playlist`
  - Port Mapping: `-p 8083:80`
  - Verification URL: `http://localhost:8083` or `http://<SERVER_PUBLIC_IP>:8083`
- **Supported Media Extensions**:
  - `.mp4`, `.webm`, `.jpg`, `.jpeg`, `.png`, `.webp` (case-insensitive).

### 2. FRONTEND UI & DESIGN SYSTEM (MODERN ROUNDED-CORNER WHITE THEME)
- **Aesthetic Principles**:
  - **Color Palette**: Pristine pure white background (`#ffffff`), soft canvas background (`#f8fafc`), crisp slate text (`#0f172a`, `#334155`, `#64748b`), subtle structural borders (`1px solid #e2e8f0`).
  - **Rounded Geometry**: Generous modern rounded corners across all elements (`border-radius: 16px` to `24px` for cards/modals, `12px` for action buttons, `9999px` for status pills).
  - **Soft Elevation**: Modern layered shadows (`box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05), 0 2px 6px -1px rgba(0, 0, 0, 0.03)`).
  - **Typography**: Clean, high-legibility Inter or system font stack with crisp weight hierarchy.
- **Navigation Bar & Control Header**:
  - Modern white glass sticky navbar (`backdrop-filter: blur(12px); background: rgba(255, 255, 255, 0.95);`).
  - Real-time library metrics badge: Total Files, Total Videos, Total Images, Pending Re-orders indicator.
  - Quick Search & Filter bar: Filter files by filename, number range, or media type (`All`, `Videos`, `Images`).
  - Action Button Hub:
    - **"Apply Reorder & Rename"**: Prominent vibrant indigo button (`background: #4f46e5; border-radius: 12px; color: #fff;`) with save icon and badge showing count of shifted files.
    - **"Undo / Restore Last"**: Clean white button (`background: #ffffff; border: 1px solid #cbd5e1;`) with undo icon, displaying timestamp of the last rename operation.
    - **"Create Docker Image"**: Modern emerald button (`background: #059669; border-radius: 12px; color: #fff;`) with container icon and target tag badge (e.g. `v3`).
    - **"Open Player (8083)"**: Outlink button to verify the newly ordered playlist in the media player.
- **Interactive Drag-and-Drop Media Grid**:
  - Powered by modern **SortableJS 1.15+** with native touch and pointer event support:
    - Fluid 60fps animations (`animation: 180`).
    - Visual feedback styling: `.sortable-ghost` (subtle dashed border `#94a3b8` on `#f1f5f9`), `.sortable-chosen` (slight scale 1.02 and elevated shadow).
  - Responsive CSS Grid: `grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px;`.
- **Media Card Architecture**:
  - Surface: Crisp pure white card (`background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; transition: transform 0.2s, box-shadow 0.2s;`).
  - Hover Lift: Subtle lift (`transform: translateY(-3px); box-shadow: 0 12px 28px -4px rgba(0, 0, 0, 0.08);`).
  - Visual Badges:
    - **Position Number Badge (Top-Left)**: Dark pill (`background: #0f172a; color: #ffffff; border-radius: 20px; font-weight: 700;`) showing the exact position number (e.g., `#1`, `#5`, `#18`). Dynamically recalculates across the entire grid instantly upon dropping any item.
    - **Media Type Badge (Top-Right)**: Pastel pill (e.g., `MP4` / `WEBM` in light blue `#e0f2fe`, `JPG` / `PNG` / `WEBP` in light emerald `#d1fae5`).
    - **Drag Handle**: Grab icon (`cursor: grab;`) for effortless re-ordering.
  - Media Thumbnail Container:
    - 16:9 aspect ratio thumbnail with rounded inner corners (`border-radius: 10px`).
    - Automatically displays thumbnail from `/usr/share/nginx/html/files/thumbs/<filename>.jpg` (or image source for photos).
    - Play overlay icon on hover for video files.
    - Direct click anywhere on the thumbnail opens the Media Watch Modal.
  - Metadata & Renaming Preview:
    - Original Filename: Truncated with full tooltip (e.g., `insta vid (587).mp4`).
    - **Target Renamed Preview Pill**: Soft light-slate/blue pill (e.g., `➔ insta vid (5).mp4`). Clearly displays in real time how the file will be renumbered when the Rename button is pressed!
    - **"Move to Position #" Quick Jump Button**: Clicking opens a quick numerical prompt (e.g., enter `5` or `18`) to immediately jump the card to that position without manual dragging across hundreds of items.

### 3. POPUP MEDIA WATCH MODAL
- Modern rounded-corner white modal (`background: #ffffff; border-radius: 24px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25); max-width: 900px; width: 92vw;`).
- Dimmed backdrop overlay (`background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(6px);`).
- Header: Filename, sequence position badge, resolution/duration details, and round close button.
- Embedded High-Performance Media Player:
  - For Videos (`.mp4`, `.webm`): HTML5 video player with rounded corners, HTTP 206 byte-range seek support, custom clean playback controls, volume boost toggle, loop, and full-screen support.
  - For Images (`.jpg`, `.png`, `.webp`): High-definition image viewer with pan/zoom and fit-to-frame controls.
- Keyboard Navigation: ESC to close, Space to play/pause, Left/Right arrow keys to scrub.

### 4. CONFLICT-FREE 2-PHASE ATOMIC RENAMING ENGINE
- **Renaming Convention**:
  - Target format: `insta vid ({N}).{ext}` where `{N}` is the 1-based index according to user rearrangement, and `{ext}` preserves the original file extension.
- **The Collision Problem**:
  - If moving file `insta vid (587).mp4` to position 5, and file `insta vid (664).mp4` to position 18, a direct rename immediately causes catastrophic file collisions with the existing `insta vid (5).mp4` and `insta vid (18).mp4`.
- **Two-Phase Conflict-Free Staging Algorithm**:
  - **Step 1: Manifest Calculation**: Compare current names against target ordered names. Identify the subset of files requiring rename.
  - **Step 2: Safety Backup Journaling**: Generate a unique timestamped JSON journal file in `backups/rename_backup_<timestamp>.json` containing:
    ```json
    {
      "timestamp": "2026-10-20T16:30:00Z",
      "total_files": 841,
      "renamed_count": 839,
      "operations": [
        {
          "original_name": "insta vid (587).mp4",
          "temp_name": "__stage_rename_587_a1b2c3d4.mp4",
          "final_name": "insta vid (5).mp4",
          "original_thumb": "thumbs/insta vid (587).mp4.jpg",
          "temp_thumb": "thumbs/__stage_rename_587_a1b2c3d4.mp4.jpg",
          "final_thumb": "thumbs/insta vid (5).mp4.jpg",
          "original_seek": "thumbs/seek/insta vid (587).mp4.jpg",
          "temp_seek": "thumbs/seek/__stage_rename_587_a1b2c3d4.mp4.jpg",
          "final_seek": "thumbs/seek/insta vid (5).mp4.jpg"
        }
      ]
    }
    ```
  - **Step 3: Phase 1 (Intermediate Token Staging)**: Rename all participating media files, thumbnail files, and seek sprite sheets to intermediate UUID-guaranteed temporary filenames (`__stage_rename_<uuid>_<n>.<ext>`). At this stage, zero target collision slots exist on disk.
  - **Step 4: Phase 2 (Target Sequential Renumbering)**: Rename all files from their temporary staging tokens directly to their final sequential names (`insta vid (1).ext`, `insta vid (2).ext`...).
  - **Step 5: Lockstep Thumbnail & Seek Sprite Renaming**:
    - Simultaneously renames `/thumbs/<name>.jpg` and `/thumbs/seek/<name>.jpg` to match the new sequential names. This guarantees the media-playlist player on port 8083 retains 100% valid thumbnails and seek storyboard previews with zero broken image paths.
  - **Step 6: Atomic Error Trap & Rollback**:
    - If any disk error, permission issue, or unexpected failure occurs during Phase 1 or 2, an automatic recovery routine executes instantly, reversing all completed renames back to their exact original names from the active journal.

### 5. INSTANT UNDO & RESTORE ENGINE
- **1-Click Restore Button**:
  - Dedicated "Undo / Restore" button prominently visible in the header.
  - Reads the most recent journal file from `backups/`.
  - Reverses the rename operations in two collision-free phases:
    1. Rename from final names back to temporary staging tokens.
    2. Rename from temporary tokens back to exact original filenames (and restore all thumbnails).
  - UI displays an instant success toast: "Restored 839 files to previous state (Backup from 16:30:00)".
- **Backup History Inspector**:
  - History modal displaying the list of past rename sessions with timestamp, file count, and individual "Restore This Snapshot" action buttons.

### 6. DOCKER CONTAINER IMAGE CREATION ENGINE
- **Workflow & Verification**:
  - User rearranges and renames files on port 9083.
  - User verifies playback order in the media player at `http://localhost:8083`.
  - User clicks **"Create Docker Image from Running Container"** in the Organizer UI.
- **Strict Version Governance (.version)**:
  - The script/API reads `../.version` (e.g., `v2`).
  - Strips the `v` prefix, increments by 1 (`v3`).
  - Target Image Tag: `sidorea/my-media-app:v3`.
  - Creates backup `${VERSION_FILE}.bak`, `${DOCKERFILE_PATH}.bak`, and `${RUN_SCRIPT_PATH}.bak`.
- **Snapshot Execution (Single-Layer Consolidation)**:
  - Exports the running `media-playlist` container filesystem and imports it into a fresh single-layer image:
    ```bash
    docker export media-playlist | docker import \
      --change "EXPOSE 80" \
      --change 'CMD ["nginx", "-g", "daemon off;"]' \
      - sidorea/my-media-app:v${NEXT_VERSION_NUM}
    ```
  - Verifies the resulting image has exactly 1 layer (`docker inspect --format '{{len .RootFS.Layers}}'`).
  - Updates `../.version` to `v${NEXT_VERSION_NUM}`.
  - Updates `../Media-Playlist-App/Dockerfile` (`FROM sidorea/my-media-app:v${NEXT_VERSION_NUM}`) and `../Media-Playlist-App/run-container.sh`.
  - Cleanly removes `.bak` files on success; automatically reverts all files if export/import fails.
- **Real-Time Live Terminal Stream**:
  - Dedicated modal with dark console log viewer (`#0f172a`, monospace font) streamed via Server-Sent Events (SSE) `/api/docker-snapshot/stream`.
  - Live progress feedback: "Streaming container filesystem...", "Verifying 1-layer RootFS...", "Tagging image...", "Container snapshot successful!".
  - Optional toggle: "Push newly created image to Docker Hub (`docker push`)".

### 7. BACKEND API SPECIFICATIONS (Python 3 / Flask / Gunicorn)
- Application Directory: `/var/www/media-organizer/`
- Directory Structure:
  ```text
  Media-Organizer-App/
  ├── app.py                         # Flask REST API, SSE streaming & UI server
  ├── config.py                      # Path, port, container, and version configurations
  ├── reorder_service.py             # 2-phase collision-free renamer, backup & rollback engine
  ├── docker_snapshot_service.py     # Docker container export/import, .version updater & SSE streamer
  ├── requirements.txt               # Flask==3.0.3, gunicorn==22.0.0, python-dotenv==1.0.1
  ├── backups/                       # Timestamped JSON rename rollback journals
  ├── static/
  │   ├── css/style.css              # Modern rounded-corner white background styling
  │   └── js/organizer.js            # SortableJS grid, preview modal, renumbering math, SSE terminal
  ├── templates/
  │   └── index.html                 # Modern white background UI portal
  └── deploy/
      ├── media-organizer.service    # Systemd service unit for Gunicorn on port 9083
      └── setup.sh                   # One-click Ubuntu 26.04 LTS deployment script
  ```
- **Key API Routes**:
  - `GET /`: Renders the Media Organizer Web Portal.
  - `GET /api/files`: Scans `/usr/share/nginx/html/files/` and returns JSON array of all media files sorted naturally:
    `[{ "filename": "insta vid (587).mp4", "type": "video", "size": 14205810, "thumb": "/api/thumb/insta%20vid%20(587).mp4", "src": "/api/media/insta%20vid%20(587).mp4" }]`
  - `GET /api/thumb/<path:filename>`: Serves thumbnail from `/usr/share/nginx/html/files/thumbs/<filename>.jpg` (or video poster/image).
  - `GET /api/media/<path:filename>`: Streams full media file with HTTP 206 byte-range streaming support.
  - `POST /api/reorder/rename`: Accepts JSON payload of re-arranged filenames `[ "insta vid (587).mp4", ... ]`. Executes 2-phase atomic renumbering to `insta vid (1).ext` ... `insta vid (N).ext`. Returns `{ "success": true, "renamed": 839, "backup_id": "20261020_163000" }`.
  - `POST /api/reorder/restore`: Reverses last rename operation using the latest backup journal.
  - `GET /api/reorder/backups`: Returns list of available restore snapshots.
  - `POST /api/docker-snapshot/start`: Triggers container export and version increment in a background thread.
  - `GET /api/docker-snapshot/stream`: SSE live log stream for container snapshot execution.

### 8. AUTOMATED UBUNTU 26.04 DEPLOYMENT SCRIPT (deploy/setup.sh)
- Fully automated bash script:
  - Installs `python3`, `python3-pip`, `python3-venv`, and `rsync`.
  - Enforces PEP 668 compliance with isolated virtual environment `/var/www/media-organizer/venv`.
  - Installs requirements (`pip install -r requirements.txt`).
  - Sets up systemd service `/etc/systemd/system/media-organizer.service` running Gunicorn on port `9083`.
  - Enables and restarts service (`systemctl daemon-reload && systemctl enable media-organizer && systemctl restart media-organizer`).
  - Prints access URL: `http://<SERVER_IP>:9083`.

### 9. STRICT MODERN TECHNOLOGY CONSTRAINTS
- ❌ No legacy Docker builder (`DOCKER_BUILDKIT=1` is strictly forbidden).
- ❌ No cache pruning (`docker builder prune` is strictly forbidden).
- ❌ No file overwrites during renaming; multi-phase staging tokens are mandatory.
- ❌ Never break thumbnails in the port 8083 player; all thumb files must be renamed synchronously.
- ❌ Never alter `.version` based on Dockerfile FROM tags; `.version` file is the sole single source of truth.
```
