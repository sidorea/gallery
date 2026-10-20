import os
import signal
import subprocess
import threading
import time
import shutil
from queue import Queue, Empty
from config import DOCKER_SCRIPT_DIR, UPDATE_SCRIPT_PATH, VERSION_FILE

class DockerBuildService:
    def __init__(self):
        self.lock = threading.Lock()
        self.is_building = False
        self.current_process = None
        self.listeners = []
        self.log_history = []
        self.last_status = "idle" # idle, building, success, failed, aborted

    def add_listener(self):
        q = Queue()
        with self.lock:
            # Replay history to newly connected listener
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

    def start_build(self):
        with self.lock:
            if self.is_building:
                return False, "Build is already in progress."

            if not os.path.exists(UPDATE_SCRIPT_PATH):
                return False, f"Build script not found at {UPDATE_SCRIPT_PATH}"

            self.is_building = True
            self.last_status = "building"
            self.log_history = []

        thread = threading.Thread(target=self._run_build_worker, daemon=True)
        thread.start()
        return True, "Docker build initiated."

    def _run_build_worker(self):
        cmd = ["bash", UPDATE_SCRIPT_PATH]
        self._broadcast(f"[SYS] Starting build execution: {' '.join(cmd)}\n")

        try:
            self.current_process = subprocess.Popen(
                cmd,
                cwd=DOCKER_SCRIPT_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                preexec_fn=os.setsid
            )

            for line in iter(self.current_process.stdout.readline, ''):
                self._broadcast(line)

            self.current_process.stdout.close()
            return_code = self.current_process.wait()

            with self.lock:
                if return_code == 0:
                    self.last_status = "success"
                    self._broadcast("\n[SYS] Build completed successfully!\n")
                elif self.last_status == "aborted":
                    self._broadcast("\n[SYS] Build was aborted by user. Safety rollback applied.\n")
                else:
                    self.last_status = "failed"
                    self._broadcast(f"\n[SYS] Build failed with return code {return_code}.\n")

        except Exception as e:
            with self.lock:
                self.last_status = "failed"
            self._broadcast(f"\n[SYS] Error running build: {str(e)}\n")
            self.rollback_safety_backups()
        finally:
            with self.lock:
                self.is_building = False
                self.current_process = None

    def abort_build(self):
        with self.lock:
            if not self.is_building or not self.current_process:
                return False, "No active build to abort."

            self.last_status = "aborted"
            try:
                # Send SIGINT to process group so bash trap handles rollback cleanly
                pgid = os.getpgid(self.current_process.pid)
                os.killpg(pgid, signal.SIGINT)
                self._broadcast("\n[SYS] Sent SIGINT to build process group...\n")
            except Exception as e:
                # Fallback to direct process termination
                try:
                    self.current_process.terminate()
                except Exception:
                    pass
                self._broadcast(f"\n[SYS] Process kill error: {str(e)}\n")

        # Give bash trap time to execute, then ensure rollback safety
        time.sleep(1.5)
        self.rollback_safety_backups()
        return True, "Build abortion requested."

    def rollback_safety_backups(self):
        """Python safety fallback ensuring any remaining .bak files are restored."""
        targets = [
            (f"{VERSION_FILE}.bak", VERSION_FILE),
            (os.path.join(DOCKER_SCRIPT_DIR, "Dockerfile.bak"), os.path.join(DOCKER_SCRIPT_DIR, "Dockerfile")),
            (os.path.join(DOCKER_SCRIPT_DIR, "run-container.sh.bak"), os.path.join(DOCKER_SCRIPT_DIR, "run-container.sh")),
        ]
        for bak_path, orig_path in targets:
            if os.path.exists(bak_path):
                try:
                    shutil.move(bak_path, orig_path)
                    self._broadcast(f"[ROLLBACK] Restored backup: {os.path.basename(orig_path)}\n")
                except Exception as ex:
                    self._broadcast(f"[ROLLBACK] Failed to restore {orig_path}: {ex}\n")

    def get_status(self):
        with self.lock:
            return {
                "is_building": self.is_building,
                "status": self.last_status,
                "log_count": len(self.log_history)
            }

docker_service = DockerBuildService()
