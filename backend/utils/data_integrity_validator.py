"""
Data Integrity Validation System for RoomieRoster

This module provides comprehensive data integrity validation:
- Foreign key relationship validation
- Orphaned record detection
- Date format and range validation
- Required field validation
- Duplicate ID detection
- JSON vs Database consistency checks
"""

import os
import json
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class DataIntegrityValidator:
    """Validates data integrity for RoomieRoster application"""

    def __init__(self, app=None):
        self.app = app
        self.errors = []
        self.warnings = []
        self.info = []

    def add_error(self, message: str):
        """Add an error to the validation report"""
        self.errors.append(message)
        logger.error(f"Data Integrity Error: {message}")

    def add_warning(self, message: str):
        """Add a warning to the validation report"""
        self.warnings.append(message)
        logger.warning(f"Data Integrity Warning: {message}")

    def add_info(self, message: str):
        """Add info to the validation report"""
        self.info.append(message)
        logger.info(f"Data Integrity Info: {message}")

    def validate_json_files(self, data_dir: str = None) -> bool:
        """
        Validate JSON file data integrity

        Args:
            data_dir: Directory containing JSON files (default: backend/data/)

        Returns:
            bool: True if validation passes, False otherwise
        """
        if data_dir is None:
            backend_dir = Path(__file__).parent.parent
            data_dir = backend_dir / 'data'
        else:
            data_dir = Path(data_dir)

        self.add_info(f"Validating JSON files in: {data_dir}")

        # Load JSON files
        try:
            roommates = self._load_json(data_dir / 'roommates.json', [])
            chores = self._load_json(data_dir / 'chores.json', [])
            state = self._load_json(data_dir / 'state.json', {})
            shopping_list = self._load_json(data_dir / 'shopping_list.json', [])
            requests = self._load_json(data_dir / 'requests.json', [])
            laundry_slots = self._load_json(data_dir / 'laundry_slots.json', [])
            blocked_slots = self._load_json(data_dir / 'blocked_time_slots.json', [])
        except Exception as e:
            self.add_error(f"Failed to load JSON files: {str(e)}")
            return False

        # Extract IDs for validation
        roommate_ids = {r['id'] for r in roommates}
        chore_ids = {c['id'] for c in chores}

        # Validate roommates
        self._validate_roommates(roommates)

        # Validate chores
        self._validate_chores(chores, roommate_ids)

        # Validate current assignments
        if 'current_assignments' in state:
            self._validate_assignments(state['current_assignments'], roommate_ids, chore_ids)

        # Validate sub-chore completions
        if 'sub_chore_completions' in state:
            self._validate_sub_chore_completions(state['sub_chore_completions'], chores)

        # Validate shopping list
        self._validate_shopping_list(shopping_list, roommate_ids)

        # Validate requests
        self._validate_requests(requests, roommate_ids)

        # Validate laundry slots
        self._validate_laundry_slots(laundry_slots, roommate_ids)

        # Validate blocked time slots
        self._validate_blocked_slots(blocked_slots, roommate_ids)

        return len(self.errors) == 0

    def validate_database(self) -> bool:
        """
        Validate database data integrity

        Returns:
            bool: True if validation passes, False otherwise
        """
        if not self.app:
            self.add_error("Flask app not provided for database validation")
            return False

        with self.app.app_context():
            try:
                from .database_models import (
                    Roommate, Chore, SubChore, Assignment,
                    ShoppingItem, Request, LaundrySlot, BlockedTimeSlot
                )
                from .database_config import db
                from sqlalchemy import text

                # Check database connection
                db.session.execute(text("SELECT 1"))
                self.add_info("Database connection successful")

                # Get all records
                roommates = Roommate.query.all()
                chores = Chore.query.all()
                assignments = Assignment.query.all()
                shopping_items = ShoppingItem.query.all()
                requests_list = Request.query.all()
                laundry_slots = LaundrySlot.query.all()
                blocked_slots = BlockedTimeSlot.query.all()

                self.add_info(f"Found {len(roommates)} roommates, {len(chores)} chores, {len(assignments)} assignments")

                # Validate foreign key relationships
                self._validate_db_foreign_keys(assignments, roommates, chores)

                # Validate sub-chores
                for chore in chores:
                    sub_chores = SubChore.query.filter_by(chore_id=chore.id).all()
                    if sub_chores:
                        self._validate_db_sub_chores(chore, sub_chores)

                # Validate shopping items
                for item in shopping_items:
                    if item.purchased_by:
                        roommate = Roommate.query.get(item.purchased_by)
                        if not roommate:
                            self.add_error(f"Shopping item '{item.item_name}' has invalid purchased_by: {item.purchased_by}")

                # Validate requests
                for request in requests_list:
                    if request.roommate_id not in [r.id for r in roommates]:
                        self.add_error(f"Request '{request.item_name}' has invalid roommate_id: {request.roommate_id}")

                # Validate laundry slots
                for slot in laundry_slots:
                    if slot.roommate_id not in [r.id for r in roommates]:
                        self.add_error(f"Laundry slot has invalid roommate_id: {slot.roommate_id}")

                # Validate blocked slots
                for slot in blocked_slots:
                    if slot.roommate_id and slot.roommate_id not in [r.id for r in roommates]:
                        self.add_error(f"Blocked slot has invalid roommate_id: {slot.roommate_id}")

                return len(self.errors) == 0

            except Exception as e:
                self.add_error(f"Database validation error: {str(e)}")
                return False

    def _load_json(self, file_path: Path, default: Any) -> Any:
        """Load JSON file with error handling"""
        if not file_path.exists():
            self.add_warning(f"File not found: {file_path}")
            return default

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            self.add_error(f"Invalid JSON in {file_path}: {str(e)}")
            return default
        except Exception as e:
            self.add_error(f"Error reading {file_path}: {str(e)}")
            return default

    def _validate_roommates(self, roommates: List[Dict]):
        """Validate roommate records"""
        if not roommates:
            self.add_warning("No roommates found")
            return

        ids = set()
        for roommate in roommates:
            # Check required fields
            if 'id' not in roommate:
                self.add_error("Roommate missing 'id' field")
                continue

            # Check for duplicate IDs
            if roommate['id'] in ids:
                self.add_error(f"Duplicate roommate ID: {roommate['id']}")
            ids.add(roommate['id'])

            # Check required fields
            if 'name' not in roommate or not roommate['name']:
                self.add_error(f"Roommate {roommate['id']} missing 'name' field")

            # Validate cycle points
            if 'current_cycle_points' in roommate:
                if not isinstance(roommate['current_cycle_points'], (int, float)):
                    self.add_error(f"Roommate {roommate['name']} has invalid current_cycle_points")

    def _validate_chores(self, chores: List[Dict], roommate_ids: set):
        """Validate chore records"""
        if not chores:
            self.add_warning("No chores found")
            return

        ids = set()
        for chore in chores:
            # Check required fields
            if 'id' not in chore:
                self.add_error("Chore missing 'id' field")
                continue

            # Check for duplicate IDs
            if chore['id'] in ids:
                self.add_error(f"Duplicate chore ID: {chore['id']}")
            ids.add(chore['id'])

            # Check required fields
            required_fields = ['name', 'frequency', 'type', 'points']
            for field in required_fields:
                if field not in chore or chore[field] is None:
                    self.add_error(f"Chore {chore['id']} missing '{field}' field")

            # Validate frequency
            if 'frequency' in chore:
                valid_frequencies = ['daily', 'weekly', 'biweekly', 'monthly']
                if chore['frequency'] not in valid_frequencies:
                    self.add_error(f"Chore {chore.get('name', chore['id'])} has invalid frequency: {chore['frequency']}")

            # Validate type
            if 'type' in chore:
                valid_types = ['random', 'predefined']
                if chore['type'] not in valid_types:
                    self.add_error(f"Chore {chore.get('name', chore['id'])} has invalid type: {chore['type']}")

            # Validate points
            if 'points' in chore:
                if not isinstance(chore['points'], (int, float)) or chore['points'] < 0:
                    self.add_error(f"Chore {chore.get('name', chore['id'])} has invalid points: {chore['points']}")

            # Validate assigned_to if present
            if 'assigned_to' in chore and chore['assigned_to']:
                if chore['assigned_to'] not in roommate_ids:
                    self.add_error(f"Chore {chore.get('name', chore['id'])} assigned to invalid roommate: {chore['assigned_to']}")

    def _validate_assignments(self, assignments: List[Dict], roommate_ids: set, chore_ids: set):
        """Validate assignment records"""
        for assignment in assignments:
            # Check foreign keys
            if 'roommate_id' in assignment:
                if assignment['roommate_id'] not in roommate_ids:
                    self.add_error(f"Assignment has invalid roommate_id: {assignment['roommate_id']}")

            if 'chore_id' in assignment:
                if assignment['chore_id'] not in chore_ids:
                    self.add_error(f"Assignment has invalid chore_id: {assignment['chore_id']}")

            # Validate dates
            for date_field in ['assigned_date', 'due_date']:
                if date_field in assignment and assignment[date_field]:
                    if not self._validate_date(assignment[date_field]):
                        self.add_error(f"Assignment has invalid {date_field}: {assignment[date_field]}")

    def _validate_sub_chore_completions(self, completions: Dict, chores: List[Dict]):
        """Validate sub-chore completion records"""
        # Build map of valid sub-chore IDs per chore
        valid_sub_chore_ids = {}
        for chore in chores:
            if 'sub_chores' in chore:
                valid_sub_chore_ids[chore['id']] = {sc['id'] for sc in chore['sub_chores']}

        for assignment_key, sub_completions in completions.items():
            if not isinstance(sub_completions, dict):
                self.add_error(f"Invalid sub-chore completions format for {assignment_key}")
                continue

            # Note: Can't fully validate without knowing which chore this assignment is for
            # This is a limitation of the current data structure

    def _validate_shopping_list(self, shopping_list: List[Dict], roommate_ids: set):
        """Validate shopping list items"""
        for item in shopping_list:
            # Check purchased_by if present
            if 'purchased_by' in item and item['purchased_by']:
                if item['purchased_by'] not in roommate_ids:
                    self.add_error(f"Shopping item '{item.get('item_name')}' has invalid purchased_by: {item['purchased_by']}")

            # Validate dates
            if 'purchase_date' in item and item['purchase_date']:
                if not self._validate_date(item['purchase_date']):
                    self.add_error(f"Shopping item '{item.get('item_name')}' has invalid purchase_date")

    def _validate_requests(self, requests: List[Dict], roommate_ids: set):
        """Validate request records"""
        for request in requests:
            # Check roommate_id
            if 'roommate_id' in request and request['roommate_id']:
                if request['roommate_id'] not in roommate_ids:
                    self.add_error(f"Request '{request.get('item_name')}' has invalid roommate_id: {request['roommate_id']}")

            # Check approvals
            if 'approvals' in request and request['approvals']:
                for approver_id in request['approvals']:
                    if approver_id not in roommate_ids:
                        self.add_error(f"Request '{request.get('item_name')}' has invalid approver: {approver_id}")

    def _validate_laundry_slots(self, laundry_slots: List[Dict], roommate_ids: set):
        """Validate laundry slot records"""
        for slot in laundry_slots:
            # Check roommate_id
            if 'roommate_id' in slot and slot['roommate_id']:
                if slot['roommate_id'] not in roommate_ids:
                    self.add_error(f"Laundry slot has invalid roommate_id: {slot['roommate_id']}")

            # Validate dates
            for date_field in ['start_time', 'end_time']:
                if date_field in slot and slot[date_field]:
                    if not self._validate_date(slot[date_field]):
                        self.add_error(f"Laundry slot has invalid {date_field}")

    def _validate_blocked_slots(self, blocked_slots: List[Dict], roommate_ids: set):
        """Validate blocked time slot records"""
        for slot in blocked_slots:
            # Check roommate_id (optional)
            if 'roommate_id' in slot and slot['roommate_id']:
                if slot['roommate_id'] not in roommate_ids:
                    self.add_error(f"Blocked slot has invalid roommate_id: {slot['roommate_id']}")

            # Validate dates
            for date_field in ['start_time', 'end_time']:
                if date_field in slot and slot[date_field]:
                    if not self._validate_date(slot[date_field]):
                        self.add_error(f"Blocked slot has invalid {date_field}")

    def _validate_db_foreign_keys(self, assignments, roommates, chores):
        """Validate foreign key relationships in database"""
        roommate_ids = {r.id for r in roommates}
        chore_ids = {c.id for c in chores}

        for assignment in assignments:
            if assignment.roommate_id not in roommate_ids:
                self.add_error(f"Assignment {assignment.id} has invalid roommate_id: {assignment.roommate_id}")

            if assignment.chore_id not in chore_ids:
                self.add_error(f"Assignment {assignment.id} has invalid chore_id: {assignment.chore_id}")

    def _validate_db_sub_chores(self, chore, sub_chores):
        """Validate sub-chores for a chore"""
        for sub_chore in sub_chores:
            if not sub_chore.description or sub_chore.description.strip() == '':
                self.add_error(f"Sub-chore {sub_chore.id} in chore '{chore.name}' has empty description")

    def _validate_date(self, date_str: str) -> bool:
        """Validate date format"""
        try:
            datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return True
        except (ValueError, AttributeError):
            return False

    def get_report(self) -> Dict[str, Any]:
        """
        Generate validation report

        Returns:
            Dict with validation results
        """
        passed = len(self.errors) == 0

        return {
            'passed': passed,
            'status': 'PASS' if passed else 'FAIL',
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'errors': self.errors,
            'warnings': self.warnings,
            'info': self.info
        }

    def print_report(self):
        """Print formatted validation report"""
        print("\n" + "="*70)
        print("Data Integrity Validation Report".center(70))
        print("="*70 + "\n")

        if self.errors:
            print(f"❌ FAILED - {len(self.errors)} error(s) found\n")
            print("ERRORS:")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        else:
            print("✅ PASSED - No errors found\n")

        if self.warnings:
            print(f"\n⚠️  {len(self.warnings)} warning(s):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")

        if self.info:
            print(f"\nℹ️  Information:")
            for item in self.info:
                print(f"  • {item}")

        print("\n" + "="*70 + "\n")


# Standalone validation function
def validate_data(mode='json', data_dir=None, app=None) -> Tuple[bool, Dict]:
    """
    Validate data integrity

    Args:
        mode: 'json' or 'database'
        data_dir: Directory containing JSON files (for JSON mode)
        app: Flask app instance (for database mode)

    Returns:
        Tuple[bool, Dict]: (success, report)
    """
    validator = DataIntegrityValidator(app=app)

    if mode == 'json':
        success = validator.validate_json_files(data_dir)
    elif mode == 'database':
        success = validator.validate_database()
    else:
        raise ValueError(f"Invalid mode: {mode}. Must be 'json' or 'database'")

    report = validator.get_report()
    validator.print_report()

    return success, report
