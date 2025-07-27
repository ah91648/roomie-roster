import random
from datetime import datetime, timedelta
from dateutil import parser
from typing import List, Dict, Optional

class ChoreAssignmentLogic:
    """Handles the logic for assigning chores to roommates."""
    
    def __init__(self, data_handler):
        self.data_handler = data_handler
    
    def should_start_new_cycle(self) -> bool:
        """Determine if a new assignment cycle should start."""
        state = self.data_handler.get_state()
        last_run_date = state.get('last_run_date')
        
        if not last_run_date:
            return True
        
        try:
            last_run = parser.parse(last_run_date)
            now = datetime.now()
            
            # Start new cycle if it's been more than a week since last run
            # or if it's a new week (Monday)
            days_since_last_run = (now - last_run).days
            
            if days_since_last_run >= 7:
                return True
            
            # Check if we've crossed into a new week (Monday = 0)
            if last_run.weekday() > now.weekday():
                return True
                
            return False
        except Exception:
            return True
    
    def is_chore_due(self, chore: Dict, last_run_date: Optional[str]) -> bool:
        """Check if a chore is due based on its frequency."""
        if not last_run_date:
            return True
        
        try:
            last_run = parser.parse(last_run_date)
            now = datetime.now()
            frequency = chore.get('frequency', 'weekly')
            
            if frequency == 'daily':
                return (now - last_run).days >= 1
            elif frequency == 'weekly':
                return (now - last_run).days >= 7
            elif frequency == 'bi-weekly':
                return (now - last_run).days >= 14
            else:
                return True
        except Exception:
            return True
    
    def assign_predefined_chore(self, chore: Dict) -> Optional[int]:
        """Assign a predefined chore using rotation logic."""
        roommates = self.data_handler.get_roommates()
        if not roommates:
            return None
        
        state = self.data_handler.get_state()
        chore_states = state.get('predefined_chore_states', {})
        
        chore_id = chore['id']
        last_assigned_roommate_id = chore_states.get(str(chore_id))
        
        # Find the next roommate in rotation
        roommate_ids = [r['id'] for r in roommates]
        
        if last_assigned_roommate_id is None:
            # First assignment, assign to first roommate
            next_roommate_id = roommate_ids[0]
        else:
            try:
                current_index = roommate_ids.index(last_assigned_roommate_id)
                next_index = (current_index + 1) % len(roommate_ids)
                next_roommate_id = roommate_ids[next_index]
            except ValueError:
                # Last assigned roommate no longer exists, assign to first
                next_roommate_id = roommate_ids[0]
        
        # Update the state
        self.data_handler.update_predefined_chore_state(chore_id, next_roommate_id)
        return next_roommate_id
    
    def assign_random_chore(self, chore: Dict) -> Optional[int]:
        """Assign a random chore using weighted selection based on current points."""
        roommates = self.data_handler.get_roommates()
        if not roommates:
            return None
        
        # Calculate weights (lower points = higher probability)
        max_points = max([r.get('current_cycle_points', 0) for r in roommates]) + 1
        weights = []
        roommate_ids = []
        
        for roommate in roommates:
            current_points = roommate.get('current_cycle_points', 0)
            # Invert the points so lower points get higher weight
            weight = max_points - current_points
            weights.append(weight)
            roommate_ids.append(roommate['id'])
        
        # Select roommate using weighted random choice
        selected_roommate_id = random.choices(roommate_ids, weights=weights)[0]
        
        # Update the selected roommate's points
        chore_points = chore.get('points', 1)
        roommates = self.data_handler.get_roommates()
        for roommate in roommates:
            if roommate['id'] == selected_roommate_id:
                roommate['current_cycle_points'] = roommate.get('current_cycle_points', 0) + chore_points
                break
        
        self.data_handler.save_roommates(roommates)
        return selected_roommate_id
    
    def reset_cycle_points(self):
        """Reset all roommates' current cycle points to 0."""
        roommates = self.data_handler.get_roommates()
        for roommate in roommates:
            roommate['current_cycle_points'] = 0
        self.data_handler.save_roommates(roommates)
    
    def assign_chores(self) -> List[Dict]:
        """Main method to assign chores to roommates with equitable distribution."""
        chores = self.data_handler.get_chores()
        roommates = self.data_handler.get_roommates()
        
        if not chores or not roommates:
            return []
        
        state = self.data_handler.get_state()
        last_run_date = state.get('last_run_date')
        current_assignments = state.get('current_assignments', [])
        
        # Check if this is an initial setup (no current assignments)
        is_initial_setup = len(current_assignments) == 0
        
        # Check if we should start a new cycle
        if self.should_start_new_cycle():
            self.reset_cycle_points()
        
        current_time = datetime.now()
        
        # Filter chores that are due
        due_chores = []
        for chore in chores:
            if is_initial_setup or self.is_chore_due(chore, last_run_date):
                due_chores.append(chore)
        
        # Use simple equitable assignment
        if len(roommates) >= 4:
            assignments = self.assign_chores_equitably_simple(due_chores, roommates, current_time)
        else:
            # Fall back to original algorithm for fewer than 4 roommates
            assignments = self.assign_chores_original(due_chores, roommates, current_time)
        
        # Update last run date and save assignments
        self.data_handler.update_last_run_date(current_time.isoformat())
        self.data_handler.save_current_assignments(assignments)
        
        return assignments
    
    def assign_chores_equitably_simple(self, chores: List[Dict], roommates: List[Dict], current_time: datetime) -> List[Dict]:
        """Simple equitable assignment ensuring everyone gets at least one chore."""
        assignments = []
        
        if not chores or not roommates:
            return assignments
        
        # Create a copy of roommates to avoid modifying original
        roommates_copy = [dict(r) for r in roommates]
        
        # Sort chores by points (ascending) to distribute fairly  
        sorted_chores = sorted(chores, key=lambda x: x.get('points', 1))
        
        # Sort roommates by current points (ascending) to prioritize those with fewer points
        sorted_roommates = sorted(roommates_copy, key=lambda x: x.get('current_cycle_points', 0))
        
        # Phase 1: ABSOLUTELY guarantee everyone gets exactly one chore
        assignments_count = {r['id']: 0 for r in roommates_copy}
        chores_used = set()
        
        # Manual assignment to ensure equity
        print(f"DEBUG: Have {len(roommates_copy)} roommates and {len(sorted_chores)} chores")
        print(f"DEBUG: Roommates: {[(r['id'], r['name']) for r in sorted_roommates]}")
        print(f"DEBUG: Chores: {[(c['id'], c['name'], c['points']) for c in sorted_chores]}")
        
        # Assign exactly one chore to each person
        for i in range(len(roommates_copy)):
            if i < len(sorted_chores):
                roommate = sorted_roommates[i]
                chore = sorted_chores[i]
                
                print(f"DEBUG: Assigning chore {chore['name']} to {roommate['name']}")
                
                assignment = self.create_assignment(chore, roommate, current_time)
                assignments.append(assignment)
                assignments_count[roommate['id']] += 1
                chores_used.add(chore['id'])
                
                # Update roommate points in our copy
                roommate['current_cycle_points'] = roommate.get('current_cycle_points', 0) + chore.get('points', 1)
                
                # Update predefined chore state if needed
                if chore.get('type') == 'predefined':
                    self.data_handler.update_predefined_chore_state(chore['id'], roommate['id'])
        
        print(f"DEBUG: After Phase 1, assignments_count: {assignments_count}")
        print(f"DEBUG: Chores used: {chores_used}")
        
        # Phase 2: Assign remaining chores with strong bias toward unassigned people
        remaining_chores = [c for c in sorted_chores if c['id'] not in chores_used]
        
        for chore in remaining_chores:
            # Find people with the minimum number of assignments
            min_assignments = min(assignments_count.values())
            candidates = [r for r in roommates_copy if assignments_count[r['id']] == min_assignments]
            
            if candidates:
                # Among people with minimum assignments, pick the one with lowest points
                selected_roommate = min(candidates, key=lambda x: x.get('current_cycle_points', 0))
            else:
                # Fallback: pick person with lowest points overall
                selected_roommate = min(roommates_copy, key=lambda x: x.get('current_cycle_points', 0))
            
            assignment = self.create_assignment(chore, selected_roommate, current_time)
            assignments.append(assignment)
            assignments_count[selected_roommate['id']] += 1
            
            # Update roommate points
            chore_points = chore.get('points', 1)
            selected_roommate['current_cycle_points'] = selected_roommate.get('current_cycle_points', 0) + chore_points
            
            # Update predefined chore state if needed
            if chore.get('type') == 'predefined':
                self.data_handler.update_predefined_chore_state(chore['id'], selected_roommate['id'])
        
        # Apply the updated points back to the original roommates list
        for original_roommate in roommates:
            for updated_roommate in roommates_copy:
                if original_roommate['id'] == updated_roommate['id']:
                    original_roommate['current_cycle_points'] = updated_roommate['current_cycle_points']
                    break
        
        # Save updated roommate points
        self.data_handler.save_roommates(roommates)
        
        return assignments
    
    def create_assignment(self, chore: Dict, roommate: Dict, current_time: datetime) -> Dict:
        """Create an assignment object."""
        frequency = chore.get('frequency', 'weekly')
        if frequency == 'daily':
            due_date = current_time + timedelta(days=1)
        elif frequency == 'weekly':
            due_date = current_time + timedelta(days=7)
        elif frequency == 'bi-weekly':
            due_date = current_time + timedelta(days=14)
        else:
            due_date = current_time + timedelta(days=7)
        
        return {
            'chore_id': chore['id'],
            'chore_name': chore['name'],
            'roommate_id': roommate['id'],
            'roommate_name': roommate['name'],
            'assigned_date': current_time.isoformat(),
            'due_date': due_date.isoformat(),
            'frequency': frequency,
            'type': chore.get('type', 'random'),
            'points': chore.get('points', 1)
        }
    
    def assign_chores_original(self, due_chores: List[Dict], roommates: List[Dict], current_time: datetime) -> List[Dict]:
        """Original assignment logic for fewer than 4 roommates."""
        assignments = []
        
        for chore in due_chores:
            # Assign based on chore type
            if chore.get('type') == 'predefined':
                assigned_roommate_id = self.assign_predefined_chore(chore)
            else:  # random type
                assigned_roommate_id = self.assign_random_chore(chore)
            
            if assigned_roommate_id:
                # Find roommate name
                roommate = next((r for r in roommates if r['id'] == assigned_roommate_id), None)
                if roommate:
                    assignment = self.create_assignment(chore, roommate, current_time)
                    assignments.append(assignment)
        
        return assignments
    
    def get_assignments_by_roommate(self) -> Dict[str, List[Dict]]:
        """Group current assignments by roommate."""
        assignments = self.data_handler.get_current_assignments()
        grouped = {}
        
        for assignment in assignments:
            roommate_name = assignment['roommate_name']
            if roommate_name not in grouped:
                grouped[roommate_name] = []
            grouped[roommate_name].append(assignment)
        
        return grouped
    
    def assign_predefined_chores_coordinated(self, predefined_chores: List[Dict], roommates: List[Dict], 
                                           cycle_assignments: Dict[int, int], current_time: datetime) -> List[Dict]:
        """Assign predefined chores using coordinated global rotation."""
        assignments = []
        
        if not predefined_chores:
            return assignments
        
        state = self.data_handler.get_state()
        
        # Get or initialize global predefined rotation index
        global_rotation_index = state.get('global_predefined_rotation', 0)
        roommate_ids = sorted([r['id'] for r in roommates])  # Sort for consistency
        
        for chore in predefined_chores:
            # Find next roommate in global rotation, but skip those who already have assignments in this cycle
            attempts = 0
            while attempts < len(roommate_ids):
                candidate_id = roommate_ids[global_rotation_index % len(roommate_ids)]
                # If this candidate has fewer than 2 assignments already, assign to them
                if cycle_assignments.get(candidate_id, 0) < 2:
                    assigned_roommate_id = candidate_id
                    break
                global_rotation_index += 1
                attempts += 1
            else:
                # If everyone has 2+ assignments, just assign to next in rotation
                assigned_roommate_id = roommate_ids[global_rotation_index % len(roommate_ids)]
            
            # Find roommate name
            roommate_name = next(
                (r['name'] for r in roommates if r['id'] == assigned_roommate_id),
                "Unknown"
            )
            
            # Calculate due date
            frequency = chore.get('frequency', 'weekly')
            if frequency == 'daily':
                due_date = current_time + timedelta(days=1)
            elif frequency == 'weekly':
                due_date = current_time + timedelta(days=7)
            elif frequency == 'bi-weekly':
                due_date = current_time + timedelta(days=14)
            else:
                due_date = current_time + timedelta(days=7)
            
            assignment = {
                'chore_id': chore['id'],
                'chore_name': chore['name'],
                'roommate_id': assigned_roommate_id,
                'roommate_name': roommate_name,
                'assigned_date': current_time.isoformat(),
                'due_date': due_date.isoformat(),
                'frequency': frequency,
                'type': chore.get('type', 'predefined'),
                'points': chore.get('points', 1)
            }
            assignments.append(assignment)
            
            # Update tracking
            cycle_assignments[assigned_roommate_id] += 1
            
            # Update individual chore state for backwards compatibility
            self.data_handler.update_predefined_chore_state(chore['id'], assigned_roommate_id)
            
            # Move to next roommate in global rotation
            global_rotation_index += 1
        
        # Save updated global rotation index
        self.data_handler.update_global_predefined_rotation(global_rotation_index % len(roommate_ids))
        
        return assignments
    
    def assign_random_chores_equitable(self, random_chores: List[Dict], roommates: List[Dict],
                                     cycle_assignments: Dict[int, int], current_time: datetime) -> List[Dict]:
        """Assign random chores with enhanced equity consideration."""
        assignments = []
        
        for chore in random_chores:
            # Calculate enhanced weights favoring people with fewer assignments
            weights = []
            roommate_ids = []
            
            max_points = max([r.get('current_cycle_points', 0) for r in roommates]) + 1
            max_assignments = max(cycle_assignments.values()) + 1
            
            for roommate in roommates:
                current_points = roommate.get('current_cycle_points', 0)
                current_assignments_count = cycle_assignments[roommate['id']]
                
                # Base weight from points (lower points = higher weight)
                point_weight = max_points - current_points
                
                # Equity bonus - heavily favor people with 0 assignments
                if current_assignments_count == 0:
                    equity_multiplier = 10  # 10x bonus for unassigned people
                elif current_assignments_count == 1:
                    equity_multiplier = 2   # 2x bonus for people with only 1 assignment
                else:
                    equity_multiplier = 1   # Normal weight for people with 2+ assignments
                
                final_weight = point_weight * equity_multiplier
                weights.append(final_weight)
                roommate_ids.append(roommate['id'])
            
            # Select roommate using enhanced weighted random choice
            selected_roommate_id = random.choices(roommate_ids, weights=weights)[0]
            
            # Find roommate name and update points
            selected_roommate = next(r for r in roommates if r['id'] == selected_roommate_id)
            roommate_name = selected_roommate['name']
            
            # Update roommate points
            chore_points = chore.get('points', 1)
            selected_roommate['current_cycle_points'] = selected_roommate.get('current_cycle_points', 0) + chore_points
            
            # Calculate due date
            frequency = chore.get('frequency', 'weekly')
            if frequency == 'daily':
                due_date = current_time + timedelta(days=1)
            elif frequency == 'weekly':
                due_date = current_time + timedelta(days=7)
            elif frequency == 'bi-weekly':
                due_date = current_time + timedelta(days=14)
            else:
                due_date = current_time + timedelta(days=7)
            
            assignment = {
                'chore_id': chore['id'],
                'chore_name': chore['name'],
                'roommate_id': selected_roommate_id,
                'roommate_name': roommate_name,
                'assigned_date': current_time.isoformat(),
                'due_date': due_date.isoformat(),
                'frequency': frequency,
                'type': chore.get('type', 'random'),
                'points': chore.get('points', 1)
            }
            assignments.append(assignment)
            
            # Update tracking
            cycle_assignments[selected_roommate_id] += 1
        
        # Save updated roommate points
        self.data_handler.save_roommates(roommates)
        
        return assignments
    
    def ensure_minimum_assignments(self, assignments: List[Dict], roommates: List[Dict], 
                                 enforce_minimum: bool = True) -> List[Dict]:
        """Ensure everyone gets at least one assignment when enforce_minimum is True."""
        if not enforce_minimum or len(assignments) < len(roommates):
            return assignments
        
        # Count assignments per roommate
        assignment_counts = {}
        for roommate in roommates:
            assignment_counts[roommate['id']] = 0
        
        for assignment in assignments:
            roommate_id = assignment['roommate_id']
            if roommate_id in assignment_counts:
                assignment_counts[roommate_id] += 1
        
        # Find people with 0 assignments and people with 2+ assignments
        unassigned = [rid for rid, count in assignment_counts.items() if count == 0]
        overassigned = [rid for rid, count in assignment_counts.items() if count >= 2]
        
        # If everyone has at least one assignment, we're good
        if not unassigned:
            return assignments
        
        # Try to redistribute from overassigned to unassigned
        for unassigned_id in unassigned:
            if not overassigned:
                break
                
            # Find a reassignable chore from someone with multiple assignments
            for assignment in assignments:
                if assignment['roommate_id'] in overassigned:
                    # Store the original assignee ID before reassigning
                    original_roommate_id = assignment['roommate_id']
                    
                    # Reassign this chore to the unassigned person
                    unassigned_roommate = next(r for r in roommates if r['id'] == unassigned_id)
                    
                    assignment['roommate_id'] = unassigned_id
                    assignment['roommate_name'] = unassigned_roommate['name']
                    
                    # Update tracking
                    assignment_counts[unassigned_id] += 1
                    assignment_counts[original_roommate_id] -= 1
                    
                    # Remove from overassigned if they now have only 1 assignment
                    if assignment_counts[original_roommate_id] < 2:
                        overassigned.remove(original_roommate_id)
                    
                    break
        
        return assignments