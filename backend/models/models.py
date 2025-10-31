"""
SQLAlchemy models for the Zeith application.

These models represent the data structure of the household management and personal
productivity platform, including chores, roommates, assignments, shopping lists,
productivity tracking (Pomodoro, to-dos, mood journaling), and analytics.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import validates

db = SQLAlchemy()


class BaseModel(db.Model):
    """Base model with common functionality for all models."""
    
    __abstract__ = True
    
    def to_dict(self, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """Convert model instance to dictionary for JSON serialization."""
        exclude = exclude or []
        data = {}
        
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                if isinstance(value, datetime):
                    value = value.isoformat()
                data[column.name] = value
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], exclude: Optional[List[str]] = None):
        """Create model instance from dictionary data."""
        exclude = exclude or ['id']  # Usually exclude ID for new records
        
        filtered_data = {k: v for k, v in data.items() if k not in exclude}
        return cls(**filtered_data)


class Roommate(BaseModel):
    """Model representing a roommate in the household."""
    
    __tablename__ = 'roommates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    current_cycle_points = db.Column(db.Integer, default=0, nullable=False)
    
    # Google Authentication fields
    google_id = db.Column(db.String(255), unique=True, nullable=True)
    google_profile_picture_url = db.Column(db.String(500), nullable=True)
    linked_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    assignments = db.relationship('Assignment', back_populates='roommate', lazy='dynamic')
    shopping_items_added = db.relationship('ShoppingItem', foreign_keys='ShoppingItem.added_by', back_populates='added_by_roommate', lazy='dynamic')
    shopping_items_purchased = db.relationship('ShoppingItem', foreign_keys='ShoppingItem.purchased_by', back_populates='purchased_by_roommate', lazy='dynamic')
    purchase_requests = db.relationship('PurchaseRequest', back_populates='requested_by_roommate', lazy='dynamic')
    approvals_given = db.relationship('Approval', back_populates='approved_by_roommate', lazy='dynamic')
    laundry_slots = db.relationship('LaundrySlot', back_populates='roommate', lazy='dynamic')
    blocked_time_slots_created = db.relationship('BlockedTimeSlot', back_populates='created_by_roommate', lazy='dynamic')
    
    @validates('name')
    def validate_name(self, key, name):
        """Validate roommate name."""
        if not name or not name.strip():
            raise ValueError("Roommate name cannot be empty")
        return name.strip()
    
    @validates('current_cycle_points')
    def validate_points(self, key, points):
        """Validate cycle points are non-negative."""
        if points < 0:
            raise ValueError("Cycle points cannot be negative")
        return points
    
    def reset_cycle_points(self):
        """Reset cycle points to zero."""
        self.current_cycle_points = 0
        return self
    
    def add_points(self, points: int):
        """Add points to current cycle total."""
        self.current_cycle_points += points
        return self
    
    def link_google_account(self, google_id: str, profile_picture_url: str = None):
        """Link Google account to roommate."""
        self.google_id = google_id
        self.google_profile_picture_url = profile_picture_url
        self.linked_at = datetime.utcnow()
        return self
    
    def unlink_google_account(self):
        """Unlink Google account from roommate."""
        self.google_id = None
        self.google_profile_picture_url = None
        self.linked_at = None
        return self
    
    @property
    def is_google_linked(self) -> bool:
        """Check if roommate has a linked Google account."""
        return self.google_id is not None
    
    def to_dict(self, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """Convert to dictionary with additional computed fields."""
        data = super().to_dict(exclude)
        data['is_google_linked'] = self.is_google_linked
        return data
    
    def __repr__(self):
        return f'<Roommate {self.id}: {self.name}>'


class Chore(BaseModel):
    """Model representing a household chore."""
    
    __tablename__ = 'chores'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    frequency = db.Column(db.String(50), nullable=False)  # daily, weekly, monthly
    type = db.Column(db.String(50), nullable=False)  # random, predefined
    points = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    sub_chores = db.relationship('SubChore', back_populates='chore', lazy='dynamic', cascade='all, delete-orphan')
    assignments = db.relationship('Assignment', back_populates='chore', lazy='dynamic')
    
    # State tracking for predefined chores
    predefined_state = db.relationship('ApplicationState', back_populates='chore', lazy='select', uselist=False)
    
    VALID_FREQUENCIES = ['daily', 'weekly', 'monthly']
    VALID_TYPES = ['random', 'predefined']
    
    @validates('frequency')
    def validate_frequency(self, key, frequency):
        """Validate chore frequency."""
        if frequency not in self.VALID_FREQUENCIES:
            raise ValueError(f"Frequency must be one of: {', '.join(self.VALID_FREQUENCIES)}")
        return frequency
    
    @validates('type')
    def validate_type(self, key, type_):
        """Validate chore type."""
        if type_ not in self.VALID_TYPES:
            raise ValueError(f"Type must be one of: {', '.join(self.VALID_TYPES)}")
        return type_
    
    @validates('points')
    def validate_points(self, key, points):
        """Validate chore points are positive."""
        if points <= 0:
            raise ValueError("Chore points must be positive")
        return points
    
    @validates('name')
    def validate_name(self, key, name):
        """Validate chore name."""
        if not name or not name.strip():
            raise ValueError("Chore name cannot be empty")
        return name.strip()
    
    def add_sub_chore(self, name: str) -> 'SubChore':
        """Add a new sub-chore to this chore."""
        sub_chore = SubChore(name=name, chore=self)
        db.session.add(sub_chore)
        return sub_chore
    
    @hybrid_property
    def sub_chores_count(self) -> int:
        """Get the count of sub-chores."""
        return self.sub_chores.count()
    
    def get_current_assignment(self) -> Optional['Assignment']:
        """Get the current active assignment for this chore."""
        return self.assignments.filter_by(is_active=True).first()
    
    def calculate_due_date(self, assigned_date: datetime = None) -> datetime:
        """Calculate due date based on frequency and assigned date."""
        if assigned_date is None:
            assigned_date = datetime.utcnow()
        
        if self.frequency == 'daily':
            return assigned_date + timedelta(days=1)
        elif self.frequency == 'weekly':
            return assigned_date + timedelta(weeks=1)
        elif self.frequency == 'monthly':
            return assigned_date + timedelta(days=30)
        else:
            return assigned_date + timedelta(days=1)  # Default to daily
    
    def to_dict(self, exclude: Optional[List[str]] = None, include_sub_chores: bool = False) -> Dict[str, Any]:
        """Convert to dictionary with optional sub-chores."""
        data = super().to_dict(exclude)
        data['sub_chores_count'] = self.sub_chores_count
        
        if include_sub_chores:
            data['sub_chores'] = [sub.to_dict() for sub in self.sub_chores.all()]
        
        return data
    
    def __repr__(self):
        return f'<Chore {self.id}: {self.name} ({self.frequency}, {self.points}pts)>'


class SubChore(BaseModel):
    """Model representing a sub-task within a chore."""
    
    __tablename__ = 'sub_chores'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300), nullable=False)
    chore_id = db.Column(db.Integer, db.ForeignKey('chores.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    chore = db.relationship('Chore', back_populates='sub_chores')
    completions = db.relationship('SubChoreCompletion', back_populates='sub_chore', lazy='dynamic', cascade='all, delete-orphan')
    
    @validates('name')
    def validate_name(self, key, name):
        """Validate sub-chore name."""
        if not name or not name.strip():
            raise ValueError("Sub-chore name cannot be empty")
        return name.strip()
    
    def is_completed_in_assignment(self, assignment: 'Assignment') -> bool:
        """Check if this sub-chore is completed in a specific assignment."""
        completion = self.completions.filter_by(assignment=assignment).first()
        return completion.completed if completion else False
    
    def toggle_completion(self, assignment: 'Assignment') -> bool:
        """Toggle completion status for this sub-chore in an assignment."""
        completion = self.completions.filter_by(assignment=assignment).first()
        
        if completion:
            completion.completed = not completion.completed
        else:
            completion = SubChoreCompletion(
                sub_chore=self,
                assignment=assignment,
                completed=True
            )
            db.session.add(completion)
        
        return completion.completed
    
    def __repr__(self):
        return f'<SubChore {self.id}: {self.name} (Chore {self.chore_id})>'


class Assignment(BaseModel):
    """Model representing a chore assignment to a roommate."""
    
    __tablename__ = 'assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    chore_id = db.Column(db.Integer, db.ForeignKey('chores.id'), nullable=False)
    roommate_id = db.Column(db.Integer, db.ForeignKey('roommates.id'), nullable=False)
    assigned_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Snapshot data for historical tracking
    chore_name = db.Column(db.String(200), nullable=False)
    roommate_name = db.Column(db.String(100), nullable=False)
    frequency = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    points = db.Column(db.Integer, nullable=False)
    
    # Relationships
    chore = db.relationship('Chore', back_populates='assignments')
    roommate = db.relationship('Roommate', back_populates='assignments')
    sub_chore_completions = db.relationship('SubChoreCompletion', back_populates='assignment', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        """Initialize assignment with snapshot data from chore and roommate."""
        super().__init__(**kwargs)
        
        # Auto-populate snapshot fields if chore and roommate are provided
        if self.chore:
            self.chore_name = self.chore.name
            self.frequency = self.chore.frequency
            self.type = self.chore.type
            self.points = self.chore.points
            
            # Calculate due date if not provided
            if not self.due_date:
                self.due_date = self.chore.calculate_due_date(self.assigned_date)
        
        if self.roommate:
            self.roommate_name = self.roommate.name
    
    @validates('assigned_date')
    def validate_assigned_date(self, key, assigned_date):
        """Validate assigned date is not in the future."""
        if assigned_date > datetime.utcnow():
            raise ValueError("Assigned date cannot be in the future")
        return assigned_date
    
    @validates('due_date')
    def validate_due_date(self, key, due_date):
        """Validate due date is after assigned date."""
        if self.assigned_date and due_date <= self.assigned_date:
            raise ValueError("Due date must be after assigned date")
        return due_date
    
    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if assignment is overdue."""
        return self.is_active and datetime.utcnow() > self.due_date
    
    @hybrid_property
    def days_until_due(self) -> int:
        """Get days until due date (negative if overdue)."""
        delta = self.due_date - datetime.utcnow()
        return delta.days
    
    def get_sub_chore_progress(self) -> Dict[str, Any]:
        """Get progress of sub-chores for this assignment."""
        total_sub_chores = self.chore.sub_chores.count()
        
        if total_sub_chores == 0:
            return {
                'total_sub_chores': 0,
                'completed_sub_chores': 0,
                'completion_percentage': 0.0,
                'sub_chore_statuses': {}
            }
        
        completed_count = self.sub_chore_completions.filter_by(completed=True).count()
        completion_percentage = (completed_count / total_sub_chores) * 100
        
        # Build status dictionary
        statuses = {}
        for completion in self.sub_chore_completions:
            statuses[str(completion.sub_chore_id)] = completion.completed
        
        return {
            'total_sub_chores': total_sub_chores,
            'completed_sub_chores': completed_count,
            'completion_percentage': round(completion_percentage, 1),
            'sub_chore_statuses': statuses
        }
    
    def mark_completed(self):
        """Mark assignment as completed."""
        self.is_active = False
        self.completed_at = datetime.utcnow()
        
        # Award points to roommate
        self.roommate.add_points(self.points)
        
        return self
    
    def mark_active(self):
        """Mark assignment as active (undo completion)."""
        if self.completed_at:
            # Remove points from roommate
            self.roommate.current_cycle_points = max(0, self.roommate.current_cycle_points - self.points)
        
        self.is_active = True
        self.completed_at = None
        return self
    
    def to_dict(self, exclude: Optional[List[str]] = None, include_progress: bool = False) -> Dict[str, Any]:
        """Convert to dictionary with optional sub-chore progress."""
        data = super().to_dict(exclude)
        data['is_overdue'] = self.is_overdue
        data['days_until_due'] = self.days_until_due
        
        if include_progress:
            data['sub_chore_progress'] = self.get_sub_chore_progress()
        
        return data
    
    def __repr__(self):
        status = "Active" if self.is_active else "Completed"
        return f'<Assignment {self.id}: {self.chore_name} -> {self.roommate_name} ({status})>'


