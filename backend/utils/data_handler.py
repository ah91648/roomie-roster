import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

class DataHandler:
    """Handles JSON file operations for the RoomieRoster application."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # File paths
        self.chores_file = self.data_dir / "chores.json"
        self.roommates_file = self.data_dir / "roommates.json"
        self.state_file = self.data_dir / "state.json"
        self.shopping_list_file = self.data_dir / "shopping_list.json"
        self.requests_file = self.data_dir / "requests.json"
        self.laundry_slots_file = self.data_dir / "laundry_slots.json"
        self.blocked_time_slots_file = self.data_dir / "blocked_time_slots.json"
        
        # Initialize files if they don't exist
        self._initialize_files()
    
    def _initialize_files(self):
        """Initialize JSON files with default data if they don't exist."""
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
        """Read JSON data from file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading {filepath}: {e}")
            return [] if 'chores' in str(filepath) or 'roommates' in str(filepath) else {}
    
    def _write_json(self, filepath: Path, data: Any):
        """Write JSON data to file."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error writing {filepath}: {e}")
            raise
    
    # Chores operations
    def get_chores(self) -> List[Dict]:
        """Get all chores."""
        return self._read_json(self.chores_file)
    
    def save_chores(self, chores: List[Dict]):
        """Save chores to file."""
        self._write_json(self.chores_file, chores)
    
    def add_chore(self, chore: Dict) -> Dict:
        """Add a new chore."""
        chores = self.get_chores()
        chores.append(chore)
        self.save_chores(chores)
        return chore
    
    def update_chore(self, chore_id: int, updated_chore: Dict) -> Dict:
        """Update an existing chore."""
        chores = self.get_chores()
        for i, chore in enumerate(chores):
            if chore['id'] == chore_id:
                chores[i] = updated_chore
                self.save_chores(chores)
                return updated_chore
        raise ValueError(f"Chore with id {chore_id} not found")
    
    def delete_chore(self, chore_id: int):
        """Delete a chore and clean up all related state data."""
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
    
    # Roommates operations
    def get_roommates(self) -> List[Dict]:
        """Get all roommates."""
        return self._read_json(self.roommates_file)
    
    def save_roommates(self, roommates: List[Dict]):
        """Save roommates to file."""
        self._write_json(self.roommates_file, roommates)
    
    def add_roommate(self, roommate: Dict) -> Dict:
        """Add a new roommate."""
        roommates = self.get_roommates()
        roommates.append(roommate)
        self.save_roommates(roommates)
        return roommate
    
    def update_roommate(self, roommate_id: int, updated_roommate: Dict) -> Dict:
        """Update an existing roommate."""
        roommates = self.get_roommates()
        for i, roommate in enumerate(roommates):
            if roommate['id'] == roommate_id:
                roommates[i] = updated_roommate
                self.save_roommates(roommates)
                return updated_roommate
        raise ValueError(f"Roommate with id {roommate_id} not found")
    
    def delete_roommate(self, roommate_id: int):
        """Delete a roommate."""
        roommates = self.get_roommates()
        roommates = [r for r in roommates if r['id'] != roommate_id]
        self.save_roommates(roommates)
    
    # State operations
    def get_state(self) -> Dict:
        """Get application state."""
        return self._read_json(self.state_file)
    
    def save_state(self, state: Dict):
        """Save application state."""
        self._write_json(self.state_file, state)
    
    def update_last_run_date(self, date_str: str):
        """Update the last run date."""
        state = self.get_state()
        state['last_run_date'] = date_str
        self.save_state(state)
    
    def update_predefined_chore_state(self, chore_id: int, roommate_id: int):
        """Update the last assigned roommate for a predefined chore."""
        state = self.get_state()
        state['predefined_chore_states'][str(chore_id)] = roommate_id
        self.save_state(state)
    
    def save_current_assignments(self, assignments: List[Dict]):
        """Save current chore assignments."""
        state = self.get_state()
        state['current_assignments'] = assignments
        self.save_state(state)
    
    def get_current_assignments(self) -> List[Dict]:
        """Get current chore assignments."""
        state = self.get_state()
        return state.get('current_assignments', [])
    
    def update_global_predefined_rotation(self, rotation_index: int):
        """Update the global predefined chore rotation index."""
        state = self.get_state()
        state['global_predefined_rotation'] = rotation_index
        self.save_state(state)
    
    # Sub-chore operations
    def get_next_sub_chore_id(self, chore_id: int) -> int:
        """Get the next available sub-chore ID for a chore."""
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
        state = self.get_state()
        assignments = state.get('current_assignments', [])
        
        # Find the assignment
        assignment = None
        if assignment_index is not None:
            if 0 <= assignment_index < len(assignments):
                assignment = assignments[assignment_index]
        else:
            # Find assignment by chore_id
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
    
    # Shopping list operations
    def get_shopping_list(self) -> List[Dict]:
        """Get all shopping list items."""
        return self._read_json(self.shopping_list_file)
    
    def save_shopping_list(self, shopping_list: List[Dict]):
        """Save shopping list to file."""
        self._write_json(self.shopping_list_file, shopping_list)
    
    def get_next_shopping_item_id(self) -> int:
        """Get the next available shopping list item ID."""
        items = self.get_shopping_list()
        if not items:
            return 1
        return max(item['id'] for item in items) + 1
    
    def add_shopping_item(self, item: Dict) -> Dict:
        """Add a new item to the shopping list."""
        items = self.get_shopping_list()
        items.append(item)
        self.save_shopping_list(items)
        return item
    
    def update_shopping_item(self, item_id: int, updated_item: Dict) -> Dict:
        """Update an existing shopping list item."""
        items = self.get_shopping_list()
        for i, item in enumerate(items):
            if item['id'] == item_id:
                items[i] = updated_item
                self.save_shopping_list(items)
                return updated_item
        raise ValueError(f"Shopping list item with id {item_id} not found")
    
    def delete_shopping_item(self, item_id: int):
        """Delete a shopping list item."""
        items = self.get_shopping_list()
        items = [item for item in items if item['id'] != item_id]
        self.save_shopping_list(items)
    
    def mark_item_purchased(self, item_id: int, purchased_by: int, purchased_by_name: str, 
                           actual_price: float = None, notes: str = None) -> Dict:
        """Mark a shopping list item as purchased."""
        from datetime import datetime
        
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
                
                self.save_shopping_list(items)
                return item
        
        raise ValueError(f"Shopping list item with id {item_id} not found")
    
    def get_shopping_list_by_status(self, status: str) -> List[Dict]:
        """Get shopping list items by status (active, purchased, etc.)."""
        items = self.get_shopping_list()
        return [item for item in items if item.get('status') == status]
    
    def get_purchase_history(self, days: int = 30) -> List[Dict]:
        """Get purchase history for the last N days."""
        from datetime import datetime, timedelta
        
        items = self.get_shopping_list()
        cutoff_date = datetime.now() - timedelta(days=days)
        
        purchase_history = []
        for item in items:
            if item.get('status') == 'purchased' and item.get('purchase_date'):
                purchase_date = datetime.fromisoformat(item['purchase_date'])
                if purchase_date >= cutoff_date:
                    purchase_history.append(item)
        
        # Sort by purchase date, most recent first
        purchase_history.sort(key=lambda x: x['purchase_date'], reverse=True)
        return purchase_history
    
    def clear_all_purchase_history(self) -> int:
        """Clear all purchase history - reset all purchased items to active status."""
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
        
        self.save_shopping_list(items)
        return cleared_count
    
    def clear_purchase_history_from_date(self, from_date_str: str) -> int:
        """Clear purchase history from a specific date onward."""
        from datetime import datetime
        from dateutil import parser
        
        try:
            # Parse the input date string (supports various formats)
            from_date = parser.parse(from_date_str)
        except Exception as e:
            raise ValueError(f"Invalid date format: {from_date_str}. Use formats like 'YYYY-MM-DD' or 'MM/DD/YYYY'")
        
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
                    continue  # Skip items with invalid dates
        
        self.save_shopping_list(items)
        return cleared_count
    
    def get_shopping_list_metadata(self) -> Dict:
        """Get metadata about the shopping list including last modification time."""
        import os
        from datetime import datetime
        
        try:
            # Get file modification time
            mod_time = os.path.getmtime(self.shopping_list_file)
            last_modified = datetime.fromtimestamp(mod_time).isoformat()
            
            # Get basic stats
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
            print(f"Error getting shopping list metadata: {e}")
            return {
                'last_modified': None,
                'total_items': 0,
                'active_items': 0,
                'purchased_items': 0,
                'timestamp': datetime.now().isoformat()
            }
    
    # Request management methods
    def get_requests(self) -> List[Dict]:
        """Get all requests."""
        return self._read_json(self.requests_file)
    
    def save_requests(self, requests: List[Dict]):
        """Save requests to file."""
        self._write_json(self.requests_file, requests)
    
    def get_next_request_id(self) -> int:
        """Get the next available request ID."""
        requests = self.get_requests()
        if not requests:
            return 1
        return max(request['id'] for request in requests) + 1
    
    def add_request(self, request: Dict) -> Dict:
        """Add a new request."""
        from datetime import datetime
        
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
        requests = self.get_requests()
        for i, request in enumerate(requests):
            if request['id'] == request_id:
                requests[i] = updated_request
                self.save_requests(requests)
                return updated_request
        raise ValueError(f"Request with id {request_id} not found")
    
    def delete_request(self, request_id: int):
        """Delete a request."""
        requests = self.get_requests()
        updated_requests = [r for r in requests if r['id'] != request_id]
        if len(updated_requests) == len(requests):
            raise ValueError(f"Request with id {request_id} not found")
        self.save_requests(updated_requests)
    
    def approve_request(self, request_id: int, approval_data: Dict) -> Dict:
        """Approve or decline a request."""
        from datetime import datetime
        
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
                other_roommates = total_roommates - 1  # Exclude requester
                
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
                    
                elif decline_count >= (other_roommates // 2 + 1):  # Majority declined
                    request['status'] = 'declined'
                    request['final_decision_date'] = datetime.now().isoformat()
                    request['final_decision_by'] = approval_data['approved_by']
                    request['final_decision_by_name'] = approval_data['approved_by_name']
                
                self.save_requests(requests)
                return request
        
        raise ValueError(f"Request with id {request_id} not found")
    
    def get_requests_by_status(self, status: str) -> List[Dict]:
        """Get requests by status (pending, approved, declined, auto-approved)."""
        requests = self.get_requests()
        return [request for request in requests if request.get('status') == status]
    
    def get_pending_requests_for_user(self, user_id: int) -> List[Dict]:
        """Get pending requests that a user hasn't voted on yet."""
        requests = self.get_requests_by_status('pending')
        pending_for_user = []
        
        for request in requests:
            # Skip requests made by this user
            if request['requested_by'] == user_id:
                continue
                
            # Check if user has already voted
            user_voted = any(approval['approved_by'] == user_id for approval in request['approvals'])
            if not user_voted:
                pending_for_user.append(request)
        
        return pending_for_user
    
    def get_requests_metadata(self) -> Dict:
        """Get metadata about requests including last modification time."""
        import os
        from datetime import datetime
        
        try:
            # Get file modification time
            mod_time = os.path.getmtime(self.requests_file)
            last_modified = datetime.fromtimestamp(mod_time).isoformat()
            
            # Get basic stats
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
            print(f"Error getting requests metadata: {e}")
            return {
                'last_modified': None,
                'total_requests': 0,
                'pending_requests': 0,
                'approved_requests': 0,
                'declined_requests': 0,
                'auto_approved_requests': 0,
                'timestamp': datetime.now().isoformat()
            }
    
    # Laundry scheduling operations
    def get_laundry_slots(self) -> List[Dict]:
        """Get all laundry slots."""
        return self._read_json(self.laundry_slots_file)
    
    def save_laundry_slots(self, slots: List[Dict]):
        """Save laundry slots to file."""
        self._write_json(self.laundry_slots_file, slots)
    
    def get_next_laundry_slot_id(self) -> int:
        """Get the next available laundry slot ID."""
        slots = self.get_laundry_slots()
        if not slots:
            return 1
        return max(slot['id'] for slot in slots) + 1
    
    def add_laundry_slot(self, slot: Dict) -> Dict:
        """Add a new laundry slot."""
        slots = self.get_laundry_slots()
        slots.append(slot)
        self.save_laundry_slots(slots)
        return slot
    
    def update_laundry_slot(self, slot_id: int, updated_slot: Dict) -> Dict:
        """Update an existing laundry slot."""
        slots = self.get_laundry_slots()
        for i, slot in enumerate(slots):
            if slot['id'] == slot_id:
                slots[i] = updated_slot
                self.save_laundry_slots(slots)
                return updated_slot
        raise ValueError(f"Laundry slot with id {slot_id} not found")
    
    def delete_laundry_slot(self, slot_id: int):
        """Delete a laundry slot."""
        slots = self.get_laundry_slots()
        original_count = len(slots)
        slots = [slot for slot in slots if slot['id'] != slot_id]
        if len(slots) == original_count:
            raise ValueError(f"Laundry slot with id {slot_id} not found")
        self.save_laundry_slots(slots)
    
    def get_laundry_slots_by_date(self, date: str) -> List[Dict]:
        """Get laundry slots for a specific date."""
        slots = self.get_laundry_slots()
        return [slot for slot in slots if slot.get('date') == date]
    
    def get_laundry_slots_by_roommate(self, roommate_id: int) -> List[Dict]:
        """Get laundry slots for a specific roommate."""
        slots = self.get_laundry_slots()
        return [slot for slot in slots if slot.get('roommate_id') == roommate_id]
    
    def get_laundry_slots_by_status(self, status: str) -> List[Dict]:
        """Get laundry slots by status (scheduled, in_progress, completed, cancelled)."""
        slots = self.get_laundry_slots()
        return [slot for slot in slots if slot.get('status') == status]
    
    def check_laundry_slot_conflicts(self, date: str, time_slot: str, machine_type: str, exclude_slot_id: int = None) -> List[Dict]:
        """Check for conflicting laundry slots on the same date/time/machine."""
        slots = self.get_laundry_slots()
        conflicts = []
        
        # Check regular laundry slot conflicts
        for slot in slots:
            # Skip the slot being edited
            if exclude_slot_id and slot['id'] == exclude_slot_id:
                continue
            
            # Skip cancelled slots
            if slot.get('status') == 'cancelled':
                continue
                
            # Check for same date, time slot, and machine type
            if (slot.get('date') == date and 
                slot.get('time_slot') == time_slot and 
                slot.get('machine_type') == machine_type):
                conflicts.append(slot)
        
        # Check blocked time slot conflicts
        blocked_conflicts = self.check_blocked_time_conflicts(date, time_slot)
        for blocked_slot in blocked_conflicts:
            # Transform blocked slot to look like a regular conflict for consistency
            conflict = {
                'id': f"blocked_{blocked_slot['id']}",
                'roommate_name': 'BLOCKED',
                'date': blocked_slot['date'],
                'time_slot': blocked_slot['time_slot'],
                'machine_type': 'all',  # Blocked slots affect all machine types
                'status': 'blocked',
                'reason': blocked_slot.get('reason', 'Time slot blocked by calendar settings'),
                'blocked_by': blocked_slot.get('created_by', 'System')
            }
            conflicts.append(conflict)
        
        return conflicts
    
    def mark_laundry_slot_completed(self, slot_id: int, actual_loads: int = None, completion_notes: str = None) -> Dict:
        """Mark a laundry slot as completed."""
        from datetime import datetime
        
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
                
                self.save_laundry_slots(slots)
                return slot
        
        raise ValueError(f"Laundry slot with id {slot_id} not found")
    
    def get_laundry_slots_metadata(self) -> Dict:
        """Get metadata about laundry slots including last modification time."""
        import os
        from datetime import datetime
        
        try:
            # Get file modification time
            mod_time = os.path.getmtime(self.laundry_slots_file)
            last_modified = datetime.fromtimestamp(mod_time).isoformat()
            
            # Get basic stats
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
            print(f"Error getting laundry slots metadata: {e}")
            return {
                'last_modified': None,
                'total_slots': 0,
                'scheduled_slots': 0,
                'in_progress_slots': 0,
                'completed_slots': 0,
                'cancelled_slots': 0,
                'timestamp': datetime.now().isoformat()
            }

    def _parse_laundry_slot_end_time(self, slot: Dict) -> Optional[datetime]:
        """
        Parse laundry slot's date and time_slot to get end datetime.
        Handles various time formats: "08:00-10:00", "12:00 PM-2:00 PM", etc.
        Returns None if parsing fails.
        """
        from datetime import datetime
        try:
            date_str = slot.get('date')  # YYYY-MM-DD format
            time_slot = slot.get('time_slot')  # e.g., "12:00 PM-2:00 PM"

            if not date_str or not time_slot:
                return None

            # Extract end time from time_slot (format: "start-end")
            if '-' in time_slot:
                end_time_str = time_slot.split('-')[1].strip()
            else:
                print(f"Warning: Invalid time_slot format: {time_slot}")
                return None

            # Combine date and end time
            datetime_str = f"{date_str} {end_time_str}"

            # Try parsing with different formats
            for fmt in ['%Y-%m-%d %I:%M %p', '%Y-%m-%d %H:%M', '%Y-%m-%d %I:%M%p']:
                try:
                    return datetime.strptime(datetime_str, fmt)
                except ValueError:
                    continue

            print(f"Warning: Could not parse datetime: {datetime_str}")
            return None

        except Exception as e:
            print(f"Error parsing laundry slot end time: {e}")
            return None

    def _is_laundry_slot_past(self, slot: Dict) -> bool:
        """
        Check if a laundry slot's end time has passed.
        Returns True if the slot is past, False otherwise.
        """
        from datetime import datetime
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
                        print(f"Auto-completed past laundry slot {slot['id']}")
                    except Exception as e:
                        print(f"Error auto-completing slot {slot['id']}: {e}")

            return completed_count

        except Exception as e:
            print(f"Error in auto_complete_past_laundry_slots: {e}")
            return 0

    def delete_old_completed_laundry_slots(self, days_threshold: int = 30) -> int:
        """
        Delete completed laundry slots older than the specified threshold.
        Default: 30 days. Returns the number of slots deleted.
        """
        from datetime import datetime, timedelta
        try:
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
            print(f"Deleted {deleted_count} old completed laundry slots")
            return deleted_count

        except Exception as e:
            print(f"Error deleting old completed laundry slots: {e}")
            return 0

    # Blocked Time Slots operations
    def get_blocked_time_slots(self) -> List[Dict]:
        """Get all blocked time slots."""
        return self._read_json(self.blocked_time_slots_file)
    
    def save_blocked_time_slots(self, blocked_slots: List[Dict]):
        """Save blocked time slots to file."""
        self._write_json(self.blocked_time_slots_file, blocked_slots)
    
    def get_next_blocked_slot_id(self) -> int:
        """Get the next available blocked slot ID."""
        blocked_slots = self.get_blocked_time_slots()
        if not blocked_slots:
            return 1
        return max(slot['id'] for slot in blocked_slots) + 1
    
    def add_blocked_time_slot(self, blocked_slot: Dict) -> Dict:
        """Add a new blocked time slot."""
        blocked_slots = self.get_blocked_time_slots()
        blocked_slots.append(blocked_slot)
        self.save_blocked_time_slots(blocked_slots)
        return blocked_slot
    
    def update_blocked_time_slot(self, slot_id: int, updated_slot: Dict) -> Dict:
        """Update an existing blocked time slot."""
        blocked_slots = self.get_blocked_time_slots()
        for i, slot in enumerate(blocked_slots):
            if slot['id'] == slot_id:
                blocked_slots[i] = updated_slot
                self.save_blocked_time_slots(blocked_slots)
                return updated_slot
        raise ValueError(f"Blocked time slot with id {slot_id} not found")
    
    def delete_blocked_time_slot(self, slot_id: int):
        """Delete a blocked time slot."""
        blocked_slots = self.get_blocked_time_slots()
        original_count = len(blocked_slots)
        blocked_slots = [slot for slot in blocked_slots if slot['id'] != slot_id]
        if len(blocked_slots) == original_count:
            raise ValueError(f"Blocked time slot with id {slot_id} not found")
        self.save_blocked_time_slots(blocked_slots)
    
    def get_blocked_time_slots_by_date(self, date: str) -> List[Dict]:
        """Get blocked time slots for a specific date."""
        blocked_slots = self.get_blocked_time_slots()
        return [slot for slot in blocked_slots if slot.get('date') == date]
    
    def check_blocked_time_conflicts(self, date: str, time_slot: str, exclude_slot_id: int = None) -> List[Dict]:
        """Check if a time slot conflicts with any blocked time slots."""
        blocked_slots = self.get_blocked_time_slots()
        conflicts = []
        
        for slot in blocked_slots:
            # Skip the slot being edited
            if exclude_slot_id and slot['id'] == exclude_slot_id:
                continue
            
            # Check if date and time slot match
            if slot.get('date') == date and slot.get('time_slot') == time_slot:
                conflicts.append(slot)
        
        return conflicts
    
    def is_time_slot_blocked(self, date: str, time_slot: str) -> bool:
        """Check if a specific time slot is blocked."""
        conflicts = self.check_blocked_time_conflicts(date, time_slot)
        return len(conflicts) > 0