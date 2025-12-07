import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import os


class DatabaseManager:
    """Manages SQLite database operations for YTM data"""

    def __init__(self, db_path: str = 'data/ytm_data.db'):
        """
        Initialize database manager

        Args:
            db_path: Path to SQLite database file
        """
        # Convert relative path to absolute path based on this file's location
        if not os.path.isabs(db_path):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, db_path)

        self.db_path = db_path
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    def _get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Create tables if they don't exist"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Create main table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fund_ytm_data (
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
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fund_date
            ON fund_ytm_data(fund_id, report_date)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_report_date
            ON fund_ytm_data(report_date)
        """)

        conn.commit()
        conn.close()
        print(f"✅ Database initialized: {self.db_path}")

    def insert_ytm_record(self, record: Dict) -> bool:
        """
        Insert or update a YTM record

        Args:
            record: Dictionary containing fund data

        Returns:
            True if successful, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO fund_ytm_data (
                    fund_id, isin_code, fund_name, provider, fund_url,
                    fund_maturity, yield_to_maturity, report_date,
                    source_type, source_document
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.get('fund_id'),
                record.get('isin_code'),
                record.get('fund_name'),
                record.get('provider'),
                record.get('fund_url'),
                record.get('fund_maturity'),
                record.get('yield_to_maturity'),
                record.get('report_date'),
                record.get('source_type'),
                record.get('source_document')
            ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"❌ Database error: {e}")
            conn.close()
            return False

    def get_latest_records(self) -> List[Dict]:
        """
        Get the most recent record for each fund

        Returns:
            List of dictionaries containing fund data
        """
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT f.*
            FROM fund_ytm_data f
            INNER JOIN (
                SELECT fund_id, MAX(report_date) as max_date
                FROM fund_ytm_data
                GROUP BY fund_id
            ) latest ON f.fund_id = latest.fund_id
                     AND f.report_date = latest.max_date
            ORDER BY f.fund_maturity, f.fund_name
        """)

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_records_by_date(self, report_date: str) -> List[Dict]:
        """
        Get all records for a specific month

        Args:
            report_date: Date in YYYY-MM-01 format

        Returns:
            List of dictionaries containing fund data
        """
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM fund_ytm_data
            WHERE report_date = ?
            ORDER BY fund_maturity, fund_name
        """, (report_date,))

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_fund_history(self, fund_id: str) -> List[Dict]:
        """
        Get historical data for a specific fund

        Args:
            fund_id: Unique fund identifier

        Returns:
            List of dictionaries containing historical data
        """
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM fund_ytm_data
            WHERE fund_id = ?
            ORDER BY report_date DESC
        """, (fund_id,))

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def record_exists(self, fund_id: str, report_date: str) -> bool:
        """
        Check if a record already exists

        Args:
            fund_id: Unique fund identifier
            report_date: Date in YYYY-MM-01 format

        Returns:
            True if record exists, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM fund_ytm_data
            WHERE fund_id = ? AND report_date = ?
        """, (fund_id, report_date))

        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def get_all_records(self) -> List[Dict]:
        """
        Get all records from the database

        Returns:
            List of all records
        """
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM fund_ytm_data
            ORDER BY report_date DESC, fund_maturity
        """)

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results


if __name__ == "__main__":
    # Test the database
    print("Testing DatabaseManager...")

    db = DatabaseManager('data/ytm_data.db')
    db.init_db()

    # Insert test record
    test_record = {
        'fund_id': 'test_fund',
        'fund_name': 'Test Fund',
        'isin_code': 'TEST123',
        'provider': 'test',
        'fund_url': 'https://example.com',
        'fund_maturity': 2030,
        'yield_to_maturity': 4.5,
        'report_date': '2024-11-01',
        'source_type': 'test'
    }

    print("\nInserting test record...")
    success = db.insert_ytm_record(test_record)
    print(f"Insert successful: {success}")

    print("\nLatest records:")
    for record in db.get_latest_records():
        print(f"  {record['fund_id']}: {record['yield_to_maturity']}%")

    print("\nTest completed!")
