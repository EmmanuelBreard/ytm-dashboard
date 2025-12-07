from abc import ABC, abstractmethod
from typing import Dict
from datetime import datetime


class BaseExtractor(ABC):
    """Base class for all fund data extractors"""

    def __init__(self, config: dict):
        """
        Initialize the extractor with fund configuration

        Args:
            config: Dictionary containing fund configuration
                Required keys: fund_id, provider, fund_name, maturity, url, source_type
                Optional keys: isin_code
        """
        self.config = config
        self.fund_id = config.get('fund_id')
        self.provider = config.get('provider')
        self.fund_name = config.get('fund_name')
        self.isin_code = config.get('isin_code')
        self.maturity = config.get('maturity')
        self.url = config.get('url')
        self.source_type = config.get('source_type')

    @abstractmethod
    async def extract(self, report_date: str = None) -> Dict:
        """
        Extract YTM data for the fund

        Args:
            report_date: Target month (YYYY-MM-01), defaults to current month

        Returns:
            {
                'fund_id': str,
                'isin_code': str or None,
                'fund_name': str,
                'provider': str,
                'fund_url': str,
                'fund_maturity': int,
                'yield_to_maturity': float or None,
                'report_date': str,
                'source_type': str,
                'source_document': str or None,  # PDF path if applicable
                'success': bool,
                'error': str or None
            }
        """
        pass

    def _get_report_date(self, report_date: str = None) -> str:
        """
        Get report date in YYYY-MM-01 format

        Args:
            report_date: Optional report date string

        Returns:
            Report date in YYYY-MM-01 format
        """
        if report_date:
            # Ensure it's in YYYY-MM-01 format
            if len(report_date) == 7:  # YYYY-MM
                return f"{report_date}-01"
            return report_date
        else:
            # Default to current month
            return datetime.now().strftime('%Y-%m-01')

    def _build_result(self, yield_to_maturity: float = None,
                     report_date: str = None,
                     source_document: str = None,
                     success: bool = False,
                     error: str = None) -> Dict:
        """
        Build a standardized result dictionary

        Args:
            yield_to_maturity: YTM value
            report_date: Report date
            source_document: Path to source document (for PDFs)
            success: Whether extraction was successful
            error: Error message if failed

        Returns:
            Standardized result dictionary
        """
        return {
            'fund_id': self.fund_id,
            'isin_code': self.isin_code,
            'fund_name': self.fund_name,
            'provider': self.provider,
            'fund_url': self.url,
            'fund_maturity': self.maturity,
            'yield_to_maturity': yield_to_maturity,
            'report_date': report_date or self._get_report_date(),
            'source_type': self.source_type,
            'source_document': source_document,
            'success': success,
            'error': error
        }
