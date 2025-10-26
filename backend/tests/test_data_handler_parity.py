"""
Test suite to ensure DataHandler and DatabaseDataHandler maintain API parity.

This test ensures that DatabaseDataHandler implements all public methods from DataHandler
with matching signatures, preventing the 68% incompleteness issue that broke multiple features.
"""
import pytest
import inspect
import sys
from pathlib import Path

# Add parent directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from utils.data_handler import DataHandler
from utils.database_data_handler import DatabaseDataHandler


class TestDataHandlerParity:
    """Test suite ensuring DatabaseDataHandler maintains API parity with DataHandler."""

    @staticmethod
    def get_public_methods(cls):
        """Get all public methods of a class (excluding magic methods and private methods)."""
        methods = {}
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            # Skip private and magic methods
            if name.startswith('_'):
                continue
            methods[name] = method
        return methods

    @staticmethod
    def get_method_signature(method):
        """Get the signature of a method for comparison."""
        try:
            return str(inspect.signature(method))
        except (ValueError, TypeError):
            return None

    def test_all_datahandler_methods_implemented(self):
        """Verify that DatabaseDataHandler implements all public methods from DataHandler."""
        data_handler_methods = self.get_public_methods(DataHandler)
        db_handler_methods = self.get_public_methods(DatabaseDataHandler)

        missing_methods = []
        for method_name in data_handler_methods:
            if method_name not in db_handler_methods:
                missing_methods.append(method_name)

        if missing_methods:
            missing_count = len(missing_methods)
            total_count = len(data_handler_methods)
            percentage = (missing_count / total_count) * 100

            error_msg = f"\n\n{'='*80}\n"
            error_msg += f"DATABASE HANDLER PARITY ERROR\n"
            error_msg += f"{'='*80}\n\n"
            error_msg += f"DatabaseDataHandler is missing {missing_count}/{total_count} methods ({percentage:.1f}% incomplete)\n\n"
            error_msg += f"Missing methods:\n"
            for i, method in enumerate(sorted(missing_methods), 1):
                signature = self.get_method_signature(data_handler_methods[method])
                error_msg += f"  {i}. {method}{signature}\n"

            error_msg += f"\n{'='*80}\n"
            error_msg += f"IMPACT: The following features are broken:\n"
            error_msg += self._categorize_broken_features(missing_methods)
            error_msg += f"{'='*80}\n"

            pytest.fail(error_msg)

    def test_method_signatures_match(self):
        """Verify that implemented methods have matching signatures."""
        data_handler_methods = self.get_public_methods(DataHandler)
        db_handler_methods = self.get_public_methods(DatabaseDataHandler)

        signature_mismatches = []

        for method_name in data_handler_methods:
            if method_name in db_handler_methods:
                dh_sig = self.get_method_signature(data_handler_methods[method_name])
                dbh_sig = self.get_method_signature(db_handler_methods[method_name])

                if dh_sig and dbh_sig and dh_sig != dbh_sig:
                    signature_mismatches.append({
                        'method': method_name,
                        'expected': dh_sig,
                        'actual': dbh_sig
                    })

        if signature_mismatches:
            error_msg = f"\n\n{'='*80}\n"
            error_msg += f"METHOD SIGNATURE MISMATCHES\n"
            error_msg += f"{'='*80}\n\n"
            error_msg += f"Found {len(signature_mismatches)} methods with mismatched signatures:\n\n"

            for mismatch in signature_mismatches:
                error_msg += f"Method: {mismatch['method']}\n"
                error_msg += f"  Expected: {mismatch['expected']}\n"
                error_msg += f"  Actual:   {mismatch['actual']}\n\n"

            error_msg += f"{'='*80}\n"
            pytest.fail(error_msg)

    def test_productivity_methods_exist(self):
        """Verify that DatabaseDataHandler implements all 17 Zeith productivity methods."""
        db_handler_methods = self.get_public_methods(DatabaseDataHandler)

        # Expected productivity methods (Zeith transformation features)
        expected_productivity_methods = [
            # Pomodoro methods (6)
            'get_pomodoro_sessions',
            'get_active_pomodoro_session',
            'add_pomodoro_session',
            'update_pomodoro_session',
            'complete_pomodoro_session',
            'get_pomodoro_stats',
            # Todo methods (5)
            'get_todo_items',
            'add_todo_item',
            'update_todo_item',
            'delete_todo_item',
            'mark_todo_completed',
            # Mood methods (4)
            'get_mood_entries',
            'add_mood_entry',
            'update_mood_entry',
            'get_mood_trends',
            # Analytics methods (2)
            'get_analytics_snapshots',
            'add_analytics_snapshot',
        ]

        missing_productivity_methods = []
        for method_name in expected_productivity_methods:
            if method_name not in db_handler_methods:
                missing_productivity_methods.append(method_name)

        if missing_productivity_methods:
            error_msg = f"\n\n{'='*80}\n"
            error_msg += f"MISSING ZEITH PRODUCTIVITY METHODS\n"
            error_msg += f"{'='*80}\n\n"
            error_msg += f"DatabaseDataHandler is missing {len(missing_productivity_methods)}/17 Zeith productivity methods\n\n"
            error_msg += f"Missing methods:\n"
            for i, method in enumerate(sorted(missing_productivity_methods), 1):
                error_msg += f"  {i}. {method}()\n"
            error_msg += f"\n{'='*80}\n"
            pytest.fail(error_msg)
        else:
            print(f"\n✅ All 17 Zeith productivity methods are implemented in DatabaseDataHandler")

    def test_no_extra_methods(self):
        """Verify that DatabaseDataHandler doesn't have unexpected extra public methods."""
        data_handler_methods = self.get_public_methods(DataHandler)
        db_handler_methods = self.get_public_methods(DatabaseDataHandler)

        # Known extra methods (Zeith productivity features)
        expected_extra_methods = {
            'get_pomodoro_sessions', 'get_active_pomodoro_session', 'add_pomodoro_session',
            'update_pomodoro_session', 'complete_pomodoro_session', 'get_pomodoro_stats',
            'get_todo_items', 'add_todo_item', 'update_todo_item', 'delete_todo_item',
            'mark_todo_completed', 'get_mood_entries', 'add_mood_entry', 'update_mood_entry',
            'get_mood_trends', 'get_analytics_snapshots', 'add_analytics_snapshot'
        }

        extra_methods = []
        unexpected_extra_methods = []
        for method_name in db_handler_methods:
            if method_name not in data_handler_methods:
                extra_methods.append(method_name)
                if method_name not in expected_extra_methods:
                    unexpected_extra_methods.append(method_name)

        # Extra methods are informational, not an error
        if extra_methods:
            print(f"\nINFO: DatabaseDataHandler has {len(extra_methods)} additional methods:")
            print(f"  - Expected (Zeith productivity): {len(expected_extra_methods)}")
            print(f"  - Unexpected: {len(unexpected_extra_methods)}")
            if unexpected_extra_methods:
                print(f"\nUnexpected extra methods:")
                for method in sorted(unexpected_extra_methods):
                    print(f"  - {method}")

    def test_parity_report_generation(self):
        """Generate a comprehensive parity report for documentation."""
        data_handler_methods = self.get_public_methods(DataHandler)
        db_handler_methods = self.get_public_methods(DatabaseDataHandler)

        report = self._generate_parity_report(data_handler_methods, db_handler_methods)

        # Write report to file
        report_path = backend_dir / "docs" / "DATA_HANDLER_PARITY.md"
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(report)

        print(f"\nParity report generated: {report_path}")

    @staticmethod
    def _categorize_broken_features(missing_methods):
        """Categorize missing methods into feature categories."""
        categories = {
            'Requests System': [
                'get_requests', 'save_requests', 'get_next_request_id',
                'add_request', 'update_request', 'delete_request',
                'approve_request', 'get_requests_by_status',
                'get_pending_requests_for_user', 'get_requests_metadata'
            ],
            'Laundry Scheduling': [
                'get_laundry_slots', 'save_laundry_slots', 'get_next_laundry_slot_id',
                'add_laundry_slot', 'update_laundry_slot', 'delete_laundry_slot',
                'get_laundry_slots_by_date', 'get_laundry_slots_by_roommate',
                'get_laundry_slots_by_status', 'check_laundry_slot_conflicts',
                'mark_laundry_slot_completed', 'get_laundry_slots_metadata'
            ],
            'Blocked Time Slots': [
                'get_blocked_time_slots', 'save_blocked_time_slots', 'get_next_blocked_slot_id',
                'add_blocked_time_slot', 'update_blocked_time_slot', 'delete_blocked_time_slot',
                'get_blocked_time_slots_by_date', 'check_blocked_time_conflicts',
                'is_time_slot_blocked'
            ],
            'Shopping List': [
                'save_shopping_list', 'get_next_shopping_item_id',
                'update_shopping_item', 'delete_shopping_item',
                'mark_item_purchased', 'get_purchase_history',
                'clear_all_purchase_history', 'clear_purchase_history_from_date',
                'get_shopping_list_metadata'
            ],
            'Sub-Chores': [
                'get_next_sub_chore_id', 'add_sub_chore', 'update_sub_chore',
                'delete_sub_chore', 'toggle_sub_chore_completion'
            ],
            'State Management': [
                'update_predefined_chore_state', 'update_global_predefined_rotation'
            ]
        }

        impact = ""
        for category, methods in categories.items():
            missing_in_category = [m for m in methods if m in missing_methods]
            if missing_in_category:
                status = "BROKEN" if len(missing_in_category) > len(methods) / 2 else "PARTIAL"
                impact += f"  - [{status}] {category}: {len(missing_in_category)}/{len(methods)} methods missing\n"

        return impact if impact else "  - No major features identified\n"

    @staticmethod
    def _generate_parity_report(dh_methods, dbh_methods):
        """Generate a markdown report of handler parity status."""
        from datetime import datetime

        missing = sorted([m for m in dh_methods if m not in dbh_methods])
        implemented = sorted([m for m in dh_methods if m in dbh_methods])
        extra = sorted([m for m in dbh_methods if m not in dh_methods])

        total = len(dh_methods)
        impl_count = len(implemented)
        missing_count = len(missing)
        completion_pct = (impl_count / total * 100) if total > 0 else 0

        report = f"""# Data Handler Parity Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

- **Total Methods in DataHandler:** {total}
- **Implemented in DatabaseDataHandler:** {impl_count} ({completion_pct:.1f}%)
- **Missing from DatabaseDataHandler:** {missing_count} ({100-completion_pct:.1f}%)
- **Extra Methods in DatabaseDataHandler:** {len(extra)}

## Parity Status

```
{'█' * int(completion_pct/5)}{'░' * (20-int(completion_pct/5))} {completion_pct:.1f}% Complete
```

## Implemented Methods ✅

The following {impl_count} methods are implemented:

"""
        for i, method in enumerate(implemented, 1):
            report += f"{i}. `{method}()`\n"

        if missing:
            report += f"\n## Missing Methods ❌\n\n"
            report += f"The following {missing_count} methods need to be implemented:\n\n"

            # Group by feature
            categories = {
                'Requests': ['request'],
                'Laundry': ['laundry'],
                'Blocked Time': ['blocked'],
                'Shopping': ['shopping'],
                'Sub-Chores': ['sub_chore'],
                'State': ['state', 'predefined', 'rotation'],
                'Other': []
            }

            categorized = {cat: [] for cat in categories}
            for method in missing:
                categorized_flag = False
                for cat, keywords in categories.items():
                    if cat == 'Other':
                        continue
                    if any(kw in method.lower() for kw in keywords):
                        categorized[cat].append(method)
                        categorized_flag = True
                        break
                if not categorized_flag:
                    categorized['Other'].append(method)

            for cat, methods in categorized.items():
                if methods:
                    report += f"\n### {cat} Methods\n\n"
                    for method in methods:
                        report += f"- [ ] `{method}()`\n"

        if extra:
            report += f"\n## Additional Methods ℹ️\n\n"
            report += f"DatabaseDataHandler has {len(extra)} additional methods not in DataHandler:\n\n"
            for method in extra:
                report += f"- `{method}()`\n"

        report += f"\n## Recommendations\n\n"
        if missing_count > 0:
            report += f"1. **Priority High:** Implement the {missing_count} missing methods to restore full functionality\n"
            report += f"2. **Add Unit Tests:** Create tests for each implemented method\n"
            report += f"3. **CI/CD Integration:** Run this parity check in your CI pipeline\n"
        else:
            report += f"1. ✅ Full parity achieved! All methods are implemented.\n"
            report += f"2. **Maintain Parity:** Run parity checks in CI/CD to prevent regression\n"
            report += f"3. **Add Unit Tests:** Ensure test coverage for all methods\n"

        report += f"\n---\n\n"
        report += f"*This report is automatically generated by `test_data_handler_parity.py`*\n"

        return report


if __name__ == "__main__":
    """Run parity check as standalone script."""
    print("Running Data Handler Parity Check...")
    print("=" * 80)

    test = TestDataHandlerParity()

    try:
        test.test_all_datahandler_methods_implemented()
        print("✅ All methods implemented")
    except AssertionError as e:
        print(str(e))

    try:
        test.test_method_signatures_match()
        print("✅ All signatures match")
    except AssertionError as e:
        print(str(e))

    test.test_no_extra_methods()
    test.test_parity_report_generation()

    print("=" * 80)
    print("Parity check complete!")
