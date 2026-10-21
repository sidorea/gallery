(() => {
  // Application State
  const state = {
    queue: [],
    xhr: null,
    isUploading: false,
    uploadStartTime: 0,
    eventSource: null,
    terminalLines: 0
  };

  // DOM Elements
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const queueSection = document.getElementById('queueSection');
  const queueList = document.getElementById('queueList');
  const queueCount = document.getElementById('queueCount');
  const queueTotalSize = document.getElementById('queueTotalSize');
  const buildToggle = document.getElementById('buildToggle');
  const btnUploadOnly = document.getElementById('btnUploadOnly');
  const btnUploadAndBuild = document.getElementById('btnUploadAndBuild');
  const btnClearQueue = document.getElementById('btnClearQueue');
  const btnAbortUpload = document.getElementById('btnAbortUpload');
  const progressCard = document.getElementById('progressCard');
  const progressBar = document.getElementById('progressBar');
  const progressText = document.getElementById('progressText');
  const progressStats = document.getElementById('progressStats');

  // Terminal Elements
  const terminalModal = document.getElementById('terminalModal');
  const btnOpenTerminal = document.getElementById('btnOpenTerminal');
  const btnCloseTerminal = document.getElementById('btnCloseTerminal');
  const terminalOutput = document.getElementById('terminalOutput');
  const terminalStatusDot = document.getElementById('terminalStatusDot');
  const headerStatusDot = document.getElementById('headerStatusDot');
  const terminalLineBadge = document.getElementById('terminalLineBadge');
  const autoScrollCheck = document.getElementById('autoScrollCheck');
  const btnCopyLogs = document.getElementById('btnCopyLogs');
  const btnAbortBuild = document.getElementById('btnAbortBuild');
  const versionBadge = document.getElementById('versionBadge');
  const fileCountBadge = document.getElementById('fileCountBadge');

  function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  // File Input and Drag & Drop
  dropzone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => {
    addFilesToQueue(e.target.files);
    fileInput.value = '';
  });

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    if (e.dataTransfer && e.dataTransfer.files) {
      addFilesToQueue(e.dataTransfer.files);
    }
  });

  function addFilesToQueue(files) {
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      // Check for duplicate in current queue
      if (!state.queue.some(f => f.name === file.name && f.size === file.size)) {
        state.queue.push(file);
      }
    }
    renderQueue();
  }

  function renderQueue() {
    queueList.innerHTML = '';
    if (state.queue.length === 0) {
      queueSection.style.display = 'none';
      btnClearQueue.style.display = 'none';
      btnUploadOnly.disabled = true;
      btnUploadAndBuild.disabled = true;
      return;
    }

    queueSection.style.display = 'block';
    btnClearQueue.style.display = 'inline-flex';
    btnUploadOnly.disabled = false;
    btnUploadAndBuild.disabled = false;

    queueCount.textContent = state.queue.length;
    const totalBytes = state.queue.reduce((acc, f) => acc + f.size, 0);
    queueTotalSize.textContent = `Total: ${formatBytes(totalBytes)}`;

    state.queue.forEach((file, idx) => {
      const card = document.createElement('div');
      card.className = 'queue-card';
      const ext = file.name.split('.').pop() || 'FILE';

      card.innerHTML = `
        <div class="card-left">
          <span class="file-badge-type">${ext}</span>
          <div class="card-details">
            <div class="card-name" title="${file.name}">${file.name}</div>
            <div class="card-size">${formatBytes(file.size)}</div>
          </div>
        </div>
        <button class="btn-remove-item" title="Remove file" data-index="${idx}">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      `;

      card.querySelector('.btn-remove-item').addEventListener('click', (e) => {
        e.stopPropagation();
        state.queue.splice(idx, 1);
        renderQueue();
      });

      queueList.appendChild(card);
    });
  }

  btnClearQueue.addEventListener('click', () => {
    state.queue = [];
    renderQueue();
  });

  // Upload Logic with XMLHttpRequest
  function startUpload(triggerBuild) {
    if (state.queue.length === 0 || state.isUploading) return;

    state.isUploading = true;
    state.uploadStartTime = Date.now();

    progressCard.style.display = 'block';
    btnAbortUpload.style.display = 'inline-flex';
    btnUploadOnly.disabled = true;
    btnUploadAndBuild.disabled = true;
    btnClearQueue.disabled = true;

    const formData = new FormData();
    state.queue.forEach(file => {
      formData.append('files', file);
    });
    formData.append('docker_build', triggerBuild ? 'true' : 'false');

    state.xhr = new XMLHttpRequest();
    state.xhr.open('POST', '/upload', true);

    state.xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const percent = Math.round((e.loaded / e.total) * 100);
        progressBar.style.width = `${percent}%`;

        const elapsedSec = (Date.now() - state.uploadStartTime) / 1000;
        const speedBytes = elapsedSec > 0 ? (e.loaded / elapsedSec) : 0;
        const speedMB = (speedBytes / (1024 * 1024)).toFixed(2);

        const remainingBytes = e.total - e.loaded;
        const etaSec = speedBytes > 0 ? Math.round(remainingBytes / speedBytes) : 0;
        const etaStr = etaSec > 60 ? `${Math.floor(etaSec / 60)}m ${etaSec % 60}s` : `${etaSec}s`;

        progressText.textContent = `Uploading ${state.queue.length} files (${formatBytes(e.loaded)} / ${formatBytes(e.total)})`;
        progressStats.textContent = `${percent}% • ${speedMB} MB/s • ETA: ${etaStr}`;
      }
    };

    state.xhr.onload = () => {
      state.isUploading = false;
      btnAbortUpload.style.display = 'none';
      btnClearQueue.disabled = false;

      if (state.xhr.status >= 200 && state.xhr.status < 300) {
        const res = JSON.parse(state.xhr.responseText || '{}');
        progressText.textContent = `Upload successful! ${res.count || state.queue.length} files saved.`;
        progressBar.style.width = '100%';
        state.queue = [];
        renderQueue();
        refreshStatus();

        if (triggerBuild || res.docker_build_triggered) {
          openTerminal();
        }
      } else {
        progressText.textContent = `Upload failed (Status ${state.xhr.status})`;
        btnUploadOnly.disabled = false;
        btnUploadAndBuild.disabled = false;
      }
    };

    state.xhr.onerror = () => {
      state.isUploading = false;
      btnAbortUpload.style.display = 'none';
      progressText.textContent = 'Upload encountered a network error.';
      btnUploadOnly.disabled = false;
      btnUploadAndBuild.disabled = false;
    };

    state.xhr.onabort = () => {
      state.isUploading = false;
      btnAbortUpload.style.display = 'none';
      progressText.textContent = 'Upload was aborted.';
      btnUploadOnly.disabled = false;
      btnUploadAndBuild.disabled = false;
    };

    state.xhr.send(formData);
  }

  btnUploadOnly.addEventListener('click', () => startUpload(false));
  btnUploadAndBuild.addEventListener('click', () => startUpload(true));

  btnAbortUpload.addEventListener('click', () => {
    if (state.xhr) {
      state.xhr.abort();
    }
  });

  // Terminal & SSE streaming
  function connectTerminalSSE() {
    if (state.eventSource) return;

    state.eventSource = new EventSource('/api/docker-build/stream');

    state.eventSource.onmessage = (e) => {
      appendTerminalLine(e.data);
    };

    state.eventSource.onerror = () => {
      terminalStatusDot.classList.remove('active');
      headerStatusDot.classList.remove('active');
    };
  }

  function appendTerminalLine(text) {
    if (terminalOutput.textContent === 'Awaiting build connection...') {
      terminalOutput.textContent = '';
    }
    terminalOutput.textContent += text + '\n';
    state.terminalLines++;
    terminalLineBadge.textContent = `${state.terminalLines} lines`;

    if (autoScrollCheck.checked) {
      terminalOutput.scrollTop = terminalOutput.scrollHeight;
    }
  }

  function openTerminal() {
    terminalModal.classList.add('open');
    connectTerminalSSE();
  }

  function closeTerminal() {
    terminalModal.classList.remove('open');
  }

  btnOpenTerminal.addEventListener('click', openTerminal);
  btnCloseTerminal.addEventListener('click', closeTerminal);
  terminalModal.addEventListener('click', (e) => {
    if (e.target === terminalModal) closeTerminal();
  });

  btnCopyLogs.addEventListener('click', () => {
    const text = terminalOutput.textContent;
    if (!text || text.trim() === '') return;

    const setCopied = () => {
      btnCopyLogs.textContent = 'Copied!';
      setTimeout(() => { btnCopyLogs.textContent = 'Copy Logs'; }, 2000);
    };

    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(setCopied).catch(fallbackCopy);
    } else {
      fallbackCopy();
    }

    function fallbackCopy() {
      try {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        setCopied();
      } catch (err) {}
    }
  });

  btnAbortBuild.addEventListener('click', async () => {
    if (confirm("Are you sure you want to abort the active Docker build and trigger safety rollback?")) {
      try {
        const res = await fetch('/api/docker-build/abort', { method: 'POST' });
        const data = await res.json();
        alert(data.message || 'Build abort requested.');
      } catch (err) {
        alert('Failed to send abort command.');
      }
    }
  });

  // Status Poll
  async function refreshStatus() {
    try {
      const res = await fetch('/api/status');
      const data = await res.json();
      versionBadge.textContent = `Ver: ${data.version || 'v1'}`;
      fileCountBadge.textContent = `Media: ${data.total_files || 0} Files`;

      const isBuilding = data.build && data.build.is_building;
      terminalStatusDot.classList.toggle('active', isBuilding);
      headerStatusDot.classList.toggle('active', isBuilding);
    } catch (e) {
      // ignore
    }
  }

  setInterval(refreshStatus, 4000);
  refreshStatus();
  connectTerminalSSE();
})();
