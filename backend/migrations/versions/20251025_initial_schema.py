"""Initial schema migration for RoomieRoster + Zeith

Revision ID: 001_initial
Revises:
Create Date: 2025-10-25

This migration creates all database tables for:
- Core RoomieRoster features (household management)
- Calendar integration features
- Zeith productivity features (Pomodoro, Todo, Mood, Analytics)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create all database tables"""

    # ========================================================================
    # CORE ROOMIEROSTER TABLES
    # ========================================================================

    # 1. Roommates table
    op.create_table('roommates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('current_cycle_points', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('google_id', sa.String(length=255), nullable=True),
        sa.Column('google_profile_picture_url', sa.Text(), nullable=True),
        sa.Column('linked_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('google_id')
    )
    op.create_index('idx_roommate_google_id', 'roommates', ['google_id'])

    # 2. Chores table
    op.create_table('chores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('frequency', sa.String(length=50), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('points', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. Sub-chores table
    op.create_table('sub_chores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chore_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=300), nullable=False),
        sa.Column('completed', sa.Boolean(), nullable=True, server_default='false'),
        sa.ForeignKeyConstraint(['chore_id'], ['chores.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_subchore_chore_id', 'sub_chores', ['chore_id'])

    # 4. Assignments table
    op.create_table('assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chore_id', sa.Integer(), nullable=False),
        sa.Column('chore_name', sa.String(length=200), nullable=False),
        sa.Column('roommate_id', sa.Integer(), nullable=False),
        sa.Column('roommate_name', sa.String(length=100), nullable=False),
        sa.Column('assigned_date', sa.DateTime(), nullable=False),
        sa.Column('due_date', sa.DateTime(), nullable=False),
        sa.Column('frequency', sa.String(length=50), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('points', sa.Integer(), nullable=False),
        sa.Column('sub_chore_completions', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['chore_id'], ['chores.id']),
        sa.ForeignKeyConstraint(['roommate_id'], ['roommates.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_assignment_roommate', 'assignments', ['roommate_id'])
    op.create_index('idx_assignment_chore', 'assignments', ['chore_id'])

    # 5. Application state table
    op.create_table('application_state',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('last_run_date', sa.DateTime(), nullable=True),
        sa.Column('predefined_chore_states', sa.JSON(), nullable=True),
        sa.Column('global_predefined_rotation', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('shopping_categories', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 6. Shopping items table
    op.create_table('shopping_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('item_name', sa.String(length=200), nullable=False),
        sa.Column('estimated_price', sa.Float(), nullable=True),
        sa.Column('actual_price', sa.Float(), nullable=True),
        sa.Column('brand_preference', sa.String(length=100), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False, server_default='General'),
        sa.Column('added_by', sa.Integer(), nullable=False),
        sa.Column('added_by_name', sa.String(length=100), nullable=False),
        sa.Column('purchased_by', sa.Integer(), nullable=True),
        sa.Column('purchased_by_name', sa.String(length=100), nullable=True),
        sa.Column('purchase_date', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='active'),
        sa.Column('date_added', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['added_by'], ['roommates.id']),
        sa.ForeignKeyConstraint(['purchased_by'], ['roommates.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_shopping_status', 'shopping_items', ['status'])
    op.create_index('idx_shopping_category', 'shopping_items', ['category'])

    # 7. Requests table
    op.create_table('requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('item_name', sa.String(length=200), nullable=False),
        sa.Column('estimated_price', sa.Float(), nullable=True),
        sa.Column('brand_preference', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('requested_by', sa.Integer(), nullable=False),
        sa.Column('requested_by_name', sa.String(length=100), nullable=False),
        sa.Column('date_requested', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='pending'),
        sa.Column('approvals', sa.JSON(), nullable=True),
        sa.Column('approval_threshold', sa.Integer(), nullable=True, server_default='2'),
        sa.Column('auto_approve_under', sa.Float(), nullable=True, server_default='10.0'),
        sa.Column('final_decision_date', sa.DateTime(), nullable=True),
        sa.Column('final_decision_by', sa.Integer(), nullable=True),
        sa.Column('final_decision_by_name', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['requested_by'], ['roommates.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_request_status', 'requests', ['status'])

    # 8. Laundry slots table
    op.create_table('laundry_slots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('roommate_id', sa.Integer(), nullable=False),
        sa.Column('roommate_name', sa.String(length=100), nullable=False),
        sa.Column('date', sa.String(length=20), nullable=False),
        sa.Column('time_slot', sa.String(length=50), nullable=False),
        sa.Column('machine_type', sa.String(length=50), nullable=False),
        sa.Column('load_type', sa.String(length=50), nullable=True),
        sa.Column('estimated_loads', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('actual_loads', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='scheduled'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_date', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['roommate_id'], ['roommates.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_laundry_date', 'laundry_slots', ['date'])

    # 9. Blocked time slots table
    op.create_table('blocked_time_slots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.String(length=20), nullable=False),
        sa.Column('time_slot', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.String(length=200), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_by_name', sa.String(length=100), nullable=False),
        sa.Column('created_date', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('sync_to_calendar', sa.Boolean(), nullable=True, server_default='false'),
        sa.ForeignKeyConstraint(['created_by'], ['roommates.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # ========================================================================
    # CALENDAR INTEGRATION TABLES
    # ========================================================================

    # 10. Household calendar preferences
    op.create_table('household_calendar_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('preferences_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_updated', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )

    # 11. User calendar preferences
    op.create_table('user_calendar_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('google_id', sa.String(length=255), nullable=False),
        sa.Column('preferences_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_updated', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('preferences_version', sa.String(length=20), nullable=True, server_default='1.0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('google_id')
    )
    op.create_index('idx_user_calendar_google_id', 'user_calendar_preferences', ['google_id'])

    # 12. Calendar event tracking
    op.create_table('calendar_event_tracking',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('source_id', sa.String(length=255), nullable=False),
        sa.Column('google_id', sa.String(length=255), nullable=False),
        sa.Column('calendar_id', sa.String(length=255), nullable=False),
        sa.Column('event_id', sa.String(length=255), nullable=False),
        sa.Column('event_title', sa.String(length=500), nullable=True),
        sa.Column('notification_type', sa.String(length=50), nullable=False),
        sa.Column('is_assignee', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_event_type_source', 'calendar_event_tracking', ['event_type', 'source_id'])
    op.create_index('idx_google_id_event_type', 'calendar_event_tracking', ['google_id', 'event_type'])
    op.create_index('idx_source_id', 'calendar_event_tracking', ['source_id'])

    # 13. Calendar sync status
    op.create_table('calendar_sync_status',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('google_id', sa.String(length=255), nullable=False),
        sa.Column('roommate_id', sa.Integer(), nullable=True),
        sa.Column('sync_enabled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('selected_calendar_id', sa.String(length=255), nullable=True, server_default='primary'),
        sa.Column('last_successful_sync', sa.DateTime(), nullable=True),
        sa.Column('last_sync_attempt', sa.DateTime(), nullable=True),
        sa.Column('last_sync_error', sa.Text(), nullable=True),
        sa.Column('total_synced_events', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_sync_failures', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('calendar_access_valid', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('calendar_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('missing_scopes', sa.JSON(), nullable=True),
        sa.Column('credentials_valid', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('credentials_expired', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('has_refresh_token', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_updated', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['roommate_id'], ['roommates.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_calendar_sync_google_id', 'calendar_sync_status', ['google_id'])

    # ========================================================================
    # ZEITH PRODUCTIVITY TABLES
    # ========================================================================

    # 14. Todo items table
    op.create_table('todo_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('roommate_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False, server_default='Personal'),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='medium'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('chore_id', sa.Integer(), nullable=True),
        sa.Column('estimated_pomodoros', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('actual_pomodoros', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['roommate_id'], ['roommates.id']),
        sa.ForeignKeyConstraint(['chore_id'], ['chores.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_todo_roommate', 'todo_items', ['roommate_id'])
    op.create_index('idx_todo_status', 'todo_items', ['status'])
    op.create_index('idx_todo_priority', 'todo_items', ['priority'])

    # 15. Pomodoro sessions table (must be created AFTER todo_items due to foreign key)
    op.create_table('pomodoro_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('roommate_id', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('planned_duration_minutes', sa.Integer(), nullable=False, server_default='25'),
        sa.Column('actual_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('session_type', sa.String(length=20), nullable=False, server_default='focus'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='in_progress'),
        sa.Column('chore_id', sa.Integer(), nullable=True),
        sa.Column('todo_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['roommate_id'], ['roommates.id']),
        sa.ForeignKeyConstraint(['chore_id'], ['chores.id']),
        sa.ForeignKeyConstraint(['todo_id'], ['todo_items.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_pomodoro_roommate', 'pomodoro_sessions', ['roommate_id'])
    op.create_index('idx_pomodoro_status', 'pomodoro_sessions', ['status'])
    op.create_index('idx_pomodoro_type', 'pomodoro_sessions', ['session_type'])

    # 16. Mood entries table
    op.create_table('mood_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('roommate_id', sa.Integer(), nullable=False),
        sa.Column('entry_date', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('mood_level', sa.Integer(), nullable=False),
        sa.Column('energy_level', sa.Integer(), nullable=True),
        sa.Column('stress_level', sa.Integer(), nullable=True),
        sa.Column('focus_level', sa.Integer(), nullable=True),
        sa.Column('mood_emoji', sa.String(length=10), nullable=True),
        sa.Column('mood_label', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('sleep_hours', sa.Float(), nullable=True),
        sa.Column('exercise_minutes', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['roommate_id'], ['roommates.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_mood_roommate_date', 'mood_entries', ['roommate_id', 'entry_date'])

    # 17. Analytics snapshots table
    op.create_table('analytics_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('snapshot_date', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('roommate_id', sa.Integer(), nullable=True),
        sa.Column('chores_completed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('chores_assigned', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_points_earned', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pomodoros_completed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('focus_time_minutes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('todos_completed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('todos_created', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('average_mood', sa.Float(), nullable=True),
        sa.Column('average_energy', sa.Float(), nullable=True),
        sa.Column('average_stress', sa.Float(), nullable=True),
        sa.Column('average_focus', sa.Float(), nullable=True),
        sa.Column('mood_entries_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_household_points', sa.Integer(), nullable=True),
        sa.Column('fairness_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['roommate_id'], ['roommates.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_snapshot_date_roommate', 'analytics_snapshots', ['snapshot_date', 'roommate_id'])


def downgrade():
    """Drop all database tables in reverse order"""

    # Drop Zeith productivity tables
    op.drop_index('idx_snapshot_date_roommate', table_name='analytics_snapshots')
    op.drop_table('analytics_snapshots')

    op.drop_index('idx_mood_roommate_date', table_name='mood_entries')
    op.drop_table('mood_entries')

    op.drop_index('idx_pomodoro_type', table_name='pomodoro_sessions')
    op.drop_index('idx_pomodoro_status', table_name='pomodoro_sessions')
    op.drop_index('idx_pomodoro_roommate', table_name='pomodoro_sessions')
    op.drop_table('pomodoro_sessions')

    op.drop_index('idx_todo_priority', table_name='todo_items')
    op.drop_index('idx_todo_status', table_name='todo_items')
    op.drop_index('idx_todo_roommate', table_name='todo_items')
    op.drop_table('todo_items')

    # Drop calendar tables
    op.drop_index('idx_calendar_sync_google_id', table_name='calendar_sync_status')
    op.drop_table('calendar_sync_status')

    op.drop_index('idx_source_id', table_name='calendar_event_tracking')
    op.drop_index('idx_google_id_event_type', table_name='calendar_event_tracking')
    op.drop_index('idx_event_type_source', table_name='calendar_event_tracking')
    op.drop_table('calendar_event_tracking')

    op.drop_index('idx_user_calendar_google_id', table_name='user_calendar_preferences')
    op.drop_table('user_calendar_preferences')

    op.drop_table('household_calendar_preferences')

    # Drop core RoomieRoster tables
    op.drop_table('blocked_time_slots')

    op.drop_index('idx_laundry_date', table_name='laundry_slots')
    op.drop_table('laundry_slots')

    op.drop_index('idx_request_status', table_name='requests')
    op.drop_table('requests')

    op.drop_index('idx_shopping_category', table_name='shopping_items')
    op.drop_index('idx_shopping_status', table_name='shopping_items')
    op.drop_table('shopping_items')

    op.drop_table('application_state')

    op.drop_index('idx_assignment_chore', table_name='assignments')
    op.drop_index('idx_assignment_roommate', table_name='assignments')
    op.drop_table('assignments')

    op.drop_index('idx_subchore_chore_id', table_name='sub_chores')
    op.drop_table('sub_chores')

    op.drop_table('chores')

    op.drop_index('idx_roommate_google_id', table_name='roommates')
    op.drop_table('roommates')
