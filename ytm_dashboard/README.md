# YTM Data Extraction & Storage System

Automated extraction of Yield-to-Maturity (YTM) data from 7 target-maturity bond funds across 3 providers, stored in SQLite database for historical tracking.

## Features

- **Multi-Provider Support**: Extracts from Carmignac, Sycomore, and Rothschild funds
- **Dual Extraction Methods**: Web scraping (Carmignac) and PDF parsing (Sycomore/Rothschild)
- **SQLite Storage**: Maintains historical YTM data with monthly snapshots
- **Automated Modal Handling**: Bypasses cookie consents and investor profile modals
- **Error Resilience**: Continues extraction even if individual funds fail

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

### Usage

```bash
# Extract current month data for all funds
python3 main.py

# Extract specific month
python3 main.py --date 2024-11

# Extract single fund
python3 main.py --fund carmignac_2027

# Test without saving to database
python3 main.py --dry-run

# List all configured funds
python3 main.py --list-funds
```

## Configured Funds

| Fund ID           | Provider    | Fund Name              | Maturity | Source |
|-------------------|-------------|------------------------|----------|--------|
| carmignac_2027    | Carmignac   | Carmignac Crédit 2027  | 2027     | Web    |
| carmignac_2029    | Carmignac   | Carmignac Crédit 2029  | 2029     | Web    |
| carmignac_2031    | Carmignac   | Carmignac Crédit 2031  | 2031     | Web    |
| sycomore_2030     | Sycomore    | Sycoyield 2030         | 2030     | PDF    |
| sycomore_2032     | Sycomore    | Sycoyield 2032         | 2032     | PDF    |
| rothschild_2028   | Rothschild  | R-co Target 2028 IG    | 2028     | PDF    |
| rothschild_2029   | Rothschild  | R-co Target 2029 IG    | 2029     | PDF    |

## Project Structure

```
ytm_dashboard/
├── main.py                  # Entry point - orchestrates all extractions
├── config.py                # Fund configurations
├── database.py              # SQLite operations
├── extractors/
│   ├── base.py              # Abstract base class
│   ├── carmignac.py         # Carmignac web scraper
│   ├── sycomore.py          # Sycomore PDF downloader + extractor
│   └── rothschild.py        # Rothschild PDF downloader + extractor
├── pdf_utils/
│   └── ytm_extractor.py     # PDF YTM extraction logic
├── data/
│   └── ytm_data.db          # SQLite database
└── reports/                 # Downloaded PDF reports
```

## Database Schema

```sql
CREATE TABLE fund_ytm_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id TEXT NOT NULL,
    isin_code TEXT,
    fund_name TEXT NOT NULL,
    provider TEXT NOT NULL,
    fund_url TEXT NOT NULL,
    fund_maturity INTEGER NOT NULL,
    yield_to_maturity REAL,
    report_date DATE NOT NULL,
    extraction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_type TEXT,
    source_document TEXT,
    UNIQUE(fund_id, report_date)
);
```

## Example Output

```
============================================================
YTM DATA EXTRACTION - December 2025
============================================================
Report Date: 2025-12-01
Funds to process: 7
============================================================

==================================================
Extracting: Carmignac Crédit 2027
==================================================
📄 Loading page...
🔓 Handling modals...
🎯 Extracting YTM...
✅ Extracted: 3.9%
💾 Saved to database

==================================================
Extracting: Sycoyield 2030
==================================================
📥 Downloading PDF report...
📄 Loading page...
🍪 Injecting cookie...
⬇️  Downloading PDF...
✅ PDF downloaded (457,916 bytes)
📊 Extracting YTM from PDF...
✅ Extracted: 4.9%
💾 Saved to database

...

============================================================
EXTRACTION SUMMARY
============================================================
✅ Carmignac Crédit 2027              3.9%
✅ Carmignac Crédit 2029              4.6%
✅ Carmignac Crédit 2031              5.1%
✅ Sycoyield 2030                     4.9%
✅ Sycoyield 2032                     4.9%
✅ R-co Target 2028 IG                2.85%
✅ R-co Target 2029 IG                3.06%

📊 Success rate: 7/7
```

## Querying the Database

```python
from database import DatabaseManager

db = DatabaseManager('data/ytm_data.db')

# Get latest data for all funds
latest = db.get_latest_records()
for record in latest:
    print(f"{record['fund_name']}: {record['yield_to_maturity']}%")

# Get historical data for one fund
history = db.get_fund_history('carmignac_2027')
for record in history:
    print(f"{record['report_date']}: {record['yield_to_maturity']}%")

# Get all records for a specific month
november_data = db.get_records_by_date('2024-11-01')
```

## Scheduled Execution

To run monthly, add to crontab:

```bash
# Run on the 5th of each month at 9 AM
0 9 5 * * cd /path/to/automation_simon && python3 main.py
```

## Troubleshooting

### Extraction Failures

- **Modal issues**: The system handles most modals automatically, but site updates may require extractor adjustments
- **PDF pattern changes**: If YTM patterns change in PDFs, update patterns in `pdf_utils/ytm_extractor.py`
- **Network timeouts**: Increase timeout values in extractor files

### Debug Mode

For detailed browser activity, modify extractor to run in non-headless mode:

```python
browser = await p.chromium.launch(headless=False)  # Shows browser window
```

## Dependencies

- **playwright**: Web automation for Carmignac scraping and PDF downloads
- **pdfplumber**: PDF text extraction for YTM parsing

## License

Private project for automated fund monitoring.
