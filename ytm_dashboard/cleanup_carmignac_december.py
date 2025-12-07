#!/usr/bin/env python3
"""
Delete premature Carmignac December 2025 data before refactoring extractor
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager

def cleanup_carmignac_december():
    """Delete Carmignac records for December 2025"""
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'ytm_data.db')
    db = DatabaseManager(db_path)

    print("=" * 60)
    print("CLEANUP: REMOVE PREMATURE CARMIGNAC DECEMBER DATA")
    print("=" * 60)

    conn = db._get_connection()
    cursor = conn.cursor()

    # Find records to delete
    cursor.execute("""
        SELECT fund_id, fund_name, report_date, yield_to_maturity
        FROM fund_ytm_data
        WHERE fund_id LIKE 'carmignac_%'
        AND report_date = '2025-12-01'
    """)

    records = cursor.fetchall()

    if not records:
        print("✅ No December 2025 Carmignac records found")
        conn.close()
        return

    print(f"\n📋 Found {len(records)} records to delete:\n")
    for record in records:
        fund_id, fund_name, report_date, ytm = record
        print(f"  - {fund_name} ({fund_id}): {ytm}% on {report_date}")

    # Delete records
    cursor.execute("""
        DELETE FROM fund_ytm_data
        WHERE fund_id LIKE 'carmignac_%'
        AND report_date = '2025-12-01'
    """)

    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()

    print(f"\n✅ Deleted {deleted_count} premature records")
    print("=" * 60)

if __name__ == "__main__":
    cleanup_carmignac_december()
