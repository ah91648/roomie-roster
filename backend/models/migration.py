"""
Migration utilities for converting JSON data to SQLAlchemy models.

This module provides utilities to migrate data from the existing JSON file-based
storage to the new SQLAlchemy database models.
"""

import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Any, Optional

from .models import (
    db, Roommate, Chore, SubChore, Assignment, SubChoreCompletion,
    ShoppingItem, PurchaseRequest, Approval, LaundrySlot, BlockedTimeSlot,
    ApplicationState
)
from ..utils.data_handler import DataHandler


class DataMigration:
    """Handles migration from JSON files to SQLAlchemy database."""
    
    def __init__(self, json_data_dir: str = "data", app_context=None):
        """Initialize migration with data directory."""
        self.json_data_dir = Path(json_data_dir)
        self.data_handler = DataHandler(json_data_dir)
        self.app_context = app_context
        
        # Migration tracking
        self.migration_log = []
        self.errors = []
    
    def log_info(self, message: str):
        """Log migration information."""
        log_entry = f"[INFO] {datetime.now().isoformat()}: {message}"
        self.migration_log.append(log_entry)
        print(log_entry)
    
    def log_error(self, message: str, error: Exception = None):
        """Log migration errors."""
        error_detail = f" - {str(error)}" if error else ""
        log_entry = f"[ERROR] {datetime.now().isoformat()}: {message}{error_detail}"
        self.errors.append(log_entry)
        print(log_entry)
    
    def migrate_roommates(self) -> bool:
        """Migrate roommates from JSON to database."""
        try:
            self.log_info("Migrating roommates...")
            
            json_roommates = self.data_handler.get_roommates()
            migrated_count = 0
            
            for roommate_data in json_roommates:
                try:
                    # Convert date strings to datetime objects
                    if roommate_data.get('linked_at'):
                        roommate_data['linked_at'] = datetime.fromisoformat(roommate_data['linked_at'])
                    
                    roommate = Roommate.from_dict(roommate_data)
                    db.session.add(roommate)
                    migrated_count += 1
                    
                except Exception as e:
                    self.log_error(f"Failed to migrate roommate {roommate_data.get('name', 'Unknown')}", e)
            
            db.session.commit()
            self.log_info(f"Successfully migrated {migrated_count} roommates")
            return True
            
        except Exception as e:
            self.log_error("Failed to migrate roommates", e)
            db.session.rollback()
            return False
    
    def migrate_chores(self) -> bool:
        """Migrate chores and sub-chores from JSON to database."""
        try:
            self.log_info("Migrating chores and sub-chores...")
            
            json_chores = self.data_handler.get_chores()
            migrated_chores = 0
            migrated_sub_chores = 0
            
            for chore_data in json_chores:
                try:
                    # Extract sub-chores data
                    sub_chores_data = chore_data.pop('sub_chores', [])
                    
                    # Create chore
                    chore = Chore.from_dict(chore_data)
                    db.session.add(chore)
                    db.session.flush()  # Get the ID
                    migrated_chores += 1
                    
                    # Create sub-chores
                    for sub_data in sub_chores_data:
                        sub_chore = SubChore(
                            name=sub_data['name'],
                            chore=chore
                        )
                        db.session.add(sub_chore)
                        migrated_sub_chores += 1
                    
                except Exception as e:
                    self.log_error(f"Failed to migrate chore {chore_data.get('name', 'Unknown')}", e)
            
            db.session.commit()
            self.log_info(f"Successfully migrated {migrated_chores} chores and {migrated_sub_chores} sub-chores")
            return True
            
        except Exception as e:
            self.log_error("Failed to migrate chores", e)
            db.session.rollback()
            return False
    
    def migrate_application_state(self) -> bool:
        """Migrate application state from JSON to database."""
        try:
            self.log_info("Migrating application state...")
            
            json_state = self.data_handler.get_state()
            
            # Migrate last run date
            if json_state.get('last_run_date'):
                ApplicationState.set_last_run_date(
                    datetime.fromisoformat(json_state['last_run_date'])
                )
            
            # Migrate global predefined rotation
            if 'global_predefined_rotation' in json_state:
                ApplicationState.set_global_predefined_rotation(
                    json_state['global_predefined_rotation']
                )
            
            # Migrate predefined chore states
            if json_state.get('predefined_chore_states'):
                for chore_id, roommate_id in json_state['predefined_chore_states'].items():
                    ApplicationState.set_predefined_chore_state(int(chore_id), roommate_id)
            
            db.session.commit()
            self.log_info("Successfully migrated application state")
            return True
            
        except Exception as e:
            self.log_error("Failed to migrate application state", e)
            db.session.rollback()
            return False
    
    def migrate_assignments(self) -> bool:
        """Migrate current assignments from JSON to database."""
        try:
            self.log_info("Migrating assignments...")
            
            json_state = self.data_handler.get_state()
            assignments_data = json_state.get('current_assignments', [])
            migrated_count = 0
            
            for assignment_data in assignments_data:
                try:
                    # Get chore and roommate objects
                    chore = db.session.query(Chore).filter_by(id=assignment_data['chore_id']).first()
                    roommate = db.session.query(Roommate).filter_by(id=assignment_data['roommate_id']).first()
                    
                    if not chore or not roommate:
                        self.log_error(f"Chore or roommate not found for assignment {assignment_data}")
                        continue
                    
                    # Create assignment
                    assignment = Assignment(
                        chore=chore,
                        roommate=roommate,
                        assigned_date=datetime.fromisoformat(assignment_data['assigned_date']),
                        due_date=datetime.fromisoformat(assignment_data['due_date'])
                    )
                    db.session.add(assignment)
                    db.session.flush()  # Get the ID
                    
                    # Migrate sub-chore completions if present
                    if 'sub_chore_completions' in assignment_data:
                        for sub_chore_id, completed in assignment_data['sub_chore_completions'].items():
                            sub_chore = db.session.query(SubChore).filter_by(
                                id=int(sub_chore_id), chore_id=chore.id
                            ).first()
                            
                            if sub_chore:
                                completion = SubChoreCompletion(
                                    sub_chore=sub_chore,
                                    assignment=assignment,
                                    completed=completed,
                                    completed_at=datetime.utcnow() if completed else None
                                )
                                db.session.add(completion)
                    
                    migrated_count += 1
                    
                except Exception as e:
                    self.log_error(f"Failed to migrate assignment {assignment_data}", e)
            
            db.session.commit()
            self.log_info(f"Successfully migrated {migrated_count} assignments")
            return True
            
        except Exception as e:
            self.log_error("Failed to migrate assignments", e)
            db.session.rollback()
            return False
    
    def migrate_shopping_items(self) -> bool:
        """Migrate shopping list items from JSON to database."""
        try:
            self.log_info("Migrating shopping list items...")
            
            json_items = self.data_handler.get_shopping_list()
            migrated_count = 0
            
            for item_data in json_items:
                try:
                    # Convert date strings to datetime objects
                    if item_data.get('date_added'):
                        item_data['date_added'] = datetime.fromisoformat(item_data['date_added'])
                    if item_data.get('purchase_date'):
                        item_data['purchase_date'] = datetime.fromisoformat(item_data['purchase_date'])
                    
                    # Handle roommate references
                    added_by_roommate = db.session.query(Roommate).filter_by(id=item_data['added_by']).first()
                    if not added_by_roommate:
                        self.log_error(f"Roommate {item_data['added_by']} not found for shopping item")
                        continue
                    
                    purchased_by_roommate = None
                    if item_data.get('purchased_by'):
                        purchased_by_roommate = db.session.query(Roommate).filter_by(id=item_data['purchased_by']).first()
                    
                    # Create shopping item
                    item = ShoppingItem.from_dict(item_data)
                    db.session.add(item)
                    migrated_count += 1
                    
                except Exception as e:
                    self.log_error(f"Failed to migrate shopping item {item_data.get('item_name', 'Unknown')}", e)
            
            db.session.commit()
            self.log_info(f"Successfully migrated {migrated_count} shopping list items")
            return True
            
        except Exception as e:
            self.log_error("Failed to migrate shopping items", e)
            db.session.rollback()
            return False
    
    def migrate_purchase_requests(self) -> bool:
        """Migrate purchase requests and approvals from JSON to database."""
        try:
            self.log_info("Migrating purchase requests and approvals...")
            
            json_requests = self.data_handler.get_requests()
            migrated_requests = 0
            migrated_approvals = 0
            
            for request_data in json_requests:
                try:
                    # Extract approvals data
                    approvals_data = request_data.pop('approvals', [])
                    
                    # Convert date strings to datetime objects
                    if request_data.get('date_requested'):
                        request_data['date_requested'] = datetime.fromisoformat(request_data['date_requested'])
                    if request_data.get('final_decision_date'):
                        request_data['final_decision_date'] = datetime.fromisoformat(request_data['final_decision_date'])
                    
                    # Handle roommate references
                    requested_by_roommate = db.session.query(Roommate).filter_by(id=request_data['requested_by']).first()
                    if not requested_by_roommate:
                        self.log_error(f"Roommate {request_data['requested_by']} not found for request")
                        continue
                    
                    # Create purchase request
                    request = PurchaseRequest.from_dict(request_data)
                    db.session.add(request)
                    db.session.flush()  # Get the ID
                    migrated_requests += 1
                    
                    # Create approvals
                    for approval_data in approvals_data:
                        try:
                            approval = Approval(
                                request=request,
                                approved_by=approval_data['approved_by'],
                                approval_status=approval_data['approval_status'],
                                approval_date=datetime.fromisoformat(approval_data['approval_date']),
                                notes=approval_data.get('notes', '')
                            )
                            db.session.add(approval)
                            migrated_approvals += 1
                        except Exception as e:
                            self.log_error(f"Failed to migrate approval for request {request.id}", e)
                    
                except Exception as e:
                    self.log_error(f"Failed to migrate request {request_data.get('item_name', 'Unknown')}", e)
            
            db.session.commit()
            self.log_info(f"Successfully migrated {migrated_requests} requests and {migrated_approvals} approvals")
            return True
            
        except Exception as e:
            self.log_error("Failed to migrate purchase requests", e)
            db.session.rollback()
            return False
    
    def migrate_laundry_slots(self) -> bool:
        """Migrate laundry slots from JSON to database."""
        try:
            self.log_info("Migrating laundry slots...")
            
            json_slots = self.data_handler.get_laundry_slots()
            migrated_count = 0
            
            for slot_data in json_slots:
                try:
                    # Convert date strings to appropriate objects
                    if slot_data.get('date'):
                        if isinstance(slot_data['date'], str):
                            slot_data['date'] = datetime.strptime(slot_data['date'], '%Y-%m-%d').date()
                    
                    if slot_data.get('created_date'):
                        slot_data['created_date'] = datetime.fromisoformat(slot_data['created_date'])
                    if slot_data.get('completed_date'):
                        slot_data['completed_date'] = datetime.fromisoformat(slot_data['completed_date'])
                    
                    # Handle roommate reference
                    roommate = db.session.query(Roommate).filter_by(id=slot_data['roommate_id']).first()
                    if not roommate:
                        self.log_error(f"Roommate {slot_data['roommate_id']} not found for laundry slot")
                        continue
                    
                    # Create laundry slot
                    slot = LaundrySlot.from_dict(slot_data)
                    db.session.add(slot)
                    migrated_count += 1
                    
                except Exception as e:
                    self.log_error(f"Failed to migrate laundry slot {slot_data.get('id', 'Unknown')}", e)
            
            db.session.commit()
            self.log_info(f"Successfully migrated {migrated_count} laundry slots")
            return True
            
        except Exception as e:
            self.log_error("Failed to migrate laundry slots", e)
            db.session.rollback()
            return False
    
    def migrate_blocked_time_slots(self) -> bool:
        """Migrate blocked time slots from JSON to database."""
        try:
            self.log_info("Migrating blocked time slots...")
            
            json_slots = self.data_handler.get_blocked_time_slots()
            migrated_count = 0
            
            for slot_data in json_slots:
                try:
                    # Convert date strings to appropriate objects
                    if slot_data.get('date'):
                        if isinstance(slot_data['date'], str):
                            slot_data['date'] = datetime.strptime(slot_data['date'], '%Y-%m-%d').date()
                    
                    if slot_data.get('created_date'):
                        slot_data['created_date'] = datetime.fromisoformat(slot_data['created_date'])
                    
                    # Handle roommate reference
                    roommate = db.session.query(Roommate).filter_by(id=slot_data['created_by']).first()
                    if not roommate:
                        self.log_error(f"Roommate {slot_data['created_by']} not found for blocked slot")
                        continue
                    
                    # Create blocked time slot
                    slot = BlockedTimeSlot.from_dict(slot_data)
                    db.session.add(slot)
                    migrated_count += 1
                    
                except Exception as e:
                    self.log_error(f"Failed to migrate blocked time slot {slot_data.get('id', 'Unknown')}", e)
            
            db.session.commit()
            self.log_info(f"Successfully migrated {migrated_count} blocked time slots")
            return True
            
        except Exception as e:
            self.log_error("Failed to migrate blocked time slots", e)
            db.session.rollback()
            return False
    
    def validate_migration(self) -> bool:
        """Validate that migration was successful by comparing counts."""
        try:
            self.log_info("Validating migration...")
            
            # Compare counts
            validation_results = []
            
            # Roommates
            json_count = len(self.data_handler.get_roommates())
            db_count = db.session.query(Roommate).count()
            validation_results.append(("Roommates", json_count, db_count))
            
            # Chores
            json_count = len(self.data_handler.get_chores())
            db_count = db.session.query(Chore).count()
            validation_results.append(("Chores", json_count, db_count))
            
            # Sub-chores
            json_sub_count = sum(len(chore.get('sub_chores', [])) for chore in self.data_handler.get_chores())
            db_sub_count = db.session.query(SubChore).count()
            validation_results.append(("Sub-chores", json_sub_count, db_sub_count))
            
            # Shopping items
            json_count = len(self.data_handler.get_shopping_list())
            db_count = db.session.query(ShoppingItem).count()
            validation_results.append(("Shopping items", json_count, db_count))
            
            # Purchase requests
            json_count = len(self.data_handler.get_requests())
            db_count = db.session.query(PurchaseRequest).count()
            validation_results.append(("Purchase requests", json_count, db_count))
            
            # Laundry slots
            json_count = len(self.data_handler.get_laundry_slots())
            db_count = db.session.query(LaundrySlot).count()
            validation_results.append(("Laundry slots", json_count, db_count))
            
            # Blocked time slots
            json_count = len(self.data_handler.get_blocked_time_slots())
            db_count = db.session.query(BlockedTimeSlot).count()
            validation_results.append(("Blocked time slots", json_count, db_count))
            
            # Log validation results
            all_valid = True
            for entity_type, json_count, db_count in validation_results:
                if json_count == db_count:
                    self.log_info(f"{entity_type}: {json_count} JSON → {db_count} DB ✓")
                else:
                    self.log_error(f"{entity_type}: {json_count} JSON → {db_count} DB ✗")
                    all_valid = False
            
            return all_valid
            
        except Exception as e:
            self.log_error("Failed to validate migration", e)
            return False
    
    def run_full_migration(self, create_backup: bool = True) -> bool:
        """Run complete migration from JSON files to database."""
        try:
            self.log_info("Starting full migration from JSON to database...")
            
            if create_backup:
                self.create_json_backup()
            
            # Clear existing database
            self.log_info("Clearing existing database...")
            db.drop_all()
            db.create_all()
            
            # Run migrations in dependency order
            migration_steps = [
                ("roommates", self.migrate_roommates),
                ("chores", self.migrate_chores),
                ("application_state", self.migrate_application_state),
                ("assignments", self.migrate_assignments),
                ("shopping_items", self.migrate_shopping_items),
                ("purchase_requests", self.migrate_purchase_requests),
                ("laundry_slots", self.migrate_laundry_slots),
                ("blocked_time_slots", self.migrate_blocked_time_slots),
            ]
            
            success_count = 0
            for step_name, migration_func in migration_steps:
                self.log_info(f"Running migration step: {step_name}")
                if migration_func():
                    success_count += 1
                else:
                    self.log_error(f"Migration step failed: {step_name}")
            
            # Validate migration
            validation_success = self.validate_migration()
            
            # Summary
            total_steps = len(migration_steps)
            self.log_info(f"Migration completed: {success_count}/{total_steps} steps successful")
            
            if validation_success:
                self.log_info("Migration validation successful!")
            else:
                self.log_error("Migration validation failed - some data may be missing")
            
            # Write migration log
            self.write_migration_log()
            
            return success_count == total_steps and validation_success
            
        except Exception as e:
            self.log_error("Full migration failed", e)
            return False
    
    def create_json_backup(self):
        """Create backup of JSON files before migration."""
        try:
            backup_dir = Path(f"{self.json_data_dir}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            backup_dir.mkdir(exist_ok=True)
            
            # Copy all JSON files
            json_files = [
                "chores.json", "roommates.json", "state.json",
                "shopping_list.json", "requests.json", "laundry_slots.json",
                "blocked_time_slots.json"
            ]
            
            for filename in json_files:
                source = self.json_data_dir / filename
                if source.exists():
                    destination = backup_dir / filename
                    destination.write_text(source.read_text())
            
            self.log_info(f"JSON backup created at: {backup_dir}")
            
        except Exception as e:
            self.log_error("Failed to create JSON backup", e)
    
    def write_migration_log(self):
        """Write migration log to file."""
        try:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            log_file = log_dir / f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            
            with open(log_file, 'w') as f:
                f.write("RoomieRoster JSON to Database Migration Log\n")
                f.write("=" * 50 + "\n\n")
                
                f.write("Migration Log:\n")
                for entry in self.migration_log:
                    f.write(entry + "\n")
                
                if self.errors:
                    f.write("\nErrors:\n")
                    for error in self.errors:
                        f.write(error + "\n")
                
                f.write(f"\nTotal log entries: {len(self.migration_log)}\n")
                f.write(f"Total errors: {len(self.errors)}\n")
            
            self.log_info(f"Migration log written to: {log_file}")
            
        except Exception as e:
            self.log_error("Failed to write migration log", e)


def run_migration(app, json_data_dir: str = "data", create_backup: bool = True) -> bool:
    """Convenience function to run migration with Flask app context."""
    with app.app_context():
        migration = DataMigration(json_data_dir, app)
        return migration.run_full_migration(create_backup)


def create_sample_data(app):
    """Create sample data for testing the new models."""
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()
        
        # Create sample roommates
        roommates = [
            Roommate(name="Alice", current_cycle_points=0),
            Roommate(name="Bob", current_cycle_points=5),
            Roommate(name="Charlie", current_cycle_points=3),
            Roommate(name="Diana", current_cycle_points=2)
        ]
        
        for roommate in roommates:
            db.session.add(roommate)
        
        db.session.flush()
        
        # Create sample chores
        chores_data = [
            {"name": "Take out Trash", "frequency": "daily", "type": "random", "points": 3},
            {"name": "Wash Dishes", "frequency": "daily", "type": "predefined", "points": 7},
            {"name": "Vacuum Living Room", "frequency": "weekly", "type": "predefined", "points": 5},
            {"name": "Clean Bathroom", "frequency": "weekly", "type": "random", "points": 8}
        ]
        
        chores = []
        for chore_data in chores_data:
            chore = Chore(**chore_data)
            db.session.add(chore)
            db.session.flush()
            
            # Add sub-chores
            if chore.name == "Take out Trash":
                sub_chores = [
                    "Collect trash from all rooms",
                    "Replace trash bags",
                    "Take bags to outdoor bin"
                ]
                for sub_name in sub_chores:
                    sub_chore = SubChore(name=sub_name, chore=chore)
                    db.session.add(sub_chore)
            
            chores.append(chore)
        
        # Create sample assignments
        assignment = Assignment(
            chore=chores[0],
            roommate=roommates[0],
            assigned_date=datetime.utcnow(),
            due_date=chores[0].calculate_due_date()
        )
        db.session.add(assignment)
        
        # Create sample shopping items
        shopping_items = [
            ShoppingItem(
                item_name="Milk",
                estimated_price=4.50,
                brand_preference="Organic Valley",
                notes="2% milk preferred",
                added_by_roommate=roommates[0]
            ),
            ShoppingItem(
                item_name="Bread",
                estimated_price=3.00,
                brand_preference="Whole wheat",
                added_by_roommate=roommates[1],
                status="purchased",
                purchased_by_roommate=roommates[2],
                actual_price=2.80,
                purchase_date=datetime.utcnow()
            )
        ]
        
        for item in shopping_items:
            db.session.add(item)
        
        # Commit all sample data
        db.session.commit()
        
        print("Sample data created successfully!")


if __name__ == "__main__":
    # This would be run with a Flask app context
    # Example: python -m backend.models.migration
    print("Migration utilities loaded. Use run_migration(app) to run migration.")