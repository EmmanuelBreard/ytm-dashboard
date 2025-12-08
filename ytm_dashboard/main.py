#!/usr/bin/env python3
"""
YTM Data Extraction - Main Orchestrator

Extracts Yield-to-Maturity data from all configured funds and stores in SQLite.

Usage:
    python main.py                    # Extract current month data
    python main.py --date 2024-11     # Extract specific month
    python main.py --fund carmignac_2027  # Extract single fund
    python main.py --dry-run          # Test without saving to DB
"""

import asyncio
import argparse
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from extractors.carmignac import CarmignacExtractor
from extractors.sycomore import SycomoreExtractor
from extractors.rothschild import RothschildExtractor
from config import FUND_CONFIG
from dashboard import generate_all_dashboards, generate_latest_dashboard


EXTRACTOR_MAP = {
    'carmignac': CarmignacExtractor,
    'sycomore': SycomoreExtractor,
    'rothschild': RothschildExtractor
}


async def extract_all_funds(report_date: str, fund_filter: str = None, dry_run: bool = False) -> tuple:
    """
    Extract YTM data for all configured funds

    Args:
        report_date: Target report date (YYYY-MM-01)
        fund_filter: Optional fund ID to extract only one fund
        dry_run: If True, don't save to database

    Returns:
        List of extraction results
    """
    # Initialize database
    db = DatabaseManager('data/ytm_data.db')
    if not dry_run:
        db.init_db()
    else:
        print("\n🔍 DRY RUN MODE - No data will be saved to database\n")

    results = []

    # Filter funds if requested
    funds_to_process = FUND_CONFIG
    if fund_filter:
        if fund_filter in FUND_CONFIG:
            funds_to_process = {fund_filter: FUND_CONFIG[fund_filter]}
        else:
            print(f"❌ Fund '{fund_filter}' not found in configuration")
            return []

    print("\n" + "="*60)
    print(f"YTM DATA EXTRACTION - {datetime.now().strftime('%B %Y')}")
    print("="*60)
    print(f"Report Date: {report_date}")
    print(f"Funds to process: {len(funds_to_process)}")
    print("="*60)

    # Process each fund
    for fund_id, config in funds_to_process.items():
        # Add fund_id to config
        config_with_id = config.copy()
        config_with_id['fund_id'] = fund_id

        # Get appropriate extractor
        extractor_class = EXTRACTOR_MAP[config['provider']]
        extractor = extractor_class(config_with_id)

        try:
            result = await extractor.extract(report_date)
            results.append(result)

            # Save to database if successful and not dry run
            if result['success'] and not dry_run:
                db.insert_ytm_record(result)
                print(f"💾 Saved to database")

        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                'fund_id': fund_id,
                'fund_name': config.get('fund_name'),
                'success': False,
                'error': str(e)
            })

    # Print summary
    print_summary(results)

    return results, report_date


def print_summary(results):
    """Print extraction summary"""
    print("\n" + "="*60)
    print("EXTRACTION SUMMARY")
    print("="*60)

    success_count = sum(1 for r in results if r.get('success'))

    for r in results:
        status = "✅" if r.get('success') else "❌"
        ytm = f"{r.get('yield_to_maturity')}%" if r.get('yield_to_maturity') else "N/A"
        fund_name = r.get('fund_name', r.get('fund_id', 'unknown'))
        print(f"{status} {fund_name:30s} {ytm:>7s}")
        if r.get('error'):
            print(f"    Error: {r['error']}")

    print(f"\n📊 Success rate: {success_count}/{len(results)}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Extract YTM data from bond funds',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                      # Extract current month for all funds
  python main.py --date 2024-11       # Extract November 2024 data
  python main.py --fund carmignac_2027 # Extract only Carmignac 2027
  python main.py --dry-run            # Test without saving
        """
    )

    parser.add_argument(
        '--date',
        help='Report date (YYYY-MM), defaults to current month',
        default=None
    )

    parser.add_argument(
        '--fund',
        help='Single fund ID to extract',
        default=None
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Test without saving to database'
    )

    parser.add_argument(
        '--list-funds',
        action='store_true',
        help='List all configured funds and exit'
    )

    parser.add_argument(
        '--no-dashboard',
        action='store_true',
        help='Skip automatic dashboard generation after extraction'
    )

    args = parser.parse_args()

    # List funds if requested
    if args.list_funds:
        print("\nConfigured Funds:")
        print("="*60)
        for fund_id, config in FUND_CONFIG.items():
            print(f"{fund_id:20s} - {config['fund_name']:30s} ({config['maturity']})")
        print("="*60)
        print(f"Total: {len(FUND_CONFIG)} funds")
        return

    # Determine report date
    if args.date:
        # Validate format
        try:
            datetime.strptime(args.date, '%Y-%m')
            report_date = f"{args.date}-01"
        except ValueError:
            print(f"❌ Invalid date format: {args.date}")
            print("   Expected format: YYYY-MM (e.g., 2024-11)")
            sys.exit(1)
    else:
        report_date = datetime.now().strftime('%Y-%m-01')

    # Run extraction
    try:
        results, report_date = asyncio.run(extract_all_funds(
            report_date=report_date,
            fund_filter=args.fund,
            dry_run=args.dry_run
        ))

        # Check if any extractions succeeded
        success_count = sum(1 for r in results if r.get('success'))

        # Regenerate dashboards if extraction succeeded and not in dry-run mode
        if success_count > 0 and not args.dry_run and not args.no_dashboard:
            print("\n" + "="*60)
            print("REGENERATING HTML DASHBOARDS")
            print("="*60)

            try:
                # Determine which dashboards to regenerate
                if args.fund:
                    # Single fund: just regenerate latest index.html
                    dashboard_success = generate_latest_dashboard(quiet=False)
                else:
                    # All funds: regenerate all historical dashboards + index
                    dashboard_success = generate_all_dashboards(quiet=False)

                if dashboard_success:
                    print("\n🌐 Dashboards updated successfully")
                else:
                    print("\n⚠️  Dashboard generation completed with errors")

            except Exception as e:
                # Dashboard failure shouldn't break extraction success
                print(f"\n⚠️  Warning: Dashboard generation failed: {e}")
                print("   (Extraction data was saved successfully)")

        elif args.dry_run:
            print("\n💡 Tip: Dashboards not regenerated (dry-run mode)")
        elif args.no_dashboard:
            print("\n💡 Tip: Dashboards not regenerated (--no-dashboard flag)")
        elif success_count == 0:
            print("\n⚠️  No successful extractions, skipping dashboard generation")

        # Exit with error code if all extractions failed
        if results and all(not r.get('success') for r in results):
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Extraction interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
