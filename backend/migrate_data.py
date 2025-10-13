#!/usr/bin/env python3
"""
Data migration script for RoomieRoster application.
Migrates data from JSON files to PostgreSQL database.
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Load environment variables from .env file
from dotenv import load_dotenv
project_root = Path(backend_dir).parent
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded environment variables from {env_path}")
else:
    print(f"⚠️ No .env file found at {env_path}")

# Import Flask and database components
from flask import Flask
from utils.database_config import database_config, db
from utils.database_models import (
    Roommate, Chore, SubChore, Assignment, ApplicationState,
    ShoppingItem, Request, LaundrySlot, BlockedTimeSlot
)
from utils.database_init import database_initializer

class DataMigrator:
    """Handles migration of data from JSON files to PostgreSQL database."""
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.logger = logging.getLogger(__name__)
        self.migration_log = []
        
    def load_json_file(self, filename: str) -> Any:
        """Load data from a JSON file."""
        file_path = self.data_dir / filename
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.logger.info(f"Loaded {filename}: {len(data) if isinstance(data, list) else 'single object'}")
                return data
            else:
                self.logger.warning(f"File {filename} does not exist")
                return [] if filename.endswith('s.json') or filename == 'requests.json' else {}
        except Exception as e:
            self.logger.error(f"Error loading {filename}: {e}")
            return [] if filename.endswith('s.json') or filename == 'requests.json' else {}
    
    def migrate_roommates(self) -> bool:
        """Migrate roommates from roommates.json"""
        self.logger.info("Migrating roommates...")
        
        try:
            roommates_data = self.load_json_file('roommates.json')
            
            for roommate_data in roommates_data:
                # Check if roommate already exists
                existing = Roommate.query.filter_by(id=roommate_data['id']).first()
                if existing:
                    self.logger.info(f"Roommate {roommate_data['name']} already exists, skipping")
                    continue
                
                # Parse linked_at datetime if present
                linked_at = None
                if roommate_data.get('linked_at'):
                    try:
                        linked_at = datetime.fromisoformat(roommate_data['linked_at'])
                    except ValueError:
                        self.logger.warning(f"Invalid linked_at format for roommate {roommate_data['name']}")
                
                roommate = Roommate(
                    id=roommate_data['id'],
                    name=roommate_data['name'],
                    current_cycle_points=roommate_data.get('current_cycle_points', 0),
                    google_id=roommate_data.get('google_id'),
                    google_profile_picture_url=roommate_data.get('google_profile_picture_url'),
                    linked_at=linked_at
                )
                
                db.session.add(roommate)
                self.migration_log.append(f"Added roommate: {roommate.name}")
            
            db.session.commit()
            self.logger.info(f"Successfully migrated {len(roommates_data)} roommates")
            return True
            
        except Exception as e:
            self.logger.error(f"Error migrating roommates: {e}")
            db.session.rollback()
            return False
    
    def migrate_chores(self) -> bool:
        """Migrate chores and sub-chores from chores.json"""
        self.logger.info("Migrating chores and sub-chores...")
        
        try:
            chores_data = self.load_json_file('chores.json')
            
            for chore_data in chores_data:
                # Check if chore already exists
                existing = Chore.query.filter_by(id=chore_data['id']).first()
                if existing:
                    self.logger.info(f"Chore {chore_data['name']} already exists, skipping")
                    continue
                
                chore = Chore(
                    id=chore_data['id'],
                    name=chore_data['name'],
                    frequency=chore_data['frequency'],
                    type=chore_data['type'],
                    points=chore_data['points']
                )
                
                db.session.add(chore)
                db.session.flush()  # Flush to get the chore ID
                
                # Add sub-chores
                for sub_chore_data in chore_data.get('sub_chores', []):
                    sub_chore = SubChore(
                        id=sub_chore_data['id'],
                        chore_id=chore.id,
                        name=sub_chore_data['name'],
                        completed=sub_chore_data.get('completed', False)
                    )
                    db.session.add(sub_chore)
                
                self.migration_log.append(f"Added chore: {chore.name} with {len(chore_data.get('sub_chores', []))} sub-chores")
            
            db.session.commit()
            self.logger.info(f"Successfully migrated {len(chores_data)} chores")
            return True
            
        except Exception as e:
            self.logger.error(f"Error migrating chores: {e}")
            db.session.rollback()
            return False
    
    def migrate_application_state(self) -> bool:
        """Migrate application state from state.json"""
        self.logger.info("Migrating application state...")
        
        try:
            state_data = self.load_json_file('state.json')
            
            # Check if application state already exists
            existing_state = ApplicationState.query.first()
            if existing_state:
                # Update existing state
                if state_data.get('last_run_date'):
                    try:
                        existing_state.last_run_date = datetime.fromisoformat(state_data['last_run_date'])
                    except ValueError:
                        self.logger.warning("Invalid last_run_date format")
                
                existing_state.predefined_chore_states = state_data.get('predefined_chore_states', {})
                existing_state.global_predefined_rotation = state_data.get('global_predefined_rotation', 0)
                
                self.migration_log.append("Updated existing application state")
            else:
                # Create new application state
                last_run_date = None
                if state_data.get('last_run_date'):
                    try:
                        last_run_date = datetime.fromisoformat(state_data['last_run_date'])
                    except ValueError:
                        self.logger.warning("Invalid last_run_date format")
                
                app_state = ApplicationState(
                    last_run_date=last_run_date,
                    predefined_chore_states=state_data.get('predefined_chore_states', {}),
                    global_predefined_rotation=state_data.get('global_predefined_rotation', 0)
                )
                
                db.session.add(app_state)
                self.migration_log.append("Created new application state")
            
            db.session.commit()
            self.logger.info("Successfully migrated application state")
            return True
            
        except Exception as e:
            self.logger.error(f"Error migrating application state: {e}")
            db.session.rollback()
            return False
    
    def migrate_assignments(self) -> bool:
        """Migrate current assignments from state.json"""
        self.logger.info("Migrating current assignments...")
        
        try:
            state_data = self.load_json_file('state.json')
            assignments_data = state_data.get('current_assignments', [])
            
            # Clear existing assignments (they should be current)
            Assignment.query.delete()
            
            for assignment_data in assignments_data:
                # Parse dates
                assigned_date = datetime.fromisoformat(assignment_data['assigned_date'])
                due_date = datetime.fromisoformat(assignment_data['due_date'])
                
                assignment = Assignment(
                    chore_id=assignment_data['chore_id'],
                    chore_name=assignment_data['chore_name'],
                    roommate_id=assignment_data['roommate_id'],
                    roommate_name=assignment_data['roommate_name'],
                    assigned_date=assigned_date,
                    due_date=due_date,
                    frequency=assignment_data['frequency'],
                    type=assignment_data['type'],
                    points=assignment_data['points'],
                    sub_chore_completions=assignment_data.get('sub_chore_completions', {})
                )
                
                db.session.add(assignment)
                self.migration_log.append(f"Added assignment: {assignment.chore_name} -> {assignment.roommate_name}")
            
            db.session.commit()
            self.logger.info(f"Successfully migrated {len(assignments_data)} assignments")
            return True
            
        except Exception as e:
            self.logger.error(f"Error migrating assignments: {e}")
            db.session.rollback()
            return False
    
    def migrate_shopping_items(self) -> bool:
        """Migrate shopping list items from shopping_list.json"""
        self.logger.info("Migrating shopping list items...")
        
        try:
            shopping_data = self.load_json_file('shopping_list.json')
            
            for item_data in shopping_data:
                # Check if item already exists
                existing = ShoppingItem.query.filter_by(id=item_data['id']).first()
                if existing:
                    self.logger.info(f"Shopping item {item_data['item_name']} already exists, skipping")
                    continue
                
                # Parse dates
                purchase_date = None
                if item_data.get('purchase_date'):
                    try:
                        purchase_date = datetime.fromisoformat(item_data['purchase_date'])
                    except ValueError:
                        self.logger.warning(f"Invalid purchase_date for item {item_data['item_name']}")
                
                date_added = None
                if item_data.get('date_added'):
                    try:
                        date_added = datetime.fromisoformat(item_data['date_added'])
                    except ValueError:
                        date_added = datetime.utcnow()
                else:
                    date_added = datetime.utcnow()
                
                shopping_item = ShoppingItem(
                    id=item_data['id'],
                    item_name=item_data['item_name'],
                    estimated_price=item_data.get('estimated_price'),
                    actual_price=item_data.get('actual_price'),
                    brand_preference=item_data.get('brand_preference'),
                    added_by=item_data['added_by'],
                    added_by_name=item_data['added_by_name'],
                    purchased_by=item_data.get('purchased_by'),
                    purchased_by_name=item_data.get('purchased_by_name'),
                    purchase_date=purchase_date,
                    notes=item_data.get('notes'),
                    status=item_data.get('status', 'active'),
                    date_added=date_added
                )
                
                db.session.add(shopping_item)
                self.migration_log.append(f"Added shopping item: {shopping_item.item_name}")
            
            db.session.commit()
            self.logger.info(f"Successfully migrated {len(shopping_data)} shopping items")
            return True
            
        except Exception as e:
            self.logger.error(f"Error migrating shopping items: {e}")
            db.session.rollback()
            return False
    
    def migrate_requests(self) -> bool:
        """Migrate purchase requests from requests.json"""
        self.logger.info("Migrating purchase requests...")
        
        try:
            requests_data = self.load_json_file('requests.json')
            
            for request_data in requests_data:
                # Check if request already exists
                existing = Request.query.filter_by(id=request_data['id']).first()
                if existing:
                    self.logger.info(f"Request {request_data['item_name']} already exists, skipping")
                    continue
                
                # Parse dates
                date_requested = None
                if request_data.get('date_requested'):
                    try:
                        date_requested = datetime.fromisoformat(request_data['date_requested'])
                    except ValueError:
                        date_requested = datetime.utcnow()
                else:
                    date_requested = datetime.utcnow()
                
                final_decision_date = None
                if request_data.get('final_decision_date'):
                    try:
                        final_decision_date = datetime.fromisoformat(request_data['final_decision_date'])
                    except ValueError:
                        self.logger.warning(f"Invalid final_decision_date for request {request_data['item_name']}")
                
                request = Request(
                    id=request_data['id'],
                    item_name=request_data['item_name'],
                    estimated_price=request_data.get('estimated_price'),
                    brand_preference=request_data.get('brand_preference'),
                    notes=request_data.get('notes'),
                    requested_by=request_data['requested_by'],
                    requested_by_name=request_data['requested_by_name'],
                    date_requested=date_requested,
                    status=request_data.get('status', 'pending'),
                    approvals=request_data.get('approvals', []),
                    approval_threshold=request_data.get('approval_threshold', 2),
                    auto_approve_under=request_data.get('auto_approve_under', 10.0),
                    final_decision_date=final_decision_date,
                    final_decision_by=request_data.get('final_decision_by'),
                    final_decision_by_name=request_data.get('final_decision_by_name')
                )
                
                db.session.add(request)
                self.migration_log.append(f"Added request: {request.item_name}")
            
            db.session.commit()
            self.logger.info(f"Successfully migrated {len(requests_data)} requests")
            return True
            
        except Exception as e:
            self.logger.error(f"Error migrating requests: {e}")
            db.session.rollback()
            return False
    
    def migrate_laundry_slots(self) -> bool:
        """Migrate laundry slots from laundry_slots.json"""
        self.logger.info("Migrating laundry slots...")
        
        try:
            laundry_data = self.load_json_file('laundry_slots.json')
            
            for slot_data in laundry_data:
                # Check if slot already exists
                existing = LaundrySlot.query.filter_by(id=slot_data['id']).first()
                if existing:
                    self.logger.info(f"Laundry slot {slot_data['id']} already exists, skipping")
                    continue
                
                # Parse dates
                created_date = None
                if slot_data.get('created_date'):
                    try:
                        created_date = datetime.fromisoformat(slot_data['created_date'])
                    except ValueError:
                        created_date = datetime.utcnow()
                else:
                    created_date = datetime.utcnow()
                
                completed_date = None
                if slot_data.get('completed_date'):
                    try:
                        completed_date = datetime.fromisoformat(slot_data['completed_date'])
                    except ValueError:
                        self.logger.warning(f"Invalid completed_date for laundry slot {slot_data['id']}")
                
                laundry_slot = LaundrySlot(
                    id=slot_data['id'],
                    roommate_id=slot_data['roommate_id'],
                    roommate_name=slot_data['roommate_name'],
                    date=slot_data['date'],
                    time_slot=slot_data['time_slot'],
                    machine_type=slot_data['machine_type'],
                    load_type=slot_data.get('load_type'),
                    estimated_loads=slot_data.get('estimated_loads', 1),
                    actual_loads=slot_data.get('actual_loads'),
                    status=slot_data.get('status', 'scheduled'),
                    notes=slot_data.get('notes'),
                    created_date=created_date,
                    completed_date=completed_date
                )
                
                db.session.add(laundry_slot)
                self.migration_log.append(f"Added laundry slot: {laundry_slot.date} {laundry_slot.time_slot}")
            
            db.session.commit()
            self.logger.info(f"Successfully migrated {len(laundry_data)} laundry slots")
            return True
            
        except Exception as e:
            self.logger.error(f"Error migrating laundry slots: {e}")
            db.session.rollback()
            return False
    
    def migrate_blocked_time_slots(self) -> bool:
        """Migrate blocked time slots from blocked_time_slots.json"""
        self.logger.info("Migrating blocked time slots...")
        
        try:
            blocked_data = self.load_json_file('blocked_time_slots.json')
            
            for slot_data in blocked_data:
                # Check if slot already exists
                existing = BlockedTimeSlot.query.filter_by(id=slot_data['id']).first()
                if existing:
                    self.logger.info(f"Blocked time slot {slot_data['id']} already exists, skipping")
                    continue
                
                # Parse created date
                created_date = None
                if slot_data.get('created_date'):
                    try:
                        created_date = datetime.fromisoformat(slot_data['created_date'])
                    except ValueError:
                        created_date = datetime.utcnow()
                else:
                    created_date = datetime.utcnow()
                
                blocked_slot = BlockedTimeSlot(
                    id=slot_data['id'],
                    date=slot_data['date'],
                    time_slot=slot_data['time_slot'],
                    reason=slot_data['reason'],
                    created_by=slot_data['created_by'],
                    created_by_name=slot_data['created_by_name'],
                    created_date=created_date,
                    sync_to_calendar=slot_data.get('sync_to_calendar', False)
                )
                
                db.session.add(blocked_slot)
                self.migration_log.append(f"Added blocked time slot: {blocked_slot.date} {blocked_slot.time_slot}")
            
            db.session.commit()
            self.logger.info(f"Successfully migrated {len(blocked_data)} blocked time slots")
            return True
            
        except Exception as e:
            self.logger.error(f"Error migrating blocked time slots: {e}")
            db.session.rollback()
            return False
    
    def run_full_migration(self, app: Flask) -> bool:
        """Run the complete data migration process."""
        self.logger.info("Starting full data migration from JSON to PostgreSQL...")
        
        with app.app_context():
            # Migration order is important due to foreign key constraints
            migration_steps = [
                ("Roommates", self.migrate_roommates),
                ("Chores and Sub-chores", self.migrate_chores),
                ("Application State", self.migrate_application_state),
                ("Current Assignments", self.migrate_assignments),
                ("Shopping Items", self.migrate_shopping_items),
                ("Purchase Requests", self.migrate_requests),
                ("Laundry Slots", self.migrate_laundry_slots),
                ("Blocked Time Slots", self.migrate_blocked_time_slots)
            ]
            
            success_count = 0
            for step_name, migration_func in migration_steps:
                self.logger.info(f"Running migration step: {step_name}")
                if migration_func():
                    success_count += 1
                    self.logger.info(f"✓ {step_name} migration completed successfully")
                else:
                    self.logger.error(f"✗ {step_name} migration failed")
            
            # Print migration summary
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"MIGRATION SUMMARY")
            self.logger.info(f"{'='*50}")
            self.logger.info(f"Steps completed: {success_count}/{len(migration_steps)}")
            
            if self.migration_log:
                self.logger.info(f"\nDetailed migration log:")
                for log_entry in self.migration_log:
                    self.logger.info(f"  - {log_entry}")
            
            success = success_count == len(migration_steps)
            if success:
                self.logger.info(f"\n🎉 MIGRATION COMPLETED SUCCESSFULLY!")
                self.logger.info(f"All data has been transferred from JSON files to PostgreSQL database.")
            else:
                self.logger.error(f"\n❌ MIGRATION PARTIALLY FAILED!")
                self.logger.error(f"Some data may not have been transferred correctly.")
            
            return success

def setup_app_for_migration():
    """Set up Flask app for migration."""
    app = Flask(__name__)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configure database
    database_config.configure_flask_app(app)
    
    if not database_config.should_use_database():
        logging.error("Database is not configured. Please set up your database connection.")
        sys.exit(1)
    
    # Initialize database
    if not database_initializer.initialize_database(app):
        logging.error("Failed to initialize database.")
        sys.exit(1)
    
    return app

def main():
    """Main migration function."""
    print("RoomieRoster Data Migration Tool")
    print("=" * 40)
    
    # Set up Flask app
    app = setup_app_for_migration()
    
    # Set up data directory
    script_dir = Path(__file__).parent
    data_dir = script_dir / "data"
    
    if not data_dir.exists():
        logging.error(f"Data directory not found: {data_dir}")
        sys.exit(1)
    
    # Run migration
    migrator = DataMigrator(str(data_dir))
    success = migrator.run_full_migration(app)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()