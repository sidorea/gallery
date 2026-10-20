(() => {
  // Application State
  const state = {
    items: [], // [{ filename, type, size, thumb, src }]
    filteredItems: [],
    filterType: 'all',
    searchQuery: '',
    rangeStart: null,
    rangeEnd: null,
    sortableInstance: null,
    currentVersion: 'v1',
    nextVersion: 'v2',
    playerPort: 8083,
    activeWatchIndex: -1,
    audioGain: 1.0,
    audioCtx: null,
    gainNode: null,
    limiter: null,
    imageZoom: 1.0,
    lastRestoreTimestamp: ''
  };

  // DOM Elements
  const mediaGrid = document.getElementById('mediaGrid');
  const btnApplyReorder = document.getElementById('btnApplyReorder');
  const reorderCountBadge = document.getElementById('reorderCountBadge');
  const btnUndoRestore = document.getElementById('btnUndoRestore');
  const lastRestoreTimestamp = document.getElementById('lastRestoreTimestamp');
  const btnHistory = document.getElementById('btnHistory');
  const btnCreateDocker = document.getElementById('btnCreateDocker');
  const nextVersionBadge = document.getElementById('nextVersionBadge');
  const btnOpenPlayer = document.getElementById('btnOpenPlayer');
  const btnOpenUpload = document.getElementById('btnOpenUpload');
  const totalFilesPill = document.getElementById('totalFilesPill');
  const totalVideosPill = document.getElementById('totalVideosPill');
  const totalImagesPill = document.getElementById('totalImagesPill');
  const pendingChangesPill = document.getElementById('pendingChangesPill');
  const searchInput = document.getElementById('searchInput');
  const rangeStartInput = document.getElementById('rangeStartInput');
  const rangeEndInput = document.getElementById('rangeEndInput');
  const btnApplyRange = document.getElementById('btnApplyRange');
  const btnResetRange = document.getElementById('btnResetRange');
  const filterTabs = document.querySelectorAll('.filter-tab');
  const toastBox = document.getElementById('toastBox');

  // Watch Modal Elements
  const watchModal = document.getElementById('watchModal');
  const btnCloseWatchModal = document.getElementById('btnCloseWatchModal');
  const modalPosBadge = document.getElementById('modalPosBadge');
  const modalFilename = document.getElementById('modalFilename');
  const modalDetails = document.getElementById('modalDetails');
  const modalVideo = document.getElementById('modalVideo');
  const modalImage = document.getElementById('modalImage');
  const imageViewerBox = document.getElementById('imageViewerBox');
  const imageControls = document.getElementById('imageControls');
  const btnZoomIn = document.getElementById('btnZoomIn');
  const btnZoomOut = document.getElementById('btnZoomOut');
  const btnZoomReset = document.getElementById('btnZoomReset');
  const modalBtnBoost = document.getElementById('modalBtnBoost');
  const modalBtnLoop = document.getElementById('modalBtnLoop');
  const modalBtnFullscreen = document.getElementById('modalBtnFullscreen');
  const modalBtnPrev = document.getElementById('modalBtnPrev');
  const modalBtnNext = document.getElementById('modalBtnNext');

  // History Modal Elements
  const historyModal = document.getElementById('historyModal');
  const btnCloseHistoryModal = document.getElementById('btnCloseHistoryModal');
  const historyList = document.getElementById('historyList');

  // Docker Modal Elements
  const dockerModal = document.getElementById('dockerModal');
  const btnCloseDockerModal = document.getElementById('btnCloseDockerModal');
  const dockerTerminalOutput = document.getElementById('dockerTerminalOutput');
  const pushDockerHubCheck = document.getElementById('pushDockerHubCheck');
  const btnCopyDockerLogs = document.getElementById('btnCopyDockerLogs');
  const btnStartSnapshotExec = document.getElementById('btnStartSnapshotExec');

  function showToast(msg, duration = 4000) {
    toastBox.textContent = msg;
    toastBox.classList.add('show');
    setTimeout(() => toastBox.classList.remove('show'), duration);
  }

  function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  function formatTime(sec) {
    if (isNaN(sec) || sec <= 0) return '00:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }

  // Load Monorepo & Version Info
  async function loadAppInfo() {
    try {
      const res = await fetch('/api/info');
      const data = await res.json();
      state.currentVersion = data.version || 'v1';
      state.playerPort = data.player_port || 8083;

      const num = parseInt(state.currentVersion.replace(/\D/g, '') || '1', 10);
      state.nextVersion = `v${num + 1}`;
      nextVersionBadge.textContent = state.nextVersion;

      const host = window.location.hostname;
      btnOpenPlayer.href = `http://${host}:${state.playerPort}/`;
      btnOpenUpload.href = `http://${host}/`;
    } catch (e) {
      console.warn("Could not load app info:", e);
    }
  }

  // Load Media Library
  async function loadLibrary() {
    try {
      const res = await fetch('/api/files');
      state.items = await res.json();
      renderGrid();
      updateMetrics();
      loadLatestBackupTimestamp();
    } catch (err) {
      mediaGrid.innerHTML = `<div style="padding:40px; text-align:center; color:var(--danger);">Error loading library: ${err.message}</div>`;
    }
  }

  async function loadLatestBackupTimestamp() {
    try {
      const res = await fetch('/api/reorder/backups');
      const backups = await res.json();
      if (backups && backups.length > 0) {
        state.lastRestoreTimestamp = backups[0].timestamp || backups[0].backup_id;
        lastRestoreTimestamp.textContent = `(${state.lastRestoreTimestamp.split('T')[1]?.substring(0, 5) || state.lastRestoreTimestamp})`;
      } else {
        lastRestoreTimestamp.textContent = '';
      }
    } catch (e) {}
  }

  // Render Drag & Drop Grid
  function renderGrid() {
    mediaGrid.innerHTML = '';
    applyFilters();

    if (state.filteredItems.length === 0) {
      mediaGrid.innerHTML = `<div style="padding:40px; text-align:center; grid-column: 1 / -1; color:var(--text-muted);">No media files match your filter query.</div>`;
      return;
    }

    state.filteredItems.forEach((item, index) => {
      const card = createCardElement(item, index);
      mediaGrid.appendChild(card);
    });

    initSortable();
    recalculateRenumberMath();
  }

  function createCardElement(item, index) {
    const card = document.createElement('div');
    card.className = 'media-card';
    card.dataset.filename = item.filename;
    card.dataset.type = item.type;
    card.dataset.index = index;

    const ext = (item.filename.split('.').pop() || '').toUpperCase();
    const isVid = item.type === 'video';

    card.innerHTML = `
      <div class="thumb-container">
        <span class="card-badge-pos">#${index + 1}</span>
        <span class="card-badge-type ${isVid ? 'badge-video' : 'badge-image'}">${ext}</span>
        <img class="thumb-img" src="${item.thumb}" loading="lazy" alt="${item.filename}" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'320\\' height=\\'180\\' fill=\\'%231e293b\\'><rect width=\\'100%\\' height=\\'100%\\'/></svg>'">
        ${isVid ? `<div class="play-overlay-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg></div>` : ''}
      </div>

      <div class="card-body">
        <div class="card-title-row">
          <span class="card-filename" title="${item.filename}">${item.filename}</span>
          <span class="drag-handle" title="Drag to reorder sequence">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="9" cy="5" r="1"></circle><circle cx="9" cy="12" r="1"></circle><circle cx="9" cy="19" r="1"></circle>
              <circle cx="15" cy="5" r="1"></circle><circle cx="15" cy="12" r="1"></circle><circle cx="15" cy="19" r="1"></circle>
            </svg>
          </span>
        </div>

        <div class="rename-preview-pill" data-role="preview-pill">
          ➔ Calculating...
        </div>

        <div class="card-footer-row">
          <span class="card-filesize">${formatBytes(item.size)}</span>
          <button class="btn-jump" title="Quick Jump to numeric position">Move to #</button>
        </div>
      </div>
    `;

    // Click on thumbnail opens Watch Modal
    card.querySelector('.thumb-container').addEventListener('click', () => {
      openWatchModal(item.filename);
    });

    // Quick Jump button
    card.querySelector('.btn-jump').addEventListener('click', (e) => {
      e.stopPropagation();
      promptQuickJump(card);
    });

    return card;
  }

  // Quick Jump Dialog
  function promptQuickJump(card) {
    const currentPos = Array.from(mediaGrid.children).indexOf(card) + 1;
    const total = mediaGrid.children.length;
    const target = prompt(`Enter target sequence number for "${card.dataset.filename}" (1 to ${total}):`, currentPos);
    if (!target) return;

    const targetNum = parseInt(target, 10);
    if (isNaN(targetNum) || targetNum < 1 || targetNum > total) {
      alert(`Invalid position. Please enter a number between 1 and ${total}.`);
      return;
    }

    const targetIndex = targetNum - 1;
    const children = Array.from(mediaGrid.children);
    if (targetIndex >= children.length) {
      mediaGrid.appendChild(card);
    } else {
      mediaGrid.insertBefore(card, children[targetIndex]);
    }

    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    recalculateRenumberMath();
  }

  // Initialize SortableJS
  function initSortable() {
    if (state.sortableInstance) {
      state.sortableInstance.destroy();
    }

    state.sortableInstance = new Sortable(mediaGrid, {
      animation: 180,
      handle: '.drag-handle, .thumb-container',
      ghostClass: 'sortable-ghost',
      chosenClass: 'sortable-chosen',
      touchStartThreshold: 4,
      onEnd: () => {
        recalculateRenumberMath();
      }
    });
  }

  // Real-Time Renumbering Calculation across whole grid
  function recalculateRenumberMath() {
    const cards = Array.from(mediaGrid.querySelectorAll('.media-card'));
    let shiftedCount = 0;

    cards.forEach((card, index) => {
      const positionNum = index + 1;
      const origName = card.dataset.filename;
      const ext = origName.substring(origName.lastIndexOf('.'));
      const targetName = `insta vid (${positionNum})${ext}`;

      // Update position badge
      const posBadge = card.querySelector('.card-badge-pos');
      if (posBadge) posBadge.textContent = `#${positionNum}`;

      // Update preview pill
      const previewPill = card.querySelector('[data-role="preview-pill"]');
      if (previewPill) {
        if (origName === targetName) {
          previewPill.textContent = `✓ ${targetName}`;
          previewPill.classList.add('unchanged');
        } else {
          previewPill.textContent = `➔ ${targetName}`;
          previewPill.classList.remove('unchanged');
          shiftedCount++;
        }
      }
    });

    // Update Action Button
    reorderCountBadge.textContent = shiftedCount;
    btnApplyReorder.disabled = (shiftedCount === 0);

    // Update Metric Pill
    if (shiftedCount > 0) {
      pendingChangesPill.style.display = 'inline-flex';
      pendingChangesPill.textContent = `${shiftedCount} Shifts Pending`;
    } else {
      pendingChangesPill.style.display = 'none';
    }
  }

  // Filters & Search
  function applyFilters() {
    let result = state.items;

    if (state.filterType === 'video') {
      result = result.filter(i => i.type === 'video');
    } else if (state.filterType === 'image') {
      result = result.filter(i => i.type === 'image');
    }

    if (state.searchQuery) {
      const q = state.searchQuery.toLowerCase();
      result = result.filter(i => i.filename.toLowerCase().includes(q));
    }

    if (state.rangeStart !== null && state.rangeEnd !== null) {
      result = result.slice(state.rangeStart - 1, state.rangeEnd);
    }

    state.filteredItems = result;
  }

  searchInput.addEventListener('input', (e) => {
    state.searchQuery = e.target.value.trim();
    renderGrid();
  });

  btnApplyRange.addEventListener('click', () => {
    const s = parseInt(rangeStartInput.value, 10);
    const e = parseInt(rangeEndInput.value, 10);
    if (!isNaN(s) && !isNaN(e) && s > 0 && e >= s) {
      state.rangeStart = s;
      state.rangeEnd = e;
      renderGrid();
    } else {
      alert("Please enter a valid range (e.g. From 1 to 50).");
    }
  });

  btnResetRange.addEventListener('click', () => {
    rangeStartInput.value = '';
    rangeEndInput.value = '';
    state.rangeStart = null;
    state.rangeEnd = null;
    renderGrid();
  });

  filterTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      filterTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      state.filterType = tab.dataset.filter;
      renderGrid();
    });
  });

  function updateMetrics() {
    totalFilesPill.textContent = `Total: ${state.items.length} Files`;
    totalVideosPill.textContent = `Videos: ${state.items.filter(i => i.type === 'video').length}`;
    totalImagesPill.textContent = `Images: ${state.items.filter(i => i.type === 'image').length}`;
  }

  // Apply Reorder & Rename Action (2-Phase Atomic Engine)
  btnApplyReorder.addEventListener('click', async () => {
    const cards = Array.from(mediaGrid.querySelectorAll('.media-card'));
    const order = cards.map(c => c.dataset.filename);

    btnApplyReorder.disabled = true;
    btnApplyReorder.innerHTML = `Renumbering...`;

    try {
      const res = await fetch('/api/reorder/rename', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order })
      });
      const data = await res.json();

      if (data.success) {
        showToast(`Successfully renumbered ${data.renamed_count} files (Backup: ${data.backup_id})`);
        await loadLibrary();
      } else {
        alert(`Renumber failed: ${data.error}`);
      }
    } catch (e) {
      alert(`Network error: ${e.message}`);
    } finally {
      btnApplyReorder.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
          <polyline points="17 21 17 13 7 13 7 21"></polyline>
          <polyline points="7 3 7 8 15 8"></polyline>
        </svg>
        Apply Reorder & Rename
        <span class="btn-pill-count" id="reorderCountBadge">0</span>
      `;
      recalculateRenumberMath();
    }
  });

  // Undo / Restore Last
  btnUndoRestore.addEventListener('click', async () => {
    if (!confirm("Are you sure you want to restore the library to the state before the last rename session?")) return;

    try {
      const res = await fetch('/api/reorder/restore', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const data = await res.json();

      if (data.success) {
        showToast(`Restored ${data.restored_count} files to previous state!`);
        await loadLibrary();
      } else {
        alert(`Restore failed: ${data.error}`);
      }
    } catch (e) {
      alert(`Error: ${e.message}`);
    }
  });

  // History Inspector Modal
  btnHistory.addEventListener('click', async () => {
    historyModal.classList.add('open');
    historyList.innerHTML = `<div style="padding:24px; text-align:center; color:var(--text-muted);">Loading backups...</div>`;
    try {
      const res = await fetch('/api/reorder/backups');
      const backups = await res.json();
      if (!backups || backups.length === 0) {
        historyList.innerHTML = `<div style="padding:24px; text-align:center; color:var(--text-muted);">No backup journals found.</div>`;
        return;
      }

      historyList.innerHTML = '';
      backups.forEach(b => {
        const item = document.createElement('div');
        item.className = 'history-item';
        item.innerHTML = `
          <div class="history-item-info">
            <h4>Session ID: ${b.backup_id}</h4>
            <p>${b.timestamp} &bull; ${b.renamed_count} files shifted (Total: ${b.total_files})</p>
          </div>
          <button class="btn btn-secondary" style="padding:6px 14px; font-size:0.8rem;" data-id="${b.backup_id}">
            Restore This Snapshot
          </button>
        `;
        item.querySelector('button').addEventListener('click', async () => {
          if (confirm(`Restore session snapshot ${b.backup_id}?`)) {
            historyModal.classList.remove('open');
            const rRes = await fetch('/api/reorder/restore', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ backup_id: b.backup_id })
            });
            const rData = await rRes.json();
            if (rData.success) {
              showToast(`Restored session ${b.backup_id}!`);
              await loadLibrary();
            } else {
              alert(`Failed: ${rData.error}`);
            }
          }
        });
        historyList.appendChild(item);
      });
    } catch (e) {
      historyList.innerHTML = `<div style="color:var(--danger); padding:24px;">Error loading history: ${e.message}</div>`;
    }
  });

  btnCloseHistoryModal.addEventListener('click', () => historyModal.classList.remove('open'));
  historyModal.addEventListener('click', (e) => { if (e.target === historyModal) historyModal.classList.remove('open'); });

  // Media Watch Modal with HTTP 206 Streaming & Audio Booster
  function initAudioContext() {
    if (state.audioCtx) return;
    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      state.audioCtx = new AudioContextClass();
      const source = state.audioCtx.createMediaElementSource(modalVideo);
      state.gainNode = state.audioCtx.createGain();
      state.limiter = state.audioCtx.createDynamicsCompressor();

      state.limiter.threshold.setValueAtTime(-1.0, state.audioCtx.currentTime);
      state.limiter.knee.setValueAtTime(0, state.audioCtx.currentTime);
      state.limiter.ratio.setValueAtTime(20.0, state.audioCtx.currentTime);
      state.limiter.attack.setValueAtTime(0.001, state.audioCtx.currentTime);
      state.limiter.release.setValueAtTime(0.1, state.audioCtx.currentTime);

      source.connect(state.gainNode);
      state.gainNode.connect(state.limiter);
      state.limiter.connect(state.audioCtx.destination);
    } catch (e) {
      console.warn("Audio booster init:", e);
    }
  }

  function openWatchModal(filename) {
    const idx = state.items.findIndex(i => i.filename === filename);
    if (idx === -1) return;
    state.activeWatchIndex = idx;
    const item = state.items[idx];

    modalPosBadge.textContent = `#${idx + 1}`;
    modalFilename.textContent = item.filename;
    modalFilename.title = item.filename;
    watchModal.classList.add('open');

    if (item.type === 'video') {
      imageViewerBox.style.display = 'none';
      imageControls.style.display = 'none';
      modalVideo.style.display = 'block';
      modalBtnBoost.style.display = 'inline-flex';
      modalBtnLoop.style.display = 'inline-flex';

      modalVideo.src = item.src;
      modalVideo.onloadedmetadata = () => {
        modalDetails.textContent = `${modalVideo.videoWidth}x${modalVideo.videoHeight} • ${formatTime(modalVideo.duration)} • ${formatBytes(item.size)}`;
      };
      modalVideo.play().catch(() => {});
      initAudioContext();
    } else {
      modalVideo.pause();
      modalVideo.src = '';
      modalVideo.style.display = 'none';
      modalBtnBoost.style.display = 'none';
      modalBtnLoop.style.display = 'none';

      imageViewerBox.style.display = 'flex';
      imageControls.style.display = 'flex';
      state.imageZoom = 1.0;
      modalImage.style.transform = `scale(1.0)`;
      modalImage.src = item.src;
      modalImage.onload = () => {
        modalDetails.textContent = `${modalImage.naturalWidth}x${modalImage.naturalHeight} Photo • ${formatBytes(item.size)}`;
      };
    }
  }

  function closeWatchModal() {
    modalVideo.pause();
    modalVideo.src = '';
    watchModal.classList.remove('open');
  }

  btnCloseWatchModal.addEventListener('click', closeWatchModal);
  watchModal.addEventListener('click', (e) => { if (e.target === watchModal) closeWatchModal(); });

  modalBtnPrev.addEventListener('click', () => {
    if (state.activeWatchIndex > 0) {
      openWatchModal(state.items[state.activeWatchIndex - 1].filename);
    }
  });
  modalBtnNext.addEventListener('click', () => {
    if (state.activeWatchIndex < state.items.length - 1) {
      openWatchModal(state.items[state.activeWatchIndex + 1].filename);
    }
  });

  // Image Zoom Controls
  btnZoomIn.addEventListener('click', () => {
    state.imageZoom = Math.min(3.0, state.imageZoom + 0.25);
    modalImage.style.transform = `scale(${state.imageZoom})`;
  });
  btnZoomOut.addEventListener('click', () => {
    state.imageZoom = Math.max(0.5, state.imageZoom - 0.25);
    modalImage.style.transform = `scale(${state.imageZoom})`;
  });
  btnZoomReset.addEventListener('click', () => {
    state.imageZoom = 1.0;
    modalImage.style.transform = `scale(1.0)`;
  });

  // Video Loop Toggle
  modalBtnLoop.addEventListener('click', () => {
    modalVideo.loop = !modalVideo.loop;
    modalBtnLoop.textContent = modalVideo.loop ? 'Loop: On' : 'Loop: Off';
    modalBtnLoop.style.background = modalVideo.loop ? 'var(--primary-light)' : '';
  });

  // Video Fullscreen
  modalBtnFullscreen.addEventListener('click', () => {
    if (!document.fullscreenElement) {
      document.getElementById('viewerContentBox').requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  });

  // Audio Booster Toggle (100% -> 150% -> 200% -> 300%)
  const boostSteps = [1.0, 1.5, 2.0, 3.0];
  modalBtnBoost.addEventListener('click', () => {
    initAudioContext();
    if (state.audioCtx && state.audioCtx.state === 'suspended') {
      state.audioCtx.resume();
    }
    let idx = boostSteps.indexOf(state.audioGain);
    idx = (idx + 1) % boostSteps.length;
    state.audioGain = boostSteps[idx];
    if (state.gainNode && state.audioCtx) {
      state.gainNode.gain.setValueAtTime(state.audioGain, state.audioCtx.currentTime);
    }
    modalBtnBoost.textContent = `Boost Audio: ${Math.round(state.audioGain * 100)}%`;
  });

  // Keyboard navigation for Watch Modal
  window.addEventListener('keydown', (e) => {
    if (!watchModal.classList.contains('open')) return;
    if (e.code === 'Escape') {
      closeWatchModal();
    } else if (e.code === 'Space') {
      e.preventDefault();
      if (modalVideo.paused) modalVideo.play();
      else modalVideo.pause();
    } else if (e.code === 'ArrowRight') {
      modalVideo.currentTime = Math.min(modalVideo.duration, modalVideo.currentTime + 5);
    } else if (e.code === 'ArrowLeft') {
      modalVideo.currentTime = Math.max(0, modalVideo.currentTime - 5);
    }
  });

  // Docker Snapshot Studio & SSE
  btnCreateDocker.addEventListener('click', () => {
    dockerModal.classList.add('open');
  });

  btnCloseDockerModal.addEventListener('click', () => dockerModal.classList.remove('open'));
  dockerModal.addEventListener('click', (e) => { if (e.target === dockerModal) dockerModal.classList.remove('open'); });

  let dockerEventSource = null;
  function connectDockerSSE() {
    if (dockerEventSource) return;
    dockerEventSource = new EventSource('/api/docker-snapshot/stream');
    dockerEventSource.onmessage = (e) => {
      if (dockerTerminalOutput.textContent === 'Awaiting snapshot command...') {
        dockerTerminalOutput.textContent = '';
      }
      dockerTerminalOutput.textContent += e.data + '\n';
      dockerTerminalOutput.scrollTop = dockerTerminalOutput.scrollHeight;
    };
  }

  btnStartSnapshotExec.addEventListener('click', async () => {
    btnStartSnapshotExec.disabled = true;
    connectDockerSSE();
    const push = pushDockerHubCheck.checked;
    try {
      const res = await fetch('/api/docker-snapshot/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ push })
      });
      const data = await res.json();
      if (!data.success) {
        alert(data.message);
        btnStartSnapshotExec.disabled = false;
      }
    } catch (e) {
      alert(`Error starting snapshot: ${e.message}`);
      btnStartSnapshotExec.disabled = false;
    }
  });

  btnCopyDockerLogs.addEventListener('click', () => {
    navigator.clipboard.writeText(dockerTerminalOutput.textContent).then(() => {
      btnCopyDockerLogs.textContent = 'Copied!';
      setTimeout(() => { btnCopyDockerLogs.textContent = 'Copy Logs'; }, 2000);
    });
  });

  // Init
  loadAppInfo();
  loadLibrary();
})();
