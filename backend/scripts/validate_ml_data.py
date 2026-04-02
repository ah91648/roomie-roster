#!/usr/bin/env python3
"""
ML Data Validation Script
Validates that we have sufficient training data for the ML grocery prediction model.

Requirements for ML training:
- 60+ days of purchase/depletion history
- 80%+ items have quantity/unit data
- Multiple purchase instances per item (min 2 for training)
- Sufficient depletion events tracked
"""

import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.database_data_handler import DatabaseDataHandler
from dotenv import load_dotenv

load_dotenv()


class MLDataValidator:
    def __init__(self):
        self.handler = DatabaseDataHandler()
        self.validation_results = {
            'data_source': None,
            'total_items': 0,
            'items_with_quantity': 0,
            'items_with_unit': 0,
            'items_with_depletion': 0,
            'total_depletion_events': 0,
            'date_range_days': 0,
            'oldest_purchase_date': None,
            'newest_purchase_date': None,
            'items_with_multiple_purchases': 0,
            'avg_purchases_per_item': 0,
            'category_distribution': {},
            'unit_distribution': {},
            'data_quality_score': 0,
            'ml_ready': False,
            'issues': [],
            'recommendations': []
        }

    def validate(self):
        """Run all validation checks."""
        print("=" * 80)
        print("ML GROCERY PREDICTION - DATA VALIDATION REPORT")
        print("=" * 80)
        print()

        # Check data source
        self._check_data_source()

        # Validate shopping items
        self._validate_shopping_items()

        # Validate purchase history
        self._validate_purchase_history()

        # Validate depletion tracking
        self._validate_depletion_tracking()

        # Calculate data quality score
        self._calculate_quality_score()

        # Generate recommendations
        self._generate_recommendations()

        # Print summary
        self._print_summary()

        return self.validation_results

    def _check_data_source(self):
        """Check if using PostgreSQL or JSON fallback."""
        if os.getenv('DATABASE_URL'):
            self.validation_results['data_source'] = 'PostgreSQL'
            print("✅ Data source: PostgreSQL (production-ready)")
        else:
            self.validation_results['data_source'] = 'JSON'
            print("⚠️  Data source: JSON fallback (not recommended for ML)")
            self.validation_results['issues'].append("JSON mode loses data on container restart - use PostgreSQL for production ML")
        print()

    def _validate_shopping_items(self):
        """Validate shopping item data quality."""
        print("📊 SHOPPING ITEM DATA QUALITY")
        print("-" * 80)

        items = self.handler.get_shopping_list()
        self.validation_results['total_items'] = len(items)

        items_with_quantity = 0
        items_with_unit = 0
        items_with_depletion = 0
        category_counts = defaultdict(int)
        unit_counts = defaultdict(int)

        for item in items:
            # Check quantity field
            if item.get('quantity') is not None and item.get('quantity') > 0:
                items_with_quantity += 1

            # Check unit field
            if item.get('unit'):
                items_with_unit += 1
                unit_counts[item['unit']] += 1

            # Check depletion tracking
            if item.get('last_depleted_date') or item.get('typical_consumption_days'):
                items_with_depletion += 1

            # Category distribution
            category = item.get('category', 'Uncategorized')
            category_counts[category] += 1

        self.validation_results['items_with_quantity'] = items_with_quantity
        self.validation_results['items_with_unit'] = items_with_unit
        self.validation_results['items_with_depletion'] = items_with_depletion
        self.validation_results['category_distribution'] = dict(category_counts)
        self.validation_results['unit_distribution'] = dict(unit_counts)

        # Calculate percentages
        if self.validation_results['total_items'] > 0:
            qty_pct = (items_with_quantity / self.validation_results['total_items']) * 100
            unit_pct = (items_with_unit / self.validation_results['total_items']) * 100
            depl_pct = (items_with_depletion / self.validation_results['total_items']) * 100
        else:
            qty_pct = unit_pct = depl_pct = 0

        print(f"Total items: {self.validation_results['total_items']}")
        print(f"Items with quantity data: {items_with_quantity} ({qty_pct:.1f}%)")
        print(f"Items with unit data: {items_with_unit} ({unit_pct:.1f}%)")
        print(f"Items with depletion tracking: {items_with_depletion} ({depl_pct:.1f}%)")
        print()

        print(f"Category distribution: {len(category_counts)} categories")
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {category}: {count} items")
        if len(category_counts) > 5:
            print(f"  - ... and {len(category_counts) - 5} more")
        print()

        print(f"Unit distribution: {len(unit_counts)} units")
        for unit, count in sorted(unit_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {unit}: {count} items")
        if len(unit_counts) > 5:
            print(f"  - ... and {len(unit_counts) - 5} more")
        print()

        # Validation checks
        if qty_pct < 80:
            self.validation_results['issues'].append(f"Only {qty_pct:.1f}% of items have quantity data (target: 80%+)")

        if unit_pct < 80:
            self.validation_results['issues'].append(f"Only {unit_pct:.1f}% of items have unit data (target: 80%+)")

        if depl_pct < 20:
            self.validation_results['issues'].append(f"Only {depl_pct:.1f}% of items have depletion tracking (target: 80%+)")

    def _validate_purchase_history(self):
        """Validate purchase history depth and frequency."""
        print("📅 PURCHASE HISTORY ANALYSIS")
        print("-" * 80)

        # Get purchase history (last 90 days)
        try:
            purchase_history = self.handler.get_purchase_history(days=90)
        except Exception as e:
            print(f"❌ Error fetching purchase history: {e}")
            self.validation_results['issues'].append(f"Cannot fetch purchase history: {e}")
            return

        if not purchase_history:
            print("❌ No purchase history found")
            self.validation_results['issues'].append("No purchase history available - cannot train ML model")
            return

        # Analyze dates
        purchase_dates = []
        for purchase in purchase_history:
            if purchase.get('purchased_date'):
                try:
                    # Handle both string and datetime
                    if isinstance(purchase['purchased_date'], str):
                        date = datetime.fromisoformat(purchase['purchased_date'].replace('Z', '+00:00'))
                    else:
                        date = purchase['purchased_date']
                    purchase_dates.append(date)
                except Exception:
                    continue

        if purchase_dates:
            oldest = min(purchase_dates)
            newest = max(purchase_dates)
            date_range = (newest - oldest).days

            self.validation_results['oldest_purchase_date'] = oldest.isoformat()
            self.validation_results['newest_purchase_date'] = newest.isoformat()
            self.validation_results['date_range_days'] = date_range

            print(f"Purchase history date range: {date_range} days")
            print(f"Oldest purchase: {oldest.strftime('%Y-%m-%d')}")
            print(f"Newest purchase: {newest.strftime('%Y-%m-%d')}")
            print()

            if date_range < 60:
                self.validation_results['issues'].append(f"Only {date_range} days of purchase history (target: 60+ days)")
            else:
                print(f"✅ Sufficient date range for ML training ({date_range} days)")
        else:
            print("❌ No valid purchase dates found")
            self.validation_results['issues'].append("No valid purchase dates in history")
            return

        # Analyze purchase frequency per item
        item_purchases = defaultdict(list)
        for purchase in purchase_history:
            item_name = purchase.get('name', 'Unknown')
            if purchase.get('purchased_date'):
                item_purchases[item_name].append(purchase)

        items_with_multiple = sum(1 for purchases in item_purchases.values() if len(purchases) >= 2)
        avg_purchases = sum(len(purchases) for purchases in item_purchases.values()) / len(item_purchases) if item_purchases else 0

        self.validation_results['items_with_multiple_purchases'] = items_with_multiple
        self.validation_results['avg_purchases_per_item'] = avg_purchases

        print(f"Total unique items purchased: {len(item_purchases)}")
        print(f"Items with 2+ purchases: {items_with_multiple} ({(items_with_multiple/len(item_purchases)*100 if item_purchases else 0):.1f}%)")
        print(f"Average purchases per item: {avg_purchases:.2f}")
        print()

        # Show top repeat items
        top_repeat_items = sorted(item_purchases.items(), key=lambda x: len(x[1]), reverse=True)[:5]
        if top_repeat_items:
            print("Top repeat purchase items:")
            for item_name, purchases in top_repeat_items:
                print(f"  - {item_name}: {len(purchases)} purchases")
        print()

        if items_with_multiple < 10:
            self.validation_results['issues'].append(f"Only {items_with_multiple} items with 2+ purchases (need more for training)")

    def _validate_depletion_tracking(self):
        """Validate depletion event tracking."""
        print("🔔 DEPLETION TRACKING ANALYSIS")
        print("-" * 80)

        try:
            depletion_history = self.handler.get_depletion_history(days=90)
        except Exception as e:
            print(f"❌ Error fetching depletion history: {e}")
            self.validation_results['issues'].append(f"Cannot fetch depletion history: {e}")
            return

        if not depletion_history:
            print("❌ No depletion events tracked")
            self.validation_results['issues'].append("No depletion events - users need to mark items as depleted")
            print()
            print("RECOMMENDATION: Educate users to mark items as 'depleted' when they run out")
            print("This is CRITICAL for ML model accuracy!")
            print()
            return

        self.validation_results['total_depletion_events'] = len(depletion_history)

        print(f"Total depletion events: {len(depletion_history)}")

        # Analyze depletion feedback
        events_with_feedback = sum(1 for event in depletion_history if event.get('depletion_feedback'))
        if events_with_feedback > 0:
            print(f"Events with user feedback: {events_with_feedback} ({(events_with_feedback/len(depletion_history)*100):.1f}%)")

        # Analyze consumption patterns
        events_with_consumption_days = [e for e in depletion_history if e.get('typical_consumption_days')]
        if events_with_consumption_days:
            avg_consumption = sum(e['typical_consumption_days'] for e in events_with_consumption_days) / len(events_with_consumption_days)
            print(f"Average consumption period: {avg_consumption:.1f} days")

        print()

    def _calculate_quality_score(self):
        """Calculate overall data quality score (0-100)."""
        score = 0
        max_score = 100

        # Data source (20 points)
        if self.validation_results['data_source'] == 'PostgreSQL':
            score += 20
        else:
            score += 10

        # Item count (10 points)
        if self.validation_results['total_items'] >= 50:
            score += 10
        elif self.validation_results['total_items'] >= 20:
            score += 7
        elif self.validation_results['total_items'] >= 10:
            score += 5

        # Quantity/unit data completeness (20 points)
        if self.validation_results['total_items'] > 0:
            qty_pct = (self.validation_results['items_with_quantity'] / self.validation_results['total_items']) * 100
            unit_pct = (self.validation_results['items_with_unit'] / self.validation_results['total_items']) * 100
            score += int((qty_pct + unit_pct) / 2 * 0.2)

        # Date range (20 points)
        if self.validation_results['date_range_days'] >= 90:
            score += 20
        elif self.validation_results['date_range_days'] >= 60:
            score += 15
        elif self.validation_results['date_range_days'] >= 30:
            score += 10

        # Purchase frequency (15 points)
        if self.validation_results['items_with_multiple_purchases'] >= 20:
            score += 15
        elif self.validation_results['items_with_multiple_purchases'] >= 10:
            score += 10
        elif self.validation_results['items_with_multiple_purchases'] >= 5:
            score += 5

        # Depletion tracking (15 points)
        if self.validation_results['total_depletion_events'] >= 50:
            score += 15
        elif self.validation_results['total_depletion_events'] >= 20:
            score += 10
        elif self.validation_results['total_depletion_events'] >= 10:
            score += 5

        self.validation_results['data_quality_score'] = score
        self.validation_results['ml_ready'] = score >= 70

    def _generate_recommendations(self):
        """Generate actionable recommendations."""
        recommendations = []

        if self.validation_results['data_source'] == 'JSON':
            recommendations.append("🔧 Switch to PostgreSQL for production ML (data persists between deployments)")

        if self.validation_results['total_items'] < 20:
            recommendations.append("📦 Add more shopping items (target: 50+ items for robust training)")

        if self.validation_results['items_with_quantity'] / max(self.validation_results['total_items'], 1) < 0.8:
            recommendations.append("📊 Ensure users enter quantity + unit when adding items (target: 80%+)")

        if self.validation_results['date_range_days'] < 60:
            recommendations.append(f"⏰ Collect more historical data (need {60 - self.validation_results['date_range_days']} more days)")

        if self.validation_results['items_with_multiple_purchases'] < 10:
            recommendations.append("🔁 Encourage repeat purchases of common items (need 10+ items with 2+ purchases)")

        if self.validation_results['total_depletion_events'] < 20:
            recommendations.append("🔔 Educate users to mark items as 'depleted' when they run out (CRITICAL for accuracy)")

        if not recommendations:
            recommendations.append("✅ Data quality is good! Ready to proceed with ML model training")

        self.validation_results['recommendations'] = recommendations

    def _print_summary(self):
        """Print validation summary."""
        print()
        print("=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        print()

        print(f"Data Quality Score: {self.validation_results['data_quality_score']}/100")

        if self.validation_results['ml_ready']:
            print("✅ ML READY: Data quality is sufficient for model training")
        else:
            print("❌ NOT ML READY: Address issues below before training")

        print()

        if self.validation_results['issues']:
            print("⚠️  ISSUES FOUND:")
            for i, issue in enumerate(self.validation_results['issues'], 1):
                print(f"  {i}. {issue}")
            print()

        print("💡 RECOMMENDATIONS:")
        for i, rec in enumerate(self.validation_results['recommendations'], 1):
            print(f"  {i}. {rec}")
        print()

        print("=" * 80)


def main():
    """Main entry point."""
    validator = MLDataValidator()
    results = validator.validate()

    # Exit with appropriate code
    if results['ml_ready']:
        print("✅ Validation passed - ready for ML model development")
        sys.exit(0)
    else:
        print("❌ Validation failed - see recommendations above")
        sys.exit(1)


if __name__ == '__main__':
    main()
