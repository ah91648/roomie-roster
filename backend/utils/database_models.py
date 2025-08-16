"""
SQLAlchemy models for RoomieRoster application.
These models mirror the JSON data structure for seamless migration.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship, declarative_base
from .database_config import db

# Use Flask-SQLAlchemy's db.Model as base
Base = db.Model

class Roommate(Base):
    """Roommate model corresponding to roommates.json"""
    __tablename__ = 'roommates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    current_cycle_points = Column(Integer, default=0)
    google_id = Column(String(255), nullable=True, unique=True)
    google_profile_picture_url = Column(Text, nullable=True)
    linked_at = Column(DateTime, nullable=True)
    
    # Relationships
    assignments = relationship("Assignment", back_populates="roommate")
    shopping_items_added = relationship("ShoppingItem", foreign_keys="ShoppingItem.added_by", back_populates="added_by_roommate")
    shopping_items_purchased = relationship("ShoppingItem", foreign_keys="ShoppingItem.purchased_by", back_populates="purchased_by_roommate")
    requests = relationship("Request", back_populates="requested_by_roommate")
    laundry_slots = relationship("LaundrySlot", back_populates="roommate")
    blocked_time_slots = relationship("BlockedTimeSlot", back_populates="created_by_roommate")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary matching JSON structure"""
        return {
            'id': self.id,
            'name': self.name,
            'current_cycle_points': self.current_cycle_points,
            'google_id': self.google_id,
            'google_profile_picture_url': self.google_profile_picture_url,
            'linked_at': self.linked_at.isoformat() if self.linked_at else None
        }

class Chore(Base):
    """Chore model corresponding to chores.json"""
    __tablename__ = 'chores'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    frequency = Column(String(50), nullable=False)  # daily, weekly, monthly
    type = Column(String(50), nullable=False)       # random, predefined
    points = Column(Integer, nullable=False)
    
    # Relationships
    sub_chores = relationship("SubChore", back_populates="chore", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="chore")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary matching JSON structure"""
        return {
            'id': self.id,
            'name': self.name,
            'frequency': self.frequency,
            'type': self.type,
            'points': self.points,
            'sub_chores': [sub_chore.to_dict() for sub_chore in self.sub_chores]
        }

class SubChore(Base):
    """Sub-chore model for chore sub-tasks"""
    __tablename__ = 'sub_chores'
    
    id = Column(Integer, primary_key=True)
    chore_id = Column(Integer, ForeignKey('chores.id'), nullable=False)
    name = Column(String(300), nullable=False)
    completed = Column(Boolean, default=False)  # This is the template, actual completion tracked in assignments
    
    # Relationships
    chore = relationship("Chore", back_populates="sub_chores")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary matching JSON structure"""
        return {
            'id': self.id,
            'name': self.name,
            'completed': self.completed
        }

class Assignment(Base):
    """Assignment model corresponding to current_assignments in state.json"""
    __tablename__ = 'assignments'
    
    id = Column(Integer, primary_key=True)
    chore_id = Column(Integer, ForeignKey('chores.id'), nullable=False)
    chore_name = Column(String(200), nullable=False)
    roommate_id = Column(Integer, ForeignKey('roommates.id'), nullable=False)
    roommate_name = Column(String(100), nullable=False)
    assigned_date = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=False)
    frequency = Column(String(50), nullable=False)
    type = Column(String(50), nullable=False)
    points = Column(Integer, nullable=False)
    sub_chore_completions = Column(JSON, default=dict)  # Store as JSON: {sub_chore_id: boolean}
    
    # Relationships
    chore = relationship("Chore", back_populates="assignments")
    roommate = relationship("Roommate", back_populates="assignments")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary matching JSON structure"""
        assignment_dict = {
            'chore_id': self.chore_id,
            'chore_name': self.chore_name,
            'roommate_id': self.roommate_id,
            'roommate_name': self.roommate_name,
            'assigned_date': self.assigned_date.isoformat(),
            'due_date': self.due_date.isoformat(),
            'frequency': self.frequency,
            'type': self.type,
            'points': self.points
        }
        
        # Add sub_chore_completions if present
        if self.sub_chore_completions:
            assignment_dict['sub_chore_completions'] = self.sub_chore_completions
            
        return assignment_dict

class ApplicationState(Base):
    """Application state model for state.json data"""
    __tablename__ = 'application_state'
    
    id = Column(Integer, primary_key=True)
    last_run_date = Column(DateTime, nullable=True)
    predefined_chore_states = Column(JSON, default=dict)  # {chore_id: last_assigned_roommate_id}
    global_predefined_rotation = Column(Integer, default=0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary matching JSON structure"""
        return {
            'last_run_date': self.last_run_date.isoformat() if self.last_run_date else None,
            'predefined_chore_states': self.predefined_chore_states or {},
            'global_predefined_rotation': self.global_predefined_rotation
        }

