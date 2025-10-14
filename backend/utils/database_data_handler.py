"""
Database-enabled DataHandler for RoomieRoster application.
Provides the same API as the original DataHandler but uses PostgreSQL when available.
Falls back to JSON files when database is not configured.
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_, and_

from .database_config import db, database_config
from .database_models import (
    Roommate, Chore, SubChore, Assignment, ApplicationState,
    ShoppingItem, Request, LaundrySlot, BlockedTimeSlot
)

class DatabaseDataHandler:
    """
    Enhanced DataHandler that uses PostgreSQL when available, with JSON fallback.
    Maintains identical API to the original DataHandler for seamless integration.
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.use_database = database_config.should_use_database()
        
        if not self.use_database:
            # Initialize JSON file paths for fallback
            self.chores_file = self.data_dir / "chores.json"
            self.roommates_file = self.data_dir / "roommates.json"
            self.state_file = self.data_dir / "state.json"
            self.shopping_list_file = self.data_dir / "shopping_list.json"
            self.requests_file = self.data_dir / "requests.json"
            self.laundry_slots_file = self.data_dir / "laundry_slots.json"
            self.blocked_time_slots_file = self.data_dir / "blocked_time_slots.json"
            self._initialize_json_files()
        
        self.logger.info(f"DataHandler initialized with {'PostgreSQL' if self.use_database else 'JSON file'} storage")
    
    def _initialize_json_files(self):
        """Initialize JSON files with default data if they don't exist (fallback mode)."""
        if not self.chores_file.exists():
            self._write_json(self.chores_file, [])
        
        if not self.roommates_file.exists():
            self._write_json(self.roommates_file, [])
        
        if not self.state_file.exists():
            default_state = {
                "last_run_date": None,
                "predefined_chore_states": {},
                "current_assignments": []
            }
            self._write_json(self.state_file, default_state)
        
        if not self.shopping_list_file.exists():
            self._write_json(self.shopping_list_file, [])
        
        if not self.requests_file.exists():
            self._write_json(self.requests_file, [])
        
        if not self.laundry_slots_file.exists():
            self._write_json(self.laundry_slots_file, [])
        
        if not self.blocked_time_slots_file.exists():
            self._write_json(self.blocked_time_slots_file, [])
    
    def _read_json(self, filepath: Path) -> Any:
        """Read JSON data from file (fallback mode)."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Error reading {filepath}: {e}")
            return [] if 'chores' in str(filepath) or 'roommates' in str(filepath) else {}
    
    def _write_json(self, filepath: Path, data: Any):
        """Write JSON data to file (fallback mode)."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error writing {filepath}: {e}")
            raise
    
    # Roommates operations
    def get_roommates(self) -> List[Dict]:
        """Get all roommates."""
        if self.use_database:
            try:
                roommates = Roommate.query.all()
                return [roommate.to_dict() for roommate in roommates]
            except SQLAlchemyError as e:
                self.logger.error(f"Database error getting roommates: {e}")
                return []
        else:
            return self._read_json(self.roommates_file)
    
    def save_roommates(self, roommates: List[Dict]):
        """Save roommates."""
        if self.use_database:
            try:
                # This is typically not used in database mode - individual operations are preferred
                # But we'll support it for compatibility
                Roommate.query.delete()
                for roommate_data in roommates:
                    roommate = Roommate(**roommate_data)
                    db.session.add(roommate)
                db.session.commit()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error saving roommates: {e}")
                db.session.rollback()
                raise
        else:
            self._write_json(self.roommates_file, roommates)
    
    def add_roommate(self, roommate: Dict) -> Dict:
        """Add a new roommate."""
        if self.use_database:
            try:
                new_roommate = Roommate(
                    id=roommate['id'],
                    name=roommate['name'],
                    current_cycle_points=roommate.get('current_cycle_points', 0),
                    google_id=roommate.get('google_id'),
                    google_profile_picture_url=roommate.get('google_profile_picture_url'),
                    linked_at=datetime.fromisoformat(roommate['linked_at']) if roommate.get('linked_at') else None
                )
                db.session.add(new_roommate)
                db.session.commit()
                return new_roommate.to_dict()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error adding roommate: {e}")
                db.session.rollback()
                raise
        else:
            roommates = self.get_roommates()
            roommates.append(roommate)
            self.save_roommates(roommates)
            return roommate
    
    def update_roommate(self, roommate_id: int, updated_roommate: Dict) -> Dict:
        """Update an existing roommate."""
        if self.use_database:
            try:
                roommate = Roommate.query.filter_by(id=roommate_id).first()
                if not roommate:
                    raise ValueError(f"Roommate with id {roommate_id} not found")
                
                roommate.name = updated_roommate['name']
                roommate.current_cycle_points = updated_roommate.get('current_cycle_points', 0)
                roommate.google_id = updated_roommate.get('google_id')
                roommate.google_profile_picture_url = updated_roommate.get('google_profile_picture_url')
                if updated_roommate.get('linked_at'):
                    roommate.linked_at = datetime.fromisoformat(updated_roommate['linked_at'])
                
                db.session.commit()
                return roommate.to_dict()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error updating roommate: {e}")
                db.session.rollback()
                raise
        else:
            roommates = self.get_roommates()
            for i, roommate in enumerate(roommates):
                if roommate['id'] == roommate_id:
                    roommates[i] = updated_roommate
                    self.save_roommates(roommates)
                    return updated_roommate
            raise ValueError(f"Roommate with id {roommate_id} not found")
    
    def delete_roommate(self, roommate_id: int):
        """Delete a roommate."""
        if self.use_database:
            try:
                roommate = Roommate.query.filter_by(id=roommate_id).first()
                if not roommate:
                    raise ValueError(f"Roommate with id {roommate_id} not found")

                # Delete associated assignments first to avoid foreign key constraint violation
                Assignment.query.filter_by(roommate_id=roommate_id).delete()

                db.session.delete(roommate)
                db.session.commit()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error deleting roommate: {e}")
                db.session.rollback()
                raise
        else:
            roommates = self.get_roommates()
            roommates = [r for r in roommates if r['id'] != roommate_id]
            self.save_roommates(roommates)
    
    # Chores operations
    def get_chores(self) -> List[Dict]:
        """Get all chores."""
        if self.use_database:
            try:
                chores = Chore.query.all()
                return [chore.to_dict() for chore in chores]
            except SQLAlchemyError as e:
                self.logger.error(f"Database error getting chores: {e}")
                return []
        else:
            return self._read_json(self.chores_file)
    
    def save_chores(self, chores: List[Dict]):
        """Save chores to storage."""
        if self.use_database:
            try:
                # Not typically used in database mode, but supported for compatibility
                Chore.query.delete()
                for chore_data in chores:
                    chore = Chore(
                        id=chore_data['id'],
                        name=chore_data['name'],
                        frequency=chore_data['frequency'],
                        type=chore_data['type'],
                        points=chore_data['points']
                    )
                    db.session.add(chore)
                    db.session.flush()
                    
                    # Add sub-chores
                    for sub_chore_data in chore_data.get('sub_chores', []):
                        sub_chore = SubChore(
                            id=sub_chore_data['id'],
                            chore_id=chore.id,
                            name=sub_chore_data['name'],
                            completed=sub_chore_data.get('completed', False)
                        )
                        db.session.add(sub_chore)
                
                db.session.commit()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error saving chores: {e}")
                db.session.rollback()
                raise
        else:
            self._write_json(self.chores_file, chores)
    
    def add_chore(self, chore: Dict) -> Dict:
        """Add a new chore."""
        if self.use_database:
            try:
                new_chore = Chore(
                    id=chore['id'],
                    name=chore['name'],
                    frequency=chore['frequency'],
                    type=chore['type'],
                    points=chore['points']
                )
                db.session.add(new_chore)
                db.session.flush()
                
                # Add sub-chores
                for sub_chore_data in chore.get('sub_chores', []):
                    sub_chore = SubChore(
                        id=sub_chore_data['id'],
                        chore_id=new_chore.id,
                        name=sub_chore_data['name'],
                        completed=sub_chore_data.get('completed', False)
                    )
                    db.session.add(sub_chore)
                
                db.session.commit()
                return new_chore.to_dict()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error adding chore: {e}")
                db.session.rollback()
                raise
        else:
            chores = self.get_chores()
            chores.append(chore)
            self.save_chores(chores)
            return chore
    
    def update_chore(self, chore_id: int, updated_chore: Dict) -> Dict:
        """Update an existing chore."""
        if self.use_database:
            try:
                chore = Chore.query.filter_by(id=chore_id).first()
                if not chore:
                    raise ValueError(f"Chore with id {chore_id} not found")
                
                chore.name = updated_chore['name']
                chore.frequency = updated_chore['frequency']
                chore.type = updated_chore['type']
                chore.points = updated_chore['points']
                
                # Update sub-chores (simplified - remove and re-add)
                SubChore.query.filter_by(chore_id=chore_id).delete()
                for sub_chore_data in updated_chore.get('sub_chores', []):
                    sub_chore = SubChore(
                        id=sub_chore_data['id'],
                        chore_id=chore_id,
                        name=sub_chore_data['name'],
                        completed=sub_chore_data.get('completed', False)
                    )
                    db.session.add(sub_chore)
                
                db.session.commit()
                return chore.to_dict()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error updating chore: {e}")
                db.session.rollback()
                raise
        else:
            chores = self.get_chores()
            for i, chore in enumerate(chores):
                if chore['id'] == chore_id:
                    chores[i] = updated_chore
                    self.save_chores(chores)
                    return updated_chore
            raise ValueError(f"Chore with id {chore_id} not found")
    
    def delete_chore(self, chore_id: int):
        """Delete a chore and clean up all related state data."""
        if self.use_database:
            try:
                chore = Chore.query.filter_by(id=chore_id).first()
                if not chore:
                    raise ValueError(f"Chore with id {chore_id} not found")
                
                # Delete related assignments
                Assignment.query.filter_by(chore_id=chore_id).delete()
                
                # Update application state to remove predefined chore states
                app_state = ApplicationState.query.first()
                if app_state and app_state.predefined_chore_states:
                    state_dict = dict(app_state.predefined_chore_states)
                    if str(chore_id) in state_dict:
                        del state_dict[str(chore_id)]
                        app_state.predefined_chore_states = state_dict
                
                db.session.delete(chore)
                db.session.commit()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error deleting chore: {e}")
                db.session.rollback()
                raise
        else:
            # Remove chore from chores list
            chores = self.get_chores()
            chores = [c for c in chores if c['id'] != chore_id]
            self.save_chores(chores)
            
            # Clean up related state data
            state = self.get_state()
            
            # Remove predefined chore state for this chore
            if str(chore_id) in state.get('predefined_chore_states', {}):
                del state['predefined_chore_states'][str(chore_id)]
            
            # Remove current assignments for this chore
            current_assignments = state.get('current_assignments', [])
            state['current_assignments'] = [
                assignment for assignment in current_assignments 
                if assignment.get('chore_id') != chore_id
            ]
            
            # Save the cleaned state
            self.save_state(state)
    
    # State operations
    def get_state(self) -> Dict:
        """Get application state."""
        if self.use_database:
            try:
                app_state = ApplicationState.query.first()
                if app_state:
                    state_dict = app_state.to_dict()
                    # Add current assignments
                    assignments = Assignment.query.all()
                    state_dict['current_assignments'] = [assignment.to_dict() for assignment in assignments]
                    return state_dict
                else:
                    return {
                        "last_run_date": None,
                        "predefined_chore_states": {},
                        "current_assignments": []
                    }
            except SQLAlchemyError as e:
                self.logger.error(f"Database error getting state: {e}")
                return {
                    "last_run_date": None,
                    "predefined_chore_states": {},
                    "current_assignments": []
                }
        else:
            return self._read_json(self.state_file)
    
    def save_state(self, state: Dict):
        """Save application state."""
        if self.use_database:
            try:
                app_state = ApplicationState.query.first()
                if not app_state:
                    app_state = ApplicationState()
                    db.session.add(app_state)
                
                # Update state fields
                if state.get('last_run_date'):
                    if isinstance(state['last_run_date'], str):
                        app_state.last_run_date = datetime.fromisoformat(state['last_run_date'])
                    else:
                        app_state.last_run_date = state['last_run_date']
                
                app_state.predefined_chore_states = state.get('predefined_chore_states', {})
                app_state.global_predefined_rotation = state.get('global_predefined_rotation', 0)
                
                # Handle current assignments separately
                if 'current_assignments' in state:
                    Assignment.query.delete()
                    for assignment_data in state['current_assignments']:
                        assignment = Assignment(
                            chore_id=assignment_data['chore_id'],
                            chore_name=assignment_data['chore_name'],
                            roommate_id=assignment_data['roommate_id'],
                            roommate_name=assignment_data['roommate_name'],
                            assigned_date=datetime.fromisoformat(assignment_data['assigned_date']),
                            due_date=datetime.fromisoformat(assignment_data['due_date']),
                            frequency=assignment_data['frequency'],
                            type=assignment_data['type'],
                            points=assignment_data['points'],
                            sub_chore_completions=assignment_data.get('sub_chore_completions', {})
                        )
                        db.session.add(assignment)
                
                db.session.commit()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error saving state: {e}")
                db.session.rollback()
                raise
        else:
            self._write_json(self.state_file, state)
    
    def update_last_run_date(self, date_str: str):
        """Update the last run date."""
        if self.use_database:
            try:
                app_state = ApplicationState.query.first()
                if not app_state:
                    app_state = ApplicationState()
                    db.session.add(app_state)
                
                app_state.last_run_date = datetime.fromisoformat(date_str)
                db.session.commit()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error updating last run date: {e}")
                db.session.rollback()
                raise
        else:
            state = self.get_state()
            state['last_run_date'] = date_str
            self.save_state(state)
    
    def get_current_assignments(self) -> List[Dict]:
        """Get current chore assignments."""
        if self.use_database:
            try:
                assignments = Assignment.query.all()
                return [assignment.to_dict() for assignment in assignments]
            except SQLAlchemyError as e:
                self.logger.error(f"Database error getting assignments: {e}")
                return []
        else:
            state = self.get_state()
            return state.get('current_assignments', [])
    
    def save_current_assignments(self, assignments: List[Dict]):
        """Save current chore assignments."""
        if self.use_database:
            try:
                # Clear existing assignments
                Assignment.query.delete()
                
                # Add new assignments
                for assignment_data in assignments:
                    assignment = Assignment(
                        chore_id=assignment_data['chore_id'],
                        chore_name=assignment_data['chore_name'],
                        roommate_id=assignment_data['roommate_id'],
                        roommate_name=assignment_data['roommate_name'],
                        assigned_date=datetime.fromisoformat(assignment_data['assigned_date']),
                        due_date=datetime.fromisoformat(assignment_data['due_date']),
                        frequency=assignment_data['frequency'],
                        type=assignment_data['type'],
                        points=assignment_data['points'],
                        sub_chore_completions=assignment_data.get('sub_chore_completions', {})
                    )
                    db.session.add(assignment)
                
                db.session.commit()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error saving assignments: {e}")
                db.session.rollback()
                raise
        else:
            state = self.get_state()
            state['current_assignments'] = assignments
            self.save_state(state)
    
    # Note: The remaining methods (shopping list, requests, laundry slots, etc.) would follow 
    # the same pattern. For brevity, I'll include a few key ones and note that the full 
    # implementation would include all methods from the original DataHandler.
    
    def get_shopping_list(self) -> List[Dict]:
        """Get all shopping list items."""
        if self.use_database:
            try:
                items = ShoppingItem.query.all()
                return [item.to_dict() for item in items]
            except SQLAlchemyError as e:
                self.logger.error(f"Database error getting shopping list: {e}")
                return []
        else:
            return self._read_json(self.shopping_list_file)
    
    def add_shopping_item(self, item: Dict) -> Dict:
        """Add a new item to the shopping list."""
        if self.use_database:
            try:
                new_item = ShoppingItem(
                    id=item['id'],
                    item_name=item['item_name'],
                    estimated_price=item.get('estimated_price'),
                    brand_preference=item.get('brand_preference'),
                    added_by=item['added_by'],
                    added_by_name=item['added_by_name'],
                    notes=item.get('notes'),
                    status=item.get('status', 'active'),
                    date_added=datetime.fromisoformat(item['date_added']) if item.get('date_added') else datetime.utcnow()
                )
                db.session.add(new_item)
                db.session.commit()
                return new_item.to_dict()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error adding shopping item: {e}")
                db.session.rollback()
                raise
        else:
            items = self.get_shopping_list()
            items.append(item)
            self._write_json(self.shopping_list_file, items)
            return item

    def get_shopping_list_by_status(self, status: str) -> List[Dict]:
        """Get shopping list items by status (active, purchased, etc.)."""
        items = self.get_shopping_list()
        return [item for item in items if item.get('status') == status]

    def get_sub_chore_progress(self, chore_id: int, assignment_index: int = None) -> Dict:
        """Get the progress of sub-chores for a specific assignment."""
        # Get the chore to find total sub-chores
        chores = self.get_chores()
        chore = next((c for c in chores if c['id'] == chore_id), None)
        if not chore:
            raise ValueError(f"Chore with id {chore_id} not found")

        total_sub_chores = len(chore.get('sub_chores', []))

        # Get completion status from assignment
        state = self.get_state()
        assignments = state.get('current_assignments', [])

        assignment = None
        if assignment_index is not None:
            if 0 <= assignment_index < len(assignments):
                assignment = assignments[assignment_index]
        else:
            assignment = next((a for a in assignments if a['chore_id'] == chore_id), None)

        if not assignment:
            return {
                "total_sub_chores": total_sub_chores,
                "completed_sub_chores": 0,
                "completion_percentage": 0.0,
                "sub_chore_statuses": {}
            }

        completions = assignment.get('sub_chore_completions', {})
        completed_count = sum(1 for status in completions.values() if status)

        completion_percentage = (completed_count / total_sub_chores * 100) if total_sub_chores > 0 else 0

        return {
            "total_sub_chores": total_sub_chores,
            "completed_sub_chores": completed_count,
            "completion_percentage": round(completion_percentage, 1),
            "sub_chore_statuses": completions
        }

    # Shopping list methods (remaining)
    def get_next_shopping_item_id(self) -> int:
        """Get the next available shopping list item ID."""
        if self.use_database:
            try:
                items = ShoppingItem.query.all()
                if not items:
                    return 1
                return max(item.id for item in items) + 1
            except SQLAlchemyError as e:
                self.logger.error(f"Database error getting next shopping item ID: {e}")
                return 1
        else:
            items = self.get_shopping_list()
            if not items:
                return 1
            return max(item['id'] for item in items) + 1

    def save_shopping_list(self, shopping_list: List[Dict]):
        """Save shopping list to storage."""
        if self.use_database:
            try:
                ShoppingItem.query.delete()
                for item_data in shopping_list:
                    item = ShoppingItem(
                        id=item_data['id'],
                        item_name=item_data['item_name'],
                        estimated_price=item_data.get('estimated_price'),
                        brand_preference=item_data.get('brand_preference'),
                        added_by=item_data['added_by'],
                        added_by_name=item_data['added_by_name'],
                        notes=item_data.get('notes'),
                        status=item_data.get('status', 'active'),
                        date_added=datetime.fromisoformat(item_data['date_added']) if item_data.get('date_added') else datetime.utcnow(),
                        purchased_by=item_data.get('purchased_by'),
                        purchased_by_name=item_data.get('purchased_by_name'),
                        purchase_date=datetime.fromisoformat(item_data['purchase_date']) if item_data.get('purchase_date') else None,
                        actual_price=item_data.get('actual_price')
                    )
                    db.session.add(item)
                db.session.commit()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error saving shopping list: {e}")
                db.session.rollback()
                raise
        else:
            self._write_json(self.shopping_list_file, shopping_list)

    def update_shopping_item(self, item_id: int, updated_item: Dict) -> Dict:
        """Update an existing shopping list item."""
        if self.use_database:
            try:
                item = ShoppingItem.query.filter_by(id=item_id).first()
                if not item:
                    raise ValueError(f"Shopping item with id {item_id} not found")

                item.item_name = updated_item['item_name']
                item.estimated_price = updated_item.get('estimated_price')
                item.brand_preference = updated_item.get('brand_preference')
                item.notes = updated_item.get('notes')
                item.status = updated_item.get('status', 'active')

                db.session.commit()
                return item.to_dict()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error updating shopping item: {e}")
                db.session.rollback()
                raise
        else:
            items = self.get_shopping_list()
            for i, item in enumerate(items):
                if item['id'] == item_id:
                    items[i] = updated_item
                    self._write_json(self.shopping_list_file, items)
                    return updated_item
            raise ValueError(f"Shopping item with id {item_id} not found")

    def delete_shopping_item(self, item_id: int):
        """Delete a shopping list item."""
        if self.use_database:
            try:
                item = ShoppingItem.query.filter_by(id=item_id).first()
                if not item:
                    raise ValueError(f"Shopping item with id {item_id} not found")

                db.session.delete(item)
                db.session.commit()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error deleting shopping item: {e}")
                db.session.rollback()
                raise
        else:
            items = self.get_shopping_list()
            items = [item for item in items if item['id'] != item_id]
            self._write_json(self.shopping_list_file, items)

    def mark_item_purchased(self, item_id: int, purchased_by: int, purchased_by_name: str,
                           actual_price: float = None, notes: str = None) -> Dict:
        """Mark a shopping list item as purchased."""
        if self.use_database:
            try:
                item = ShoppingItem.query.filter_by(id=item_id).first()
                if not item:
                    raise ValueError(f"Shopping item with id {item_id} not found")

                item.status = 'purchased'
                item.purchased_by = purchased_by
                item.purchased_by_name = purchased_by_name
                item.purchase_date = datetime.utcnow()
                if actual_price is not None:
                    item.actual_price = actual_price
                if notes:
                    if item.notes:
                        item.notes += f" | Purchase note: {notes}"
                    else:
                        item.notes = f"Purchase note: {notes}"

                db.session.commit()
                return item.to_dict()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error marking item purchased: {e}")
                db.session.rollback()
                raise
        else:
            items = self.get_shopping_list()
            for item in items:
                if item['id'] == item_id:
                    item['status'] = 'purchased'
                    item['purchased_by'] = purchased_by
                    item['purchased_by_name'] = purchased_by_name
                    item['purchase_date'] = datetime.now().isoformat()
                    if actual_price is not None:
                        item['actual_price'] = actual_price
                    if notes:
                        if item.get('notes'):
                            item['notes'] += f" | Purchase note: {notes}"
                        else:
                            item['notes'] = f"Purchase note: {notes}"

                    self._write_json(self.shopping_list_file, items)
                    return item

            raise ValueError(f"Shopping item with id {item_id} not found")

    def get_purchase_history(self, days: int = 30) -> List[Dict]:
        """Get purchase history for the last N days."""
        from datetime import timedelta

        if self.use_database:
            try:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                items = ShoppingItem.query.filter(
                    ShoppingItem.status == 'purchased',
                    ShoppingItem.purchase_date >= cutoff_date
                ).order_by(ShoppingItem.purchase_date.desc()).all()
                return [item.to_dict() for item in items]
            except SQLAlchemyError as e:
                self.logger.error(f"Database error getting purchase history: {e}")
                return []
        else:
            items = self.get_shopping_list()
            cutoff_date = datetime.now() - timedelta(days=days)

            purchase_history = []
            for item in items:
                if item.get('status') == 'purchased' and item.get('purchase_date'):
                    purchase_date = datetime.fromisoformat(item['purchase_date'])
                    if purchase_date >= cutoff_date:
                        purchase_history.append(item)

            purchase_history.sort(key=lambda x: x['purchase_date'], reverse=True)
            return purchase_history

    def clear_all_purchase_history(self) -> int:
        """Clear all purchase history - reset all purchased items to active status."""
        if self.use_database:
            try:
                items = ShoppingItem.query.filter_by(status='purchased').all()
                cleared_count = len(items)
                for item in items:
                    item.status = 'active'
                    item.purchased_by = None
                    item.purchased_by_name = None
                    item.purchase_date = None
                    item.actual_price = None
                db.session.commit()
                return cleared_count
            except SQLAlchemyError as e:
                self.logger.error(f"Database error clearing purchase history: {e}")
                db.session.rollback()
                raise
        else:
            items = self.get_shopping_list()
            cleared_count = 0

            for item in items:
                if item.get('status') == 'purchased':
                    item['status'] = 'active'
                    item['purchased_by'] = None
                    item['purchased_by_name'] = None
                    item['purchase_date'] = None
                    item['actual_price'] = None
                    cleared_count += 1

            self._write_json(self.shopping_list_file, items)
            return cleared_count

    def clear_purchase_history_from_date(self, from_date_str: str) -> int:
        """Clear purchase history from a specific date onward."""
        from dateutil import parser

        try:
            from_date = parser.parse(from_date_str)
        except Exception as e:
            raise ValueError(f"Invalid date format: {from_date_str}")

        if self.use_database:
            try:
                items = ShoppingItem.query.filter(
                    ShoppingItem.status == 'purchased',
                    ShoppingItem.purchase_date >= from_date
                ).all()
                cleared_count = len(items)
                for item in items:
                    item.status = 'active'
                    item.purchased_by = None
                    item.purchased_by_name = None
                    item.purchase_date = None
                    item.actual_price = None
                db.session.commit()
                return cleared_count
            except SQLAlchemyError as e:
                self.logger.error(f"Database error clearing purchase history from date: {e}")
                db.session.rollback()
                raise
        else:
            items = self.get_shopping_list()
            cleared_count = 0

            for item in items:
                if item.get('status') == 'purchased' and item.get('purchase_date'):
                    try:
                        purchase_date = datetime.fromisoformat(item['purchase_date'])
                        if purchase_date >= from_date:
                            item['status'] = 'active'
                            item['purchased_by'] = None
                            item['purchased_by_name'] = None
                            item['purchase_date'] = None
                            item['actual_price'] = None
                            cleared_count += 1
                    except Exception:
                        continue

            self._write_json(self.shopping_list_file, items)
            return cleared_count

    def get_shopping_list_metadata(self) -> Dict:
        """Get metadata about the shopping list including last modification time."""
        import os

        try:
            if self.use_database:
                items = self.get_shopping_list()
                active_count = len([item for item in items if item.get('status') == 'active'])
                purchased_count = len([item for item in items if item.get('status') == 'purchased'])

                # For database mode, use current timestamp as "last modified"
                return {
                    'last_modified': datetime.utcnow().isoformat(),
                    'total_items': len(items),
                    'active_items': active_count,
                    'purchased_items': purchased_count,
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                mod_time = os.path.getmtime(self.shopping_list_file)
                last_modified = datetime.fromtimestamp(mod_time).isoformat()

                items = self.get_shopping_list()
                active_count = len([item for item in items if item.get('status') == 'active'])
                purchased_count = len([item for item in items if item.get('status') == 'purchased'])

                return {
                    'last_modified': last_modified,
                    'total_items': len(items),
                    'active_items': active_count,
                    'purchased_items': purchased_count,
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            self.logger.error(f"Error getting shopping list metadata: {e}")
            return {
                'last_modified': None,
                'total_items': 0,
                'active_items': 0,
                'purchased_items': 0,
                'timestamp': datetime.utcnow().isoformat()
            }

    # Sub-chore operations
    def get_next_sub_chore_id(self, chore_id: int) -> int:
        """Get the next available sub-chore ID for a chore."""
        if self.use_database:
            try:
                sub_chores = SubChore.query.filter_by(chore_id=chore_id).all()
                if not sub_chores:
                    return 1
                return max(sc.id for sc in sub_chores) + 1
            except SQLAlchemyError as e:
                self.logger.error(f"Database error getting next sub-chore ID: {e}")
                return 1
        else:
            chores = self.get_chores()
            chore = next((c for c in chores if c['id'] == chore_id), None)
            if not chore:
                raise ValueError(f"Chore with id {chore_id} not found")

            if 'sub_chores' not in chore or not chore['sub_chores']:
                return 1

            max_id = max(sub['id'] for sub in chore['sub_chores'])
            return max_id + 1

    def add_sub_chore(self, chore_id: int, sub_chore_name: str) -> Dict:
        """Add a new sub-chore to a chore."""
        if self.use_database:
            try:
                chore = Chore.query.filter_by(id=chore_id).first()
                if not chore:
                    raise ValueError(f"Chore with id {chore_id} not found")

                new_sub_chore = SubChore(
                    id=self.get_next_sub_chore_id(chore_id),
                    chore_id=chore_id,
                    name=sub_chore_name,
                    completed=False
                )
                db.session.add(new_sub_chore)
                db.session.commit()
                return new_sub_chore.to_dict()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error adding sub-chore: {e}")
                db.session.rollback()
                raise
        else:
            chores = self.get_chores()

            for chore in chores:
                if chore['id'] == chore_id:
                    if 'sub_chores' not in chore:
                        chore['sub_chores'] = []

                    new_sub_chore = {
                        "id": self.get_next_sub_chore_id(chore_id),
                        "name": sub_chore_name,
                        "completed": False
                    }
                    chore['sub_chores'].append(new_sub_chore)
                    self.save_chores(chores)
                    return new_sub_chore

            raise ValueError(f"Chore with id {chore_id} not found")

    def update_sub_chore(self, chore_id: int, sub_chore_id: int, sub_chore_name: str) -> Dict:
        """Update a sub-chore's name."""
        if self.use_database:
            try:
                sub_chore = SubChore.query.filter_by(id=sub_chore_id, chore_id=chore_id).first()
                if not sub_chore:
                    raise ValueError(f"Sub-chore with id {sub_chore_id} not found in chore {chore_id}")

                sub_chore.name = sub_chore_name
                db.session.commit()
                return sub_chore.to_dict()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error updating sub-chore: {e}")
                db.session.rollback()
                raise
        else:
            chores = self.get_chores()

            for chore in chores:
                if chore['id'] == chore_id:
                    if 'sub_chores' in chore:
                        for sub_chore in chore['sub_chores']:
                            if sub_chore['id'] == sub_chore_id:
                                sub_chore['name'] = sub_chore_name
                                self.save_chores(chores)
                                return sub_chore

            raise ValueError(f"Sub-chore with id {sub_chore_id} not found in chore {chore_id}")

    def delete_sub_chore(self, chore_id: int, sub_chore_id: int):
        """Delete a sub-chore from a chore."""
        if self.use_database:
            try:
                sub_chore = SubChore.query.filter_by(id=sub_chore_id, chore_id=chore_id).first()
                if not sub_chore:
                    raise ValueError(f"Sub-chore with id {sub_chore_id} not found in chore {chore_id}")

                db.session.delete(sub_chore)
                db.session.commit()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error deleting sub-chore: {e}")
                db.session.rollback()
                raise
        else:
            chores = self.get_chores()

            for chore in chores:
                if chore['id'] == chore_id:
                    if 'sub_chores' in chore:
                        chore['sub_chores'] = [sc for sc in chore['sub_chores'] if sc['id'] != sub_chore_id]
                        self.save_chores(chores)
                        return

            raise ValueError(f"Sub-chore with id {sub_chore_id} not found in chore {chore_id}")

    def toggle_sub_chore_completion(self, chore_id: int, sub_chore_id: int, assignment_index: int = None) -> Dict:
        """Toggle the completion status of a sub-chore in an assignment."""
        if self.use_database:
            try:
                # Get assignments
                assignments = Assignment.query.all()

                # Find the assignment
                assignment = None
                if assignment_index is not None:
                    if 0 <= assignment_index < len(assignments):
                        assignment = assignments[assignment_index]
                else:
                    assignment = Assignment.query.filter_by(chore_id=chore_id).first()

                if not assignment:
                    raise ValueError(f"Assignment for chore {chore_id} not found")

                # Initialize sub_chore_completions if not exists
                if assignment.sub_chore_completions is None:
                    assignment.sub_chore_completions = {}

                # Toggle completion status
                completions = dict(assignment.sub_chore_completions)
                current_status = completions.get(str(sub_chore_id), False)
                completions[str(sub_chore_id)] = not current_status
                assignment.sub_chore_completions = completions

                db.session.commit()
                return {
                    "sub_chore_id": sub_chore_id,
                    "completed": completions[str(sub_chore_id)]
                }
            except SQLAlchemyError as e:
                self.logger.error(f"Database error toggling sub-chore completion: {e}")
                db.session.rollback()
                raise
        else:
            state = self.get_state()
            assignments = state.get('current_assignments', [])

            # Find the assignment
            assignment = None
            if assignment_index is not None:
                if 0 <= assignment_index < len(assignments):
                    assignment = assignments[assignment_index]
            else:
                assignment = next((a for a in assignments if a['chore_id'] == chore_id), None)

            if not assignment:
                raise ValueError(f"Assignment for chore {chore_id} not found")

            # Initialize sub_chore_completions if not exists
            if 'sub_chore_completions' not in assignment:
                assignment['sub_chore_completions'] = {}

            # Toggle completion status
            current_status = assignment['sub_chore_completions'].get(str(sub_chore_id), False)
            assignment['sub_chore_completions'][str(sub_chore_id)] = not current_status

            self.save_state(state)
            return {
                "sub_chore_id": sub_chore_id,
                "completed": assignment['sub_chore_completions'][str(sub_chore_id)]
            }

    # State management methods
    def update_predefined_chore_state(self, chore_id: int, roommate_id: int):
        """Update the last assigned roommate for a predefined chore."""
        if self.use_database:
            try:
                app_state = ApplicationState.query.first()
                if not app_state:
                    app_state = ApplicationState()
                    db.session.add(app_state)

                states = dict(app_state.predefined_chore_states or {})
                states[str(chore_id)] = roommate_id
                app_state.predefined_chore_states = states
                db.session.commit()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error updating predefined chore state: {e}")
                db.session.rollback()
                raise
        else:
            state = self.get_state()
            state['predefined_chore_states'][str(chore_id)] = roommate_id
            self.save_state(state)

    def update_global_predefined_rotation(self, rotation_index: int):
        """Update the global predefined chore rotation index."""
        if self.use_database:
            try:
                app_state = ApplicationState.query.first()
                if not app_state:
                    app_state = ApplicationState()
                    db.session.add(app_state)

                app_state.global_predefined_rotation = rotation_index
                db.session.commit()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error updating global predefined rotation: {e}")
                db.session.rollback()
                raise
        else:
            state = self.get_state()
            state['global_predefined_rotation'] = rotation_index
            self.save_state(state)

    # Request management methods
    def get_requests(self) -> List[Dict]:
        """Get all requests."""
        if self.use_database:
            try:
                requests = Request.query.all()
                return [request.to_dict() for request in requests]
            except SQLAlchemyError as e:
                self.logger.error(f"Database error getting requests: {e}")
                return []
        else:
            return self._read_json(self.requests_file)

    def save_requests(self, requests: List[Dict]):
        """Save requests to storage."""
        if self.use_database:
            try:
                Request.query.delete()
                for request_data in requests:
                    request = Request(
                        id=request_data['id'],
                        item_name=request_data['item_name'],
                        estimated_price=request_data.get('estimated_price'),
                        brand_preference=request_data.get('brand_preference'),
                        requested_by=request_data['requested_by'],
                        requested_by_name=request_data['requested_by_name'],
                        notes=request_data.get('notes'),
                        status=request_data.get('status', 'pending'),
                        approval_threshold=request_data.get('approval_threshold', 1),
                        auto_approve_under=request_data.get('auto_approve_under', 10.0),
                        date_requested=datetime.fromisoformat(request_data['date_requested']) if request_data.get('date_requested') else datetime.utcnow(),
                        approvals=request_data.get('approvals', []),
                        final_decision_by=request_data.get('final_decision_by'),
                        final_decision_by_name=request_data.get('final_decision_by_name'),
                        final_decision_date=datetime.fromisoformat(request_data['final_decision_date']) if request_data.get('final_decision_date') else None
                    )
                    db.session.add(request)
                db.session.commit()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error saving requests: {e}")
                db.session.rollback()
                raise
        else:
            self._write_json(self.requests_file, requests)

    def get_next_request_id(self) -> int:
        """Get the next available request ID."""
        if self.use_database:
            try:
                requests = Request.query.all()
                if not requests:
                    return 1
                return max(request.id for request in requests) + 1
            except SQLAlchemyError as e:
                self.logger.error(f"Database error getting next request ID: {e}")
                return 1
        else:
            requests = self.get_requests()
            if not requests:
                return 1
            return max(request['id'] for request in requests) + 1

    def add_request(self, request: Dict) -> Dict:
        """Add a new request."""
        if self.use_database:
            try:
                new_request = Request(
                    id=request['id'],
                    item_name=request['item_name'],
                    estimated_price=request.get('estimated_price'),
                    brand_preference=request.get('brand_preference'),
                    requested_by=request['requested_by'],
                    requested_by_name=request['requested_by_name'],
                    notes=request.get('notes'),
                    status=request.get('status', 'pending'),
                    approval_threshold=request.get('approval_threshold', 1),
                    auto_approve_under=request.get('auto_approve_under', 10.0),
                    date_requested=datetime.fromisoformat(request['date_requested']) if request.get('date_requested') else datetime.utcnow(),
                    approvals=request.get('approvals', [])
                )

                # Check if should auto-approve
                if request.get('estimated_price', 0) <= request.get('auto_approve_under', 0):
                    new_request.status = 'auto-approved'
                    new_request.final_decision_date = datetime.utcnow()
                    new_request.final_decision_by_name = 'System Auto-Approval'

                    # Auto-promote to shopping list
                    shopping_item = ShoppingItem(
                        id=self.get_next_shopping_item_id(),
                        item_name=request['item_name'],
                        estimated_price=request.get('estimated_price'),
                        brand_preference=request.get('brand_preference', ''),
                        notes=f"Auto-approved request: {request.get('notes', '')}",
                        added_by=request['requested_by'],
                        added_by_name=request['requested_by_name'],
                        status='active',
                        date_added=datetime.utcnow()
                    )
                    db.session.add(shopping_item)

                db.session.add(new_request)
                db.session.commit()
                return new_request.to_dict()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error adding request: {e}")
                db.session.rollback()
                raise
        else:
            requests = self.get_requests()

            # Check if should auto-approve
            if request.get('estimated_price', 0) <= request.get('auto_approve_under', 0):
                request['status'] = 'auto-approved'
                request['final_decision_date'] = datetime.now().isoformat()
                request['final_decision_by_name'] = 'System Auto-Approval'

                # Auto-promote to shopping list
                shopping_item = {
                    'id': self.get_next_shopping_item_id(),
                    'item_name': request['item_name'],
                    'estimated_price': request.get('estimated_price'),
                    'brand_preference': request.get('brand_preference', ''),
                    'notes': f"Auto-approved request: {request.get('notes', '')}",
                    'added_by': request['requested_by'],
                    'added_by_name': request['requested_by_name'],
                    'status': 'active',
                    'date_added': datetime.now().isoformat(),
                    'actual_price': None,
                    'purchased_by': None,
                    'purchased_by_name': None,
                    'purchase_date': None
                }
                self.add_shopping_item(shopping_item)

            requests.append(request)
            self.save_requests(requests)
            return request

    def update_request(self, request_id: int, updated_request: Dict) -> Dict:
        """Update an existing request."""
        if self.use_database:
            try:
                request = Request.query.filter_by(id=request_id).first()
                if not request:
                    raise ValueError(f"Request with id {request_id} not found")

                request.item_name = updated_request['item_name']
                request.estimated_price = updated_request.get('estimated_price')
                request.brand_preference = updated_request.get('brand_preference')
                request.notes = updated_request.get('notes')
                request.status = updated_request.get('status', 'pending')

                db.session.commit()
                return request.to_dict()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error updating request: {e}")
                db.session.rollback()
                raise
        else:
            requests = self.get_requests()
            for i, request in enumerate(requests):
                if request['id'] == request_id:
                    requests[i] = updated_request
                    self.save_requests(requests)
                    return updated_request
            raise ValueError(f"Request with id {request_id} not found")

    def delete_request(self, request_id: int):
        """Delete a request."""
        if self.use_database:
            try:
                request = Request.query.filter_by(id=request_id).first()
                if not request:
                    raise ValueError(f"Request with id {request_id} not found")

                db.session.delete(request)
                db.session.commit()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error deleting request: {e}")
                db.session.rollback()
                raise
        else:
            requests = self.get_requests()
            updated_requests = [r for r in requests if r['id'] != request_id]
            if len(updated_requests) == len(requests):
                raise ValueError(f"Request with id {request_id} not found")
            self.save_requests(updated_requests)

    def approve_request(self, request_id: int, approval_data: Dict) -> Dict:
        """Approve or decline a request."""
        if self.use_database:
            try:
                request = Request.query.filter_by(id=request_id).first()
                if not request:
                    raise ValueError(f"Request with id {request_id} not found")

                if request.status != 'pending':
                    raise ValueError(f"Request {request_id} is not pending approval")

                # Add approval to list
                approval = {
                    'approved_by': approval_data['approved_by'],
                    'approved_by_name': approval_data['approved_by_name'],
                    'approval_status': approval_data['approval_status'],
                    'approval_date': datetime.utcnow().isoformat(),
                    'notes': approval_data.get('notes', '')
                }

                # Remove any existing approval from this user
                approvals = [a for a in request.approvals if a['approved_by'] != approval_data['approved_by']]
                approvals.append(approval)
                request.approvals = approvals

                # Check if request is now approved or declined
                approval_count = len([a for a in approvals if a['approval_status'] == 'approved'])
                decline_count = len([a for a in approvals if a['approval_status'] == 'declined'])

                roommates = Roommate.query.all()
                total_roommates = len(roommates)
                other_roommates = total_roommates - 1

                if approval_count >= request.approval_threshold:
                    request.status = 'approved'
                    request.final_decision_date = datetime.utcnow()
                    request.final_decision_by = approval_data['approved_by']
                    request.final_decision_by_name = approval_data['approved_by_name']

                    # Auto-promote to shopping list
                    shopping_item = ShoppingItem(
                        id=self.get_next_shopping_item_id(),
                        item_name=request.item_name,
                        estimated_price=request.estimated_price,
                        brand_preference=request.brand_preference or '',
                        notes=f"Approved request: {request.notes or ''}",
                        added_by=request.requested_by,
                        added_by_name=request.requested_by_name,
                        status='active',
                        date_added=datetime.utcnow()
                    )
                    db.session.add(shopping_item)

                elif decline_count >= (other_roommates // 2 + 1):
                    request.status = 'declined'
                    request.final_decision_date = datetime.utcnow()
                    request.final_decision_by = approval_data['approved_by']
                    request.final_decision_by_name = approval_data['approved_by_name']

                db.session.commit()
                return request.to_dict()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error approving request: {e}")
                db.session.rollback()
                raise
        else:
            requests = self.get_requests()
            for request in requests:
                if request['id'] == request_id:
                    if request['status'] != 'pending':
                        raise ValueError(f"Request {request_id} is not pending approval")

                    # Add approval to list
                    approval = {
                        'approved_by': approval_data['approved_by'],
                        'approved_by_name': approval_data['approved_by_name'],
                        'approval_status': approval_data['approval_status'],
                        'approval_date': datetime.now().isoformat(),
                        'notes': approval_data.get('notes', '')
                    }

                    # Remove any existing approval from this user
                    request['approvals'] = [a for a in request['approvals']
                                          if a['approved_by'] != approval_data['approved_by']]
                    request['approvals'].append(approval)

                    # Check if request is now approved or declined
                    approval_count = len([a for a in request['approvals'] if a['approval_status'] == 'approved'])
                    decline_count = len([a for a in request['approvals'] if a['approval_status'] == 'declined'])

                    roommates = self.get_roommates()
                    total_roommates = len(roommates)
                    other_roommates = total_roommates - 1

                    if approval_count >= request['approval_threshold']:
                        request['status'] = 'approved'
                        request['final_decision_date'] = datetime.now().isoformat()
                        request['final_decision_by'] = approval_data['approved_by']
                        request['final_decision_by_name'] = approval_data['approved_by_name']

                        # Auto-promote to shopping list
                        shopping_item = {
                            'id': self.get_next_shopping_item_id(),
                            'item_name': request['item_name'],
                            'estimated_price': request.get('estimated_price'),
                            'brand_preference': request.get('brand_preference', ''),
                            'notes': f"Approved request: {request.get('notes', '')}",
                            'added_by': request['requested_by'],
                            'added_by_name': request['requested_by_name'],
                            'status': 'active',
                            'date_added': datetime.now().isoformat(),
                            'actual_price': None,
                            'purchased_by': None,
                            'purchased_by_name': None,
                            'purchase_date': None
                        }
                        self.add_shopping_item(shopping_item)

                    elif decline_count >= (other_roommates // 2 + 1):
                        request['status'] = 'declined'
                        request['final_decision_date'] = datetime.now().isoformat()
                        request['final_decision_by'] = approval_data['approved_by']
                        request['final_decision_by_name'] = approval_data['approved_by_name']

                    self.save_requests(requests)
                    return request

            raise ValueError(f"Request with id {request_id} not found")

    def get_requests_by_status(self, status: str) -> List[Dict]:
        """Get requests by status."""
        requests = self.get_requests()
        return [request for request in requests if request.get('status') == status]

    def get_pending_requests_for_user(self, user_id: int) -> List[Dict]:
        """Get pending requests that a user hasn't voted on yet."""
        requests = self.get_requests_by_status('pending')
        pending_for_user = []

        for request in requests:
            if request['requested_by'] == user_id:
                continue

            user_voted = any(approval['approved_by'] == user_id for approval in request['approvals'])
            if not user_voted:
                pending_for_user.append(request)

        return pending_for_user

    def get_requests_metadata(self) -> Dict:
        """Get metadata about requests including last modification time."""
        import os

        try:
            if self.use_database:
                requests = self.get_requests()
                pending_count = len([r for r in requests if r.get('status') == 'pending'])
                approved_count = len([r for r in requests if r.get('status') == 'approved'])
                declined_count = len([r for r in requests if r.get('status') == 'declined'])
                auto_approved_count = len([r for r in requests if r.get('status') == 'auto-approved'])

                return {
                    'last_modified': datetime.utcnow().isoformat(),
                    'total_requests': len(requests),
                    'pending_requests': pending_count,
                    'approved_requests': approved_count,
                    'declined_requests': declined_count,
                    'auto_approved_requests': auto_approved_count,
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                mod_time = os.path.getmtime(self.requests_file)
                last_modified = datetime.fromtimestamp(mod_time).isoformat()

                requests = self.get_requests()
                pending_count = len([r for r in requests if r.get('status') == 'pending'])
                approved_count = len([r for r in requests if r.get('status') == 'approved'])
                declined_count = len([r for r in requests if r.get('status') == 'declined'])
                auto_approved_count = len([r for r in requests if r.get('status') == 'auto-approved'])

                return {
                    'last_modified': last_modified,
                    'total_requests': len(requests),
                    'pending_requests': pending_count,
                    'approved_requests': approved_count,
                    'declined_requests': declined_count,
                    'auto_approved_requests': auto_approved_count,
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            self.logger.error(f"Error getting requests metadata: {e}")
            return {
                'last_modified': None,
                'total_requests': 0,
                'pending_requests': 0,
                'approved_requests': 0,
                'declined_requests': 0,
                'auto_approved_requests': 0,
                'timestamp': datetime.utcnow().isoformat()
            }

    # Laundry scheduling operations
    def get_laundry_slots(self) -> List[Dict]:
        """Get all laundry slots."""
        if self.use_database:
            try:
                slots = LaundrySlot.query.all()
                return [slot.to_dict() for slot in slots]
            except SQLAlchemyError as e:
                self.logger.error(f"Database error getting laundry slots: {e}")
                return []
        else:
            return self._read_json(self.laundry_slots_file)

    def save_laundry_slots(self, slots: List[Dict]):
        """Save laundry slots to storage."""
        if self.use_database:
            try:
                LaundrySlot.query.delete()
                for slot_data in slots:
                    slot = LaundrySlot(
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
                        created_at=datetime.fromisoformat(slot_data['created_at']) if slot_data.get('created_at') else datetime.utcnow(),
                        completed_date=datetime.fromisoformat(slot_data['completed_date']) if slot_data.get('completed_date') else None
                    )
                    db.session.add(slot)
                db.session.commit()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error saving laundry slots: {e}")
                db.session.rollback()
                raise
        else:
            self._write_json(self.laundry_slots_file, slots)

    def get_next_laundry_slot_id(self) -> int:
        """Get the next available laundry slot ID."""
        if self.use_database:
            try:
                slots = LaundrySlot.query.all()
                if not slots:
                    return 1
                return max(slot.id for slot in slots) + 1
            except SQLAlchemyError as e:
                self.logger.error(f"Database error getting next laundry slot ID: {e}")
                return 1
        else:
            slots = self.get_laundry_slots()
            if not slots:
                return 1
            return max(slot['id'] for slot in slots) + 1

    def add_laundry_slot(self, slot: Dict) -> Dict:
        """Add a new laundry slot."""
        if self.use_database:
            try:
                new_slot = LaundrySlot(
                    id=slot['id'],
                    roommate_id=slot['roommate_id'],
                    roommate_name=slot['roommate_name'],
                    date=slot['date'],
                    time_slot=slot['time_slot'],
                    machine_type=slot['machine_type'],
                    load_type=slot.get('load_type'),
                    estimated_loads=slot.get('estimated_loads', 1),
                    status=slot.get('status', 'scheduled'),
                    notes=slot.get('notes'),
                    created_at=datetime.fromisoformat(slot['created_at']) if slot.get('created_at') else datetime.utcnow()
                )
                db.session.add(new_slot)
                db.session.commit()
                return new_slot.to_dict()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error adding laundry slot: {e}")
                db.session.rollback()
                raise
        else:
            slots = self.get_laundry_slots()
            slots.append(slot)
            self._write_json(self.laundry_slots_file, slots)
            return slot

    def update_laundry_slot(self, slot_id: int, updated_slot: Dict) -> Dict:
        """Update an existing laundry slot."""
        if self.use_database:
            try:
                slot = LaundrySlot.query.filter_by(id=slot_id).first()
                if not slot:
                    raise ValueError(f"Laundry slot with id {slot_id} not found")

                slot.roommate_id = updated_slot['roommate_id']
                slot.roommate_name = updated_slot['roommate_name']
                slot.date = updated_slot['date']
                slot.time_slot = updated_slot['time_slot']
                slot.machine_type = updated_slot['machine_type']
                slot.load_type = updated_slot.get('load_type')
                slot.estimated_loads = updated_slot.get('estimated_loads', 1)
                slot.status = updated_slot.get('status', 'scheduled')
                slot.notes = updated_slot.get('notes')

                db.session.commit()
                return slot.to_dict()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error updating laundry slot: {e}")
                db.session.rollback()
                raise
        else:
            slots = self.get_laundry_slots()
            for i, slot in enumerate(slots):
                if slot['id'] == slot_id:
                    slots[i] = updated_slot
                    self._write_json(self.laundry_slots_file, slots)
                    return updated_slot
            raise ValueError(f"Laundry slot with id {slot_id} not found")

    def delete_laundry_slot(self, slot_id: int):
        """Delete a laundry slot."""
        if self.use_database:
            try:
                slot = LaundrySlot.query.filter_by(id=slot_id).first()
                if not slot:
                    raise ValueError(f"Laundry slot with id {slot_id} not found")

                db.session.delete(slot)
                db.session.commit()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error deleting laundry slot: {e}")
                db.session.rollback()
                raise
        else:
            slots = self.get_laundry_slots()
            original_count = len(slots)
            slots = [slot for slot in slots if slot['id'] != slot_id]
            if len(slots) == original_count:
                raise ValueError(f"Laundry slot with id {slot_id} not found")
            self._write_json(self.laundry_slots_file, slots)

    def get_laundry_slots_by_date(self, date: str) -> List[Dict]:
        """Get laundry slots for a specific date."""
        slots = self.get_laundry_slots()
        return [slot for slot in slots if slot.get('date') == date]

    def get_laundry_slots_by_roommate(self, roommate_id: int) -> List[Dict]:
        """Get laundry slots for a specific roommate."""
        slots = self.get_laundry_slots()
        return [slot for slot in slots if slot.get('roommate_id') == roommate_id]

    def get_laundry_slots_by_status(self, status: str) -> List[Dict]:
        """Get laundry slots by status."""
        slots = self.get_laundry_slots()
        return [slot for slot in slots if slot.get('status') == status]

    def check_laundry_slot_conflicts(self, date: str, time_slot: str, machine_type: str, exclude_slot_id: int = None) -> List[Dict]:
        """Check for conflicting laundry slots."""
        slots = self.get_laundry_slots()
        conflicts = []

        for slot in slots:
            if exclude_slot_id and slot['id'] == exclude_slot_id:
                continue

            if slot.get('status') == 'cancelled':
                continue

            if (slot.get('date') == date and
                slot.get('time_slot') == time_slot and
                slot.get('machine_type') == machine_type):
                conflicts.append(slot)

        # Check blocked time slot conflicts
        blocked_conflicts = self.check_blocked_time_conflicts(date, time_slot)
        for blocked_slot in blocked_conflicts:
            conflict = {
                'id': f"blocked_{blocked_slot['id']}",
                'roommate_name': 'BLOCKED',
                'date': blocked_slot['date'],
                'time_slot': blocked_slot['time_slot'],
                'machine_type': 'all',
                'status': 'blocked',
                'reason': blocked_slot.get('reason', 'Time slot blocked by calendar settings'),
                'blocked_by': blocked_slot.get('created_by', 'System')
            }
            conflicts.append(conflict)

        return conflicts

    def mark_laundry_slot_completed(self, slot_id: int, actual_loads: int = None, completion_notes: str = None) -> Dict:
        """Mark a laundry slot as completed."""
        if self.use_database:
            try:
                slot = LaundrySlot.query.filter_by(id=slot_id).first()
                if not slot:
                    raise ValueError(f"Laundry slot with id {slot_id} not found")

                if slot.status == 'completed':
                    raise ValueError(f"Laundry slot {slot_id} is already completed")

                slot.status = 'completed'
                slot.completed_date = datetime.utcnow()

                if actual_loads is not None:
                    slot.actual_loads = actual_loads

                if completion_notes:
                    if slot.notes:
                        slot.notes += f" | Completion: {completion_notes}"
                    else:
                        slot.notes = f"Completion: {completion_notes}"

                db.session.commit()
                return slot.to_dict()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error marking laundry slot completed: {e}")
                db.session.rollback()
                raise
        else:
            slots = self.get_laundry_slots()
            for slot in slots:
                if slot['id'] == slot_id:
                    if slot.get('status') == 'completed':
                        raise ValueError(f"Laundry slot {slot_id} is already completed")

                    slot['status'] = 'completed'
                    slot['completed_date'] = datetime.now().isoformat()

                    if actual_loads is not None:
                        slot['actual_loads'] = actual_loads

                    if completion_notes:
                        if slot.get('notes'):
                            slot['notes'] += f" | Completion: {completion_notes}"
                        else:
                            slot['notes'] = f"Completion: {completion_notes}"

                    self._write_json(self.laundry_slots_file, slots)
                    return slot

            raise ValueError(f"Laundry slot with id {slot_id} not found")

    def get_laundry_slots_metadata(self) -> Dict:
        """Get metadata about laundry slots."""
        import os

        try:
            if self.use_database:
                slots = self.get_laundry_slots()
                scheduled_count = len([slot for slot in slots if slot.get('status') == 'scheduled'])
                in_progress_count = len([slot for slot in slots if slot.get('status') == 'in_progress'])
                completed_count = len([slot for slot in slots if slot.get('status') == 'completed'])
                cancelled_count = len([slot for slot in slots if slot.get('status') == 'cancelled'])

                return {
                    'last_modified': datetime.utcnow().isoformat(),
                    'total_slots': len(slots),
                    'scheduled_slots': scheduled_count,
                    'in_progress_slots': in_progress_count,
                    'completed_slots': completed_count,
                    'cancelled_slots': cancelled_count,
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                mod_time = os.path.getmtime(self.laundry_slots_file)
                last_modified = datetime.fromtimestamp(mod_time).isoformat()

                slots = self.get_laundry_slots()
                scheduled_count = len([slot for slot in slots if slot.get('status') == 'scheduled'])
                in_progress_count = len([slot for slot in slots if slot.get('status') == 'in_progress'])
                completed_count = len([slot for slot in slots if slot.get('status') == 'completed'])
                cancelled_count = len([slot for slot in slots if slot.get('status') == 'cancelled'])

                return {
                    'last_modified': last_modified,
                    'total_slots': len(slots),
                    'scheduled_slots': scheduled_count,
                    'in_progress_slots': in_progress_count,
                    'completed_slots': completed_count,
                    'cancelled_slots': cancelled_count,
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            self.logger.error(f"Error getting laundry slots metadata: {e}")
            return {
                'last_modified': None,
                'total_slots': 0,
                'scheduled_slots': 0,
                'in_progress_slots': 0,
                'completed_slots': 0,
                'cancelled_slots': 0,
                'timestamp': datetime.utcnow().isoformat()
            }

    def _parse_laundry_slot_end_time(self, slot: Dict) -> Optional[datetime]:
        """
        Parse laundry slot's date and time_slot to get end datetime.
        Handles various time formats: "08:00-10:00", "12:00 PM-2:00 PM", etc.
        Returns None if parsing fails.
        """
        try:
            date_str = slot.get('date')  # YYYY-MM-DD format
            time_slot = slot.get('time_slot')  # e.g., "12:00 PM-2:00 PM"

            if not date_str or not time_slot:
                return None

            # Extract end time from time_slot (format: "start-end")
            if '-' in time_slot:
                end_time_str = time_slot.split('-')[1].strip()
            else:
                self.logger.warning(f"Invalid time_slot format: {time_slot}")
                return None

            # Combine date and end time
            datetime_str = f"{date_str} {end_time_str}"

            # Try parsing with different formats
            for fmt in ['%Y-%m-%d %I:%M %p', '%Y-%m-%d %H:%M', '%Y-%m-%d %I:%M%p']:
                try:
                    return datetime.strptime(datetime_str, fmt)
                except ValueError:
                    continue

            self.logger.warning(f"Could not parse datetime: {datetime_str}")
            return None

        except Exception as e:
            self.logger.error(f"Error parsing laundry slot end time: {e}")
            return None

    def _is_laundry_slot_past(self, slot: Dict) -> bool:
        """
        Check if a laundry slot's end time has passed.
        Returns True if the slot is past, False otherwise.
        """
        end_time = self._parse_laundry_slot_end_time(slot)
        if end_time is None:
            # If we can't parse the time, assume it's not past (safe default)
            return False

        return datetime.now() > end_time

    def get_active_laundry_slots(self) -> List[Dict]:
        """
        Get all active laundry slots (not past their end time).
        Filters out slots whose end time has already passed.
        """
        all_slots = self.get_laundry_slots()
        active_slots = [slot for slot in all_slots if not self._is_laundry_slot_past(slot)]
        return active_slots

    def auto_complete_past_laundry_slots(self) -> int:
        """
        Automatically mark past scheduled laundry slots as completed.
        Only affects slots with status='scheduled' whose end time has passed.
        Returns the number of slots auto-completed.
        """
        try:
            all_slots = self.get_laundry_slots()
            completed_count = 0

            for slot in all_slots:
                # Only auto-complete scheduled slots
                if slot.get('status') != 'scheduled':
                    continue

                # Check if slot is past
                if self._is_laundry_slot_past(slot):
                    try:
                        # Mark as completed
                        self.mark_laundry_slot_completed(
                            slot['id'],
                            actual_loads=slot.get('estimated_loads'),
                            completion_notes="Auto-completed (past scheduled time)"
                        )
                        completed_count += 1
                        self.logger.info(f"Auto-completed past laundry slot {slot['id']}")
                    except Exception as e:
                        self.logger.error(f"Error auto-completing slot {slot['id']}: {e}")

            return completed_count

        except Exception as e:
            self.logger.error(f"Error in auto_complete_past_laundry_slots: {e}")
            return 0

    def delete_old_completed_laundry_slots(self, days_threshold: int = 30) -> int:
        """
        Delete completed laundry slots older than the specified threshold.
        Default: 30 days. Returns the number of slots deleted.
        """
        try:
            if self.use_database:
                from datetime import timedelta
                cutoff_date = datetime.now() - timedelta(days=days_threshold)

                deleted_count = LaundrySlot.query.filter(
                    and_(
                        LaundrySlot.status == 'completed',
                        LaundrySlot.completed_date < cutoff_date
                    )
                ).delete()

                db.session.commit()
                self.logger.info(f"Deleted {deleted_count} old completed laundry slots")
                return deleted_count
            else:
                # JSON file mode
                from datetime import timedelta
                slots = self.get_laundry_slots()
                cutoff_date = datetime.now() - timedelta(days=days_threshold)

                initial_count = len(slots)
                filtered_slots = []

                for slot in slots:
                    # Keep slot if not completed OR completed recently
                    if slot.get('status') != 'completed':
                        filtered_slots.append(slot)
                    else:
                        completed_date_str = slot.get('completed_date')
                        if completed_date_str:
                            try:
                                completed_date = datetime.fromisoformat(completed_date_str)
                                if completed_date >= cutoff_date:
                                    filtered_slots.append(slot)
                            except ValueError:
                                # If date parsing fails, keep the slot
                                filtered_slots.append(slot)
                        else:
                            # No completion date, keep it
                            filtered_slots.append(slot)

                deleted_count = initial_count - len(filtered_slots)
                self.save_laundry_slots(filtered_slots)
                self.logger.info(f"Deleted {deleted_count} old completed laundry slots")
                return deleted_count

        except Exception as e:
            self.logger.error(f"Error deleting old completed laundry slots: {e}")
            if self.use_database:
                db.session.rollback()
            return 0

    # Blocked Time Slots operations
    def get_blocked_time_slots(self) -> List[Dict]:
        """Get all blocked time slots."""
        if self.use_database:
            try:
                blocked_slots = BlockedTimeSlot.query.all()
                return [slot.to_dict() for slot in blocked_slots]
            except SQLAlchemyError as e:
                self.logger.error(f"Database error getting blocked time slots: {e}")
                return []
        else:
            return self._read_json(self.blocked_time_slots_file)

    def save_blocked_time_slots(self, blocked_slots: List[Dict]):
        """Save blocked time slots to storage."""
        if self.use_database:
            try:
                BlockedTimeSlot.query.delete()
                for slot_data in blocked_slots:
                    slot = BlockedTimeSlot(
                        id=slot_data['id'],
                        date=slot_data['date'],
                        time_slot=slot_data['time_slot'],
                        reason=slot_data.get('reason'),
                        created_by=slot_data.get('created_by'),
                        created_by_name=slot_data.get('created_by_name'),
                        sync_to_calendar=slot_data.get('sync_to_calendar', False),
                        created_at=datetime.fromisoformat(slot_data['created_at']) if slot_data.get('created_at') else datetime.utcnow()
                    )
                    db.session.add(slot)
                db.session.commit()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error saving blocked time slots: {e}")
                db.session.rollback()
                raise
        else:
            self._write_json(self.blocked_time_slots_file, blocked_slots)

    def get_next_blocked_slot_id(self) -> int:
        """Get the next available blocked slot ID."""
        if self.use_database:
            try:
                blocked_slots = BlockedTimeSlot.query.all()
                if not blocked_slots:
                    return 1
                return max(slot.id for slot in blocked_slots) + 1
            except SQLAlchemyError as e:
                self.logger.error(f"Database error getting next blocked slot ID: {e}")
                return 1
        else:
            blocked_slots = self.get_blocked_time_slots()
            if not blocked_slots:
                return 1
            return max(slot['id'] for slot in blocked_slots) + 1

    def add_blocked_time_slot(self, blocked_slot: Dict) -> Dict:
        """Add a new blocked time slot."""
        if self.use_database:
            try:
                new_slot = BlockedTimeSlot(
                    id=blocked_slot['id'],
                    date=blocked_slot['date'],
                    time_slot=blocked_slot['time_slot'],
                    reason=blocked_slot.get('reason'),
                    created_by=blocked_slot.get('created_by'),
                    created_by_name=blocked_slot.get('created_by_name'),
                    sync_to_calendar=blocked_slot.get('sync_to_calendar', False),
                    created_at=datetime.fromisoformat(blocked_slot['created_at']) if blocked_slot.get('created_at') else datetime.utcnow()
                )
                db.session.add(new_slot)
                db.session.commit()
                return new_slot.to_dict()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error adding blocked time slot: {e}")
                db.session.rollback()
                raise
        else:
            blocked_slots = self.get_blocked_time_slots()
            blocked_slots.append(blocked_slot)
            self._write_json(self.blocked_time_slots_file, blocked_slots)
            return blocked_slot

    def update_blocked_time_slot(self, slot_id: int, updated_slot: Dict) -> Dict:
        """Update an existing blocked time slot."""
        if self.use_database:
            try:
                slot = BlockedTimeSlot.query.filter_by(id=slot_id).first()
                if not slot:
                    raise ValueError(f"Blocked time slot with id {slot_id} not found")

                slot.date = updated_slot['date']
                slot.time_slot = updated_slot['time_slot']
                slot.reason = updated_slot.get('reason')
                slot.sync_to_calendar = updated_slot.get('sync_to_calendar', False)

                db.session.commit()
                return slot.to_dict()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error updating blocked time slot: {e}")
                db.session.rollback()
                raise
        else:
            blocked_slots = self.get_blocked_time_slots()
            for i, slot in enumerate(blocked_slots):
                if slot['id'] == slot_id:
                    blocked_slots[i] = updated_slot
                    self._write_json(self.blocked_time_slots_file, blocked_slots)
                    return updated_slot
            raise ValueError(f"Blocked time slot with id {slot_id} not found")

    def delete_blocked_time_slot(self, slot_id: int):
        """Delete a blocked time slot."""
        if self.use_database:
            try:
                slot = BlockedTimeSlot.query.filter_by(id=slot_id).first()
                if not slot:
                    raise ValueError(f"Blocked time slot with id {slot_id} not found")

                db.session.delete(slot)
                db.session.commit()
            except SQLAlchemyError as e:
                self.logger.error(f"Database error deleting blocked time slot: {e}")
                db.session.rollback()
                raise
        else:
            blocked_slots = self.get_blocked_time_slots()
            original_count = len(blocked_slots)
            blocked_slots = [slot for slot in blocked_slots if slot['id'] != slot_id]
            if len(blocked_slots) == original_count:
                raise ValueError(f"Blocked time slot with id {slot_id} not found")
            self._write_json(self.blocked_time_slots_file, blocked_slots)

    def get_blocked_time_slots_by_date(self, date: str) -> List[Dict]:
        """Get blocked time slots for a specific date."""
        blocked_slots = self.get_blocked_time_slots()
        return [slot for slot in blocked_slots if slot.get('date') == date]

    def check_blocked_time_conflicts(self, date: str, time_slot: str, exclude_slot_id: int = None) -> List[Dict]:
        """Check if a time slot conflicts with any blocked time slots."""
        blocked_slots = self.get_blocked_time_slots()
        conflicts = []

        for slot in blocked_slots:
            if exclude_slot_id and slot['id'] == exclude_slot_id:
                continue

            if slot.get('date') == date and slot.get('time_slot') == time_slot:
                conflicts.append(slot)

        return conflicts

    def is_time_slot_blocked(self, date: str, time_slot: str) -> bool:
        """Check if a specific time slot is blocked."""
        conflicts = self.check_blocked_time_conflicts(date, time_slot)
        return len(conflicts) > 0