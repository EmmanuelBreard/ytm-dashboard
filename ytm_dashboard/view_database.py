#!/usr/bin/env python3
"""
Simple database viewer
Usage: python3 view_database.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager

def main():
    db = DatabaseManager('data/ytm_data.db')

    print("\n" + "="*80)
    print("YTM DATABASE VIEWER")
    print("="*80)

    # Get all records
    all_records = db.get_all_records()

    print(f"\nTotal records: {len(all_records)}")

    if not all_records:
        print("\nDatabase is empty. Run 'python3 main.py' to extract data.")
        return

    # Show latest records for each fund
    print("\n" + "-"*80)
    print("LATEST YTM VALUES")
    print("-"*80)

    latest = db.get_latest_records()

    print(f"\n{'Fund Name':30s} {'Maturity'} {'YTM':>7s} {'Report Date':12s}")
    print("-"*80)

    for record in latest:
        print(f"{record['fund_name']:30s} "
              f"{record['fund_maturity']}    "
              f"{record['yield_to_maturity']:>6.2f}% "
              f"{record['report_date']}")

    # Show all records by date
    print("\n" + "-"*80)
    print("ALL RECORDS (by date)")
    print("-"*80)

    print(f"\n{'Date':12s} {'Fund Name':30s} {'YTM':>7s} {'Source':8s}")
    print("-"*80)

    for record in all_records:
        print(f"{record['report_date']:12s} "
              f"{record['fund_name']:30s} "
              f"{record['yield_to_maturity']:>6.2f}% "
              f"{record['source_type']:8s}")

    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
