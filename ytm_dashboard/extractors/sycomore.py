import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime, timedelta
from pathlib import Path
import os
import sys
import re
import io
from typing import Dict, Tuple
import pdfplumber

# Import parent directory for pdf_utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base import BaseExtractor
from pdf_utils.ytm_extractor import extract_ytm_from_pdf


class SycomoreExtractor(BaseExtractor):
    """Extractor for Sycomore fund YTM data (PDF download + extraction)"""

    async def extract(self, report_date: str = None) -> Dict:
        """
        Extract YTM data from Sycomore fund by downloading and parsing PDF

        Args:
            report_date: Target month (YYYY-MM-01), defaults to current month

        Returns:
            Standardized result dictionary
        """
        report_date = self._get_report_date(report_date)

        try:
            print(f"\n{'='*50}")
            print(f"Extracting: {self.fund_name}")
            print(f"{'='*50}")

            # Step 1: Download PDF
            print("📥 Downloading PDF report...")
            pdf_path = await self.download_report()

            if not pdf_path:
                return self._build_result(
                    report_date=report_date,
                    error="Failed to download PDF report"
                )

            # Step 2: Extract YTM from PDF
            print("📊 Extracting YTM from PDF...")
            pdf_result = extract_ytm_from_pdf(pdf_path, self.provider)

            if pdf_result['success']:
                ytm = pdf_result['yield_to_maturity']
                # Use PDF-extracted date if available, otherwise use report_date
                extracted_date = pdf_result.get('report_date') or report_date

                print(f"✅ Extracted: {ytm}%")
                return self._build_result(
                    yield_to_maturity=ytm,
                    report_date=extracted_date,
                    source_document=pdf_path,
                    success=True
                )
            else:
                print(f"❌ Failed to extract YTM: {pdf_result['error']}")
                return self._build_result(
                    report_date=report_date,
                    source_document=pdf_path,
                    error=f"PDF extraction failed: {pdf_result['error']}"
                )

        except Exception as e:
            error = f"Unexpected error: {str(e)}"
            print(f"❌ {error}")
            return self._build_result(report_date=report_date, error=error)

    def validate_pdf_content(self, content: bytes, expected_report_month: str = None) -> Tuple[bool, str]:
        """
        Validate that downloaded PDF is the correct monthly report

        Args:
            content: PDF file bytes
            expected_report_month: Expected month in format "YYYY-MM" (e.g., "2025-11")

        Returns:
            (is_valid, reason)
        """
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                first_page = pdf.pages[0].extract_text()

                # Check 1: Reject KIID/DIC documents
                if any(kw in first_page for kw in ["Document d'informations clés", "KIID", "Document d'information clé"]):
                    return False, "PDF is a KIID/DIC, not a monthly report"

                # Check 2: Extract and validate ISIN if configured
                isin_match = re.search(r'ISIN[:\s]+([A-Z]{2}[A-Z0-9]{10})', first_page)

                if self.isin_code:
                    if isin_match:
                        found_isin = isin_match.group(1)
                        if found_isin != self.isin_code:
                            return False, f"ISIN mismatch: expected {self.isin_code}, found {found_isin}"
                    # If ISIN is configured but not found in PDF, that's okay (some monthly reports don't have ISIN)

                # Check 3: Validate fund name
                if self.fund_name not in first_page and "Sycoyield" not in first_page:
                    return False, f"Fund name '{self.fund_name}' not found in PDF"

                # Check 4: Validate report month if specified
                if expected_report_month:
                    year, month = expected_report_month.split('-')
                    month_num = int(month)

                    # Month names in French and English
                    month_names = {
                        1: ['janvier', 'january'], 2: ['février', 'february', 'fevrier'],
                        3: ['mars', 'march'], 4: ['avril', 'april'],
                        5: ['mai', 'may'], 6: ['juin', 'june'],
                        7: ['juillet', 'july'], 8: ['août', 'august', 'aout'],
                        9: ['septembre', 'september'], 10: ['octobre', 'october'],
                        11: ['novembre', 'november'], 12: ['décembre', 'december', 'decembre']}

                    expected_month_names = month_names.get(month_num, [])
                    first_page_lower = first_page.lower()

                    # Check if any expected month name is in the PDF
                    if not any(name in first_page_lower for name in expected_month_names):
                        return False, f"PDF doesn't contain expected month ({expected_month_names[0]} {year})"

                return True, "PDF validated successfully"

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    async def download_report(self) -> str:
        """
        Download the latest monthly report PDF

        Returns:
            Path to downloaded PDF, or None if failed
        """
        # Use absolute path based on this file's location
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, "reports")
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled']
                )

                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    locale='fr-FR',
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    accept_downloads=True
                )

                # Inject guest_profile cookie to bypass modal
                print("🍪 Injecting cookie...")
                guest_profile_cookie = {
                    'name': 'guest_profile',
                    'value': 'eyJpdiI6IkNRd3hCeFRlYTFqdXVwODc1MWd1VHc9PSIsInZhbHVlIjoiRDFhWW05UUd3dGlUT3RxblM1S1AzS0diM3IyTGNyOWJWazZXWE9iQzRPRnA1TzY1cUFEMm9WM1pvcVMyMHVXS0dXenNRNGo2V3NuekkrS0tZMzd6NWc9PSIsIm1hYyI6ImI0NWMzNTUxOTFmMjljN2ZlMDRmMDhkZTUzNzZiODRiZjA4MWQ1ZmRiZmVjZGRiMWQ3MjA0NzA1OTUyMjBlZTAiLCJ0YWciOiIifQ%3D%3D',
                    'domain': '.sycomore-am.com',
                    'path': '/',
                    'httpOnly': False,
                    'secure': False,
                    'sameSite': 'Lax'
                }

                await context.add_cookies([guest_profile_cookie])

                page = await context.new_page()

                # Navigate to page
                print("📄 Loading page...")
                await page.goto(self.url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(3)

                # Search for report download link
                report_url = None

                # Strategy 1: Look for "Voir le dernier reporting" button
                try:
                    report_button = page.locator('a:has-text("Voir le dernier reporting")').first
                    if await report_button.is_visible(timeout=3000):
                        href = await report_button.get_attribute('href')
                        report_url = href
                        print(f"  ✓ Found report button")
                except:
                    pass

                # Strategy 2: Look for reporting download links
                if not report_url:
                    try:
                        reporting_links = await page.locator('a[href*="/telecharger/reporting/"]').all()
                        if reporting_links:
                            href = await reporting_links[0].get_attribute('href')
                            report_url = href
                            print(f"  ✓ Found reporting link")
                    except:
                        pass

                if not report_url:
                    await browser.close()
                    print("❌ Could not find report download link")
                    return None

                # Download the PDF
                print(f"⬇️  Downloading PDF...")

                # Calculate expected report month (previous month)
                current_date = datetime.now()
                expected_month = (current_date.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')

                timestamp = expected_month.replace('-', '')  # Use expected_month (e.g., "2025-11" → "202511")
                safe_fund_name = self.fund_name.lower().replace(' ', '_')
                report_filename = f"{safe_fund_name}_report_{timestamp}.pdf"
                report_path = os.path.join(output_dir, report_filename)

                # Try API download first
                try:
                    response = await page.request.get(report_url)

                    if response.ok:
                        content = await response.body()

                        if content.startswith(b'%PDF'):
                            # Validate content before saving
                            is_valid, reason = self.validate_pdf_content(content, expected_month)

                            if is_valid:
                                with open(report_path, 'wb') as f:
                                    f.write(content)

                                file_size = os.path.getsize(report_path)
                                print(f"✅ PDF downloaded and validated ({file_size:,} bytes)")
                                await browser.close()
                                return report_path
                            else:
                                print(f"  ❌ PDF validation failed: {reason}")
                                raise Exception(f"PDF validation failed: {reason}")
                        else:
                            raise Exception("Not a PDF")

                except:
                    # Try navigation download
                    download_page = await context.new_page()

                    try:
                        async with download_page.expect_download(timeout=10000) as download_info:
                            await download_page.goto(report_url)

                        download = await download_info.value
                        await download.save_as(report_path)

                        # Validate the downloaded file
                        with open(report_path, 'rb') as f:
                            content = f.read()

                        is_valid, reason = self.validate_pdf_content(content, expected_month)

                        if is_valid:
                            file_size = os.path.getsize(report_path)
                            print(f"✅ PDF downloaded and validated ({file_size:,} bytes)")
                            await browser.close()
                            return report_path
                        else:
                            print(f"  ❌ PDF validation failed: {reason}")
                            # Delete invalid PDF
                            os.remove(report_path)
                            await browser.close()
                            return None

                    except Exception as e:
                        print(f"❌ Download failed: {e}")
                        await browser.close()
                        return None

                await browser.close()

        except Exception as e:
            print(f"❌ Error downloading report: {str(e)}")
            return None

        return None
