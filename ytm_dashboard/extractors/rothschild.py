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


class RothschildExtractor(BaseExtractor):
    """Extractor for Rothschild fund YTM data (PDF download + extraction)"""

    async def extract(self, report_date: str = None) -> Dict:
        """
        Extract YTM data from Rothschild fund by downloading and parsing PDF

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
                if self.fund_name not in first_page and "Target 202" not in first_page:
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
                        11: ['novembre', 'november'], 12: ['décembre', 'december', 'decembre']
                    }

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
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    accept_downloads=True
                )

                page = await context.new_page()

                # Navigate to page
                print("📄 Loading page...")
                await page.goto(self.url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(2)

                # Handle cookie consent
                print("🍪 Handling cookie consent...")
                await self.handle_cookie_consent(page)

                # Handle modal
                print("🔓 Handling modal...")
                await self.handle_modal(page)

                # Look for Reporting section
                print("📊 Looking for Reporting section...")
                await self.navigate_to_reporting(page)

                # Find and download report
                print("⬇️  Finding report download link...")
                report_url, content = await self.find_report(page)

                if not content:
                    await browser.close()
                    return None

                # Save PDF
                timestamp = datetime.now().strftime('%Y%m')
                safe_fund_name = self.fund_name.lower().replace(' ', '_').replace('-', '_')
                report_filename = f"{safe_fund_name}_report_{timestamp}.pdf"
                report_path = os.path.join(output_dir, report_filename)

                with open(report_path, 'wb') as f:
                    f.write(content)

                file_size = os.path.getsize(report_path)
                print(f"✅ PDF downloaded ({file_size:,} bytes)")

                await browser.close()
                return report_path

        except Exception as e:
            print(f"❌ Error downloading report: {str(e)}")
            return None

    async def handle_cookie_consent(self, page):
        """Handle OneTrust GDPR cookie consent banner"""
        try:
            cookie_selectors = [
                '#onetrust-accept-btn-handler',
                'button:has-text("ACCEPT ALL COOKIES")',
                'button:has-text("Autoriser tous les cookies")',
            ]

            for selector in cookie_selectors:
                try:
                    elem = page.locator(selector).first
                    if await elem.is_visible(timeout=3000):
                        await elem.click()
                        await asyncio.sleep(1)
                        print("  ✓ Cookie consent handled")
                        return
                except:
                    continue

            print("  ✓ No cookie banner")

        except Exception as e:
            print(f"  ⚠️  Cookie consent error: {e}")

    async def handle_modal(self, page):
        """Handle Rothschild country/profile modal"""
        try:
            modal = page.locator('section.modal#modal_disclaimer')
            if not await modal.is_visible(timeout=5000):
                print("  ✓ No modal")
                return

            print("  → Selecting country...")
            await page.click('#styled_filter_country_language')
            await asyncio.sleep(0.5)
            await page.click('ul.select-options li[rel="fr-fr"]')
            await asyncio.sleep(0.5)

            print("  → Selecting profile...")
            await page.click('#styled_filter_user_type')
            await asyncio.sleep(0.5)
            await page.click('ul.select-options li[rel="professional"]')
            await asyncio.sleep(0.5)

            print("  → Checking acknowledgment...")
            await page.wait_for_selector('#i_agree:not([disabled])', timeout=5000)
            await page.check('#i_agree')
            await asyncio.sleep(0.5)

            print("  → Submitting...")
            await page.wait_for_selector('button.btnSubmit:not([disabled])', timeout=5000)
            await page.click('button.btnSubmit')

            await page.wait_for_selector('section.modal#modal_disclaimer', state='hidden', timeout=10000)
            print("  ✓ Modal handled")
            await asyncio.sleep(2)

        except Exception as e:
            print(f"  ⚠️  Modal error: {e}")

    async def navigate_to_reporting(self, page):
        """Navigate to Reporting section"""
        try:
            reporting_selectors = [
                'a:has-text("Reporting")',
                'button:has-text("Reporting")',
                '[data-tab="reporting"]',
            ]

            for selector in reporting_selectors:
                try:
                    elem = page.locator(selector).first
                    if await elem.is_visible(timeout=2000):
                        await elem.click()
                        await asyncio.sleep(1)
                        print(f"  ✓ Clicked Reporting tab")
                        return
                except:
                    continue

            # Scroll and try again
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await asyncio.sleep(1)

            for selector in reporting_selectors:
                try:
                    elem = page.locator(selector).first
                    if await elem.is_visible(timeout=2000):
                        await elem.scroll_into_view_if_needed()
                        await elem.click()
                        await asyncio.sleep(1)
                        print(f"  ✓ Found Reporting section")
                        return
                except:
                    continue

            print("  ⚠️  Reporting section not required")

        except Exception as e:
            print(f"  ⚠️  Navigation error: {e}")

    async def find_report(self, page):
        """Find and download the monthly report PDF with validation"""
        try:
            # Calculate expected report month (previous month)
            current_date = datetime.now()
            expected_month = (current_date.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')

            # Strategy 1: Try specific monthly report selectors
            pdf_selectors = [
                'a[href$=".pdf"]:has-text("Rapport mensuel")',
                'a[href$=".pdf"]:has-text("Monthly report")',
                'a[href$=".pdf"]:has-text("Mensuel")',
                'a[href$=".pdf"]:has-text("Monthly")',
            ]

            for selector in pdf_selectors:
                try:
                    elem = page.locator(selector).first
                    if await elem.is_visible(timeout=2000):
                        report_url = await elem.get_attribute('href')
                        text = await elem.inner_text()

                        # Make URL absolute
                        if report_url.startswith('/'):
                            report_url = f"https://am.eu.rothschildandco.com{report_url}"

                        # Download and validate
                        print(f"  → Testing PDF: {text[:50]}")
                        response = await page.request.get(report_url)

                        if response.ok:
                            content = await response.body()

                            if content.startswith(b'%PDF'):
                                # Validate content
                                is_valid, reason = self.validate_pdf_content(content, expected_month)

                                if is_valid:
                                    print(f"  ✅ Found and validated: {text[:50]}")
                                    return report_url, content
                                else:
                                    print(f"  ❌ PDF invalid: {reason}")
                                    continue  # Try next PDF
                except:
                    continue

            # Strategy 2: Iterate through all PDFs and filter
            print("  → Searching all PDF links...")
            pdf_links = await page.query_selector_all('a[href$=".pdf"]')

            for link in pdf_links:
                try:
                    text = await link.inner_text()
                    href = await link.get_attribute('href')

                    # Filter for monthly reports, exclude KIID/DIC
                    if any(kw in text.lower() for kw in ['mensuel', 'monthly report', 'rapport mensuel']):
                        if not any(exclude in text.lower() for exclude in ['dic', 'kiid', 'document d\'information']):

                            # Make URL absolute
                            if href.startswith('/'):
                                href = f"https://am.eu.rothschildandco.com{href}"

                            # Download and validate
                            print(f"  → Testing PDF: {text[:50]}")
                            response = await page.request.get(href)

                            if response.ok:
                                content = await response.body()

                                if content.startswith(b'%PDF'):
                                    # Validate content
                                    is_valid, reason = self.validate_pdf_content(content, expected_month)

                                    if is_valid:
                                        print(f"  ✅ Found and validated: {text[:50]}")
                                        return href, content
                                    else:
                                        print(f"  ❌ PDF invalid: {reason}")
                                        continue
                except:
                    continue

            raise Exception("Could not find valid monthly report PDF")

        except Exception as e:
            print(f"  ❌ Download error: {e}")
            return None, None
