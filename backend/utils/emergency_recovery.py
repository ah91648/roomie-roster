"""
Emergency Recovery System for RoomieRoster

This module provides emergency data recovery capabilities:
- Automatic JSON snapshots before write operations
- Emergency restore from backups
- Database-to-JSON fallback mechanism
- Hybrid synchronization for data safety
"""

import os
import json
import gzip
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class EmergencyRecovery:
    """Handles emergency data backup and recovery operations"""

    def __init__(self, backup_dir: str = None):
        """
        Initialize emergency recovery system

        Args:
            backup_dir: Directory for emergency backups (default: backend/emergency_backups/)
        """
        if backup_dir is None:
            backend_dir = Path(__file__).parent.parent
            self.backup_dir = backend_dir / 'emergency_backups'
        else:
            self.backup_dir = Path(backup_dir)

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.max_backups = 10  # Keep last 10 backups
        self.data_dir = Path(__file__).parent.parent / 'data'

    def create_emergency_backup(self, reason: str = "manual") -> Optional[str]:
        """
        Create an emergency backup snapshot of all JSON files

        Args:
            reason: Reason for backup (e.g., "pre_migration", "manual", "auto")

        Returns:
            str: Path to backup file, or None if failed
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"emergency_backup_{timestamp}_{reason}"
        backup_path = self.backup_dir / f"{backup_name}.json.gz"

        try:
            # Collect all data files
            backup_data = {
                'timestamp': datetime.now().isoformat(),
                'reason': reason,
                'files': {}
            }

            json_files = [
                'roommates.json',
                'chores.json',
                'state.json',
                'shopping_list.json',
                'requests.json',
                'laundry_slots.json',
                'blocked_time_slots.json'
            ]

            for filename in json_files:
                file_path = self.data_dir / filename
                if file_path.exists():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            backup_data['files'][filename] = json.load(f)
                        logger.info(f"Backed up {filename}")
                    except Exception as e:
                        logger.error(f"Failed to backup {filename}: {str(e)}")
                        backup_data['files'][filename] = None

            # Write compressed backup
            with gzip.open(backup_path, 'wt', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2)

            logger.info(f"Emergency backup created: {backup_path}")

            # Clean up old backups
            self._cleanup_old_backups()

            return str(backup_path)

        except Exception as e:
            logger.error(f"Failed to create emergency backup: {str(e)}")
            return None

    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available emergency backups

        Returns:
            List of backup information dictionaries
        """
        backups = []

        for backup_file in sorted(self.backup_dir.glob("emergency_backup_*.json.gz"), reverse=True):
            try:
                stats = backup_file.stat()
                # Extract timestamp and reason from filename
                parts = backup_file.stem.replace('.json', '').split('_')

                backup_info = {
                    'filename': backup_file.name,
                    'path': str(backup_file),
                    'size_mb': round(stats.st_size / (1024 * 1024), 2),
                    'created': datetime.fromtimestamp(stats.st_mtime).isoformat(),
                    'timestamp': '_'.join(parts[2:4]) if len(parts) >= 4 else 'unknown',
                    'reason': parts[4] if len(parts) > 4 else 'unknown'
                }
                backups.append(backup_info)
            except Exception as e:
                logger.error(f"Error reading backup file {backup_file}: {str(e)}")

        return backups

    def restore_from_backup(self, backup_file: str = None) -> bool:
        """
        Restore data from an emergency backup

        Args:
            backup_file: Path to backup file (uses most recent if None)

        Returns:
            bool: True if restoration successful
        """
        try:
            # Find backup file
            if backup_file is None:
                backups = list(sorted(self.backup_dir.glob("emergency_backup_*.json.gz"), reverse=True))
                if not backups:
                    logger.error("No backup files found")
                    return False
                backup_path = backups[0]
            else:
                backup_path = Path(backup_file)

            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False

            logger.info(f"Restoring from backup: {backup_path}")

            # Read backup
            with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                backup_data = json.load(f)

            # Create a backup of current state before restoring
            self.create_emergency_backup(reason="pre_restore")

            # Restore each file
            restored_files = []
            for filename, data in backup_data.get('files', {}).items():
                if data is None:
                    logger.warning(f"Skipping {filename} (was not in backup)")
                    continue

                file_path = self.data_dir / filename
                try:
                    # Create backup of existing file
                    if file_path.exists():
                        backup_copy = file_path.with_suffix('.json.bak')
                        shutil.copy2(file_path, backup_copy)

                    # Write restored data
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2)

                    restored_files.append(filename)
                    logger.info(f"Restored {filename}")

                except Exception as e:
                    logger.error(f"Failed to restore {filename}: {str(e)}")
                    return False

            logger.info(f"Successfully restored {len(restored_files)} files from backup")
            logger.info(f"Backup timestamp: {backup_data.get('timestamp')}")
            logger.info(f"Backup reason: {backup_data.get('reason')}")

            return True

        except Exception as e:
            logger.error(f"Failed to restore from backup: {str(e)}")
            return False

    def sync_database_to_json(self, app) -> bool:
        """
        Sync database content to JSON files as safety backup

        Args:
            app: Flask application instance

        Returns:
            bool: True if sync successful
        """
        try:
            # Create emergency backup before syncing
            self.create_emergency_backup(reason="pre_db_sync")

            with app.app_context():
                from .database_models import (
                    Roommate, Chore, SubChore, Assignment,
                    ShoppingItem, Request, LaundrySlot, BlockedTimeSlot
                )

                # Sync roommates
                roommates = Roommate.query.all()
                roommates_data = [
                    {
                        'id': r.id,
                        'name': r.name,
                        'current_cycle_points': r.current_cycle_points,
                        'google_id': r.google_id,
                        'google_profile_picture_url': r.google_profile_picture_url,
                        'linked_at': r.linked_at.isoformat() if r.linked_at else None
                    }
                    for r in roommates
                ]
                self._write_json_file('roommates.json', roommates_data)

                # Sync chores with sub-chores
                chores = Chore.query.all()
                chores_data = []
                for chore in chores:
                    sub_chores = SubChore.query.filter_by(chore_id=chore.id).all()
                    chore_dict = {
                        'id': chore.id,
                        'name': chore.name,
                        'description': chore.description,
                        'frequency': chore.frequency,
                        'type': chore.type,
                        'points': chore.points
                    }
                    if sub_chores:
                        chore_dict['sub_chores'] = [
                            {
                                'id': sc.id,
                                'description': sc.description
                            }
                            for sc in sub_chores
                        ]
                    chores_data.append(chore_dict)
                self._write_json_file('chores.json', chores_data)

                # Sync current assignments
                assignments = Assignment.query.all()
                assignments_data = [
                    {
                        'chore_id': a.chore_id,
                        'chore_name': a.chore.name if a.chore else None,
                        'roommate_id': a.roommate_id,
                        'roommate_name': a.roommate.name if a.roommate else None,
                        'assigned_date': a.assigned_date.isoformat() if a.assigned_date else None,
                        'due_date': a.due_date.isoformat() if a.due_date else None,
                        'frequency': a.frequency,
                        'type': a.type,
                        'points': a.points
                    }
                    for a in assignments
                ]

                # Update state.json with assignments
                state_path = self.data_dir / 'state.json'
                if state_path.exists():
                    with open(state_path, 'r', encoding='utf-8') as f:
                        state_data = json.load(f)
                else:
                    state_data = {}

                state_data['current_assignments'] = assignments_data
                self._write_json_file('state.json', state_data)

                # Sync shopping list
                shopping_items = ShoppingItem.query.all()
                shopping_data = [
                    {
                        'id': item.id,
                        'item_name': item.item_name,
                        'category': item.category,
                        'quantity': item.quantity,
                        'estimated_price': item.estimated_price,
                        'actual_price': item.actual_price,
                        'status': item.status,
                        'purchased_by': item.purchased_by,
                        'purchase_date': item.purchase_date.isoformat() if item.purchase_date else None,
                        'notes': item.notes
                    }
                    for item in shopping_items
                ]
                self._write_json_file('shopping_list.json', shopping_data)

                # Sync requests
                requests_list = Request.query.all()
                requests_data = [
                    {
                        'id': req.id,
                        'item_name': req.item_name,
                        'category': req.category,
                        'quantity': req.quantity,
                        'estimated_price': req.estimated_price,
                        'roommate_id': req.roommate_id,
                        'reason': req.reason,
                        'status': req.status,
                        'approvals': req.approvals or [],
                        'created_at': req.created_at.isoformat() if req.created_at else None
                    }
                    for req in requests_list
                ]
                self._write_json_file('requests.json', requests_data)

                # Sync laundry slots
                laundry_slots = LaundrySlot.query.all()
                laundry_data = [
                    {
                        'id': slot.id,
                        'roommate_id': slot.roommate_id,
                        'start_time': slot.start_time.isoformat() if slot.start_time else None,
                        'end_time': slot.end_time.isoformat() if slot.end_time else None,
                        'machine_type': slot.machine_type,
                        'load_type': slot.load_type,
                        'estimated_loads': slot.estimated_loads,
                        'actual_loads': slot.actual_loads,
                        'status': slot.status,
                        'notes': slot.notes
                    }
                    for slot in laundry_slots
                ]
                self._write_json_file('laundry_slots.json', laundry_data)

                # Sync blocked time slots
                blocked_slots = BlockedTimeSlot.query.all()
                blocked_data = [
                    {
                        'id': slot.id,
                        'roommate_id': slot.roommate_id,
                        'start_time': slot.start_time.isoformat() if slot.start_time else None,
                        'end_time': slot.end_time.isoformat() if slot.end_time else None,
                        'reason': slot.reason,
                        'sync_to_calendar': slot.sync_to_calendar
                    }
                    for slot in blocked_slots
                ]
                self._write_json_file('blocked_time_slots.json', blocked_data)

                logger.info("Successfully synced database to JSON files")
                return True

        except Exception as e:
            logger.error(f"Failed to sync database to JSON: {str(e)}")
            return False

    def _write_json_file(self, filename: str, data: Any):
        """Write data to JSON file with error handling"""
        file_path = self.data_dir / filename
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Wrote {filename}")
        except Exception as e:
            logger.error(f"Failed to write {filename}: {str(e)}")
            raise

    def _cleanup_old_backups(self):
        """Remove old backups keeping only the most recent ones"""
        try:
            backups = sorted(self.backup_dir.glob("emergency_backup_*.json.gz"), reverse=True)

            # Remove backups beyond max_backups
            for old_backup in backups[self.max_backups:]:
                try:
                    old_backup.unlink()
                    logger.info(f"Removed old backup: {old_backup.name}")
                except Exception as e:
                    logger.error(f"Failed to remove old backup {old_backup}: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {str(e)}")

    def get_recovery_status(self) -> Dict[str, Any]:
        """
        Get current recovery system status

        Returns:
            Dict with recovery system status
        """
        backups = self.list_backups()

        return {
            'backup_directory': str(self.backup_dir),
            'backup_count': len(backups),
            'max_backups': self.max_backups,
            'latest_backup': backups[0] if backups else None,
            'total_backup_size_mb': sum(b['size_mb'] for b in backups)
        }


# Global recovery instance
emergency_recovery = EmergencyRecovery()


# Decorator for automatic pre-write backups
def with_emergency_backup(reason: str = "auto"):
    """
    Decorator to automatically create emergency backup before database writes

    Usage:
        @with_emergency_backup(reason="create_chore")
        def create_chore(...):
            # Your database write code
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                # Create backup before write
                backup_path = emergency_recovery.create_emergency_backup(reason=reason)
                if backup_path:
                    logger.debug(f"Pre-write backup created: {backup_path}")

                # Execute the function
                return func(*args, **kwargs)

            except Exception as e:
                logger.error(f"Error in {func.__name__}: {str(e)}")
                raise

        return wrapper
    return decorator
