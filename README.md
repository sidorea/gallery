# 🚀 Gallery Monorepo

**High-Performance Media Streaming, Automated File Drop-Box & Visual Sequencing Studio**  
*Optimized for Ubuntu 26.04 LTS ("Resolute Raccoon") & Docker Buildx*

---

## 📐 Architecture & Ports Overview

| Component | Repository Path | Service / Port | Description |
| :--- | :--- | :--- | :--- |
| **Media-Playlist-App** | `Media-Playlist-App/` | **Port 8083** (HTTP) | Hardened Alpine Nginx container serving zero-copy HTTP 206 video streaming, seek storyboard sprite preview scrubbing, and Web Audio 300% volume booster. |
| **File-Upload-App** | `File-Upload-App/` | **Port 80** / `5000` | Automated file drop-box reverse-proxied through Nginx on Port 80 with chunked upload, live terminal SSE streaming, and automated `update-file.sh` trigger. |
| **Media-Organizer-App** | `Media-Organizer-App/` | **Port 9083** | Visual drag-and-drop sequencing studio with SortableJS, collision-proof 2-phase atomic renamer, 1-click restore, and 1-layer Docker container snapshot engine. |
| **Shared Library** | `files/` | File Storage | Shared persistent media library with `thumbs/` (320px) and `thumbs/seek/` (NxN sprite sheets). |
| **Version Truth** | `.version` | Version File | Single source of truth governing container version tags (e.g., `v1`). |

---

## 📁 Monorepo Structure

```text
/home/ubuntu/gallery/
├── .version                          # Single source of truth for version tags (e.g. "v1")
├── .gitignore                        # Global ignore (.venv, __pycache__, .bak, *.log)
├── README.md                         # Monorepo architecture & deployment guide
│
├── files/                            # Shared media library (/usr/share/nginx/html/files/)
│   ├── thumbs/                       # 320px playlist preview thumbnails
│   └── thumbs/seek/                  # NxN storyboard seek sprite sheets
│
├── Media-Playlist-App/               # APP 1: Gallery Player & Nginx Streaming (Port 8083)
│   ├── Dockerfile                    # Hardened Alpine Nginx Dockerfile
│   ├── nginx.conf                    # Zero-copy HTTP 206 byte-range streaming config
│   ├── index.html                    # Web Player (Vanilla JS, 100dvh, Web Audio 300% boost)
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

## ⚡ Quickstart Deployment on Ubuntu 24.04 / 26.04 LTS

Deploy all applications, services, and containers with a single command:

```bash
cd /home/ubuntu/gallery
./setup.sh
```

This single unified setup script automatically:
1. Allocates a 2GB swapfile if system RAM < 4GB.
2. Installs system packages (`docker.io`, `python3`, `nginx`, `rsync`, `ffmpeg`).
3. Deploys **File-Upload-App** on **Port 80** with host Nginx reverse proxy.
4. Deploys the unified **`media-playlist` container** serving both the **Web Media Player** on **Port 8083** and the **Media Organizer Studio** on **Port 9083**.
5. Runs health checks and outputs active URLs.

---

## 🔑 Key Features & Technologies

### 1. Collision-Free 2-Phase Atomic Renaming Engine
When reordering hundreds of sequential files (e.g. moving item #587 to #5 and item #664 to #18):
- **Phase 1 (Token Staging)**: All participating media, thumbnails (`thumbs/<name>.jpg`), and seek sprite sheets (`thumbs/seek/<name>.jpg`) are renamed to temporary UUID tokens (`__stage_rename_<uuid>_<n>.<ext>`), eliminating target collision slots on disk.
- **Phase 2 (Target Sequential Renumbering)**: Files are atomically renamed from temporary tokens to sequential names `insta vid (1).ext` through `insta vid (N).ext`.
- **Automatic Rollback**: Any disk exception immediately triggers an atomic rollback restoring files to original state using the JSON backup journal in `backups/`.

### 2. Modern Docker Buildx & 1-Layer Snapshot Studio
- Incrementally updates and builds containers with Buildx caching (`--cache-from`).
- Creates single consolidated layer Docker images from the active running container using `docker export | docker import ...`.
- Version governance is strictly bound to `../.version`.

### 3. Web Audio 300% Volume Booster & Storyboard Scrubbing
- **Web Audio Booster**: Connects `AudioContext` -> `GainNode` -> `DynamicsCompressorNode` for soft-limiting distortion-free 3.0x gain on quiet mobile video recordings.
- **Adaptive Seek Storyboards**: Generates 10x10 (100 frame), 15x15 (225 frame), or 20x20 (400 frame) preview sprite sheets for instant lag-free seek scrubbing.
