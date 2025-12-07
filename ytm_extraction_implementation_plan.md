# YTM Data Extraction & SQLite Storage - Implementation Plan

## Overview

Build a unified Python script that:
1. Extracts Yield-to-Maturity (YTM) data from 7 target-maturity bond funds across 3 providers
2. Stores the data in a SQLite database
3. Supports monthly execution to build historical data

## Database Schema

### SQLite Database: `ytm_data.db`

```sql
-- Main table for YTM records
CREATE TABLE IF NOT EXISTS fund_ytm_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id TEXT NOT NULL,           -- Unique identifier (e.g., "carmignac_2027")
    isin_code TEXT,                  -- ISIN code if available
    fund_name TEXT NOT NULL,         -- Display name (e.g., "Carmignac Crédit 2027")
    provider TEXT NOT NULL,          -- "carmignac", "sycomore", "rothschild"
    fund_url TEXT NOT NULL,          -- Source URL
    fund_maturity INTEGER NOT NULL,  -- Target year (e.g., 2027, 2029, 2031)
    yield_to_maturity REAL,          -- YTM as decimal (e.g., 4.90 for 4.90%)
    report_date DATE NOT NULL,       -- Month of the data (YYYY-MM-01)
    extraction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_type TEXT,                -- "web" or "pdf"
    source_document TEXT,            -- Path to PDF if applicable
    UNIQUE(fund_id, report_date)     -- One entry per fund per month
);

-- Index for efficient queries
CREATE INDEX IF NOT EXISTS idx_fund_date ON fund_ytm_data(fund_id, report_date);
CREATE INDEX IF NOT EXISTS idx_report_date ON fund_ytm_data(report_date);
```

## Fund Configuration

```python
FUND_CONFIG = {
    # Carmignac funds (web extraction)
    "carmignac_2027": {
        "provider": "carmignac",
        "fund_name": "Carmignac Crédit 2027",
        "isin_code": "FR00140081Y1",
        "maturity": 2027,
        "url": "https://www.carmignac.com/fr-fr/nos-fonds-notre-gestion/carmignac-credit-2027-FR00140081Y1-a-eur-acc",
        "source_type": "web"
    },
    "carmignac_2029": {
        "provider": "carmignac",
        "fund_name": "Carmignac Crédit 2029",
        "isin_code": "FR001400KAV4",
        "maturity": 2029,
        "url": "https://www.carmignac.com/en/our-funds/carmignac-credit-2029-FR001400KAV4-a-eur-acc/documents",
        "source_type": "web"
    },
    "carmignac_2031": {
        "provider": "carmignac",
        "fund_name": "Carmignac Crédit 2031",
        "isin_code": "FR001400U4S3",
        "maturity": 2031,
        "url": "https://www.carmignac.com/fr-fr/nos-fonds-notre-gestion/carmignac-credit-2031-FR001400U4S3-a-eur-acc",
        "source_type": "web"
    },
    
    # Sycomore funds (PDF extraction)
    "sycomore_2030": {
        "provider": "sycomore",
        "fund_name": "Sycoyield 2030",
        "isin_code": None,  # Add if known
        "maturity": 2030,
        "url": "https://fr.sycomore-am.com/fonds/53/sycoyield-2030/169",
        "source_type": "pdf"
    },
    "sycomore_2032": {
        "provider": "sycomore",
        "fund_name": "Sycoyield 2032",
        "isin_code": None,
        "maturity": 2032,
        "url": "https://fr.sycomore-am.com/fonds/58/sycoyield-2032/187",
        "source_type": "pdf"
    },
    
    # Rothschild funds (PDF extraction)
    "rothschild_2028": {
        "provider": "rothschild",
        "fund_name": "R-co Target 2028 IG",
        "isin_code": None,
        "maturity": 2028,
        "url": "https://am.eu.rothschildandco.com/fr/nos-fonds/r-co-target-2028-ig/",
        "source_type": "pdf"
    },
    "rothschild_2029": {
        "provider": "rothschild",
        "fund_name": "R-co Target 2029 IG",
        "isin_code": None,
        "maturity": 2029,
        "url": "https://am.eu.rothschildandco.com/en/our-funds/r-co-target-2029-ig/",
        "source_type": "pdf"
    }
}
```

## Project Structure

```
ytm_dashboard/
├── main.py                      # Entry point - orchestrates all extractions
├── database.py                  # SQLite operations
├── extractors/
│   ├── __init__.py
│   ├── base.py                  # Abstract base class for extractors
│   ├── carmignac.py             # Carmignac web extractor (from existing code)
│   ├── sycomore.py              # Sycomore PDF downloader + YTM extractor
│   └── rothschild.py            # Rothschild PDF downloader + YTM extractor
├── pdf_utils/
│   ├── __init__.py
│   └── ytm_extractor.py         # PDF YTM extraction logic (pdfplumber)
├── config.py                    # Fund configurations and settings
├── reports/                     # Downloaded PDF reports (gitignored)
├── data/
│   └── ytm_data.db              # SQLite database
└── requirements.txt
```

