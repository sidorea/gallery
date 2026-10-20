import os
import shutil
import subprocess
import threading
import time
from queue import Queue, Empty
from config import VERSION_FILE, DOCKERFILE_PATH, RUN_SCRIPT_PATH, CONTAINER_NAME, DOCKER_REPO, MEDIA_DIR, MEDIA_PLAYLIST_DIR

class DockerSnapshotService:
    def __init__(self):
        self.lock = threading.Lock()
        self.is_running = False
        self.listeners = []
        self.log_history = []
        self.last_status = "idle"

    def add_listener(self):
        q = Queue()
        with self.lock:
            for line in self.log_history:
                q.put(line)
            self.listeners.append(q)
        return q

    def remove_listener(self, q):
        with self.lock:
            if q in self.listeners:
                self.listeners.remove(q)

    def _broadcast(self, line):
        with self.lock:
            self.log_history.append(line)
            for q in list(self.listeners):
                try:
                    q.put_nowait(line)
                except Exception:
                    pass

    def start_snapshot(self, push_to_hub=False):
        with self.lock:
            if self.is_running:
                return False, "Docker snapshot operation is already running."

            self.is_running = True
            self.last_status = "running"
            self.log_history = []

        thread = threading.Thread(target=self._run_snapshot_worker, args=(push_to_hub,), daemon=True)
        thread.start()
        return True, "Container snapshot initiated."

    def _run_snapshot_worker(self, push_to_hub):
        self._broadcast("=== Initiating Docker Container Snapshot Studio ===\n")
        self._broadcast(f"Active Media Container: {CONTAINER_NAME}\n")

        # 1. Read current version
        if not os.path.exists(VERSION_FILE):
            curr_tag = "v1"
        else:
            try:
                with open(VERSION_FILE, 'r') as f:
                    curr_tag = f.read().strip() or "v1"
            except Exception:
                curr_tag = "v1"

        curr_num_str = curr_tag.lstrip('v')
        try:
            curr_num = int(curr_num_str)
        except ValueError:
            curr_num = 1
        next_num = curr_num + 1
        next_tag = f"v{next_num}"
        target_image = f"{DOCKER_REPO}:{next_tag}"
        latest_image = f"{DOCKER_REPO}:latest"

        self._broadcast(f"Current Governance Tag: {curr_tag}\n")
        self._broadcast(f"New Target Tag        : {next_tag} ({target_image})\n")

        # Create safety backups
        bak_version = f"{VERSION_FILE}.bak"
        bak_dockerfile = f"{DOCKERFILE_PATH}.bak"
        bak_run = f"{RUN_SCRIPT_PATH}.bak"

        try:
            if os.path.exists(VERSION_FILE):
                shutil.copy2(VERSION_FILE, bak_version)
            if os.path.exists(DOCKERFILE_PATH):
                shutil.copy2(DOCKERFILE_PATH, bak_dockerfile)
            if os.path.exists(RUN_SCRIPT_PATH):
                shutil.copy2(RUN_SCRIPT_PATH, bak_run)
        except Exception as e:
            self._broadcast(f"[ERROR] Failed to create safety backups: {e}\n")
            with self.lock:
                self.is_running = False
                self.last_status = "failed"
            return

        temp_container = f"media-snapshot-worker-{next_num}"
        try:
            # 2. Create export container with all active media files
            self._broadcast(f"[PREPARE] Creating filesystem staging container: {temp_container}...\n")
            subprocess.run(
                ["docker", "rm", "-f", temp_container],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            create_proc = subprocess.run(
                ["docker", "create", "--name", temp_container, f"{DOCKER_REPO}:{curr_tag}"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
            )

            if os.path.exists(MEDIA_DIR):
                self._broadcast(f"[COPY] Syncing active library into container rootfs: {MEDIA_DIR}...\n")
                subprocess.run(
                    ["docker", "cp", f"{MEDIA_DIR}/.", f"{temp_container}:/usr/share/nginx/html/files/"],
                    check=True, stdout=subprocess.DEVNULL
                )

            # 3. Export and Import into 1 single layer
            self._broadcast("[EXPORT] Streaming container filesystem into single consolidated layer...\n")
            export_cmd = f"docker export {temp_container} | docker import --change 'EXPOSE 80 9083' --change 'CMD [\"/entrypoint.sh\"]' - {target_image}"
            proc = subprocess.Popen(
                export_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = proc.communicate()
            subprocess.run(["docker", "rm", "-f", temp_container], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            if proc.returncode != 0:
                self._broadcast(f"[ERROR] Export/import failed: {stderr}\n")
                self._revert_backups(bak_version, bak_dockerfile, bak_run)
                with self.lock:
                    self.is_running = False
                    self.last_status = "failed"
                return

            self._broadcast(f"[IMPORT] Image created: {stdout.strip()}\n")

            # Tag latest
            subprocess.run(["docker", "tag", target_image, latest_image], check=True)
            self._broadcast(f"[TAG] Tagged {latest_image}\n")

            # 4. Verify Layer Count
            self._broadcast("[VERIFY] Verifying 1-layer filesystem consolidation...\n")
            inspect_proc = subprocess.run(
                ["docker", "inspect", "--format", "{{len .RootFS.Layers}}", target_image],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            layer_count = inspect_proc.stdout.strip()
            self._broadcast(f"[VERIFY] Layer count: {layer_count}\n")

            if layer_count != "1":
                self._broadcast(f"[ERROR] Layer count verification failed (Expected 1, got {layer_count})\n")
                self._revert_backups(bak_version, bak_dockerfile, bak_run)
                with self.lock:
                    self.is_running = False
                    self.last_status = "failed"
                return

            # 5. Update .version, Dockerfile, run-container.sh
            self._broadcast(f"[UPDATE] Updating {VERSION_FILE} to {next_tag}...\n")
            with open(VERSION_FILE, 'w') as f:
                f.write(f"{next_tag}\n")

            if os.path.exists(DOCKERFILE_PATH):
                self._broadcast(f"[UPDATE] Updating FROM tag in {DOCKERFILE_PATH}...\n")
                with open(DOCKERFILE_PATH, 'r') as f:
                    df_content = f.read()
                new_df = []
                for line in df_content.splitlines():
                    if line.startswith("FROM "):
                        new_df.append(f"FROM {target_image}")
                    else:
                        new_df.append(line)
                with open(DOCKERFILE_PATH, 'w') as f:
                    f.write("\n".join(new_df) + "\n")

            if os.path.exists(RUN_SCRIPT_PATH):
                self._broadcast(f"[UPDATE] Updating target image in {RUN_SCRIPT_PATH}...\n")
                subprocess.run(
                    ["sed", "-i", f"s|${DOCKER_REPO}:v[0-9]*|${target_image}|g", RUN_SCRIPT_PATH],
                    check=False
                )

            # Restart media-playlist container with new image
            self._broadcast("[DEPLOY] Restarting media-playlist container on port 8083...\n")
            run_script = os.path.join(MEDIA_PLAYLIST_DIR, "run-container.sh")
            if os.path.exists(run_script):
                subprocess.run(["bash", run_script], check=False)

            # Docker Push
            if push_to_hub:
                self._broadcast(f"[PUSH] Pushing {target_image} and {latest_image} to Docker Hub...\n")
                for img_to_push in [target_image, latest_image]:
                    self._broadcast(f"[PUSH] Pushing {img_to_push}...\n")
                    push_proc = subprocess.Popen(
                        ["docker", "push", img_to_push],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                    )
                    for line in iter(push_proc.stdout.readline, ''):
                        self._broadcast(line)
                    push_proc.stdout.close()
                    push_proc.wait()
                self._broadcast("[PUSH] Successfully pushed image and latest to Docker Hub!\n")

            # Clean up backups
            self._remove_backups(bak_version, bak_dockerfile, bak_run)

            self._broadcast("===========================================\n")
            self._broadcast(f"Container snapshot successful! New 1-layer image: {target_image}\n")
            self._broadcast("===========================================\n")

            with self.lock:
                self.last_status = "success"

        except Exception as ex:
            self._broadcast(f"[FATAL] Snapshot error: {str(ex)}\n")
            self._revert_backups(bak_version, bak_dockerfile, bak_run)
            with self.lock:
                self.last_status = "failed"
        finally:
            with self.lock:
                self.is_running = False

    def _revert_backups(self, bak_version, bak_dockerfile, bak_run):
        self._broadcast("[ROLLBACK] Reverting configuration backups...\n")
        if os.path.exists(bak_version):
            shutil.move(bak_version, VERSION_FILE)
        if os.path.exists(bak_dockerfile):
            shutil.move(bak_dockerfile, DOCKERFILE_PATH)
        if os.path.exists(bak_run):
            shutil.move(bak_run, RUN_SCRIPT_PATH)

    def _remove_backups(self, bak_version, bak_dockerfile, bak_run):
        for p in (bak_version, bak_dockerfile, bak_run):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

    def get_status(self):
        with self.lock:
            return {
                "is_running": self.is_running,
                "status": self.last_status,
                "log_count": len(self.log_history)
            }

docker_snapshot_service = DockerSnapshotService()
