import os
import re
import json
import uuid
import datetime
from config import MEDIA_DIR, THUMBS_DIR, SEEK_DIR, BACKUPS_DIR

class ReorderService:
    def __init__(self):
        self.media_dir = MEDIA_DIR
        self.thumbs_dir = THUMBS_DIR
        self.seek_dir = SEEK_DIR
        self.backups_dir = BACKUPS_DIR

    def _safe_rename(self, src, dst):
        """Helper to rename if src exists."""
        if os.path.exists(src):
            os.rename(src, dst)
            return True
        return False

    def execute_reorder(self, requested_order):
        """
        Executes a 2-phase collision-free renumbering of media files and their
        associated thumbnail and seek sprite assets.
        Format: insta vid ({N}).{ext}
        """
        if not requested_order:
            return {'success': False, 'error': 'No files supplied for reordering.'}

        # Step 1: Manifest Calculation
        operations = []
        batch_id = uuid.uuid4().hex[:8]
        timestamp_str = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        for idx, orig_name in enumerate(requested_order, start=1):
            if not orig_name:
                continue

            orig_path = os.path.join(self.media_dir, orig_name)
            if not os.path.exists(orig_path):
                continue

            _, ext = os.path.splitext(orig_name)
            final_name = f"insta vid ({idx}){ext}"

            # Only participate if name actually changes
            if orig_name == final_name:
                continue

            temp_name = f"__stage_rename_{batch_id}_{idx}{ext}"

            # Thumbnails paths
            orig_thumb = f"{orig_name}.jpg"
            temp_thumb = f"{temp_name}.jpg"
            final_thumb = f"{final_name}.jpg"

            # Seek sprite paths
            orig_seek = f"{orig_name}.jpg"
            temp_seek = f"{temp_name}.jpg"
            final_seek = f"{final_name}.jpg"

            operations.append({
                'original_name': orig_name,
                'temp_name': temp_name,
                'final_name': final_name,
                'original_thumb': orig_thumb,
                'temp_thumb': temp_thumb,
                'final_thumb': final_thumb,
                'original_seek': orig_seek,
                'temp_seek': temp_seek,
                'final_seek': final_seek,
            })

        if not operations:
            return {
                'success': True,
                'renamed_count': 0,
                'message': 'Files are already in the requested order.'
            }

        # Step 2: Safety Backup Journaling
        backup_filename = f"rename_backup_{timestamp_str}.json"
        backup_filepath = os.path.join(self.backups_dir, backup_filename)

        journal = {
            'timestamp': datetime.datetime.utcnow().isoformat() + "Z",
            'backup_id': timestamp_str,
            'total_files': len(requested_order),
            'renamed_count': len(operations),
            'operations': operations
        }

        with open(backup_filepath, 'w') as f:
            json.dump(journal, f, indent=2)

        # Step 3: Phase 1 - Intermediate Token Staging (UUID-guaranteed)
        phase1_completed = []
        try:
            for op in operations:
                # 1. Media
                s_media = os.path.join(self.media_dir, op['original_name'])
                t_media = os.path.join(self.media_dir, op['temp_name'])
                self._safe_rename(s_media, t_media)

                # 2. Thumbnail
                s_thumb = os.path.join(self.thumbs_dir, op['original_thumb'])
                t_thumb = os.path.join(self.thumbs_dir, op['temp_thumb'])
                self._safe_rename(s_thumb, t_thumb)

                # 3. Seek sprite
                s_seek = os.path.join(self.seek_dir, op['original_seek'])
                t_seek = os.path.join(self.seek_dir, op['temp_seek'])
                self._safe_rename(s_seek, t_seek)

                phase1_completed.append(op)
        except Exception as e:
            # Atomic rollback of Phase 1
            for op in reversed(phase1_completed):
                self._safe_rename(os.path.join(self.media_dir, op['temp_name']), os.path.join(self.media_dir, op['original_name']))
                self._safe_rename(os.path.join(self.thumbs_dir, op['temp_thumb']), os.path.join(self.thumbs_dir, op['original_thumb']))
                self._safe_rename(os.path.join(self.seek_dir, op['temp_seek']), os.path.join(self.seek_dir, op['original_seek']))
            return {'success': False, 'error': f'Phase 1 staging failed, rolled back: {str(e)}'}

        # Step 4: Phase 2 - Target Sequential Renumbering
        phase2_completed = []
        try:
            for op in operations:
                # 1. Media
                t_media = os.path.join(self.media_dir, op['temp_name'])
                f_media = os.path.join(self.media_dir, op['final_name'])
                self._safe_rename(t_media, f_media)

                # 2. Thumbnail
                t_thumb = os.path.join(self.thumbs_dir, op['temp_thumb'])
                f_thumb = os.path.join(self.thumbs_dir, op['final_thumb'])
                self._safe_rename(t_thumb, f_thumb)

                # 3. Seek sprite
                t_seek = os.path.join(self.seek_dir, op['temp_seek'])
                f_seek = os.path.join(self.seek_dir, op['final_seek'])
                self._safe_rename(t_seek, f_seek)

                phase2_completed.append(op)
        except Exception as e:
            # Atomic rollback of Phase 2
            # 1. Revert completed phase2 back to temp
            for op in reversed(phase2_completed):
                self._safe_rename(os.path.join(self.media_dir, op['final_name']), os.path.join(self.media_dir, op['temp_name']))
                self._safe_rename(os.path.join(self.thumbs_dir, op['final_thumb']), os.path.join(self.thumbs_dir, op['temp_thumb']))
                self._safe_rename(os.path.join(self.seek_dir, op['final_seek']), os.path.join(self.seek_dir, op['temp_seek']))
            # 2. Revert all from temp back to original
            for op in reversed(operations):
                self._safe_rename(os.path.join(self.media_dir, op['temp_name']), os.path.join(self.media_dir, op['original_name']))
                self._safe_rename(os.path.join(self.thumbs_dir, op['temp_thumb']), os.path.join(self.thumbs_dir, op['original_thumb']))
                self._safe_rename(os.path.join(self.seek_dir, op['temp_seek']), os.path.join(self.seek_dir, op['original_seek']))
            return {'success': False, 'error': f'Phase 2 target naming failed, rolled back: {str(e)}'}

        return {
            'success': True,
            'renamed_count': len(operations),
            'backup_id': timestamp_str,
            'backup_file': backup_filename
        }

    def restore_backup(self, backup_id=None):
        """
        Reverses the rename operations in two collision-free phases using a journal.
        If backup_id is None, the most recent backup is restored.
        """
        if not os.path.exists(self.backups_dir):
            return {'success': False, 'error': 'No backups directory found.'}

        backup_file = None
        if backup_id:
            candidate = os.path.join(self.backups_dir, f"rename_backup_{backup_id}.json")
            if os.path.exists(candidate):
                backup_file = candidate
            else:
                candidate = os.path.join(self.backups_dir, backup_id)
                if os.path.exists(candidate):
                    backup_file = candidate

        if not backup_file:
            files = sorted([
                f for f in os.listdir(self.backups_dir)
                if f.startswith("rename_backup_") and f.endswith(".json")
            ], reverse=True)
            if not files:
                return {'success': False, 'error': 'No backup journals found to restore.'}
            backup_file = os.path.join(self.backups_dir, files[0])

        try:
            with open(backup_file, 'r') as f:
                journal = json.load(f)
        except Exception as e:
            return {'success': False, 'error': f'Failed to read backup journal: {str(e)}'}

        operations = journal.get('operations', [])
        if not operations:
            return {'success': False, 'error': 'Journal contains no operations.'}

        batch_id = uuid.uuid4().hex[:8]

        # Phase 1: Move from final_name to temp_name
        for op in operations:
            op['restore_temp_name'] = f"__stage_restore_{batch_id}_{op['original_name']}"
            op['restore_temp_thumb'] = f"__stage_restore_{batch_id}_{op['original_thumb']}"
            op['restore_temp_seek'] = f"__stage_restore_{batch_id}_{op['original_seek']}"

            # Media
            self._safe_rename(
                os.path.join(self.media_dir, op['final_name']),
                os.path.join(self.media_dir, op['restore_temp_name'])
            )
            # Thumb
            self._safe_rename(
                os.path.join(self.thumbs_dir, op['final_thumb']),
                os.path.join(self.thumbs_dir, op['restore_temp_thumb'])
            )
            # Seek
            self._safe_rename(
                os.path.join(self.seek_dir, op['final_seek']),
                os.path.join(self.seek_dir, op['restore_temp_seek'])
            )

        # Phase 2: Move from restore_temp_name back to original_name
        for op in operations:
            self._safe_rename(
                os.path.join(self.media_dir, op['restore_temp_name']),
                os.path.join(self.media_dir, op['original_name'])
            )
            self._safe_rename(
                os.path.join(self.thumbs_dir, op['restore_temp_thumb']),
                os.path.join(self.thumbs_dir, op['original_thumb'])
            )
            self._safe_rename(
                os.path.join(self.seek_dir, op['restore_temp_seek']),
                os.path.join(self.seek_dir, op['original_seek'])
            )

        # Archive restored journal
        try:
            archived = backup_file + ".restored"
            os.rename(backup_file, archived)
        except Exception:
            pass

        return {
            'success': True,
            'restored_count': len(operations),
            'timestamp': journal.get('timestamp')
        }

    def list_backups(self):
        if not os.path.exists(self.backups_dir):
            return []

        backups = []
        files = sorted([
            f for f in os.listdir(self.backups_dir)
            if f.startswith("rename_backup_") and f.endswith(".json")
        ], reverse=True)

        for fname in files:
            fpath = os.path.join(self.backups_dir, fname)
            try:
                with open(fpath, 'r') as f:
                    data = json.load(f)
                    backups.append({
                        'backup_id': data.get('backup_id'),
                        'filename': fname,
                        'timestamp': data.get('timestamp'),
                        'total_files': data.get('total_files'),
                        'renamed_count': data.get('renamed_count')
                    })
            except Exception:
                pass
        return backups

reorder_service = ReorderService()