---

## Implementation Phases

### Phase 1: Database Layer (`database.py`)

**Tasks:**
1. Create SQLite database with schema above
2. Implement `DatabaseManager` class with methods:
   - `init_db()` - Create tables if not exist
   - `insert_ytm_record(record: dict)` - Insert/update a single record
   - `get_latest_records()` - Get most recent data for all funds
   - `get_records_by_date(report_date)` - Get all records for a specific month
   - `get_fund_history(fund_id)` - Get historical data for one fund
   - `record_exists(fund_id, report_date)` - Check if data already exists

**Key considerations:**
- Use `INSERT OR REPLACE` for upsert behavior based on unique constraint
- Store dates as ISO format strings (YYYY-MM-01)
- Keep report PDFs paths relative for portability

**Validation:**
```python
# Test: Create DB, insert sample record, query it back
python -c "
from database import DatabaseManager
db = DatabaseManager('data/ytm_data.db')
db.init_db()
db.insert_ytm_record({
    'fund_id': 'test_fund',
    'fund_name': 'Test Fund',
    'provider': 'test',
    'fund_url': 'https://example.com',
    'fund_maturity': 2030,
    'yield_to_maturity': 4.5,
    'report_date': '2024-11-01',
    'source_type': 'test'
})
print(db.get_latest_records())
"
```

---

### Phase 2: PDF YTM Extractor (`pdf_utils/ytm_extractor.py`)

**Tasks:**
1. Create `extract_ytm_from_pdf(pdf_path: str, provider: str) -> dict`
2. Handle provider-specific patterns:

**Sycomore pattern (French):**
```
"Rendement à maturité** 4,9%"
# or
"Rendement à maturité 4,9%"
```
Regex: `r"Rendement\s+(?:à|a)\s+maturit[ée]\**\s*(\d+[,\.]\d+)\s*%"`

**Rothschild pattern (French/English):**
```
"Yield to Maturity: 3.06%"
# or  
"Rendement actuariel : 2,85%"
```
Regex: `r"(?:Yield\s+to\s+Maturity|Rendement\s+actuariel)\s*[:\s]+(\d+[,\.]\d+)\s*%"`

**Implementation:**
```python
import pdfplumber
import re
from typing import Optional, Dict

def extract_ytm_from_pdf(pdf_path: str, provider: str) -> Dict:
    """
    Extract YTM from PDF report
    
    Returns:
        {
            'yield_to_maturity': float or None,
            'report_date': str or None,  # Extracted from PDF if possible
            'raw_text_match': str,        # For debugging
            'success': bool,
            'error': str or None
        }
    """
    patterns = {
        'sycomore': [
            r"Rendement\s+(?:à|a)\s+maturit[ée]\**\s*(\d+[,\.]\d+)\s*%",
            r"YTM\s*[:\s]+(\d+[,\.]\d+)\s*%"
        ],
        'rothschild': [
            r"(?:Yield\s+to\s+Maturity|YTM)\s*[:\s]+(\d+[,\.]\d+)\s*%",
            r"Rendement\s+(?:actuariel|à\s+maturité)\s*[:\s]+(\d+[,\.]\d+)\s*%"
        ]
    }
    
    # Extract text from all pages
    # Search for pattern matches
    # Parse French number format (comma as decimal separator)
    # Return structured result
```

**Validation:**
```bash
# Test with existing Sycomore PDF
python -c "
from pdf_utils.ytm_extractor import extract_ytm_from_pdf
result = extract_ytm_from_pdf('reports/sycoyield_2030_report_202411.pdf', 'sycomore')
print(f'YTM: {result[\"yield_to_maturity\"]}%')
# Expected: 4.9
"
```

---

### Phase 3: Base Extractor Class (`extractors/base.py`)

**Tasks:**
1. Create abstract base class defining interface:

```python
from abc import ABC, abstractmethod
from typing import Dict

class BaseExtractor(ABC):
    """Base class for all fund data extractors"""
    
    def __init__(self, config: dict):
        self.config = config
        self.fund_id = config.get('fund_id')
        self.provider = config.get('provider')
    
    @abstractmethod
    async def extract(self, report_date: str = None) -> Dict:
        """
        Extract YTM data for the fund
        
        Args:
            report_date: Target month (YYYY-MM-01), defaults to current month
            
        Returns:
            {
                'fund_id': str,
                'isin_code': str,
                'fund_name': str,
                'fund_url': str,
                'fund_maturity': int,
                'yield_to_maturity': float,
                'report_date': str,
                'source_type': str,
                'source_document': str,  # PDF path if applicable
                'success': bool,
                'error': str or None
            }
        """
        pass
```

