#!/usr/bin/env python3
"""
Test Carmignac PDF-based extraction
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extractors.carmignac import CarmignacExtractor
from config import FUND_CONFIG

async def test_carmignac_extraction():
    """Test Carmignac PDF extraction for all 3 funds"""

    print("=" * 60)
    print("TESTING CARMIGNAC PDF EXTRACTION")
    print("=" * 60 + "\n")

    # Test with October 2025 since that's the most recent data available
    report_date = "2025-10-01"
    print(f"Testing extraction for: {report_date}")
    print("=" * 60 + "\n")

    carmignac_funds = {
        'carmignac_2027': FUND_CONFIG['carmignac_2027'],
        'carmignac_2029': FUND_CONFIG['carmignac_2029'],
        'carmignac_2031': FUND_CONFIG['carmignac_2031'],
    }

    results = []

    for fund_id, fund_config in carmignac_funds.items():
        # Add fund_id to config
        config_with_id = fund_config.copy()
        config_with_id['fund_id'] = fund_id

        extractor = CarmignacExtractor(config_with_id)

        result = await extractor.extract(report_date)
        results.append(result)

        print(f"\nResult for {fund_config['fund_name']}:")
        print(f"  Success: {result['success']}")
        if result['success']:
            print(f"  YTM: {result['yield_to_maturity']}%")
            print(f"  Report Date: {result['report_date']}")
            print(f"  Source: {result.get('source_document', 'N/A')}")
        else:
            print(f"  Error: {result.get('error', 'Unknown error')}")

    print("\n" + "=" * 60)
    print(f"RESULTS: {sum(1 for r in results if r['success'])}/{len(results)} successful")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    asyncio.run(test_carmignac_extraction())