class SubChoreCompletion(BaseModel):
    """Model tracking completion status of sub-chores within assignments."""
    
    __tablename__ = 'sub_chore_completions'
    
    id = db.Column(db.Integer, primary_key=True)
    sub_chore_id = db.Column(db.Integer, db.ForeignKey('sub_chores.id', ondelete='CASCADE'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id', ondelete='CASCADE'), nullable=False)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    sub_chore = db.relationship('SubChore', back_populates='completions')
    assignment = db.relationship('Assignment', back_populates='sub_chore_completions')
    
    # Unique constraint to prevent duplicate completions
    __table_args__ = (
        db.UniqueConstraint('sub_chore_id', 'assignment_id', name='unique_sub_chore_assignment'),
    )
    
    def toggle_completion(self) -> bool:
        """Toggle completion status."""
        self.completed = not self.completed
        self.completed_at = datetime.utcnow() if self.completed else None
        return self.completed
    
    def __repr__(self):
        status = "Completed" if self.completed else "Pending"
        return f'<SubChoreCompletion {self.id}: SubChore {self.sub_chore_id} Assignment {self.assignment_id} ({status})>'


class ShoppingItem(BaseModel):
    """Model representing items on the shared shopping list."""
    
    __tablename__ = 'shopping_items'
    
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(200), nullable=False)
    estimated_price = db.Column(db.Numeric(10, 2), nullable=True)
    actual_price = db.Column(db.Numeric(10, 2), nullable=True)
    brand_preference = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Who added the item
    added_by = db.Column(db.Integer, db.ForeignKey('roommates.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Purchase information
    purchased_by = db.Column(db.Integer, db.ForeignKey('roommates.id'), nullable=True)
    purchase_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='active', nullable=False)  # active, purchased
    
    # Relationships
    added_by_roommate = db.relationship('Roommate', foreign_keys=[added_by], back_populates='shopping_items_added')
    purchased_by_roommate = db.relationship('Roommate', foreign_keys=[purchased_by], back_populates='shopping_items_purchased')
    
    VALID_STATUSES = ['active', 'purchased']
    
    @validates('item_name')
    def validate_item_name(self, key, item_name):
        """Validate item name."""
        if not item_name or not item_name.strip():
            raise ValueError("Item name cannot be empty")
        return item_name.strip()
    
    @validates('status')
    def validate_status(self, key, status):
        """Validate item status."""
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(self.VALID_STATUSES)}")
        return status
    
    @validates('estimated_price', 'actual_price')
    def validate_prices(self, key, price):
        """Validate prices are non-negative."""
        if price is not None and price < 0:
            raise ValueError(f"{key.replace('_', ' ').title()} cannot be negative")
        return price
    
    def mark_purchased(self, purchased_by_id: int, actual_price: float = None, purchase_notes: str = None):
        """Mark item as purchased."""
        self.status = 'purchased'
        self.purchased_by = purchased_by_id
        self.purchase_date = datetime.utcnow()
        
        if actual_price is not None:
            self.actual_price = actual_price
        
        if purchase_notes:
            if self.notes:
                self.notes += f" | Purchase note: {purchase_notes}"
            else:
                self.notes = f"Purchase note: {purchase_notes}"
        
        return self
    
    def mark_active(self):
        """Mark item as active (undo purchase)."""
        self.status = 'active'
        self.purchased_by = None
        self.purchase_date = None
        self.actual_price = None
        return self
    
    @hybrid_property
    def is_purchased(self) -> bool:
        """Check if item is purchased."""
        return self.status == 'purchased'
    
    @hybrid_property
    def price_difference(self) -> Optional[float]:
        """Get difference between actual and estimated price."""
        if self.actual_price and self.estimated_price:
            return float(self.actual_price - self.estimated_price)
        return None
    
    def to_dict(self, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """Convert to dictionary with additional computed fields."""
        data = super().to_dict(exclude)
        
        # Add roommate names for convenience
        if self.added_by_roommate:
            data['added_by_name'] = self.added_by_roommate.name
        
        if self.purchased_by_roommate:
            data['purchased_by_name'] = self.purchased_by_roommate.name
        
        data['is_purchased'] = self.is_purchased
        data['price_difference'] = self.price_difference
        
        # Convert Decimal to float for JSON serialization
        if data.get('estimated_price'):
            data['estimated_price'] = float(data['estimated_price'])
        if data.get('actual_price'):
            data['actual_price'] = float(data['actual_price'])
        
        return data
    
    def __repr__(self):
        return f'<ShoppingItem {self.id}: {self.item_name} ({self.status})>'


class PurchaseRequest(BaseModel):
    """Model representing purchase requests that require roommate approval."""
    
    __tablename__ = 'purchase_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(200), nullable=False)
    estimated_price = db.Column(db.Numeric(10, 2), nullable=False)
    brand_preference = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Request information
    requested_by = db.Column(db.Integer, db.ForeignKey('roommates.id'), nullable=False)
    date_requested = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Approval settings
    approval_threshold = db.Column(db.Integer, default=2, nullable=False)
    auto_approve_under = db.Column(db.Numeric(10, 2), default=10.0, nullable=False)
    
    # Status and decision tracking
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, approved, declined, auto-approved
    final_decision_date = db.Column(db.DateTime, nullable=True)
    final_decision_by = db.Column(db.Integer, db.ForeignKey('roommates.id'), nullable=True)
    
    # Relationships
    requested_by_roommate = db.relationship('Roommate', foreign_keys=[requested_by], back_populates='purchase_requests')
    final_decision_by_roommate = db.relationship('Roommate', foreign_keys=[final_decision_by])
    approvals = db.relationship('Approval', back_populates='request', lazy='dynamic', cascade='all, delete-orphan')
    
    VALID_STATUSES = ['pending', 'approved', 'declined', 'auto-approved']
    
    def __init__(self, **kwargs):
        """Initialize request and check for auto-approval."""
        super().__init__(**kwargs)
        
        # Check for auto-approval
        if self.estimated_price <= self.auto_approve_under:
            self.status = 'auto-approved'
            self.final_decision_date = datetime.utcnow()
            # final_decision_by stays None for system auto-approval
    
    @validates('item_name')
    def validate_item_name(self, key, item_name):
        """Validate item name."""
        if not item_name or not item_name.strip():
            raise ValueError("Item name cannot be empty")
        return item_name.strip()
    
    @validates('status')
    def validate_status(self, key, status):
        """Validate request status."""
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(self.VALID_STATUSES)}")
        return status
    
    @validates('estimated_price')
    def validate_estimated_price(self, key, price):
        """Validate estimated price is positive."""
        if price <= 0:
            raise ValueError("Estimated price must be positive")
        return price
    
    @validates('approval_threshold')
    def validate_approval_threshold(self, key, threshold):
        """Validate approval threshold is positive."""
        if threshold <= 0:
            raise ValueError("Approval threshold must be positive")
        return threshold
    
    def add_approval(self, approved_by_id: int, approval_status: str, notes: str = None) -> 'Approval':
        """Add or update an approval for this request."""
        if self.status != 'pending':
            raise ValueError(f"Cannot add approval to {self.status} request")
        
        # Remove existing approval from this user
        existing = self.approvals.filter_by(approved_by=approved_by_id).first()
        if existing:
            db.session.delete(existing)
        
        # Add new approval
        approval = Approval(
            request=self,
            approved_by=approved_by_id,
            approval_status=approval_status,
            notes=notes or ""
        )
        db.session.add(approval)
        
        # Check if request should be finalized
        self._check_approval_status()
        
        return approval
    
    def _check_approval_status(self):
        """Check if request has enough approvals or declines to finalize."""
        approval_count = self.approvals.filter_by(approval_status='approved').count()
        decline_count = self.approvals.filter_by(approval_status='declined').count()
        
        # Get total roommates for decline threshold calculation
        total_roommates = db.session.query(Roommate).count()
        other_roommates = total_roommates - 1  # Exclude requester
        decline_threshold = (other_roommates // 2) + 1  # Majority
        
        if approval_count >= self.approval_threshold:
            self.status = 'approved'
            self.final_decision_date = datetime.utcnow()
            # Set final_decision_by to the user who provided the deciding approval
            latest_approval = self.approvals.filter_by(approval_status='approved').order_by(Approval.approval_date.desc()).first()
            if latest_approval:
                self.final_decision_by = latest_approval.approved_by
        elif decline_count >= decline_threshold:
            self.status = 'declined'
            self.final_decision_date = datetime.utcnow()
            # Set final_decision_by to the user who provided the deciding decline
            latest_decline = self.approvals.filter_by(approval_status='declined').order_by(Approval.approval_date.desc()).first()
            if latest_decline:
                self.final_decision_by = latest_decline.approved_by
    
    def promote_to_shopping_list(self) -> 'ShoppingItem':
        """Convert approved request to shopping list item."""
        if self.status not in ['approved', 'auto-approved']:
            raise ValueError("Only approved requests can be promoted to shopping list")
        
        # Create shopping item
        shopping_item = ShoppingItem(
            item_name=self.item_name,
            estimated_price=self.estimated_price,
            brand_preference=self.brand_preference,
            notes=f"{'Auto-approved' if self.status == 'auto-approved' else 'Approved'} request: {self.notes or ''}",
            added_by=self.requested_by
        )
        
        db.session.add(shopping_item)
        return shopping_item
    
    @hybrid_property
    def is_auto_approved(self) -> bool:
        """Check if request was auto-approved."""
        return self.status == 'auto-approved'
    
    def get_approval_summary(self) -> Dict[str, Any]:
        """Get summary of approvals for this request."""
        approvals = self.approvals.all()
        
        return {
            'total_approvals': len(approvals),
            'approved_count': len([a for a in approvals if a.approval_status == 'approved']),
            'declined_count': len([a for a in approvals if a.approval_status == 'declined']),
            'approval_threshold': self.approval_threshold,
            'approvals': [a.to_dict() for a in approvals]
        }
    
    def to_dict(self, exclude: Optional[List[str]] = None, include_approvals: bool = False) -> Dict[str, Any]:
        """Convert to dictionary with optional approval details."""
        data = super().to_dict(exclude)
        
        # Add roommate names for convenience
        if self.requested_by_roommate:
            data['requested_by_name'] = self.requested_by_roommate.name
        
        if self.final_decision_by_roommate:
            data['final_decision_by_name'] = self.final_decision_by_roommate.name
        else:
            data['final_decision_by_name'] = 'System Auto-Approval' if self.is_auto_approved else None
        
        data['is_auto_approved'] = self.is_auto_approved
        
        # Convert Decimal to float for JSON serialization
        if data.get('estimated_price'):
            data['estimated_price'] = float(data['estimated_price'])
        if data.get('auto_approve_under'):
            data['auto_approve_under'] = float(data['auto_approve_under'])
        
        if include_approvals:
            data['approval_summary'] = self.get_approval_summary()
        
        return data
    
    def __repr__(self):
        return f'<PurchaseRequest {self.id}: {self.item_name} ({self.status})>'


class Approval(BaseModel):
    """Model representing individual approvals for purchase requests."""
    
    __tablename__ = 'approvals'
    
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('purchase_requests.id', ondelete='CASCADE'), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('roommates.id'), nullable=False)
    approval_status = db.Column(db.String(20), nullable=False)  # approved, declined
    approval_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    request = db.relationship('PurchaseRequest', back_populates='approvals')
    approved_by_roommate = db.relationship('Roommate', back_populates='approvals_given')
    
    # Unique constraint to prevent duplicate approvals from same user
    __table_args__ = (
        db.UniqueConstraint('request_id', 'approved_by', name='unique_request_approval'),
    )
    
    VALID_APPROVAL_STATUSES = ['approved', 'declined']
    
    @validates('approval_status')
    def validate_approval_status(self, key, status):
        """Validate approval status."""
        if status not in self.VALID_APPROVAL_STATUSES:
            raise ValueError(f"Approval status must be one of: {', '.join(self.VALID_APPROVAL_STATUSES)}")
        return status
    
    def to_dict(self, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """Convert to dictionary with roommate name."""
        data = super().to_dict(exclude)
        
        if self.approved_by_roommate:
            data['approved_by_name'] = self.approved_by_roommate.name
        
        return data
    
    def __repr__(self):
        return f'<Approval {self.id}: Request {self.request_id} {self.approval_status} by {self.approved_by}>'


class LaundrySlot(BaseModel):
    """Model representing laundry time slot reservations."""
    
    __tablename__ = 'laundry_slots'
    
    id = db.Column(db.Integer, primary_key=True)
    roommate_id = db.Column(db.Integer, db.ForeignKey('roommates.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(20), nullable=False)  # e.g., "10:00-12:00"
    duration_hours = db.Column(db.Integer, default=2, nullable=False)
    load_type = db.Column(db.String(50), nullable=False)  # darks, lights, delicates, etc.
    status = db.Column(db.String(20), default='scheduled', nullable=False)  # scheduled, in_progress, completed, cancelled
    machine_type = db.Column(db.String(20), default='washer', nullable=False)  # washer, dryer
    estimated_loads = db.Column(db.Integer, default=1, nullable=False)
    actual_loads = db.Column(db.Integer, default=0, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_date = db.Column(db.DateTime, nullable=True)
    reminder_sent = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relationships
    roommate = db.relationship('Roommate', back_populates='laundry_slots')
    
    VALID_STATUSES = ['scheduled', 'in_progress', 'completed', 'cancelled']
    VALID_LOAD_TYPES = ['darks', 'lights', 'delicates', 'colors', 'whites', 'mixed']
    VALID_MACHINE_TYPES = ['washer', 'dryer']
    
    @validates('status')
    def validate_status(self, key, status):
        """Validate laundry slot status."""
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(self.VALID_STATUSES)}")
        return status
    
    @validates('load_type')
    def validate_load_type(self, key, load_type):
        """Validate load type."""
        if load_type not in self.VALID_LOAD_TYPES:
            raise ValueError(f"Load type must be one of: {', '.join(self.VALID_LOAD_TYPES)}")
        return load_type
    
    @validates('machine_type')
    def validate_machine_type(self, key, machine_type):
        """Validate machine type."""
        if machine_type not in self.VALID_MACHINE_TYPES:
            raise ValueError(f"Machine type must be one of: {', '.join(self.VALID_MACHINE_TYPES)}")
        return machine_type
    
    @validates('estimated_loads', 'actual_loads')
    def validate_loads(self, key, loads):
        """Validate load counts are non-negative."""
        if loads < 0:
            raise ValueError(f"{key.replace('_', ' ').title()} cannot be negative")
        return loads
    
    @validates('duration_hours')
    def validate_duration(self, key, duration):
        """Validate duration is positive."""
        if duration <= 0:
            raise ValueError("Duration must be positive")
        return duration
    
    def mark_completed(self, actual_loads: int = None, completion_notes: str = None):
        """Mark laundry slot as completed."""
        if self.status == 'completed':
            raise ValueError("Laundry slot is already completed")
        
        self.status = 'completed'
        self.completed_date = datetime.utcnow()
        
        if actual_loads is not None:
            self.actual_loads = actual_loads
        
        if completion_notes:
            if self.notes:
                self.notes += f" | Completion: {completion_notes}"
            else:
                self.notes = f"Completion: {completion_notes}"
        
        return self
    
    def mark_in_progress(self):
        """Mark laundry slot as in progress."""
        if self.status not in ['scheduled']:
            raise ValueError(f"Cannot mark {self.status} slot as in progress")
        
        self.status = 'in_progress'
        return self
    
    def cancel_slot(self, reason: str = None):
        """Cancel laundry slot."""
        if self.status == 'completed':
            raise ValueError("Cannot cancel completed laundry slot")
        
        self.status = 'cancelled'
        
        if reason:
            if self.notes:
                self.notes += f" | Cancelled: {reason}"
            else:
                self.notes = f"Cancelled: {reason}"
        
        return self
    
    @hybrid_property
    def is_active(self) -> bool:
        """Check if slot is active (not cancelled or completed)."""
        return self.status in ['scheduled', 'in_progress']
    
    @hybrid_property
    def is_today(self) -> bool:
        """Check if slot is scheduled for today."""
        return self.date == datetime.utcnow().date()
    
    def check_conflicts(self, exclude_self: bool = True) -> List['LaundrySlot']:
        """Check for conflicting laundry slots."""
        query = db.session.query(LaundrySlot).filter(
            LaundrySlot.date == self.date,
            LaundrySlot.time_slot == self.time_slot,
            LaundrySlot.machine_type == self.machine_type,
            LaundrySlot.status.in_(['scheduled', 'in_progress'])
        )
        
        if exclude_self and self.id:
            query = query.filter(LaundrySlot.id != self.id)
        
        return query.all()
    
    def to_dict(self, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """Convert to dictionary with roommate name."""
        data = super().to_dict(exclude)
        
        if self.roommate:
            data['roommate_name'] = self.roommate.name
        
        data['is_active'] = self.is_active
        data['is_today'] = self.is_today
        
        return data
    
    def __repr__(self):
        return f'<LaundrySlot {self.id}: {self.date} {self.time_slot} - {self.roommate.name if self.roommate else "Unknown"} ({self.status})>'


class BlockedTimeSlot(BaseModel):
    """Model representing blocked time slots that prevent laundry scheduling."""
    
    __tablename__ = 'blocked_time_slots'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(20), nullable=False)  # e.g., "10:00-12:00"
    reason = db.Column(db.String(200), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('roommates.id'), nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    sync_to_calendar = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relationships
    created_by_roommate = db.relationship('Roommate', back_populates='blocked_time_slots_created')
    
    @validates('reason')
    def validate_reason(self, key, reason):
        """Validate reason is provided."""
        if not reason or not reason.strip():
            raise ValueError("Reason for blocking time slot cannot be empty")
        return reason.strip()
    
    @hybrid_property
    def is_today(self) -> bool:
        """Check if blocked slot is for today."""
        return self.date == datetime.utcnow().date()
    
    @hybrid_property
    def is_future(self) -> bool:
        """Check if blocked slot is in the future."""
        return self.date > datetime.utcnow().date()
    
    def check_conflicts(self, exclude_self: bool = True) -> List['LaundrySlot']:
        """Check for conflicting laundry slots."""
        query = db.session.query(LaundrySlot).filter(
            LaundrySlot.date == self.date,
            LaundrySlot.time_slot == self.time_slot,
            LaundrySlot.status.in_(['scheduled', 'in_progress'])
        )
        
        return query.all()
    
    def to_dict(self, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """Convert to dictionary with creator name."""
        data = super().to_dict(exclude)
        
        if self.created_by_roommate:
            data['created_by_name'] = self.created_by_roommate.name
        
        data['is_today'] = self.is_today
        data['is_future'] = self.is_future
        
        return data
    
    def __repr__(self):
        return f'<BlockedTimeSlot {self.id}: {self.date} {self.time_slot} - {self.reason}>'


class ApplicationState(BaseModel):
    """Model representing application state and metadata."""

    __tablename__ = 'application_state'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)  # JSON serialized value
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Special relationship for predefined chore states
    chore_id = db.Column(db.Integer, db.ForeignKey('chores.id'), nullable=True)
    chore = db.relationship('Chore', back_populates='predefined_state')

    @validates('key')
    def validate_key(self, key_name, key_value):
        """Validate state key."""
        if not key_value or not key_value.strip():
            raise ValueError("State key cannot be empty")
        return key_value.strip()

    def set_value(self, value: Any):
        """Set value (will be JSON serialized)."""
        if isinstance(value, (dict, list)):
            self.value = json.dumps(value)
        else:
            self.value = str(value)
        self.last_updated = datetime.utcnow()
        return self

    def get_value(self, default: Any = None) -> Any:
        """Get value (will be JSON deserialized if applicable)."""
        if self.value is None:
            return default

        try:
            # Try to parse as JSON
            return json.loads(self.value)
        except (json.JSONDecodeError, TypeError):
            # Return as string if not valid JSON
            return self.value

    @classmethod
    def get_state_value(cls, key: str, default: Any = None) -> Any:
        """Get a state value by key."""
        state = db.session.query(cls).filter_by(key=key).first()
        return state.get_value(default) if state else default

    @classmethod
    def set_state_value(cls, key: str, value: Any) -> 'ApplicationState':
        """Set a state value by key."""
        state = db.session.query(cls).filter_by(key=key).first()

        if state:
            state.set_value(value)
        else:
            state = cls(key=key)
            state.set_value(value)
            db.session.add(state)

        return state

    @classmethod
    def get_last_run_date(cls) -> Optional[datetime]:
        """Get the last run date."""
        value = cls.get_state_value('last_run_date')
        if value:
            try:
                return datetime.fromisoformat(value)
            except (ValueError, TypeError):
                return None
        return None

    @classmethod
    def set_last_run_date(cls, date: datetime = None):
        """Set the last run date."""
        if date is None:
            date = datetime.utcnow()
        cls.set_state_value('last_run_date', date.isoformat())

    @classmethod
    def get_global_predefined_rotation(cls) -> int:
        """Get the global predefined rotation index."""
        return cls.get_state_value('global_predefined_rotation', 0)

    @classmethod
    def set_global_predefined_rotation(cls, rotation_index: int):
        """Set the global predefined rotation index."""
        cls.set_state_value('global_predefined_rotation', rotation_index)

    @classmethod
    def get_predefined_chore_state(cls, chore_id: int) -> Optional[int]:
        """Get the last assigned roommate ID for a predefined chore."""
        key = f'predefined_chore_{chore_id}'
        return cls.get_state_value(key)

    @classmethod
    def set_predefined_chore_state(cls, chore_id: int, roommate_id: int):
        """Set the last assigned roommate ID for a predefined chore."""
        key = f'predefined_chore_{chore_id}'
        state = cls.set_state_value(key, roommate_id)
        state.chore_id = chore_id
        return state

    def __repr__(self):
        return f'<ApplicationState {self.id}: {self.key} = {self.value[:50] if self.value else None}>'


# ============================================================================
# PRODUCTIVITY FEATURE MODELS (ZEITH)
# ============================================================================


class PomodoroSession(BaseModel):
    """Model representing a Pomodoro focus session."""

    __tablename__ = 'pomodoro_sessions'

    id = db.Column(db.Integer, primary_key=True)
    roommate_id = db.Column(db.Integer, db.ForeignKey('roommates.id'), nullable=False)

    # Session timing
    start_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    planned_duration_minutes = db.Column(db.Integer, default=25, nullable=False)
    actual_duration_minutes = db.Column(db.Integer, nullable=True)

    # Session type
    session_type = db.Column(db.String(20), default='focus', nullable=False)  # focus, short_break, long_break
    status = db.Column(db.String(20), default='in_progress', nullable=False)  # in_progress, completed, interrupted

    # Optional linking to chores, todos, or laundry slots
    chore_id = db.Column(db.Integer, db.ForeignKey('chores.id'), nullable=True)
    todo_id = db.Column(db.Integer, db.ForeignKey('todo_items.id'), nullable=True)
    laundry_slot_id = db.Column(db.Integer, db.ForeignKey('laundry_slots.id'), nullable=True)

    # Notes and metadata
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    roommate = db.relationship('Roommate', backref='pomodoro_sessions')
    chore = db.relationship('Chore', backref='pomodoro_sessions')
    todo = db.relationship('TodoItem', backref='pomodoro_sessions', foreign_keys='PomodoroSession.todo_id')
    laundry_slot = db.relationship('LaundrySlot', backref='pomodoro_sessions')

    VALID_SESSION_TYPES = ['focus', 'short_break', 'long_break']
    VALID_STATUSES = ['in_progress', 'completed', 'interrupted']

    @validates('session_type')
    def validate_session_type(self, key, session_type):
        """Validate session type."""
        if session_type not in self.VALID_SESSION_TYPES:
            raise ValueError(f"Session type must be one of: {', '.join(self.VALID_SESSION_TYPES)}")
        return session_type

    @validates('status')
    def validate_status(self, key, status):
        """Validate session status."""
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(self.VALID_STATUSES)}")
        return status

    @validates('planned_duration_minutes')
    def validate_planned_duration(self, key, duration):
        """Validate planned duration is positive."""
        if duration <= 0:
            raise ValueError("Planned duration must be positive")
        return duration

    def complete_session(self, notes: str = None):
        """Mark session as completed."""
        if self.status != 'in_progress':
            raise ValueError(f"Cannot complete {self.status} session")

        self.status = 'completed'
        self.end_time = datetime.utcnow()
        self.actual_duration_minutes = int((self.end_time - self.start_time).total_seconds() / 60)

        if notes:
            self.notes = notes if not self.notes else f"{self.notes} | {notes}"

        return self

    def interrupt_session(self, reason: str = None):
        """Mark session as interrupted."""
        if self.status != 'in_progress':
            raise ValueError(f"Cannot interrupt {self.status} session")

        self.status = 'interrupted'
        self.end_time = datetime.utcnow()
        self.actual_duration_minutes = int((self.end_time - self.start_time).total_seconds() / 60)

        if reason:
            self.notes = reason if not self.notes else f"{self.notes} | Interrupted: {reason}"

        return self

    @hybrid_property
    def is_active(self) -> bool:
        """Check if session is currently active."""
        return self.status == 'in_progress'

    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if active session has exceeded planned duration."""
        if not self.is_active:
            return False
        elapsed_minutes = (datetime.utcnow() - self.start_time).total_seconds() / 60
        return elapsed_minutes > self.planned_duration_minutes

    @hybrid_property
    def elapsed_minutes(self) -> int:
        """Get elapsed time in minutes."""
        if self.end_time:
            return int((self.end_time - self.start_time).total_seconds() / 60)
        return int((datetime.utcnow() - self.start_time).total_seconds() / 60)

    def to_dict(self, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """Convert to dictionary with additional fields."""
        data = super().to_dict(exclude)

        if self.roommate:
            data['roommate_name'] = self.roommate.name

        if self.chore:
            data['chore_name'] = self.chore.name

        if self.todo:
            data['todo_title'] = self.todo.title

        if self.laundry_slot:
            data['laundry_slot_time'] = f"{self.laundry_slot.date} {self.laundry_slot.time_slot}"
            data['laundry_slot_load_type'] = self.laundry_slot.load_type

        data['is_active'] = self.is_active
        data['is_overdue'] = self.is_overdue
        data['elapsed_minutes'] = self.elapsed_minutes

        return data

    def __repr__(self):
        return f'<PomodoroSession {self.id}: {self.roommate.name if self.roommate else "Unknown"} - {self.planned_duration_minutes}min ({self.status})>'


class TodoItem(BaseModel):
    """Model representing personal to-do list items (separate from household chores)."""

    __tablename__ = 'todo_items'

    id = db.Column(db.Integer, primary_key=True)
    roommate_id = db.Column(db.Integer, db.ForeignKey('roommates.id'), nullable=False)

    # Task details
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), default='Personal', nullable=False)  # Personal, Work, Household, etc.

    # Priority and status
    priority = db.Column(db.String(20), default='medium', nullable=False)  # low, medium, high, urgent
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, in_progress, completed

    # Timing
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    due_date = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Optional chore linkage
    chore_id = db.Column(db.Integer, db.ForeignKey('chores.id'), nullable=True)

    # Pomodoro estimation
    estimated_pomodoros = db.Column(db.Integer, default=1, nullable=True)
    actual_pomodoros = db.Column(db.Integer, default=0, nullable=False)

    # Tags for flexible categorization
    tags = db.Column(JSON, nullable=True)  # ['urgent', 'health', 'finance']

    # Order for manual sorting
    display_order = db.Column(db.Integer, default=0, nullable=False)

    # Relationships
    roommate = db.relationship('Roommate', backref='todo_items')
    chore = db.relationship('Chore', backref='todo_items')

    VALID_PRIORITIES = ['low', 'medium', 'high', 'urgent']
    VALID_STATUSES = ['pending', 'in_progress', 'completed']

    @validates('title')
    def validate_title(self, key, title):
        """Validate title is not empty."""
        if not title or not title.strip():
            raise ValueError("Title cannot be empty")
        return title.strip()

    @validates('priority')
    def validate_priority(self, key, priority):
        """Validate priority level."""
        if priority not in self.VALID_PRIORITIES:
            raise ValueError(f"Priority must be one of: {', '.join(self.VALID_PRIORITIES)}")
        return priority

    @validates('status')
    def validate_status(self, key, status):
        """Validate status."""
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(self.VALID_STATUSES)}")
        return status

    @validates('estimated_pomodoros')
    def validate_estimated_pomodoros(self, key, count):
        """Validate pomodoro estimate is non-negative."""
        if count is not None and count < 0:
            raise ValueError("Estimated pomodoros cannot be negative")
        return count

    def mark_completed(self):
        """Mark todo as completed."""
        if self.status == 'completed':
            raise ValueError("Todo is already completed")

        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        return self

    def mark_in_progress(self):
        """Mark todo as in progress."""
        if self.status == 'completed':
            raise ValueError("Cannot mark completed todo as in progress")

        self.status = 'in_progress'
        return self

    def mark_pending(self):
        """Mark todo as pending (undo completion/progress)."""
        self.status = 'pending'
        if self.completed_at:
            self.completed_at = None
        return self

    def increment_pomodoro_count(self):
        """Increment actual pomodoro count."""
        self.actual_pomodoros += 1
        return self

    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if todo is overdue."""
        return (self.due_date is not None and
                self.status != 'completed' and
                datetime.utcnow() > self.due_date)

    @hybrid_property
    def days_until_due(self) -> Optional[int]:
        """Get days until due date (negative if overdue)."""
        if self.due_date is None:
            return None
        delta = self.due_date - datetime.utcnow()
        return delta.days

    @hybrid_property
    def pomodoro_progress_percentage(self) -> float:
        """Get pomodoro completion percentage."""
        if self.estimated_pomodoros is None or self.estimated_pomodoros == 0:
            return 0.0
        return min(100.0, (self.actual_pomodoros / self.estimated_pomodoros) * 100)

    def to_dict(self, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """Convert to dictionary with additional fields."""
        data = super().to_dict(exclude)

        if self.roommate:
            data['roommate_name'] = self.roommate.name

        if self.chore:
            data['chore_name'] = self.chore.name

        data['is_overdue'] = self.is_overdue
        data['days_until_due'] = self.days_until_due
        data['pomodoro_progress_percentage'] = self.pomodoro_progress_percentage

        return data

    def __repr__(self):
        return f'<TodoItem {self.id}: {self.title} ({self.priority}, {self.status})>'


class MoodEntry(BaseModel):
    """Model representing mood journal entries for productivity correlation."""

    __tablename__ = 'mood_entries'

    id = db.Column(db.Integer, primary_key=True)
    roommate_id = db.Column(db.Integer, db.ForeignKey('roommates.id'), nullable=False)

    # Entry timing
    entry_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Mood metrics (1-5 scale)
    mood_level = db.Column(db.Integer, nullable=False)  # 1=very_sad, 2=sad, 3=neutral, 4=good, 5=great
    energy_level = db.Column(db.Integer, nullable=True)  # 1=exhausted, 5=energized
    stress_level = db.Column(db.Integer, nullable=True)  # 1=relaxed, 5=very_stressed
    focus_level = db.Column(db.Integer, nullable=True)  # 1=distracted, 5=very_focused

    # Mood emoji/label
    mood_emoji = db.Column(db.String(10), nullable=True)  # 😔, 😟, 😐, 😊, 😄
    mood_label = db.Column(db.String(50), nullable=True)  # sad, tired, good, great, anxious, etc.

    # Journal notes
    notes = db.Column(db.Text, nullable=True)

    # Tags for flexible categorization
    tags = db.Column(JSON, nullable=True)  # ['productive', 'relaxed', 'stressed', 'social']

    # Contextual data (optional)
    sleep_hours = db.Column(db.Float, nullable=True)
    exercise_minutes = db.Column(db.Integer, nullable=True)

    # Relationships
    roommate = db.relationship('Roommate', backref='mood_entries')

    @validates('mood_level', 'energy_level', 'stress_level', 'focus_level')
    def validate_levels(self, key, value):
        """Validate all levels are in 1-5 range."""
        if value is not None and (value < 1 or value > 5):
            raise ValueError(f"{key.replace('_', ' ').title()} must be between 1 and 5")
        return value

    @validates('sleep_hours')
    def validate_sleep_hours(self, key, hours):
        """Validate sleep hours are reasonable."""
        if hours is not None and (hours < 0 or hours > 24):
            raise ValueError("Sleep hours must be between 0 and 24")
        return hours

    @validates('exercise_minutes')
    def validate_exercise_minutes(self, key, minutes):
        """Validate exercise minutes are non-negative."""
        if minutes is not None and minutes < 0:
            raise ValueError("Exercise minutes cannot be negative")
        return minutes

    @hybrid_property
    def is_today(self) -> bool:
        """Check if entry is for today."""
        return self.entry_date.date() == datetime.utcnow().date()

    @hybrid_property
    def overall_wellbeing_score(self) -> float:
        """Calculate overall wellbeing score (average of all metrics)."""
        scores = [self.mood_level]

        if self.energy_level:
            scores.append(self.energy_level)
        if self.stress_level:
            scores.append(6 - self.stress_level)  # Invert stress (lower is better)
        if self.focus_level:
            scores.append(self.focus_level)

        return round(sum(scores) / len(scores), 1) if scores else 0.0

    def get_mood_emoji_from_level(self) -> str:
        """Get appropriate emoji based on mood level."""
        emoji_map = {
            1: '😔',  # very sad
            2: '😟',  # sad
            3: '😐',  # neutral
            4: '😊',  # good
            5: '😄'   # great
        }
        return emoji_map.get(self.mood_level, '😐')

    def auto_set_emoji(self):
        """Automatically set emoji based on mood level."""
        if not self.mood_emoji:
            self.mood_emoji = self.get_mood_emoji_from_level()
        return self

    def to_dict(self, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """Convert to dictionary with additional fields."""
        data = super().to_dict(exclude)

        if self.roommate:
            data['roommate_name'] = self.roommate.name

        data['is_today'] = self.is_today
        data['overall_wellbeing_score'] = self.overall_wellbeing_score

        return data

    def __repr__(self):
        return f'<MoodEntry {self.id}: {self.roommate.name if self.roommate else "Unknown"} - {self.mood_level}/5 ({self.entry_date.date()})>'


class AnalyticsSnapshot(BaseModel):
    """Model storing daily analytics snapshots for historical tracking."""

    __tablename__ = 'analytics_snapshots'

    id = db.Column(db.Integer, primary_key=True)
    snapshot_date = db.Column(db.Date, default=datetime.utcnow, nullable=False)
    roommate_id = db.Column(db.Integer, db.ForeignKey('roommates.id'), nullable=True)  # NULL for household-wide

    # Chore metrics
    chores_completed = db.Column(db.Integer, default=0, nullable=False)
    chores_assigned = db.Column(db.Integer, default=0, nullable=False)
    total_points_earned = db.Column(db.Integer, default=0, nullable=False)

    # Productivity metrics
    pomodoros_completed = db.Column(db.Integer, default=0, nullable=False)
    focus_time_minutes = db.Column(db.Integer, default=0, nullable=False)
    todos_completed = db.Column(db.Integer, default=0, nullable=False)
    todos_created = db.Column(db.Integer, default=0, nullable=False)

    # Mood metrics
    average_mood = db.Column(db.Float, nullable=True)
    average_energy = db.Column(db.Float, nullable=True)
    average_stress = db.Column(db.Float, nullable=True)
    average_focus = db.Column(db.Float, nullable=True)
    mood_entries_count = db.Column(db.Integer, default=0, nullable=False)

    # Household metrics (when roommate_id is NULL)
    total_household_points = db.Column(db.Integer, nullable=True)
    fairness_score = db.Column(db.Float, nullable=True)  # 0-100, measures point distribution equity

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    roommate = db.relationship('Roommate', backref='analytics_snapshots')

    # Unique constraint to prevent duplicate snapshots
    __table_args__ = (
        db.UniqueConstraint('snapshot_date', 'roommate_id', name='unique_snapshot_per_day'),
    )

    @validates('chores_completed', 'chores_assigned', 'total_points_earned',
               'pomodoros_completed', 'focus_time_minutes', 'todos_completed',
               'todos_created', 'mood_entries_count')
    def validate_non_negative_counts(self, key, value):
        """Validate counts are non-negative."""
        if value < 0:
            raise ValueError(f"{key.replace('_', ' ').title()} cannot be negative")
        return value

    @validates('average_mood', 'average_energy', 'average_stress', 'average_focus')
    def validate_averages(self, key, value):
        """Validate averages are in 1-5 range."""
        if value is not None and (value < 1 or value > 5):
            raise ValueError(f"{key.replace('_', ' ').title()} must be between 1 and 5")
        return value

    @validates('fairness_score')
    def validate_fairness_score(self, key, score):
        """Validate fairness score is in 0-100 range."""
        if score is not None and (score < 0 or score > 100):
            raise ValueError("Fairness score must be between 0 and 100")
        return score

    @hybrid_property
    def is_household_snapshot(self) -> bool:
        """Check if this is a household-wide snapshot."""
        return self.roommate_id is None

    @hybrid_property
    def chore_completion_rate(self) -> float:
        """Calculate chore completion rate as percentage."""
        if self.chores_assigned == 0:
            return 0.0
        return round((self.chores_completed / self.chores_assigned) * 100, 1)

    @hybrid_property
    def productivity_score(self) -> float:
        """Calculate composite productivity score."""
        # Weighted average of normalized metrics
        chore_score = self.chore_completion_rate / 10  # 0-10 scale
        pomodoro_score = min(10, self.pomodoros_completed)  # Cap at 10
        todo_score = min(10, self.todos_completed * 2)  # Cap at 10
        mood_score = (self.average_mood or 3) * 2  # 0-10 scale

        # Weighted combination
        total_score = (chore_score * 0.3 + pomodoro_score * 0.3 +
                      todo_score * 0.2 + mood_score * 0.2)

        return round(total_score, 1)

    def to_dict(self, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """Convert to dictionary with additional fields."""
        data = super().to_dict(exclude)

        if self.roommate:
            data['roommate_name'] = self.roommate.name

        data['is_household_snapshot'] = self.is_household_snapshot
        data['chore_completion_rate'] = self.chore_completion_rate
        data['productivity_score'] = self.productivity_score

        return data

    def __repr__(self):
        target = self.roommate.name if self.roommate else "Household"
        return f'<AnalyticsSnapshot {self.id}: {target} - {self.snapshot_date}>'


# Database utility functions
def create_all_tables(app):
    """Create all database tables."""
    with app.app_context():
        db.create_all()


def drop_all_tables(app):
    """Drop all database tables."""
    with app.app_context():
        db.drop_all()


def reset_database(app):
    """Reset database by dropping and recreating all tables."""
    with app.app_context():
        db.drop_all()
        db.create_all()