---

### Phase 4: Carmignac Extractor (`extractors/carmignac.py`)

**Tasks:**
1. Adapt existing `carmignac_ytm_extractor.py` to new structure
2. Implement `CarmignacExtractor(BaseExtractor)`
3. Key methods:
   - `async def extract()` - Main extraction flow
   - `async def handle_modals(page)` - Cookie/profile modal handling
   - `async def extract_ytm_value(page)` - Parse YTM from page HTML

**Note:** This is mostly a refactor of existing working code into the new class structure.

**Validation:**
```bash
python -c "
import asyncio
from extractors.carmignac import CarmignacExtractor
from config import FUND_CONFIG

extractor = CarmignacExtractor(FUND_CONFIG['carmignac_2027'])
result = asyncio.run(extractor.extract())
print(f'Success: {result[\"success\"]}')
print(f'YTM: {result[\"yield_to_maturity\"]}%')
# Expected: ~3.90%
"
```

---

### Phase 5: Sycomore Extractor (`extractors/sycomore.py`)

**Tasks:**
1. Adapt existing `sycomore_report_downloader.py`
2. Implement `SycomoreExtractor(BaseExtractor)`
3. Integration flow:
   - Download PDF report (existing code)
   - Extract YTM from PDF (Phase 2 code)
   - Return unified result

**Key considerations:**
- Cookie injection for modal bypass (already implemented)
- PDF storage in `reports/` directory
- Extract report date from PDF filename or content

**Validation:**
```bash
python -c "
import asyncio
from extractors.sycomore import SycomoreExtractor
from config import FUND_CONFIG

extractor = SycomoreExtractor(FUND_CONFIG['sycomore_2030'])
result = asyncio.run(extractor.extract())
print(f'Success: {result[\"success\"]}')
print(f'YTM: {result[\"yield_to_maturity\"]}%')
# Expected: ~4.90%
"
```

---

### Phase 6: Rothschild Extractor (`extractors/rothschild.py`)

**Tasks:**
1. Adapt existing `rothschild_report_downloader.py`
2. Implement `RothschildExtractor(BaseExtractor)`
3. Integration flow:
   - Handle GDPR + profile modal (existing code)
   - Download PDF report
   - Extract YTM from PDF

**Key considerations:**
- More complex modal handling (country dropdown, profile selection, checkbox)
- May need to navigate to "Reporting" tab
- Handle both FR and EN page variants

**Validation:**
```bash
python -c "
import asyncio
from extractors.rothschild import RothschildExtractor
from config import FUND_CONFIG

extractor = RothschildExtractor(FUND_CONFIG['rothschild_2028'])
result = asyncio.run(extractor.extract())
print(f'Success: {result[\"success\"]}')
print(f'YTM: {result[\"yield_to_maturity\"]}%')
# Expected: ~2.85%
"
```

---

### Phase 7: Main Orchestrator (`main.py`)

**Tasks:**
1. Create main script that:
   - Initializes database
   - Iterates through all fund configs
   - Calls appropriate extractor for each
   - Stores results in SQLite
   - Generates summary report

```python
#!/usr/bin/env python3
"""
YTM Data Extraction - Main Orchestrator

Usage:
    python main.py                    # Extract current month data
    python main.py --date 2024-11     # Extract specific month
    python main.py --fund carmignac_2027  # Extract single fund
    python main.py --dry-run          # Test without saving to DB
"""

import asyncio
import argparse
from datetime import datetime
from database import DatabaseManager
from extractors.carmignac import CarmignacExtractor
from extractors.sycomore import SycomoreExtractor
from extractors.rothschild import RothschildExtractor
from config import FUND_CONFIG

EXTRACTOR_MAP = {
    'carmignac': CarmignacExtractor,
    'sycomore': SycomoreExtractor,
    'rothschild': RothschildExtractor
}

async def extract_all_funds(report_date: str, dry_run: bool = False):
    """Extract YTM data for all configured funds"""
    db = DatabaseManager('data/ytm_data.db')
    if not dry_run:
        db.init_db()
    
    results = []
    
    for fund_id, config in FUND_CONFIG.items():
        config['fund_id'] = fund_id
        extractor_class = EXTRACTOR_MAP[config['provider']]
        extractor = extractor_class(config)
        
        print(f"\n{'='*50}")
        print(f"Extracting: {config['fund_name']}")
        print(f"{'='*50}")
        
        try:
            result = await extractor.extract(report_date)
            results.append(result)
            
            if result['success'] and not dry_run:
                db.insert_ytm_record(result)
                print(f"✅ Saved: {result['yield_to_maturity']}%")
            elif result['success']:
                print(f"✅ Extracted: {result['yield_to_maturity']}% (dry run)")
            else:
                print(f"❌ Failed: {result['error']}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({'fund_id': fund_id, 'success': False, 'error': str(e)})
    
    # Print summary
    print_summary(results)
    return results

def print_summary(results):
    """Print extraction summary"""
    print("\n" + "="*60)
    print("EXTRACTION SUMMARY")
    print("="*60)
    
    success_count = sum(1 for r in results if r.get('success'))
    
    for r in results:
        status = "✅" if r.get('success') else "❌"
        ytm = f"{r.get('yield_to_maturity')}%" if r.get('yield_to_maturity') else "N/A"
        print(f"{status} {r.get('fund_id', 'unknown')}: {ytm}")
    
    print(f"\nSuccess rate: {success_count}/{len(results)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract YTM data from bond funds')
    parser.add_argument('--date', help='Report date (YYYY-MM)', default=None)
    parser.add_argument('--fund', help='Single fund ID to extract', default=None)
    parser.add_argument('--dry-run', action='store_true', help='Test without saving')
    args = parser.parse_args()
    
    # Determine report date
    if args.date:
        report_date = f"{args.date}-01"
    else:
        report_date = datetime.now().strftime('%Y-%m-01')
    
    asyncio.run(extract_all_funds(report_date, args.dry_run))
```

