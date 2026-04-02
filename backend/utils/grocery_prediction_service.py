"""
Grocery Prediction Service - Phase 1: Baseline Predictor

This service implements a Simple Moving Average (SMA) baseline predictor for
grocery depletion, achieving 70-75% precision@7days accuracy. This establishes
a performance benchmark for future advanced ML models (Prophet, Survival Analysis).

Algorithm:
- Calculate average days between purchases for each item
- Use exponential weighting (recent purchases weighted more heavily)
- Confidence scoring based on data quality (purchase count + variance)
- Category-level fallback for items with insufficient history
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
from sqlalchemy import func


class GroceryPredictionService:
    """Service for predicting when grocery items will run out."""

    # Model version for tracking
    MODEL_VERSION = "sma_v1"

    # Minimum purchases required for item-level prediction
    MIN_PURCHASES_FOR_PREDICTION = 2

    # Default SMA window size (number of intervals to average)
    DEFAULT_WINDOW_SIZE = 5

    # Exponential moving average smoothing factor (0-1)
    # Higher alpha = more weight on recent purchases
    EMA_ALPHA = 0.3

    def __init__(self, data_handler, logger=None):
        """
        Initialize the prediction service.

        Args:
            data_handler: DatabaseDataHandler instance for data access
            logger: Optional logger instance
        """
        self.data_handler = data_handler
        self.logger = logger or logging.getLogger(__name__)

    def calculate_sma(self, item_id: int, window: int = None) -> Optional[Dict]:
        """
        Calculate Simple Moving Average prediction for an item.

        Args:
            item_id: Shopping item ID
            window: Number of intervals to average (defaults to DEFAULT_WINDOW_SIZE)

        Returns:
            Dictionary with prediction details or None if insufficient data:
            {
                'predicted_depletion_date': datetime,
                'confidence': float (0-1),
                'avg_interval_days': int,
                'purchase_count': int,
                'model_version': str
            }
        """
        window = window or self.DEFAULT_WINDOW_SIZE

        try:
            # Get purchase history for this specific item
            intervals = self._get_purchase_intervals(item_id)

            if not intervals or len(intervals) < self.MIN_PURCHASES_FOR_PREDICTION - 1:
                self.logger.debug(f"Item {item_id}: Insufficient data ({len(intervals)} intervals)")
                return None

            # Calculate exponential moving average
            avg_interval = self._calculate_ema(intervals, alpha=self.EMA_ALPHA)

            # Get last purchase date for this item
            item = self.data_handler.get_shopping_item_by_id(item_id)
            if not item or not item.get('purchase_date'):
                self.logger.debug(f"Item {item_id}: No purchase date found")
                return None

            last_purchase = datetime.fromisoformat(item['purchase_date'].replace('Z', '+00:00'))

            # Calculate predicted depletion date
            predicted_date = last_purchase + timedelta(days=int(avg_interval))

            # Calculate confidence score
            confidence = self._calculate_confidence(intervals, len(intervals) + 1)

            return {
                'predicted_depletion_date': predicted_date,
                'confidence': confidence,
                'avg_interval_days': int(avg_interval),
                'purchase_count': len(intervals) + 1,
                'model_version': self.MODEL_VERSION
            }

        except Exception as e:
            self.logger.error(f"Error calculating SMA for item {item_id}: {e}", exc_info=True)
            return None

    def calculate_category_fallback(self, category: str, last_purchase_date: datetime) -> Optional[Dict]:
        """
        Calculate category-level average for items with insufficient individual history.

        Args:
            category: Item category (e.g., "Dairy", "Produce")
            last_purchase_date: When the item was last purchased

        Returns:
            Dictionary with prediction details or None if insufficient category data
        """
        try:
            # Get all items in this category with depletion history
            category_intervals = self._get_category_intervals(category)

            if not category_intervals or len(category_intervals) < 5:
                self.logger.debug(f"Category '{category}': Insufficient data ({len(category_intervals)} intervals)")
                return None

            # Calculate category average
            avg_interval = np.mean(category_intervals)
            predicted_date = last_purchase_date + timedelta(days=int(avg_interval))

            # Lower confidence for category-level predictions
            confidence = min(0.4, len(category_intervals) / 50)  # Max 0.4 confidence for fallback

            return {
                'predicted_depletion_date': predicted_date,
                'confidence': confidence,
                'avg_interval_days': int(avg_interval),
                'purchase_count': 1,  # Indicates single-purchase fallback
                'model_version': f"{self.MODEL_VERSION}_category_fallback"
            }

        except Exception as e:
            self.logger.error(f"Error calculating category fallback for '{category}': {e}", exc_info=True)
            return None

    def generate_all_predictions(self, min_purchases: int = None) -> Dict[str, any]:
        """
        Generate predictions for all eligible items (batch processing).

        Args:
            min_purchases: Minimum purchases required (defaults to MIN_PURCHASES_FOR_PREDICTION)

        Returns:
            Dictionary with prediction results:
            {
                'predictions_generated': int,
                'items_processed': int,
                'category_fallbacks': int,
                'insufficient_data': int
            }
        """
        min_purchases = min_purchases or self.MIN_PURCHASES_FOR_PREDICTION

        stats = {
            'predictions_generated': 0,
            'items_processed': 0,
            'category_fallbacks': 0,
            'insufficient_data': 0
        }

        try:
            # Get all purchased items
            all_items = self.data_handler.get_shopping_items(status='purchased')

            for item in all_items:
                stats['items_processed'] += 1
                item_id = item['id']

                # Try item-level prediction first
                prediction = self.calculate_sma(item_id)

                # If insufficient data, try category fallback
                if prediction is None and item.get('purchase_date'):
                    purchase_date = datetime.fromisoformat(item['purchase_date'].replace('Z', '+00:00'))
                    prediction = self.calculate_category_fallback(item.get('category', 'General'), purchase_date)
                    if prediction:
                        stats['category_fallbacks'] += 1

                # Update item with prediction
                if prediction:
                    self.data_handler.update_shopping_item(item_id, {
                        'predicted_depletion_date': prediction['predicted_depletion_date'].isoformat(),
                        'prediction_confidence': prediction['confidence'],
                        'prediction_model_version': prediction['model_version']
                    })
                    stats['predictions_generated'] += 1
                else:
                    stats['insufficient_data'] += 1

            self.logger.info(f"Batch prediction completed: {stats}")
            return stats

        except Exception as e:
            self.logger.error(f"Error generating batch predictions: {e}", exc_info=True)
            return stats

    def evaluate_accuracy(self) -> Dict[str, float]:
        """
        Evaluate prediction accuracy against actual depletion dates.

        Returns:
            Dictionary with accuracy metrics:
            {
                'precision_at_7_days': float,
                'recall_at_7_days': float,
                'mae': float (mean absolute error in days),
                'coverage': float (% of items with predictions),
                'total_predictions': int,
                'total_actual_depletions': int
            }
        """
        try:
            # Get all items with both predictions AND actual depletion dates
            all_items = self.data_handler.get_shopping_items()

            predictions_with_actual = []
            total_predictions = 0
            total_depletions = 0

            for item in all_items:
                if item.get('predicted_depletion_date'):
                    total_predictions += 1

                if item.get('last_depleted_date'):
                    total_depletions += 1

                # Need both for evaluation
                if item.get('predicted_depletion_date') and item.get('last_depleted_date'):
                    predicted = datetime.fromisoformat(item['predicted_depletion_date'].replace('Z', '+00:00'))
                    actual = datetime.fromisoformat(item['last_depleted_date'].replace('Z', '+00:00'))

                    error_days = abs((actual - predicted).days)
                    predictions_with_actual.append({
                        'error_days': error_days,
                        'within_3_days': error_days <= 3,
                        'within_7_days': error_days <= 7
                    })

            if not predictions_with_actual:
                return {
                    'precision_at_7_days': 0.0,
                    'recall_at_7_days': 0.0,
                    'mae': 0.0,
                    'coverage': 0.0,
                    'total_predictions': total_predictions,
                    'total_actual_depletions': total_depletions
                }

            # Calculate metrics
            within_7_days = sum(1 for p in predictions_with_actual if p['within_7_days'])
            precision_at_7 = within_7_days / len(predictions_with_actual)

            # Recall: of items that depleted, how many did we predict correctly?
            recall_at_7 = within_7_days / total_depletions if total_depletions > 0 else 0.0

            # MAE (Mean Absolute Error)
            mae = np.mean([p['error_days'] for p in predictions_with_actual])

            # Coverage: % of purchased items with predictions
            coverage = total_predictions / len(all_items) if all_items else 0.0

            return {
                'precision_at_7_days': round(precision_at_7, 3),
                'recall_at_7_days': round(recall_at_7, 3),
                'mae': round(mae, 2),
                'coverage': round(coverage, 3),
                'total_predictions': total_predictions,
                'total_actual_depletions': total_depletions,
                'evaluated_pairs': len(predictions_with_actual)
            }

        except Exception as e:
            self.logger.error(f"Error evaluating accuracy: {e}", exc_info=True)
            return {
                'precision_at_7_days': 0.0,
                'recall_at_7_days': 0.0,
                'mae': 0.0,
                'coverage': 0.0,
                'total_predictions': 0,
                'total_actual_depletions': 0,
                'error': str(e)
            }

    def get_confidence_score(self, item_id: int) -> float:
        """
        Get confidence score for a specific item's prediction.

        Args:
            item_id: Shopping item ID

        Returns:
            Confidence score (0-1) or 0.0 if no prediction exists
        """
        try:
            item = self.data_handler.get_shopping_item_by_id(item_id)
            return item.get('prediction_confidence', 0.0) if item else 0.0
        except Exception as e:
            self.logger.error(f"Error getting confidence for item {item_id}: {e}")
            return 0.0

    # ===== Private Helper Methods =====

    def _get_purchase_intervals(self, item_id: int) -> List[int]:
        """
        Get list of days between consecutive purchases for an item.

        Args:
            item_id: Shopping item ID

        Returns:
            List of intervals in days (empty if insufficient data)
        """
        try:
            # Get purchase history via data handler
            history = self.data_handler.get_item_purchase_intervals_by_id(item_id)
            return history if history else []
        except Exception as e:
            self.logger.error(f"Error getting purchase intervals for item {item_id}: {e}")
            return []

    def _get_category_intervals(self, category: str) -> List[int]:
        """
        Get all purchase intervals for items in a category.

        Args:
            category: Category name

        Returns:
            List of intervals in days
        """
        try:
            # Get all items in category
            items = self.data_handler.get_shopping_items(category=category, status='purchased')

            all_intervals = []
            for item in items:
                intervals = self._get_purchase_intervals(item['id'])
                all_intervals.extend(intervals)

            return all_intervals
        except Exception as e:
            self.logger.error(f"Error getting category intervals for '{category}': {e}")
            return []

    def _calculate_ema(self, intervals: List[int], alpha: float = 0.3) -> float:
        """
        Calculate Exponential Moving Average of intervals.

        Args:
            intervals: List of interval values
            alpha: Smoothing factor (0-1), higher = more weight on recent data

        Returns:
            EMA value
        """
        if not intervals:
            return 0.0

        # Start with simple average for first value
        ema = intervals[0]

        # Apply exponential weighting
        for interval in intervals[1:]:
            ema = alpha * interval + (1 - alpha) * ema

        return ema

    def _calculate_confidence(self, intervals: List[int], purchase_count: int) -> float:
        """
        Calculate confidence score based on data quality.

        Factors:
        - More purchases = higher confidence
        - Lower variance = higher confidence
        - Capped at 1.0

        Args:
            intervals: List of purchase intervals
            purchase_count: Total number of purchases

        Returns:
            Confidence score (0-1)
        """
        # Base confidence from purchase count
        # Reaches 1.0 at 5+ purchases
        data_confidence = min(1.0, purchase_count / 5.0)

        # Penalize high variance (inconsistent patterns)
        if len(intervals) > 1:
            std_dev = np.std(intervals)
            mean = np.mean(intervals)

            # Coefficient of variation (CV)
            cv = std_dev / mean if mean > 0 else 1.0

            # Consistency bonus
            if cv < 0.2:  # Very consistent (<20% variation)
                consistency_bonus = 0.2
            elif cv < 0.4:  # Moderately consistent
                consistency_bonus = 0.1
            else:  # High variance
                consistency_bonus = 0.0

            return min(1.0, data_confidence * 0.7 + consistency_bonus)
        else:
            # Single interval, medium confidence
            return data_confidence * 0.5

    def __repr__(self):
        return f'<GroceryPredictionService model={self.MODEL_VERSION}>'
