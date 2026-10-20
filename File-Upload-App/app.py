import os
import re
import time
from queue import Empty
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from config import UPLOAD_FOLDER, VERSION_FILE, ALLOWED_EXTENSIONS
from docker_service import docker_service

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = None # Unlimited upload

def sanitize_filename(filename):
    """
    Sanitizes filename while strictly preserving spaces, parentheses, numbers,
    and valid extensions (e.g., 'insta vid (841).mp4').
    Removes path traversal and dangerous shell characters.
    """
    filename = os.path.basename(filename).strip()
    # Remove null bytes and directory separators
    filename = filename.replace('\x00', '').replace('/', '').replace('\\', '')
    # Allow alphanumeric, spaces, dots, dashes, underscores, parentheses, and brackets
    clean_name = re.sub(r'[^a-zA-Z0-9\s\.\-_()\[\]]', '', filename)
    clean_name = re.sub(r'\s+', ' ', clean_name).strip()
    return clean_name or f"upload_{int(time.time())}"

def allowed_file(filename):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def handle_upload():
    if 'files' not in request.files and 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No files provided in request.'}), 400

    uploaded_files = request.files.getlist('files')
    if not uploaded_files or (len(uploaded_files) == 1 and uploaded_files[0].filename == ''):
        single = request.files.get('file')
        uploaded_files = [single] if single and single.filename != '' else []

    if not uploaded_files:
        return jsonify({'success': False, 'error': 'Empty file list received.'}), 400

    saved_list = []
    for file_storage in uploaded_files:
        if not file_storage or not file_storage.filename:
            continue

        raw_filename = file_storage.filename
        clean_name = sanitize_filename(raw_filename)

        if not allowed_file(clean_name):
            continue

        dest_path = os.path.join(app.config['UPLOAD_FOLDER'], clean_name)
        # Auto-overwrite existing file
        file_storage.save(dest_path)
        saved_list.append(clean_name)

    trigger_build = request.form.get('docker_build', 'false').lower() in ('true', '1', 'yes')
    build_started = False
    build_msg = ""

    if trigger_build and saved_list:
        build_started, build_msg = docker_service.start_build()

    return jsonify({
        'success': True,
        'count': len(saved_list),
        'files': saved_list,
        'docker_build_triggered': build_started,
        'message': build_msg
    })

@app.route('/api/docker-build/start', methods=['POST'])
def start_build():
    success, msg = docker_service.start_build()
    return jsonify({'success': success, 'message': msg})

@app.route('/api/docker-build/abort', methods=['POST'])
def abort_build():
    success, msg = docker_service.abort_build()
    return jsonify({'success': success, 'message': msg})

@app.route('/api/docker-build/stream')
def stream_build_logs():
    q = docker_service.add_listener()

    def generate():
        try:
            # Initial connection message
            yield "data: [SYS] Connected to build log stream.\n\n"
            while True:
                try:
                    # Timeout after 15 seconds to yield SSE heartbeat
                    line = q.get(timeout=15.0)
                    formatted = line.rstrip('\r\n')
                    yield f"data: {formatted}\n\n"
                except Empty:
                    # 15s Heartbeat ping to keep HTTP connection alive through reverse proxies
                    yield ": ping\n\n"
        except GeneratorExit:
            docker_service.remove_listener(q)
        finally:
            docker_service.remove_listener(q)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-transform',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )

@app.route('/api/status')
def get_status():
    version = "unknown"
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, 'r') as f:
                version = f.read().strip()
        except Exception:
            pass

    file_count = 0
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        try:
            file_count = len([
                f for f in os.listdir(app.config['UPLOAD_FOLDER'])
                if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], f)) and not f.startswith('.')
            ])
        except Exception:
            pass

    build_info = docker_service.get_status()

    return jsonify({
        'version': version,
        'total_files': file_count,
        'build': build_info
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