**Validation:**
```bash
# Full extraction test
python main.py --dry-run

# Single fund test
python main.py --fund carmignac_2027 --dry-run

# Save to database
python main.py
```

---

## Dependencies (`requirements.txt`)

```
playwright>=1.40.0
pdfplumber>=0.10.0
```

**Setup commands:**
```bash
pip install -r requirements.txt
playwright install chromium
```

---

## Execution Order for Claude Code

1. **Phase 1**: Create `database.py` → Test with sample data
2. **Phase 2**: Create `pdf_utils/ytm_extractor.py` → Test with existing Sycomore PDF
3. **Phase 3**: Create `extractors/base.py` → Just the interface
4. **Phase 4**: Create `extractors/carmignac.py` → Test extraction
5. **Phase 5**: Create `extractors/sycomore.py` → Test full PDF flow
6. **Phase 6**: Create `extractors/rothschild.py` → Test full PDF flow
7. **Phase 7**: Create `main.py` → Integration test

---

## Expected Output Examples

### Database Query Result
```json
[
    {
        "fund_id": "carmignac_2027",
        "isin_code": "FR00140081Y1",
        "fund_name": "Carmignac Crédit 2027",
        "provider": "carmignac",
        "fund_url": "https://www.carmignac.com/...",
        "fund_maturity": 2027,
        "yield_to_maturity": 3.90,
        "report_date": "2024-11-01",
        "source_type": "web"
    },
    {
        "fund_id": "sycomore_2030",
        "isin_code": null,
        "fund_name": "Sycoyield 2030",
        "provider": "sycomore",
        "fund_url": "https://fr.sycomore-am.com/...",
        "fund_maturity": 2030,
        "yield_to_maturity": 4.90,
        "report_date": "2024-11-01",
        "source_type": "pdf",
        "source_document": "reports/sycoyield_2030_report_202411.pdf"
    }
]
```

### CLI Output
```
============================================================
YTM DATA EXTRACTION - November 2024
============================================================

==================================================
Extracting: Carmignac Crédit 2027
==================================================
📄 Loading page...
🔓 Handling modals...
📊 Extracting YTM...
✅ Saved: 3.90%

==================================================
Extracting: Sycoyield 2030
==================================================
📄 Loading page...
🍪 Injecting cookie...
📥 Downloading PDF...
📊 Extracting YTM from PDF...
✅ Saved: 4.90%

...

============================================================
EXTRACTION SUMMARY
============================================================
✅ carmignac_2027: 3.90%
✅ carmignac_2029: 4.60%
✅ carmignac_2031: 5.10%
✅ sycomore_2030: 4.90%
✅ sycomore_2032: 4.90%
✅ rothschild_2028: 2.85%
✅ rothschild_2029: 3.06%

Success rate: 7/7
```

---

## Notes for Claude Code

1. **Use existing code**: The `carmignac_ytm_extractor.py`, `sycomore_report_downloader.py`, and `rothschild_report_downloader.py` contain working implementations - refactor them into the new structure.

2. **Test incrementally**: Each phase should be tested before moving to the next.

3. **Handle French number format**: Always convert `4,9` → `4.9` (comma to period).

4. **Headless mode**: Default to `headless=True` for production, but support `headless=False` for debugging.

5. **Error resilience**: If one fund fails, continue with others and report failures at the end.

6. **PDF storage**: Keep PDFs in `reports/` with format `{provider}_{maturity}_report_{YYYYMM}.pdf`

7. **Database location**: Store in `data/ytm_data.db` - create directory if needed.
