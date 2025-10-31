"""Add laundry_slot_id to pomodoro_sessions

Revision ID: 002_laundry_slot_pomodoro
Revises: 001_initial
Create Date: 2025-10-31

This migration adds support for linking Pomodoro sessions to laundry slots,
allowing users to track focus sessions while doing laundry.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_laundry_slot_pomodoro'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    """Add laundry_slot_id column to pomodoro_sessions table"""

    # Add the laundry_slot_id column
    op.add_column('pomodoro_sessions',
        sa.Column('laundry_slot_id', sa.Integer(), nullable=True)
    )

    # Add foreign key constraint to laundry_slots table
    op.create_foreign_key(
        'fk_pomodoro_sessions_laundry_slot_id',
        'pomodoro_sessions',
        'laundry_slots',
        ['laundry_slot_id'],
        ['id']
    )

    # Add index for better query performance
    op.create_index(
        'idx_pomodoro_laundry_slot',
        'pomodoro_sessions',
        ['laundry_slot_id']
    )


def downgrade():
    """Remove laundry_slot_id column from pomodoro_sessions table"""

    # Drop the index first
    op.drop_index('idx_pomodoro_laundry_slot', table_name='pomodoro_sessions')

    # Drop the foreign key constraint
    op.drop_constraint(
        'fk_pomodoro_sessions_laundry_slot_id',
        'pomodoro_sessions',
        type_='foreignkey'
    )

    # Drop the column
    op.drop_column('pomodoro_sessions', 'laundry_slot_id')
