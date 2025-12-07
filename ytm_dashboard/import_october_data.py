#!/usr/bin/env python3
"""
Import October 2025 data from PRD reference values
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from config import FUND_CONFIG

# October 2025 YTM values from PRD
OCTOBER_DATA = {
    'carmignac_2027': 3.90,
    'carmignac_2029': 4.60,
    'carmignac_2031': 5.10,
    'sycomore_2030': 4.90,
    'sycomore_2032': 4.90,
    'rothschild_2028': 2.85,  # R-co Target 2028 IG
    'rothschild_2029': 3.06,  # R-co Target 2029 IG
}

REPORT_DATE = '2025-10-01'

def import_october_data():
    """Import October 2025 reference data into database"""
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'ytm_data.db')
    db = DatabaseManager(db_path)

    print("=" * 60)
    print("IMPORTING OCTOBER 2025 DATA")
    print("=" * 60)

    imported = 0
    skipped = 0

    for fund_id, ytm in OCTOBER_DATA.items():
        if fund_id not in FUND_CONFIG:
            print(f"⚠️  {fund_id} not in config, skipping")
            skipped += 1
            continue

        fund = FUND_CONFIG[fund_id]

        # Check if already exists
        if db.record_exists(fund_id, REPORT_DATE):
            print(f"⏭️  {fund['fund_name']} - Already exists")
            skipped += 1
            continue

        record = {
            'fund_id': fund_id,
            'isin_code': fund.get('isin_code'),
            'fund_name': fund['fund_name'],
            'provider': fund['provider'],
            'fund_url': fund['url'],
            'fund_maturity': fund['maturity'],
            'yield_to_maturity': ytm,
            'report_date': REPORT_DATE,
            'source_type': 'manual',
            'source_document': 'product_requirement_document.md'
        }

        success = db.insert_ytm_record(record)
        if success:
            print(f"✅ {fund['fund_name']}: {ytm}%")
            imported += 1
        else:
            print(f"❌ Failed to import {fund['fund_name']}")

    print("=" * 60)
    print(f"✅ Imported: {imported}")
    print(f"⏭️  Skipped: {skipped}")
    print("=" * 60)

if __name__ == "__main__":
    import_october_data()
