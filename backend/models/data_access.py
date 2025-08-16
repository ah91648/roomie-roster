"""
Data Access Layer (DAO) for RoomieRoster SQLAlchemy models.

This module provides a SQLAlchemy-based replacement for the DataHandler class,
maintaining the same API while using database persistence instead of JSON files.
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
import json
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .models import (
    db, Roommate, Chore, SubChore, Assignment, SubChoreCompletion,
    ShoppingItem, PurchaseRequest, Approval, LaundrySlot, BlockedTimeSlot,
    ApplicationState
)


class DatabaseDataHandler:
    """SQLAlchemy-based data handler that replicates DataHandler API."""
    
    def __init__(self, session: Session = None):
        """Initialize with optional session (defaults to db.session)."""
        self.session = session or db.session
    
    def _commit_or_rollback(self):
        """Commit changes or rollback on error."""
        try:
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise e
    
    # Chores operations
    def get_chores(self) -> List[Dict]:
        """Get all chores."""
        chores = self.session.query(Chore).all()
        return [chore.to_dict(include_sub_chores=True) for chore in chores]
    
    def save_chores(self, chores: List[Dict]):
        """Save chores to database (bulk replace operation)."""
        # This method is kept for API compatibility but not recommended
        # Individual add/update/delete methods should be used instead
        try:
            # Clear existing chores (dangerous operation)
            self.session.query(Chore).delete()
            
            # Add new chores
            for chore_data in chores:
                chore = Chore.from_dict(chore_data)
                self.session.add(chore)
                
                # Add sub-chores if present
                if 'sub_chores' in chore_data:
                    for sub_data in chore_data['sub_chores']:
                        sub_chore = SubChore(
                            name=sub_data['name'],
                            chore=chore
                        )
                        self.session.add(sub_chore)
            
            self._commit_or_rollback()
        except Exception as e:
            raise ValueError(f"Failed to save chores: {str(e)}")
    
    def add_chore(self, chore_data: Dict) -> Dict:
        """Add a new chore."""
        try:
            # Extract sub-chores data
            sub_chores_data = chore_data.pop('sub_chores', [])
            
            # Create chore
            chore = Chore.from_dict(chore_data)
            self.session.add(chore)
            self.session.flush()  # Get the ID
            
            # Add sub-chores
            for sub_data in sub_chores_data:
                sub_chore = SubChore(
                    name=sub_data['name'],
                    chore=chore
                )
                self.session.add(sub_chore)
            
            self._commit_or_rollback()
            return chore.to_dict(include_sub_chores=True)
        except IntegrityError as e:
            raise ValueError(f"Chore with this name may already exist: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to add chore: {str(e)}")
    
    def update_chore(self, chore_id: int, updated_chore: Dict) -> Dict:
        """Update an existing chore."""
        try:
            chore = self.session.query(Chore).filter_by(id=chore_id).first()
            if not chore:
                raise ValueError(f"Chore with id {chore_id} not found")
            
            # Update chore fields
            for key, value in updated_chore.items():
                if key != 'sub_chores' and hasattr(chore, key):
                    setattr(chore, key, value)
            
            # Handle sub-chores update if present
            if 'sub_chores' in updated_chore:
                # Remove existing sub-chores
                self.session.query(SubChore).filter_by(chore_id=chore_id).delete()
                
                # Add new sub-chores
                for sub_data in updated_chore['sub_chores']:
                    sub_chore = SubChore(
                        name=sub_data['name'],
                        chore=chore
                    )
                    self.session.add(sub_chore)
            
            self._commit_or_rollback()
            return chore.to_dict(include_sub_chores=True)
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to update chore: {str(e)}")
    
    def delete_chore(self, chore_id: int):
        """Delete a chore and clean up all related state data."""
        try:
            chore = self.session.query(Chore).filter_by(id=chore_id).first()
            if not chore:
                raise ValueError(f"Chore with id {chore_id} not found")
            
            # Clean up predefined chore state
            ApplicationState.set_state_value(f'predefined_chore_{chore_id}', None)
            
            # Mark related assignments as inactive
            assignments = self.session.query(Assignment).filter_by(chore_id=chore_id, is_active=True).all()
            for assignment in assignments:
                assignment.is_active = False
            
            # Delete the chore (cascade will handle sub-chores)
            self.session.delete(chore)
            self._commit_or_rollback()
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to delete chore: {str(e)}")
    
    # Roommates operations
    def get_roommates(self) -> List[Dict]:
        """Get all roommates."""
        roommates = self.session.query(Roommate).all()
        return [roommate.to_dict() for roommate in roommates]
    
    def save_roommates(self, roommates: List[Dict]):
        """Save roommates to database (bulk replace operation)."""
        try:
            # Clear existing roommates (dangerous operation)
            self.session.query(Roommate).delete()
            
            # Add new roommates
            for roommate_data in roommates:
                roommate = Roommate.from_dict(roommate_data)
                self.session.add(roommate)
            
            self._commit_or_rollback()
        except Exception as e:
            raise ValueError(f"Failed to save roommates: {str(e)}")
    
    def add_roommate(self, roommate_data: Dict) -> Dict:
        """Add a new roommate."""
        try:
            roommate = Roommate.from_dict(roommate_data)
            self.session.add(roommate)
            self._commit_or_rollback()
            return roommate.to_dict()
        except IntegrityError as e:
            raise ValueError(f"Roommate with this name may already exist: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to add roommate: {str(e)}")
    
    def update_roommate(self, roommate_id: int, updated_roommate: Dict) -> Dict:
        """Update an existing roommate."""
        try:
            roommate = self.session.query(Roommate).filter_by(id=roommate_id).first()
            if not roommate:
                raise ValueError(f"Roommate with id {roommate_id} not found")
            
            # Update roommate fields
            for key, value in updated_roommate.items():
                if hasattr(roommate, key):
                    setattr(roommate, key, value)
            
            self._commit_or_rollback()
            return roommate.to_dict()
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to update roommate: {str(e)}")
    
    def delete_roommate(self, roommate_id: int):
        """Delete a roommate."""
        try:
            roommate = self.session.query(Roommate).filter_by(id=roommate_id).first()
            if not roommate:
                raise ValueError(f"Roommate with id {roommate_id} not found")
            
            # Mark related assignments as inactive
            assignments = self.session.query(Assignment).filter_by(roommate_id=roommate_id, is_active=True).all()
            for assignment in assignments:
                assignment.is_active = False
            
            # Delete the roommate
            self.session.delete(roommate)
            self._commit_or_rollback()
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to delete roommate: {str(e)}")
    
    # State operations
    def get_state(self) -> Dict:
        """Get application state in legacy format."""
        try:
            last_run_date = ApplicationState.get_last_run_date()
            global_rotation = ApplicationState.get_global_predefined_rotation()
            
            # Get predefined chore states
            predefined_states = {}
            chores = self.session.query(Chore).filter_by(type='predefined').all()
            for chore in chores:
                state_value = ApplicationState.get_predefined_chore_state(chore.id)
                if state_value:
                    predefined_states[str(chore.id)] = state_value
            
            # Get current assignments
            current_assignments = self.get_current_assignments()
            
            return {
                'last_run_date': last_run_date.isoformat() if last_run_date else None,
                'predefined_chore_states': predefined_states,
                'global_predefined_rotation': global_rotation,
                'current_assignments': current_assignments
            }
        except Exception as e:
            raise ValueError(f"Failed to get state: {str(e)}")
    
    def save_state(self, state: Dict):
        """Save application state."""
        try:
            if 'last_run_date' in state and state['last_run_date']:
                if isinstance(state['last_run_date'], str):
                    date_obj = datetime.fromisoformat(state['last_run_date'])
                else:
                    date_obj = state['last_run_date']
                ApplicationState.set_last_run_date(date_obj)
            
            if 'global_predefined_rotation' in state:
                ApplicationState.set_global_predefined_rotation(state['global_predefined_rotation'])
            
            if 'predefined_chore_states' in state:
                for chore_id, roommate_id in state['predefined_chore_states'].items():
                    ApplicationState.set_predefined_chore_state(int(chore_id), roommate_id)
            
            self._commit_or_rollback()
        except Exception as e:
            raise ValueError(f"Failed to save state: {str(e)}")
    
    def update_last_run_date(self, date_str: str):
        """Update the last run date."""
        try:
            date_obj = datetime.fromisoformat(date_str)
            ApplicationState.set_last_run_date(date_obj)
            self._commit_or_rollback()
        except Exception as e:
            raise ValueError(f"Failed to update last run date: {str(e)}")
    
    def update_predefined_chore_state(self, chore_id: int, roommate_id: int):
        """Update the last assigned roommate for a predefined chore."""
        try:
            ApplicationState.set_predefined_chore_state(chore_id, roommate_id)
            self._commit_or_rollback()
        except Exception as e:
            raise ValueError(f"Failed to update predefined chore state: {str(e)}")
    
    def save_current_assignments(self, assignments: List[Dict]):
        """Save current chore assignments."""
        try:
            # Mark all current assignments as inactive
            self.session.query(Assignment).filter_by(is_active=True).update({'is_active': False})
            
            # Create new assignments
            for assignment_data in assignments:
                # Get chore and roommate objects
                chore = self.session.query(Chore).filter_by(id=assignment_data['chore_id']).first()
                roommate = self.session.query(Roommate).filter_by(id=assignment_data['roommate_id']).first()
                
                if not chore or not roommate:
                    continue
                
                assignment = Assignment(
                    chore=chore,
                    roommate=roommate,
                    assigned_date=datetime.fromisoformat(assignment_data['assigned_date']),
                    due_date=datetime.fromisoformat(assignment_data['due_date'])
                )
                self.session.add(assignment)
            
            self._commit_or_rollback()
        except Exception as e:
            raise ValueError(f"Failed to save current assignments: {str(e)}")
    
    def get_current_assignments(self) -> List[Dict]:
        """Get current chore assignments in legacy format."""
        try:
            assignments = self.session.query(Assignment).filter_by(is_active=True).all()
            return [assignment.to_dict(include_progress=True) for assignment in assignments]
        except Exception as e:
            raise ValueError(f"Failed to get current assignments: {str(e)}")
    
    def update_global_predefined_rotation(self, rotation_index: int):
        """Update the global predefined chore rotation index."""
        try:
            ApplicationState.set_global_predefined_rotation(rotation_index)
            self._commit_or_rollback()
        except Exception as e:
            raise ValueError(f"Failed to update global rotation: {str(e)}")
    
    # Sub-chore operations
    def get_next_sub_chore_id(self, chore_id: int) -> int:
        """Get the next available sub-chore ID for a chore (legacy compatibility)."""
        # With auto-incrementing IDs, this isn't needed, but kept for compatibility
        max_id = self.session.query(func.max(SubChore.id)).scalar() or 0
        return max_id + 1
    
    def add_sub_chore(self, chore_id: int, sub_chore_name: str) -> Dict:
        """Add a new sub-chore to a chore."""
        try:
            chore = self.session.query(Chore).filter_by(id=chore_id).first()
            if not chore:
                raise ValueError(f"Chore with id {chore_id} not found")
            
            sub_chore = SubChore(name=sub_chore_name, chore=chore)
            self.session.add(sub_chore)
            self._commit_or_rollback()
            return sub_chore.to_dict()
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to add sub-chore: {str(e)}")
    
    def update_sub_chore(self, chore_id: int, sub_chore_id: int, sub_chore_name: str) -> Dict:
        """Update a sub-chore's name."""
        try:
            sub_chore = self.session.query(SubChore).filter_by(
                id=sub_chore_id, chore_id=chore_id
            ).first()
            
            if not sub_chore:
                raise ValueError(f"Sub-chore with id {sub_chore_id} not found in chore {chore_id}")
            
            sub_chore.name = sub_chore_name
            self._commit_or_rollback()
            return sub_chore.to_dict()
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to update sub-chore: {str(e)}")
    
    def delete_sub_chore(self, chore_id: int, sub_chore_id: int):
        """Delete a sub-chore from a chore."""
        try:
            sub_chore = self.session.query(SubChore).filter_by(
                id=sub_chore_id, chore_id=chore_id
            ).first()
            
            if not sub_chore:
                raise ValueError(f"Sub-chore with id {sub_chore_id} not found in chore {chore_id}")
            
            self.session.delete(sub_chore)
            self._commit_or_rollback()
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to delete sub-chore: {str(e)}")
    
    def toggle_sub_chore_completion(self, chore_id: int, sub_chore_id: int, assignment_index: int = None) -> Dict:
        """Toggle the completion status of a sub-chore in an assignment."""
        try:
            # Find the assignment
            if assignment_index is not None:
                assignments = self.session.query(Assignment).filter_by(
                    chore_id=chore_id, is_active=True
                ).all()
                if assignment_index >= len(assignments):
                    raise ValueError(f"Assignment index {assignment_index} out of range")
                assignment = assignments[assignment_index]
            else:
                assignment = self.session.query(Assignment).filter_by(
                    chore_id=chore_id, is_active=True
                ).first()
            
            if not assignment:
                raise ValueError(f"Assignment for chore {chore_id} not found")
            
            # Find or create sub-chore completion
            sub_chore = self.session.query(SubChore).filter_by(
                id=sub_chore_id, chore_id=chore_id
            ).first()
            
            if not sub_chore:
                raise ValueError(f"Sub-chore with id {sub_chore_id} not found")
            
            completion = self.session.query(SubChoreCompletion).filter_by(
                sub_chore_id=sub_chore_id, assignment_id=assignment.id
            ).first()
            
            if completion:
                completion.toggle_completion()
            else:
                completion = SubChoreCompletion(
                    sub_chore=sub_chore,
                    assignment=assignment,
                    completed=True,
                    completed_at=datetime.utcnow()
                )
                self.session.add(completion)
            
            self._commit_or_rollback()
            return {
                "sub_chore_id": sub_chore_id,
                "completed": completion.completed
            }
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to toggle sub-chore completion: {str(e)}")
    
    def get_sub_chore_progress(self, chore_id: int, assignment_index: int = None) -> Dict:
        """Get the progress of sub-chores for a specific assignment."""
        try:
            # Find the assignment
            if assignment_index is not None:
                assignments = self.session.query(Assignment).filter_by(
                    chore_id=chore_id, is_active=True
                ).all()
                if assignment_index >= len(assignments):
                    return {
                        "total_sub_chores": 0,
                        "completed_sub_chores": 0,
                        "completion_percentage": 0.0,
                        "sub_chore_statuses": {}
                    }
                assignment = assignments[assignment_index]
            else:
                assignment = self.session.query(Assignment).filter_by(
                    chore_id=chore_id, is_active=True
                ).first()
            
            if not assignment:
                return {
                    "total_sub_chores": 0,
                    "completed_sub_chores": 0,
                    "completion_percentage": 0.0,
                    "sub_chore_statuses": {}
                }
            
            return assignment.get_sub_chore_progress()
        except Exception as e:
            raise ValueError(f"Failed to get sub-chore progress: {str(e)}")
    
    # Shopping list operations
    def get_shopping_list(self) -> List[Dict]:
        """Get all shopping list items."""
        items = self.session.query(ShoppingItem).all()
        return [item.to_dict() for item in items]
    
    def save_shopping_list(self, shopping_list: List[Dict]):
        """Save shopping list to database (bulk replace operation)."""
        try:
            # Clear existing items (dangerous operation)
            self.session.query(ShoppingItem).delete()
            
            # Add new items
            for item_data in shopping_list:
                item = ShoppingItem.from_dict(item_data)
                self.session.add(item)
            
            self._commit_or_rollback()
        except Exception as e:
            raise ValueError(f"Failed to save shopping list: {str(e)}")
    
    def get_next_shopping_item_id(self) -> int:
        """Get the next available shopping list item ID (legacy compatibility)."""
        max_id = self.session.query(func.max(ShoppingItem.id)).scalar() or 0
        return max_id + 1
    
    def add_shopping_item(self, item_data: Dict) -> Dict:
        """Add a new item to the shopping list."""
        try:
            item = ShoppingItem.from_dict(item_data)
            self.session.add(item)
            self._commit_or_rollback()
            return item.to_dict()
        except Exception as e:
            raise ValueError(f"Failed to add shopping item: {str(e)}")
    
    def update_shopping_item(self, item_id: int, updated_item: Dict) -> Dict:
        """Update an existing shopping list item."""
        try:
            item = self.session.query(ShoppingItem).filter_by(id=item_id).first()
            if not item:
                raise ValueError(f"Shopping list item with id {item_id} not found")
            
            # Update item fields
            for key, value in updated_item.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            
            self._commit_or_rollback()
            return item.to_dict()
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to update shopping item: {str(e)}")
    
    def delete_shopping_item(self, item_id: int):
        """Delete a shopping list item."""
        try:
            item = self.session.query(ShoppingItem).filter_by(id=item_id).first()
            if not item:
                raise ValueError(f"Shopping list item with id {item_id} not found")
            
            self.session.delete(item)
            self._commit_or_rollback()
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to delete shopping item: {str(e)}")
    
    def mark_item_purchased(self, item_id: int, purchased_by: int, purchased_by_name: str, 
                           actual_price: float = None, notes: str = None) -> Dict:
        """Mark a shopping list item as purchased."""
        try:
            item = self.session.query(ShoppingItem).filter_by(id=item_id).first()
            if not item:
                raise ValueError(f"Shopping list item with id {item_id} not found")
            
            item.mark_purchased(purchased_by, actual_price, notes)
            self._commit_or_rollback()
            return item.to_dict()
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to mark item as purchased: {str(e)}")
    
    def get_shopping_list_by_status(self, status: str) -> List[Dict]:
        """Get shopping list items by status (active, purchased, etc.)."""
        items = self.session.query(ShoppingItem).filter_by(status=status).all()
        return [item.to_dict() for item in items]
    
    def get_purchase_history(self, days: int = 30) -> List[Dict]:
        """Get purchase history for the last N days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        items = self.session.query(ShoppingItem).filter(
            ShoppingItem.status == 'purchased',
            ShoppingItem.purchase_date >= cutoff_date
        ).order_by(ShoppingItem.purchase_date.desc()).all()
        
        return [item.to_dict() for item in items]
    
    def clear_all_purchase_history(self) -> int:
        """Clear all purchase history - reset all purchased items to active status."""
        try:
            items = self.session.query(ShoppingItem).filter_by(status='purchased').all()
            cleared_count = 0
            
            for item in items:
                item.mark_active()
                cleared_count += 1
            
            self._commit_or_rollback()
            return cleared_count
        except Exception as e:
            raise ValueError(f"Failed to clear purchase history: {str(e)}")
    
    def clear_purchase_history_from_date(self, from_date_str: str) -> int:
        """Clear purchase history from a specific date onward."""
        try:
            from dateutil import parser
            from_date = parser.parse(from_date_str)
            
            items = self.session.query(ShoppingItem).filter(
                ShoppingItem.status == 'purchased',
                ShoppingItem.purchase_date >= from_date
            ).all()
            
            cleared_count = 0
            for item in items:
                item.mark_active()
                cleared_count += 1
            
            self._commit_or_rollback()
            return cleared_count
        except Exception as e:
            raise ValueError(f"Failed to clear purchase history from date: {str(e)}")
    
    def get_shopping_list_metadata(self) -> Dict:
        """Get metadata about the shopping list."""
        try:
            # Get basic stats
            total_items = self.session.query(ShoppingItem).count()
            active_count = self.session.query(ShoppingItem).filter_by(status='active').count()
            purchased_count = self.session.query(ShoppingItem).filter_by(status='purchased').count()
            
            # Get last modification time (approximate)
            last_modified_item = self.session.query(ShoppingItem).order_by(
                ShoppingItem.date_added.desc()
            ).first()
            
            last_modified = last_modified_item.date_added.isoformat() if last_modified_item else None
            
            return {
                'last_modified': last_modified,
                'total_items': total_items,
                'active_items': active_count,
                'purchased_items': purchased_count,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'last_modified': None,
                'total_items': 0,
                'active_items': 0,
                'purchased_items': 0,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    # Request management methods
    def get_requests(self) -> List[Dict]:
        """Get all requests."""
        requests = self.session.query(PurchaseRequest).all()
        return [request.to_dict(include_approvals=True) for request in requests]
    
    def save_requests(self, requests: List[Dict]):
        """Save requests to database (bulk replace operation)."""
        try:
            # Clear existing requests (dangerous operation)
            self.session.query(PurchaseRequest).delete()
            
            # Add new requests
            for request_data in requests:
                request = PurchaseRequest.from_dict(request_data)
                self.session.add(request)
                
                # Add approvals if present
                if 'approvals' in request_data:
                    for approval_data in request_data['approvals']:
                        approval = Approval(
                            request=request,
                            approved_by=approval_data['approved_by'],
                            approval_status=approval_data['approval_status'],
                            approval_date=datetime.fromisoformat(approval_data['approval_date']),
                            notes=approval_data.get('notes', '')
                        )
                        self.session.add(approval)
            
            self._commit_or_rollback()
        except Exception as e:
            raise ValueError(f"Failed to save requests: {str(e)}")
    
    def get_next_request_id(self) -> int:
        """Get the next available request ID (legacy compatibility)."""
        max_id = self.session.query(func.max(PurchaseRequest.id)).scalar() or 0
        return max_id + 1
    
    def add_request(self, request_data: Dict) -> Dict:
        """Add a new request."""
        try:
            request = PurchaseRequest.from_dict(request_data)
            self.session.add(request)
            self.session.flush()  # Get the ID
            
            # Check if auto-approved and create shopping item
            if request.status == 'auto-approved':
                shopping_item = request.promote_to_shopping_list()
                self.session.add(shopping_item)
            
            self._commit_or_rollback()
            return request.to_dict(include_approvals=True)
        except Exception as e:
            raise ValueError(f"Failed to add request: {str(e)}")
    
    def update_request(self, request_id: int, updated_request: Dict) -> Dict:
        """Update an existing request."""
        try:
            request = self.session.query(PurchaseRequest).filter_by(id=request_id).first()
            if not request:
                raise ValueError(f"Request with id {request_id} not found")
            
            # Update request fields
            for key, value in updated_request.items():
                if key not in ['approvals'] and hasattr(request, key):
                    setattr(request, key, value)
            
            self._commit_or_rollback()
            return request.to_dict(include_approvals=True)
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to update request: {str(e)}")
    
    def delete_request(self, request_id: int):
        """Delete a request."""
        try:
            request = self.session.query(PurchaseRequest).filter_by(id=request_id).first()
            if not request:
                raise ValueError(f"Request with id {request_id} not found")
            
            self.session.delete(request)
            self._commit_or_rollback()
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to delete request: {str(e)}")
    
    def approve_request(self, request_id: int, approval_data: Dict) -> Dict:
        """Approve or decline a request."""
        try:
            request = self.session.query(PurchaseRequest).filter_by(id=request_id).first()
            if not request:
                raise ValueError(f"Request with id {request_id} not found")
            
            approval = request.add_approval(
                approved_by_id=approval_data['approved_by'],
                approval_status=approval_data['approval_status'],
                notes=approval_data.get('notes', '')
            )
            
            # If request is now approved, create shopping item
            if request.status == 'approved':
                shopping_item = request.promote_to_shopping_list()
                self.session.add(shopping_item)
            
            self._commit_or_rollback()
            return request.to_dict(include_approvals=True)
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to approve request: {str(e)}")
    
    def get_requests_by_status(self, status: str) -> List[Dict]:
        """Get requests by status (pending, approved, declined, auto-approved)."""
        requests = self.session.query(PurchaseRequest).filter_by(status=status).all()
        return [request.to_dict(include_approvals=True) for request in requests]
    
    def get_pending_requests_for_user(self, user_id: int) -> List[Dict]:
        """Get pending requests that a user hasn't voted on yet."""
        # Get pending requests not made by this user
        pending_requests = self.session.query(PurchaseRequest).filter(
            PurchaseRequest.status == 'pending',
            PurchaseRequest.requested_by != user_id
        ).all()
        
        # Filter out requests where user has already voted
        results = []
        for request in pending_requests:
            user_voted = self.session.query(Approval).filter(
                Approval.request_id == request.id,
                Approval.approved_by == user_id
            ).first()
            
            if not user_voted:
                results.append(request.to_dict(include_approvals=True))
        
        return results
    
    def get_requests_metadata(self) -> Dict:
        """Get metadata about requests."""
        try:
            # Get basic stats
            total_requests = self.session.query(PurchaseRequest).count()
            pending_count = self.session.query(PurchaseRequest).filter_by(status='pending').count()
            approved_count = self.session.query(PurchaseRequest).filter_by(status='approved').count()
            declined_count = self.session.query(PurchaseRequest).filter_by(status='declined').count()
            auto_approved_count = self.session.query(PurchaseRequest).filter_by(status='auto-approved').count()
            
            # Get last modification time (approximate)
            last_modified_request = self.session.query(PurchaseRequest).order_by(
                PurchaseRequest.date_requested.desc()
            ).first()
            
            last_modified = last_modified_request.date_requested.isoformat() if last_modified_request else None
            
            return {
                'last_modified': last_modified,
                'total_requests': total_requests,
                'pending_requests': pending_count,
                'approved_requests': approved_count,
                'declined_requests': declined_count,
                'auto_approved_requests': auto_approved_count,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
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
        slots = self.session.query(LaundrySlot).all()
        return [slot.to_dict() for slot in slots]
    
    def save_laundry_slots(self, slots: List[Dict]):
        """Save laundry slots to database (bulk replace operation)."""
        try:
            # Clear existing slots (dangerous operation)
            self.session.query(LaundrySlot).delete()
            
            # Add new slots
            for slot_data in slots:
                slot = LaundrySlot.from_dict(slot_data)
                self.session.add(slot)
            
            self._commit_or_rollback()
        except Exception as e:
            raise ValueError(f"Failed to save laundry slots: {str(e)}")
    
    def get_next_laundry_slot_id(self) -> int:
        """Get the next available laundry slot ID (legacy compatibility)."""
        max_id = self.session.query(func.max(LaundrySlot.id)).scalar() or 0
        return max_id + 1
    
    def add_laundry_slot(self, slot_data: Dict) -> Dict:
        """Add a new laundry slot."""
        try:
            slot = LaundrySlot.from_dict(slot_data)
            self.session.add(slot)
            self._commit_or_rollback()
            return slot.to_dict()
        except Exception as e:
            raise ValueError(f"Failed to add laundry slot: {str(e)}")
    
    def update_laundry_slot(self, slot_id: int, updated_slot: Dict) -> Dict:
        """Update an existing laundry slot."""
        try:
            slot = self.session.query(LaundrySlot).filter_by(id=slot_id).first()
            if not slot:
                raise ValueError(f"Laundry slot with id {slot_id} not found")
            
            # Update slot fields
            for key, value in updated_slot.items():
                if hasattr(slot, key):
                    setattr(slot, key, value)
            
            self._commit_or_rollback()
            return slot.to_dict()
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to update laundry slot: {str(e)}")
    
    def delete_laundry_slot(self, slot_id: int):
        """Delete a laundry slot."""
        try:
            slot = self.session.query(LaundrySlot).filter_by(id=slot_id).first()
            if not slot:
                raise ValueError(f"Laundry slot with id {slot_id} not found")
            
            self.session.delete(slot)
            self._commit_or_rollback()
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to delete laundry slot: {str(e)}")
    
    def get_laundry_slots_by_date(self, date_str: str) -> List[Dict]:
        """Get laundry slots for a specific date."""
        try:
            # Parse date string
            if isinstance(date_str, str):
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                date_obj = date_str
            
            slots = self.session.query(LaundrySlot).filter_by(date=date_obj).all()
            return [slot.to_dict() for slot in slots]
        except Exception as e:
            raise ValueError(f"Failed to get laundry slots by date: {str(e)}")
    
    def get_laundry_slots_by_roommate(self, roommate_id: int) -> List[Dict]:
        """Get laundry slots for a specific roommate."""
        slots = self.session.query(LaundrySlot).filter_by(roommate_id=roommate_id).all()
        return [slot.to_dict() for slot in slots]
    
    def get_laundry_slots_by_status(self, status: str) -> List[Dict]:
        """Get laundry slots by status (scheduled, in_progress, completed, cancelled)."""
        slots = self.session.query(LaundrySlot).filter_by(status=status).all()
        return [slot.to_dict() for slot in slots]
    
    def check_laundry_slot_conflicts(self, date_str: str, time_slot: str, machine_type: str, exclude_slot_id: int = None) -> List[Dict]:
        """Check for conflicting laundry slots on the same date/time/machine."""
        try:
            # Parse date string
            if isinstance(date_str, str):
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                date_obj = date_str
            
            # Query for conflicts
            query = self.session.query(LaundrySlot).filter(
                LaundrySlot.date == date_obj,
                LaundrySlot.time_slot == time_slot,
                LaundrySlot.machine_type == machine_type,
                LaundrySlot.status.in_(['scheduled', 'in_progress'])
            )
            
            if exclude_slot_id:
                query = query.filter(LaundrySlot.id != exclude_slot_id)
            
            conflicts = query.all()
            
            # Check blocked time slot conflicts
            blocked_conflicts = self.check_blocked_time_conflicts(date_str, time_slot)
            
            # Convert to dict format
            result = [slot.to_dict() for slot in conflicts]
            
            # Add blocked slot conflicts in compatible format
            for blocked_slot in blocked_conflicts:
                conflict = {
                    'id': f"blocked_{blocked_slot['id']}",
                    'roommate_name': 'BLOCKED',
                    'date': blocked_slot['date'],
                    'time_slot': blocked_slot['time_slot'],
                    'machine_type': 'all',
                    'status': 'blocked',
                    'reason': blocked_slot.get('reason', 'Time slot blocked'),
                    'blocked_by': blocked_slot.get('created_by_name', 'System')
                }
                result.append(conflict)
            
            return result
        except Exception as e:
            raise ValueError(f"Failed to check laundry slot conflicts: {str(e)}")
    
    def mark_laundry_slot_completed(self, slot_id: int, actual_loads: int = None, completion_notes: str = None) -> Dict:
        """Mark a laundry slot as completed."""
        try:
            slot = self.session.query(LaundrySlot).filter_by(id=slot_id).first()
            if not slot:
                raise ValueError(f"Laundry slot with id {slot_id} not found")
            
            slot.mark_completed(actual_loads, completion_notes)
            self._commit_or_rollback()
            return slot.to_dict()
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to mark laundry slot as completed: {str(e)}")
    
    def get_laundry_slots_metadata(self) -> Dict:
        """Get metadata about laundry slots."""
        try:
            # Get basic stats
            total_slots = self.session.query(LaundrySlot).count()
            scheduled_count = self.session.query(LaundrySlot).filter_by(status='scheduled').count()
            in_progress_count = self.session.query(LaundrySlot).filter_by(status='in_progress').count()
            completed_count = self.session.query(LaundrySlot).filter_by(status='completed').count()
            cancelled_count = self.session.query(LaundrySlot).filter_by(status='cancelled').count()
            
            # Get last modification time (approximate)
            last_modified_slot = self.session.query(LaundrySlot).order_by(
                LaundrySlot.created_date.desc()
            ).first()
            
            last_modified = last_modified_slot.created_date.isoformat() if last_modified_slot else None
            
            return {
                'last_modified': last_modified,
                'total_slots': total_slots,
                'scheduled_slots': scheduled_count,
                'in_progress_slots': in_progress_count,
                'completed_slots': completed_count,
                'cancelled_slots': cancelled_count,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'last_modified': None,
                'total_slots': 0,
                'scheduled_slots': 0,
                'in_progress_slots': 0,
                'completed_slots': 0,
                'cancelled_slots': 0,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    # Blocked Time Slots operations
    def get_blocked_time_slots(self) -> List[Dict]:
        """Get all blocked time slots."""
        blocked_slots = self.session.query(BlockedTimeSlot).all()
        return [slot.to_dict() for slot in blocked_slots]
    
    def save_blocked_time_slots(self, blocked_slots: List[Dict]):
        """Save blocked time slots to database (bulk replace operation)."""
        try:
            # Clear existing blocked slots (dangerous operation)
            self.session.query(BlockedTimeSlot).delete()
            
            # Add new blocked slots
            for slot_data in blocked_slots:
                slot = BlockedTimeSlot.from_dict(slot_data)
                self.session.add(slot)
            
            self._commit_or_rollback()
        except Exception as e:
            raise ValueError(f"Failed to save blocked time slots: {str(e)}")
    
    def get_next_blocked_slot_id(self) -> int:
        """Get the next available blocked slot ID (legacy compatibility)."""
        max_id = self.session.query(func.max(BlockedTimeSlot.id)).scalar() or 0
        return max_id + 1
    
    def add_blocked_time_slot(self, blocked_slot: Dict) -> Dict:
        """Add a new blocked time slot."""
        try:
            slot = BlockedTimeSlot.from_dict(blocked_slot)
            self.session.add(slot)
            self._commit_or_rollback()
            return slot.to_dict()
        except Exception as e:
            raise ValueError(f"Failed to add blocked time slot: {str(e)}")
    
    def update_blocked_time_slot(self, slot_id: int, updated_slot: Dict) -> Dict:
        """Update an existing blocked time slot."""
        try:
            slot = self.session.query(BlockedTimeSlot).filter_by(id=slot_id).first()
            if not slot:
                raise ValueError(f"Blocked time slot with id {slot_id} not found")
            
            # Update slot fields
            for key, value in updated_slot.items():
                if hasattr(slot, key):
                    setattr(slot, key, value)
            
            self._commit_or_rollback()
            return slot.to_dict()
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to update blocked time slot: {str(e)}")
    
    def delete_blocked_time_slot(self, slot_id: int):
        """Delete a blocked time slot."""
        try:
            slot = self.session.query(BlockedTimeSlot).filter_by(id=slot_id).first()
            if not slot:
                raise ValueError(f"Blocked time slot with id {slot_id} not found")
            
            self.session.delete(slot)
            self._commit_or_rollback()
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to delete blocked time slot: {str(e)}")
    
    def get_blocked_time_slots_by_date(self, date_str: str) -> List[Dict]:
        """Get blocked time slots for a specific date."""
        try:
            # Parse date string
            if isinstance(date_str, str):
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                date_obj = date_str
            
            slots = self.session.query(BlockedTimeSlot).filter_by(date=date_obj).all()
            return [slot.to_dict() for slot in slots]
        except Exception as e:
            raise ValueError(f"Failed to get blocked time slots by date: {str(e)}")
    
    def check_blocked_time_conflicts(self, date_str: str, time_slot: str, exclude_slot_id: int = None) -> List[Dict]:
        """Check if a time slot conflicts with any blocked time slots."""
        try:
            # Parse date string
            if isinstance(date_str, str):
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                date_obj = date_str
            
            # Query for conflicts
            query = self.session.query(BlockedTimeSlot).filter(
                BlockedTimeSlot.date == date_obj,
                BlockedTimeSlot.time_slot == time_slot
            )
            
            if exclude_slot_id:
                query = query.filter(BlockedTimeSlot.id != exclude_slot_id)
            
            conflicts = query.all()
            return [slot.to_dict() for slot in conflicts]
        except Exception as e:
            raise ValueError(f"Failed to check blocked time conflicts: {str(e)}")
    
    def is_time_slot_blocked(self, date_str: str, time_slot: str) -> bool:
        """Check if a specific time slot is blocked."""
        conflicts = self.check_blocked_time_conflicts(date_str, time_slot)
        return len(conflicts) > 0