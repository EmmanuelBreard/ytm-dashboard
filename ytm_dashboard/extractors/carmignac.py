import asyncio
from playwright.async_api import async_playwright
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


class CarmignacExtractor(BaseExtractor):
    """Extractor for Carmignac fund YTM data (PDF download + extraction)"""

    async def extract(self, report_date: str = None) -> Dict:
        """
        Extract YTM data from Carmignac fund by downloading and parsing PDF

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
            print("📥 Downloading Monthly Factsheet PDF...")
            pdf_path = await self.download_factsheet()

            if not pdf_path:
                return self._build_result(
                    report_date=report_date,
                    error="Failed to download Monthly Factsheet PDF"
                )

            # Step 2: Extract and validate factsheet date
            print("🗓️  Validating factsheet date...")
            factsheet_date, date_error = self.extract_factsheet_date(pdf_path)

            if not factsheet_date:
                return self._build_result(
                    report_date=report_date,
                    source_document=pdf_path,
                    error=f"Could not extract factsheet date: {date_error}"
                )

            # Validate factsheet date matches expected month
            is_valid, validation_msg = self.validate_factsheet_date(
                factsheet_date,
                report_date
            )

            if not is_valid:
                print(f"  ⚠️  {validation_msg}")
                return self._build_result(
                    report_date=report_date,
                    source_document=pdf_path,
                    error=f"Data not current: {validation_msg}"
                )

            print(f"  ✅ {validation_msg}")

            # Step 3: Extract YTM from PDF
            print("📊 Extracting YTM from PDF...")
            ytm = self.extract_ytm_from_pdf(pdf_path)

            if ytm is None:
                return self._build_result(
                    report_date=report_date,
                    source_document=pdf_path,
                    error="Could not extract Yield to Maturity from PDF"
                )

            print(f"✅ Extracted: {ytm}%")
            return self._build_result(
                yield_to_maturity=ytm,
                report_date=report_date,
                source_document=pdf_path,
                success=True
            )

        except Exception as e:
            error = f"Unexpected error: {str(e)}"
            print(f"❌ {error}")
            return self._build_result(report_date=report_date, error=error)

    async def download_factsheet(self) -> str:
        """
        Download the Monthly Factsheet PDF from Carmignac fund page

        Returns:
            Path to downloaded PDF, or None if failed
        """
        # Use absolute path
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
                    locale='en-US',
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    accept_downloads=True
                )

                page = await context.new_page()

                # Navigate to fund page
                print(f"📄 Loading page: {self.url}")
                await page.goto(self.url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(3)

                # Handle modals (reuse existing modal handling code)
                await self.handle_modals(page)

                # Find "Monthly Factsheet" or "Reporting mensuel" download link
                factsheet_url = None

                # Strategy 1: Look for text links (English and French)
                text_patterns = [
                    "Monthly Factsheet",
                    "monthly factsheet",
                    "Reporting mensuel",
                    "reporting mensuel"
                ]

                for text in text_patterns:
                    if factsheet_url:
                        break
                    try:
                        factsheet_link = page.locator(f'a:has-text("{text}")').first
                        if await factsheet_link.is_visible(timeout=2000):
                            href = await factsheet_link.get_attribute('href')
                            if href:
                                factsheet_url = href
                                print(f"  ✓ Found factsheet link: '{text}'")
                                break
                    except:
                        pass

                # Strategy 2: Look for href patterns containing factsheet/reporting
                if not factsheet_url:
                    href_patterns = ['factsheet', 'reporting', 'mensuel']
                    for pattern in href_patterns:
                        try:
                            links = await page.locator(f'a[href*="{pattern}"]').all()
                            for link in links:
                                href = await link.get_attribute('href')
                                if href and href.endswith('.pdf'):
                                    factsheet_url = href
                                    print(f"  ✓ Found PDF via href pattern: '{pattern}'")
                                    break
                            if factsheet_url:
                                break
                        except:
                            pass

                # Strategy 3: Look for any PDF link in Key documents section
                if not factsheet_url:
                    try:
                        # Find PDF links
                        pdf_links = await page.locator('a[href$=".pdf"]').all()
                        for link in pdf_links:
                            href = await link.get_attribute('href')
                            # Get link text or parent text for context
                            try:
                                link_text = await link.inner_text()
                                if any(keyword in link_text.lower() for keyword in ['factsheet', 'reporting', 'mensuel', 'monthly']):
                                    factsheet_url = href
                                    print(f"  ✓ Found PDF via link text")
                                    break
                            except:
                                pass
                    except:
                        pass

                if not factsheet_url:
                    await browser.close()
                    print("❌ Could not find Monthly Factsheet download link")
                    return None

                # Make URL absolute if needed
                if factsheet_url.startswith('/'):
                    base_url = '/'.join(self.url.split('/')[:3])
                    factsheet_url = base_url + factsheet_url

                # Download the PDF
                print(f"⬇️  Downloading PDF...")
                timestamp = datetime.now().strftime('%Y%m')
                safe_fund_name = self.fund_name.lower().replace(' ', '_')
                pdf_filename = f"{safe_fund_name}_factsheet_{timestamp}.pdf"
                pdf_path = os.path.join(output_dir, pdf_filename)

                # Try API download
                try:
                    response = await page.request.get(factsheet_url)

                    if response.ok:
                        content = await response.body()

                        if content.startswith(b'%PDF'):
                            with open(pdf_path, 'wb') as f:
                                f.write(content)

                            file_size = os.path.getsize(pdf_path)
                            print(f"✅ PDF downloaded ({file_size:,} bytes)")
                            await browser.close()
                            return pdf_path
                        else:
                            raise Exception("Not a PDF")
                except:
                    # Try navigation download
                    download_page = await context.new_page()

                    try:
                        async with download_page.expect_download(timeout=10000) as download_info:
                            await download_page.goto(factsheet_url)

                        download = await download_info.value
                        await download.save_as(pdf_path)

                        file_size = os.path.getsize(pdf_path)
                        print(f"✅ PDF downloaded ({file_size:,} bytes)")
                        await browser.close()
                        return pdf_path

                    except Exception as e:
                        print(f"❌ Download failed: {e}")
                        await browser.close()
                        return None

                await browser.close()

        except Exception as e:
            print(f"❌ Error downloading factsheet: {str(e)}")
            return None

        return None

    async def handle_modals(self, page) -> None:
        """
        Handle the 2-step modal process on Carmignac pages

        Step 1: Accept data usage terms
        Step 2: Confirm professional investor profile
        """
        try:
            await asyncio.sleep(1)

            modal_selectors = [
                'button:has-text("Accept")',
                'button:has-text("Accepter")',
                'button:has-text("J\'accepte")',
                'button:has-text("Continuer")',
                'button:has-text("Continue")',
                'button:has-text("Confirm")',
                'button:has-text("Confirmer")',
                '[data-testid*="accept"]',
                '[class*="accept"]',
                '[id*="accept"]',
                '.modal button.primary',
                '.cookie-consent button',
            ]

            # Try to click through up to 3 modal steps
            for step in range(3):
                modal_clicked = False

                for selector in modal_selectors:
                    try:
                        button = page.locator(selector).first
                        if await button.is_visible(timeout=2000):
                            print(f"  → Clicking modal button")
                            await button.click(timeout=5000)
                            modal_clicked = True
                            await asyncio.sleep(1)
                            break
                    except:
                        continue

                if not modal_clicked:
                    break

            print("  ✓ Modals handled")

        except Exception as e:
            print(f"  ⚠️  Modal warning: {str(e)}")

    def extract_factsheet_date(self, pdf_path: str) -> Tuple[datetime, str]:
        """
        Extract factsheet date from PDF header

        Args:
            pdf_path: Path to downloaded PDF

        Returns:
            (datetime object, error message) or (None, error)
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                first_page = pdf.pages[0].extract_text()

                # Patterns: Support both English and French versions
                # English: "Monthly Factsheet - DD/MM/YYYY"
                # French: "Reporting mensuel - DD/MM/YYYY"
                patterns = [
                    r'Monthly Factsheet\s*-\s*(\d{2})/(\d{2})/(\d{4})',
                    r'Reporting mensuel\s*-\s*(\d{2})/(\d{2})/(\d{4})',
                ]

                for pattern in patterns:
                    match = re.search(pattern, first_page, re.IGNORECASE)
                    if match:
                        day, month, year = match.groups()
                        date_str = f"{year}-{month}-{day}"
                        factsheet_date = datetime.strptime(date_str, '%Y-%m-%d')
                        return factsheet_date, f"{day}/{month}/{year}"

                return None, "Could not find date pattern in PDF (tried both English and French formats)"

        except Exception as e:
            return None, f"Error reading PDF: {str(e)}"

    def validate_factsheet_date(self, factsheet_date: datetime, expected_report_date: str) -> Tuple[bool, str]:
        """
        Validate that factsheet date matches expected month

        Args:
            factsheet_date: Date extracted from PDF
            expected_report_date: Expected report date (YYYY-MM-01)

        Returns:
            (is_valid, reason)
        """
        # Extract expected year and month
        expected_dt = datetime.strptime(expected_report_date, '%Y-%m-%d')
        expected_year = expected_dt.year
        expected_month = expected_dt.month

        factsheet_year = factsheet_date.year
        factsheet_month = factsheet_date.month

        # Factsheet date should be from the expected month
        # For November report, we expect "31/10/2025" or "30/11/2025"
        # The factsheet date is typically the last day of the previous month

        # Check if factsheet is from expected month
        if factsheet_year == expected_year and factsheet_month == expected_month:
            return True, f"Factsheet date matches ({factsheet_date.strftime('%d/%m/%Y')})"

        # Check if factsheet is from previous month (acceptable if it's end of month)
        if factsheet_year == expected_year and factsheet_month == expected_month - 1:
            # Check if it's the last day of the month
            next_day = factsheet_date + timedelta(days=1)
            if next_day.month != factsheet_date.month:
                return True, f"Factsheet is end of previous month ({factsheet_date.strftime('%d/%m/%Y')})"

        # Date doesn't match
        factsheet_month_name = factsheet_date.strftime('%B %Y')
        expected_month_name = expected_dt.strftime('%B %Y')
        return False, f"Factsheet date ({factsheet_month_name}) doesn't match expected month ({expected_month_name})"

    def extract_ytm_from_pdf(self, pdf_path: str) -> float:
        """
        Extract Yield to Maturity (EUR) from PDF KEY FIGURES section

        Args:
            pdf_path: Path to downloaded PDF

        Returns:
            YTM value as float, or None if not found
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                first_page = pdf.pages[0].extract_text()

                # Pattern: "Yield to Maturity (EUR) (1)   4.6%"
                # Look for the line and extract percentage
                patterns = [
                    r'Yield to Maturity \(EUR\)[^\n]*?(\d+\.?\d*)%',  # "Yield to Maturity (EUR) (1)   4.6%"
                    r'Yield to Maturity[^\n]*?\(EUR\)[^\n]*?(\d+\.?\d*)%',  # Alternative format
                ]

                for pattern in patterns:
                    match = re.search(pattern, first_page, re.IGNORECASE)
                    if match:
                        ytm_str = match.group(1)
                        ytm = float(ytm_str)
                        return ytm

                return None

        except Exception as e:
            print(f"  ❌ Error extracting YTM: {str(e)}")
            return None
