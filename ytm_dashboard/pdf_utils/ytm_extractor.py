import pdfplumber
import re
from typing import Dict, Optional
from datetime import datetime


def extract_ytm_from_pdf(pdf_path: str, provider: str) -> Dict:
    """
    Extract YTM from PDF report

    Args:
        pdf_path: Path to the PDF file
        provider: Provider name ('sycomore' or 'rothschild')

    Returns:
        {
            'yield_to_maturity': float or None,
            'report_date': str or None,  # Extracted from PDF if possible
            'raw_text_match': str,        # For debugging
            'success': bool,
            'error': str or None
        }
    """
    # Define patterns for each provider
    patterns = {
        'sycomore': [
            r"Rendement\s+(?:à|a)\s+maturit[ée]\**\s*([\d]+[,\.][\d]+)\s*%",
            r"YTM\s*[:\s]+([\d]+[,\.][\d]+)\s*%"
        ],
        'rothschild': [
            r"(?:Taux\s+actuariel|YTW)\s+EUR\s+([\d]+[,\.][\d]+)",
            r"(?:Yield\s+to\s+[Mm]aturity|YTM)\s*[:\s]+([\d]+[,\.][\d]+)\s*%",
            r"Rendement\s+(?:actuariel|à\s+maturité)\s*[:\s]+([\d]+[,\.][\d]+)\s*%"
        ]
    }

    # Date patterns to extract report date
    date_patterns = [
        r"(?:au|as\s+of|date)\s*[:\s]*(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})",
        r"(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})",
        r"(?:Novembre|November|Décembre|December)\s+(\d{4})",
    ]

    result = {
        'yield_to_maturity': None,
        'report_date': None,
        'raw_text_match': '',
        'success': False,
        'error': None
    }

    try:
        # Extract text from all pages
        full_text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"

        if not full_text:
            result['error'] = "No text extracted from PDF"
            return result

        # Search for YTM patterns
        provider_patterns = patterns.get(provider.lower(), [])
        ytm_found = False

        for pattern in provider_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                ytm_str = match.group(1)
                result['raw_text_match'] = match.group(0)

                # Convert French number format (comma) to decimal (period)
                ytm_str = ytm_str.replace(',', '.')

                try:
                    result['yield_to_maturity'] = float(ytm_str)
                    ytm_found = True
                    break
                except ValueError:
                    result['error'] = f"Could not convert YTM value: {ytm_str}"
                    return result

        if not ytm_found:
            result['error'] = f"YTM not found in PDF for provider: {provider}"
            return result

        # Try to extract report date from filename first
        filename_date_match = re.search(r'(\d{6})\.pdf$', pdf_path)
        if filename_date_match:
            date_str = filename_date_match.group(1)  # Format: YYYYMM
            year = date_str[:4]
            month = date_str[4:6]
            result['report_date'] = f"{year}-{month}-01"
        else:
            # Try to extract from PDF content
            for pattern in date_patterns:
                match = re.search(pattern, full_text)
                if match:
                    # Handle different date formats
                    if len(match.groups()) == 3:
                        day, month, year = match.groups()
                        try:
                            result['report_date'] = f"{year}-{month.zfill(2)}-01"
                            break
                        except:
                            continue
                    elif len(match.groups()) == 1:
                        year = match.group(1)
                        # Default to current month if only year is found
                        month = datetime.now().strftime('%m')
                        result['report_date'] = f"{year}-{month}-01"
                        break

        result['success'] = True
        return result

    except FileNotFoundError:
        result['error'] = f"PDF file not found: {pdf_path}"
        return result
    except Exception as e:
        result['error'] = f"Error extracting from PDF: {str(e)}"
        return result


def parse_french_number(number_str: str) -> float:
    """
    Convert French number format to float

    Args:
        number_str: Number string (e.g., "4,90" or "4.90")

    Returns:
        Float value
    """
    return float(number_str.replace(',', '.'))


if __name__ == "__main__":
    # Test with existing PDFs
    import sys
    import os

    print("Testing PDF YTM Extractor...\n")

    # Test Sycomore PDF
    sycomore_pdf = "../reports/sycoyield_2030_report_202511.pdf"
    if os.path.exists(sycomore_pdf):
        print(f"Testing Sycomore PDF: {sycomore_pdf}")
        result = extract_ytm_from_pdf(sycomore_pdf, 'sycomore')
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"YTM: {result['yield_to_maturity']}%")
            print(f"Report Date: {result['report_date']}")
            print(f"Match: {result['raw_text_match']}")
        else:
            print(f"Error: {result['error']}")
        print()

    # Test Rothschild PDF
    rothschild_pdf = "../reports/r_co_target_2028_ig_report_202511.pdf"
    if os.path.exists(rothschild_pdf):
        print(f"Testing Rothschild PDF: {rothschild_pdf}")
        result = extract_ytm_from_pdf(rothschild_pdf, 'rothschild')
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"YTM: {result['yield_to_maturity']}%")
            print(f"Report Date: {result['report_date']}")
            print(f"Match: {result['raw_text_match']}")
        else:
            print(f"Error: {result['error']}")
        print()

    print("Test completed!")
