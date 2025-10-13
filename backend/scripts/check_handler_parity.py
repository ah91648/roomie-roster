#!/usr/bin/env python3
"""
Standalone script to check DataHandler and DatabaseDataHandler parity.

This script can be run in CI/CD pipelines to ensure API parity between
the JSON-based and database-based data handlers.

Usage:
    python scripts/check_handler_parity.py [--verbose] [--fail-on-missing]

Exit codes:
    0 - Full parity achieved
    1 - Missing methods detected
    2 - Signature mismatches detected
"""

import sys
import inspect
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from utils.data_handler import DataHandler
from utils.database_data_handler import DatabaseDataHandler


class ParityChecker:
    """Checks API parity between DataHandler and DatabaseDataHandler."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.data_handler_methods = self.get_public_methods(DataHandler)
        self.db_handler_methods = self.get_public_methods(DatabaseDataHandler)

    @staticmethod
    def get_public_methods(cls):
        """Get all public methods of a class."""
        methods = {}
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if not name.startswith('_'):
                methods[name] = method
        return methods

    @staticmethod
    def get_method_signature(method):
        """Get the signature of a method."""
        try:
            return str(inspect.signature(method))
        except (ValueError, TypeError):
            return None

    def check_missing_methods(self):
        """Check for methods missing from DatabaseDataHandler."""
        missing = []
        for method_name in self.data_handler_methods:
            if method_name not in self.db_handler_methods:
                missing.append(method_name)

        return sorted(missing)

    def check_signature_mismatches(self):
        """Check for methods with mismatched signatures."""
        mismatches = []

        for method_name in self.data_handler_methods:
            if method_name in self.db_handler_methods:
                dh_sig = self.get_method_signature(self.data_handler_methods[method_name])
                dbh_sig = self.get_method_signature(self.db_handler_methods[method_name])

                if dh_sig and dbh_sig and dh_sig != dbh_sig:
                    mismatches.append({
                        'method': method_name,
                        'expected': dh_sig,
                        'actual': dbh_sig
                    })

        return mismatches

    def check_extra_methods(self):
        """Check for extra methods in DatabaseDataHandler."""
        extra = []
        for method_name in self.db_handler_methods:
            if method_name not in self.data_handler_methods:
                extra.append(method_name)

        return sorted(extra)

    def generate_report(self, missing, mismatches, extra):
        """Generate a detailed parity report."""
        total = len(self.data_handler_methods)
        implemented = total - len(missing)
        completion_pct = (implemented / total * 100) if total > 0 else 0

        lines = []
        lines.append("=" * 80)
        lines.append("DATA HANDLER PARITY CHECK REPORT")
        lines.append("=" * 80)
        lines.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Summary
        lines.append("SUMMARY:")
        lines.append(f"  Total Methods:       {total}")
        lines.append(f"  Implemented:         {implemented} ({completion_pct:.1f}%)")
        lines.append(f"  Missing:             {len(missing)} ({100-completion_pct:.1f}%)")
        lines.append(f"  Signature Mismatches: {len(mismatches)}")
        lines.append(f"  Extra Methods:       {len(extra)}")
        lines.append("")

        # Progress bar
        bar_length = 50
        filled = int(completion_pct / 100 * bar_length)
        bar = '█' * filled + '░' * (bar_length - filled)
        lines.append(f"Completion: [{bar}] {completion_pct:.1f}%")
        lines.append("")

        # Status
        if len(missing) == 0 and len(mismatches) == 0:
            lines.append("✅ STATUS: FULL PARITY - All methods implemented with matching signatures")
        elif len(missing) > 0:
            lines.append(f"❌ STATUS: INCOMPLETE - {len(missing)} methods missing")
        elif len(mismatches) > 0:
            lines.append(f"⚠️  STATUS: SIGNATURE MISMATCH - {len(mismatches)} methods have different signatures")

        lines.append("=" * 80)
        lines.append("")

        # Missing methods
        if missing:
            lines.append(f"MISSING METHODS ({len(missing)}):")
            lines.append("")
            self._add_categorized_methods(lines, missing)
            lines.append("")

        # Signature mismatches
        if mismatches:
            lines.append(f"SIGNATURE MISMATCHES ({len(mismatches)}):")
            lines.append("")
            for mismatch in mismatches:
                lines.append(f"  Method: {mismatch['method']}")
                lines.append(f"    Expected: {mismatch['expected']}")
                lines.append(f"    Actual:   {mismatch['actual']}")
                lines.append("")

        # Extra methods (informational)
        if extra and self.verbose:
            lines.append(f"ADDITIONAL METHODS ({len(extra)}):")
            lines.append("  (These are extra methods not in DataHandler)")
            lines.append("")
            for method in extra:
                lines.append(f"  - {method}()")
            lines.append("")

        # Impact assessment
        if missing:
            lines.append("IMPACT ASSESSMENT:")
            lines.append("")
            lines.append(self._assess_impact(missing))
            lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)

    def _add_categorized_methods(self, lines, methods):
        """Add methods to report, grouped by category."""
        categories = {
            'Requests System': ['request'],
            'Laundry Scheduling': ['laundry'],
            'Blocked Time Slots': ['blocked'],
            'Shopping List': ['shopping'],
            'Sub-Chores': ['sub_chore'],
            'State Management': ['state', 'predefined', 'rotation'],
        }

        categorized = {cat: [] for cat in categories}
        categorized['Other'] = []

        for method in methods:
            assigned = False
            for cat, keywords in categories.items():
                if any(kw in method.lower() for kw in keywords):
                    categorized[cat].append(method)
                    assigned = True
                    break
            if not assigned:
                categorized['Other'].append(method)

        for cat, cat_methods in categorized.items():
            if cat_methods:
                lines.append(f"  {cat}:")
                for method in cat_methods:
                    sig = self.get_method_signature(self.data_handler_methods[method])
                    lines.append(f"    - {method}{sig}")
                lines.append("")

    def _assess_impact(self, missing):
        """Assess the impact of missing methods."""
        impact_map = {
            'Requests System': ['request'],
            'Laundry Scheduling': ['laundry'],
            'Blocked Time Slots': ['blocked'],
            'Shopping List': ['shopping'],
            'Sub-Chores': ['sub_chore'],
        }

        impacts = []
        for feature, keywords in impact_map.items():
            affected = [m for m in missing if any(kw in m.lower() for kw in keywords)]
            if affected:
                impacts.append(f"  ❌ {feature}: {len(affected)} methods missing - FEATURE BROKEN")

        return "\n".join(impacts) if impacts else "  ℹ️ No critical features affected"


def main():
    """Main entry point for the parity checker."""
    parser = argparse.ArgumentParser(
        description="Check API parity between DataHandler and DatabaseDataHandler"
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output including extra methods'
    )
    parser.add_argument(
        '--fail-on-missing',
        action='store_true',
        help='Exit with error code 1 if missing methods found'
    )
    parser.add_argument(
        '--fail-on-mismatch',
        action='store_true',
        help='Exit with error code 2 if signature mismatches found'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Write report to file instead of stdout'
    )

    args = parser.parse_args()

    # Run parity check
    checker = ParityChecker(verbose=args.verbose)
    missing = checker.check_missing_methods()
    mismatches = checker.check_signature_mismatches()
    extra = checker.check_extra_methods()

    # Generate report
    report = checker.generate_report(missing, mismatches, extra)

    # Output report
    if args.output:
        Path(args.output).write_text(report)
        print(f"Report written to: {args.output}")
    else:
        print(report)

    # Determine exit code
    exit_code = 0

    if missing and args.fail_on_missing:
        exit_code = 1
    elif mismatches and args.fail_on_mismatch:
        exit_code = 2

    if exit_code == 0 and not missing and not mismatches:
        print("\n✅ Parity check passed!")
    elif exit_code > 0:
        print(f"\n❌ Parity check failed with exit code {exit_code}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
