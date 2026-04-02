"""Add prediction fields to shopping_items

Revision ID: 004_prediction_fields
Revises: 003_ml_tracking_fields
Create Date: 2025-11-12

This migration adds prediction fields to the shopping_items table to store
Phase 1 baseline predictor (Simple Moving Average) results. These fields enable
the app to display when items are predicted to run out.

New fields:
- predicted_depletion_date: When the ML model predicts the item will run out
- prediction_confidence: Confidence score (0-1) based on data quality
- prediction_model_version: Model identifier (e.g., "sma_v1", "ema_v1")
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_prediction_fields'
down_revision = '003_ml_tracking_fields'
branch_labels = None
depends_on = None


def upgrade():
    """Add prediction fields to shopping_items table"""

    # Add predicted_depletion_date (when item predicted to run out)
    op.add_column('shopping_items',
        sa.Column('predicted_depletion_date', sa.DateTime(), nullable=True,
                 comment='ML predicted date when item will run out')
    )

    # Add prediction_confidence (0-1 score based on data quality)
    op.add_column('shopping_items',
        sa.Column('prediction_confidence', sa.Float(), nullable=True,
                 comment='Prediction confidence score (0-1 range)')
    )

    # Add prediction_model_version (model identifier)
    op.add_column('shopping_items',
        sa.Column('prediction_model_version', sa.String(length=50), nullable=True,
                 server_default='sma_v1',
                 comment='Model version that generated the prediction (e.g., sma_v1)')
    )

    # Create index for efficient prediction queries
    op.create_index(
        'idx_shopping_predicted_depletion',
        'shopping_items',
        ['predicted_depletion_date'],
        postgresql_where=sa.text('predicted_depletion_date IS NOT NULL')
    )

    # Add check constraint for valid confidence scores (0-1 range)
    op.create_check_constraint(
        'ck_shopping_confidence_range',
        'shopping_items',
        'prediction_confidence IS NULL OR (prediction_confidence >= 0 AND prediction_confidence <= 1)'
    )


def downgrade():
    """Remove prediction fields from shopping_items table"""

    # Drop check constraint first
    op.drop_constraint('ck_shopping_confidence_range', 'shopping_items', type_='check')

    # Drop index
    op.drop_index('idx_shopping_predicted_depletion', table_name='shopping_items')

    # Drop columns
    op.drop_column('shopping_items', 'prediction_model_version')
    op.drop_column('shopping_items', 'prediction_confidence')
    op.drop_column('shopping_items', 'predicted_depletion_date')