class ShoppingItem(Base):
    """Shopping list item model corresponding to shopping_list.json"""
    __tablename__ = 'shopping_items'
    
    id = Column(Integer, primary_key=True)
    item_name = Column(String(200), nullable=False)
    estimated_price = Column(Float, nullable=True)
    actual_price = Column(Float, nullable=True)
    brand_preference = Column(String(100), nullable=True)
    added_by = Column(Integer, ForeignKey('roommates.id'), nullable=False)
    added_by_name = Column(String(100), nullable=False)
    purchased_by = Column(Integer, ForeignKey('roommates.id'), nullable=True)
    purchased_by_name = Column(String(100), nullable=True)
    purchase_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(50), default='active')  # active, purchased
    date_added = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    added_by_roommate = relationship("Roommate", foreign_keys=[added_by], back_populates="shopping_items_added")
    purchased_by_roommate = relationship("Roommate", foreign_keys=[purchased_by], back_populates="shopping_items_purchased")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary matching JSON structure"""
        return {
            'id': self.id,
            'item_name': self.item_name,
            'estimated_price': self.estimated_price,
            'actual_price': self.actual_price,
            'brand_preference': self.brand_preference,
            'added_by': self.added_by,
            'added_by_name': self.added_by_name,
            'purchased_by': self.purchased_by,
            'purchased_by_name': self.purchased_by_name,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'notes': self.notes,
            'status': self.status,
            'date_added': self.date_added.isoformat() if self.date_added else None
        }

class Request(Base):
    """Purchase request model corresponding to requests.json"""
    __tablename__ = 'requests'
    
    id = Column(Integer, primary_key=True)
    item_name = Column(String(200), nullable=False)
    estimated_price = Column(Float, nullable=True)
    brand_preference = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    requested_by = Column(Integer, ForeignKey('roommates.id'), nullable=False)
    requested_by_name = Column(String(100), nullable=False)
    date_requested = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default='pending')  # pending, approved, declined, auto-approved
    approvals = Column(JSON, default=list)  # List of approval objects
    approval_threshold = Column(Integer, default=2)
    auto_approve_under = Column(Float, default=10.0)
    final_decision_date = Column(DateTime, nullable=True)
    final_decision_by = Column(Integer, nullable=True)
    final_decision_by_name = Column(String(100), nullable=True)
    
    # Relationships
    requested_by_roommate = relationship("Roommate", back_populates="requests")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary matching JSON structure"""
        return {
            'id': self.id,
            'item_name': self.item_name,
            'estimated_price': self.estimated_price,
            'brand_preference': self.brand_preference,
            'notes': self.notes,
            'requested_by': self.requested_by,
            'requested_by_name': self.requested_by_name,
            'date_requested': self.date_requested.isoformat() if self.date_requested else None,
            'status': self.status,
            'approvals': self.approvals or [],
            'approval_threshold': self.approval_threshold,
            'auto_approve_under': self.auto_approve_under,
            'final_decision_date': self.final_decision_date.isoformat() if self.final_decision_date else None,
            'final_decision_by': self.final_decision_by,
            'final_decision_by_name': self.final_decision_by_name
        }

class LaundrySlot(Base):
    """Laundry scheduling model corresponding to laundry_slots.json"""
    __tablename__ = 'laundry_slots'
    
    id = Column(Integer, primary_key=True)
    roommate_id = Column(Integer, ForeignKey('roommates.id'), nullable=False)
    roommate_name = Column(String(100), nullable=False)
    date = Column(String(20), nullable=False)  # YYYY-MM-DD format
    time_slot = Column(String(50), nullable=False)  # e.g., "08:00-10:00"
    machine_type = Column(String(50), nullable=False)  # washer, dryer, both
    load_type = Column(String(50), nullable=True)  # lights, darks, delicates, etc.
    estimated_loads = Column(Integer, default=1)
    actual_loads = Column(Integer, nullable=True)
    status = Column(String(50), default='scheduled')  # scheduled, in_progress, completed, cancelled
    notes = Column(Text, nullable=True)
    created_date = Column(DateTime, default=datetime.utcnow)
    completed_date = Column(DateTime, nullable=True)
    
    # Relationships
    roommate = relationship("Roommate", back_populates="laundry_slots")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary matching JSON structure"""
        return {
            'id': self.id,
            'roommate_id': self.roommate_id,
            'roommate_name': self.roommate_name,
            'date': self.date,
            'time_slot': self.time_slot,
            'machine_type': self.machine_type,
            'load_type': self.load_type,
            'estimated_loads': self.estimated_loads,
            'actual_loads': self.actual_loads,
            'status': self.status,
            'notes': self.notes,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None
        }

class BlockedTimeSlot(Base):
    """Blocked time slots model corresponding to blocked_time_slots.json"""
    __tablename__ = 'blocked_time_slots'
    
    id = Column(Integer, primary_key=True)
    date = Column(String(20), nullable=False)  # YYYY-MM-DD format
    time_slot = Column(String(50), nullable=False)  # e.g., "08:00-10:00"
    reason = Column(String(200), nullable=False)
    created_by = Column(Integer, ForeignKey('roommates.id'), nullable=False)
    created_by_name = Column(String(100), nullable=False)
    created_date = Column(DateTime, default=datetime.utcnow)
    sync_to_calendar = Column(Boolean, default=False)
    
    # Relationships
    created_by_roommate = relationship("Roommate", back_populates="blocked_time_slots")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary matching JSON structure"""
        return {
            'id': self.id,
            'date': self.date,
            'time_slot': self.time_slot,
            'reason': self.reason,
            'created_by': self.created_by,
            'created_by_name': self.created_by_name,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'sync_to_calendar': self.sync_to_calendar
        }