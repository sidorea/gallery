import os
import re
import mimetypes
from queue import Empty
from flask import Flask, render_template, request, jsonify, Response, send_file, stream_with_context
from config import MEDIA_DIR, THUMBS_DIR, VERSION_FILE, CONTAINER_NAME, SUPPORTED_EXTENSIONS, APP_PORT, PLAYER_PORT
from reorder_service import reorder_service
from docker_snapshot_service import docker_snapshot_service

app = Flask(__name__)

def natural_sort_key(s):
    """Key for natural alphanumeric sorting (insta vid (1), insta vid (2)...)"""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def get_media_type(filename):
    _, ext = os.path.splitext(filename.lower())
    if ext in ('.mp4', '.webm', '.mov', '.mkv'):
        return 'video'
    elif ext in ('.jpg', '.jpeg', '.png', '.webp'):
        return 'image'
    return 'other'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/info')
def get_info():
    version = "v1"
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, 'r') as f:
                version = f.read().strip() or "v1"
        except Exception:
            pass

    return jsonify({
        'version': version,
        'container': CONTAINER_NAME,
        'player_port': PLAYER_PORT,
        'organizer_port': APP_PORT
    })

@app.route('/api/files')
def list_files():
    if not os.path.exists(MEDIA_DIR):
        return jsonify([])

    raw_files = [
        f for f in os.listdir(MEDIA_DIR)
        if os.path.isfile(os.path.join(MEDIA_DIR, f))
        and not f.startswith('.')
        and not f.startswith('__stage_')
        and f.lower().endswith(SUPPORTED_EXTENSIONS)
    ]
    raw_files.sort(key=natural_sort_key)

    items = []
    for f in raw_files:
        fpath = os.path.join(MEDIA_DIR, f)
        size = os.path.getsize(fpath)
        mtype = get_media_type(f)
        items.append({
            'filename': f,
            'type': mtype,
            'size': size,
            'thumb': f"/api/thumb/{f}",
            'src': f"/api/media/{f}"
        })

    return jsonify(items)

@app.route('/api/thumb/<path:filename>')
def serve_thumbnail(filename):
    # Try exact match with .jpg suffix in thumbs dir (from generate-thumbs.sh)
    candidate1 = os.path.join(THUMBS_DIR, f"{filename}.jpg")
    if os.path.exists(candidate1):
        return send_file(candidate1, mimetype='image/jpeg')

    # Try direct name match in thumbs dir
    candidate2 = os.path.join(THUMBS_DIR, filename)
    if os.path.exists(candidate2):
        return send_file(candidate2)

    # For images, serve the image itself if thumbnail does not exist yet
    media_path = os.path.join(MEDIA_DIR, filename)
    if os.path.exists(media_path) and get_media_type(filename) == 'image':
        mime_type, _ = mimetypes.guess_type(media_path)
        return send_file(media_path, mimetype=mime_type or 'image/jpeg')

    return ('', 404)

@app.route('/api/media/<path:filename>')
def stream_media(filename):
    """
    Streams media file with robust HTTP 206 Partial Content byte-range support.
    """
    path = os.path.join(MEDIA_DIR, filename)
    if not os.path.exists(path):
        return ('File not found', 404)

    file_size = os.path.getsize(path)
    mime_type, _ = mimetypes.guess_type(path)
    if not mime_type:
        mime_type = 'video/mp4' if filename.lower().endswith('.mp4') else 'application/octet-stream'

    range_header = request.headers.get('Range', None)
    if not range_header:
        # Full content response
        resp = send_file(path, mimetype=mime_type)
        resp.headers['Accept-Ranges'] = 'bytes'
        return resp

    # Parse Range: bytes=start-end
    match = re.search(r'bytes=(\d+)-(\d*)', range_header)
    if not match:
        return ('Invalid Range', 416)

    start = int(match.group(1))
    end_str = match.group(2)
    end = int(end_str) if end_str else file_size - 1

    if start >= file_size or end >= file_size or start > end:
        resp = Response(status=416)
        resp.headers['Content-Range'] = f"bytes */{file_size}"
        return resp

    length = end - start + 1

    def generate_chunks():
        with open(path, 'rb') as f:
            f.seek(start)
            remaining = length
            chunk_size = 512 * 1024 # 512KB chunks
            while remaining > 0:
                read_size = min(remaining, chunk_size)
                data = f.read(read_size)
                if not data:
                    break
                remaining -= len(data)
                yield data

    resp = Response(
        generate_chunks(),
        status=206,
        mimetype=mime_type,
        direct_passthrough=True
    )
    resp.headers['Accept-Ranges'] = 'bytes'
    resp.headers['Content-Range'] = f"bytes {start}-{end}/{file_size}"
    resp.headers['Content-Length'] = str(length)
    resp.headers['Cache-Control'] = 'no-cache'
    return resp

@app.route('/api/reorder/rename', methods=['POST'])
def handle_reorder_rename():
    data = request.get_json(force=True, silent=True) or {}
    order = data.get('order') if isinstance(data, dict) else data
    if not isinstance(order, list):
        return jsonify({'success': False, 'error': 'Invalid payload format. Expected list of filenames.'}), 400

    result = reorder_service.execute_reorder(order)
    return jsonify(result)

@app.route('/api/reorder/restore', methods=['POST'])
def handle_restore():
    data = request.get_json(force=True, silent=True) or {}
    backup_id = data.get('backup_id') if isinstance(data, dict) else None
    result = reorder_service.restore_backup(backup_id)
    return jsonify(result)

@app.route('/api/reorder/backups')
def list_backups():
    backups = reorder_service.list_backups()
    return jsonify(backups)

@app.route('/api/docker-snapshot/start', methods=['POST'])
def start_snapshot():
    data = request.get_json(force=True, silent=True) or {}
    push = data.get('push', False)
    success, msg = docker_snapshot_service.start_snapshot(push_to_hub=push)
    return jsonify({'success': success, 'message': msg})

@app.route('/api/docker-snapshot/stream')
def stream_snapshot_logs():
    q = docker_snapshot_service.add_listener()

    def generate():
        try:
            yield "data: [SYS] Connected to container snapshot stream.\n\n"
            while True:
                try:
                    line = q.get(timeout=15.0)
                    formatted = line.rstrip('\r\n')
                    yield f"data: {formatted}\n\n"
                except Empty:
                    yield ": ping\n\n"
        except GeneratorExit:
            docker_snapshot_service.remove_listener(q)
        finally:
            docker_snapshot_service.remove_listener(q)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-transform',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=APP_PORT, debug=False)
