#!/usr/bin/env python3
"""Manually migrate chores with proper sub-chore ID handling"""
import os
import json
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

# Load environment
project_root = Path(__file__).parent.parent
load_dotenv(project_root / '.env')

from flask import Flask
from utils.database_config import database_config, db
from utils.database_models import Roommate, Chore, SubChore, Assignment

app = Flask(__name__)
database_config.configure_flask_app(app)

def load_json(filename):
    """Load JSON file"""
    file_path = Path(__file__).parent / 'data' / filename
    with open(file_path, 'r') as f:
        return json.load(f)

with app.app_context():
    print("Starting manual chore migration...")

    # Load data
    chores_data = load_json('chores.json')
    state_data = load_json('state.json')

    # Migrate chores (let database auto-generate sub-chore IDs)
    for chore_data in chores_data:
        # Check if exists
        existing = Chore.query.filter_by(id=chore_data['id']).first()
        if existing:
            print(f"✓ Chore {chore_data['name']} already exists")
            continue

        # Create chore
        chore = Chore(
            id=chore_data['id'],
            name=chore_data['name'],
            frequency=chore_data['frequency'],
            type=chore_data['type'],
            points=chore_data['points']
        )
        db.session.add(chore)
        db.session.flush()  # Get the chore ID

        # Add sub-chores (DON'T set ID - let database auto-generate)
        if 'sub_chores' in chore_data:
            for sub_data in chore_data['sub_chores']:
                sub_chore = SubChore(
                    # id is auto-generated
                    chore_id=chore.id,
                    name=sub_data.get('name', sub_data.get('description', '')),
                    completed=False
                )
                db.session.add(sub_chore)

        db.session.commit()
        sub_count = SubChore.query.filter_by(chore_id=chore.id).count()
        print(f"✓ Added chore: {chore.name} with {sub_count} sub-chores")

    # Migrate assignments
    if 'current_assignments' in state_data:
        for assign_data in state_data['current_assignments']:
            # Check if exists
            existing = Assignment.query.filter_by(
                chore_id=assign_data['chore_id'],
                roommate_id=assign_data['roommate_id']
            ).first()
            if existing:
                print(f"✓ Assignment {assign_data['chore_name']} -> {assign_data['roommate_name']} already exists")
                continue

            # Parse dates
            assigned_date = None
            due_date = None
            if assign_data.get('assigned_date'):
                try:
                    assigned_date = datetime.fromisoformat(assign_data['assigned_date'])
                except:
                    pass
            if assign_data.get('due_date'):
                try:
                    due_date = datetime.fromisoformat(assign_data['due_date'])
                except:
                    pass

            # Create assignment
            assignment = Assignment(
                chore_id=assign_data['chore_id'],
                chore_name=assign_data.get('chore_name'),
                roommate_id=assign_data['roommate_id'],
                roommate_name=assign_data.get('roommate_name'),
                assigned_date=assigned_date,
                due_date=due_date,
                frequency=assign_data.get('frequency'),
                type=assign_data.get('type'),
                points=assign_data.get('points'),
                sub_chore_completions=assign_data.get('sub_chore_completions', {})
            )
            db.session.add(assignment)
            db.session.commit()
            print(f"✓ Added assignment: {assign_data['chore_name']} -> {assign_data['roommate_name']}")

    print("\n✅ Manual migration complete!")
    print("\n=== FINAL DATABASE CONTENTS ===")
    print(f"Roommates: {Roommate.query.count()}")
    print(f"Chores: {Chore.query.count()}")
    print(f"Sub-chores: {SubChore.query.count()}")
    print(f"Assignments: {Assignment.query.count()}")
