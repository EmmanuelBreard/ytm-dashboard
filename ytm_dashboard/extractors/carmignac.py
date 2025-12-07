import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime
import re
from typing import Dict, Optional
from .base import BaseExtractor


class CarmignacExtractor(BaseExtractor):
    """Extractor for Carmignac fund YTM data (web scraping)"""

    async def extract(self, report_date: str = None) -> Dict:
        """
        Extract YTM data from Carmignac fund web page

        Args:
            report_date: Target month (YYYY-MM-01), defaults to current month

        Returns:
            Standardized result dictionary
        """
        report_date = self._get_report_date(report_date)

        try:
            async with async_playwright() as p:
                print(f"\n{'='*50}")
                print(f"Extracting: {self.fund_name}")
                print(f"{'='*50}")

                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = await context.new_page()

                # Navigate to fund page
                print("📄 Loading page...")
                await page.goto(self.url, wait_until='domcontentloaded', timeout=30000)

                # Handle modals
                print("🔓 Handling modals...")
                await self.handle_modals(page)

                # Wait for page to settle
                await asyncio.sleep(2)

                # Extract YTM
                print("🎯 Extracting YTM...")
                ytm_value = await self.extract_ytm_value(page)

                await browser.close()

                if ytm_value:
                    print(f"✅ Extracted: {ytm_value}%")
                    return self._build_result(
                        yield_to_maturity=ytm_value,
                        report_date=report_date,
                        success=True
                    )
                else:
                    print("❌ Failed to extract YTM")
                    return self._build_result(
                        report_date=report_date,
                        error="Could not find Yield to Maturity value"
                    )

        except PlaywrightTimeoutError as e:
            error = f"Timeout error: {str(e)}"
            print(f"❌ {error}")
            return self._build_result(report_date=report_date, error=error)

        except Exception as e:
            error = f"Unexpected error: {str(e)}"
            print(f"❌ {error}")
            return self._build_result(report_date=report_date, error=error)

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

    async def extract_ytm_value(self, page) -> Optional[float]:
        """
        Extract Yield to Maturity value from page
        Handles both English and French labels and number formats
        """
        search_terms = [
            "Yield to Maturity",
            "yield to maturity",
            "Rendement à maturité",
            "rendement à maturité",
            "YTM",
        ]

        try:
            content = await page.content()

            # Strategy 1: Look for text containing the label followed by percentage
            for term in search_terms:
                patterns = [
                    rf'{term}[:\s]*([0-9]+[.,][0-9]+)\s*%',
                    rf'{term}.*?([0-9]+[.,][0-9]+)\s*%',
                ]

                for pattern in patterns:
                    match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                    if match:
                        value_str = match.group(1).replace(',', '.')
                        return float(value_str)

            # Strategy 2: Use Playwright locators
            for term in search_terms:
                try:
                    label_element = page.locator(f'text="{term}"').first
                    if await label_element.count() > 0:
                        parent = label_element.locator('xpath=..')
                        parent_text = await parent.inner_text()

                        match = re.search(r'([0-9]+[.,][0-9]+)\s*%', parent_text)
                        if match:
                            value_str = match.group(1).replace(',', '.')
                            return float(value_str)
                except:
                    continue

            # Strategy 3: Search all percentage elements
            percentage_elements = await page.locator('text=/%/').all()
            for elem in percentage_elements:
                try:
                    text = await elem.inner_text()
                    parent = elem.locator('xpath=../..')
                    context_text = await parent.inner_text()

                    if any(term.lower() in context_text.lower() for term in search_terms):
                        match = re.search(r'([0-9]+[.,][0-9]+)\s*%', text)
                        if match:
                            value_str = match.group(1).replace(',', '.')
                            return float(value_str)
                except:
                    continue

        except Exception as e:
            print(f"  ⚠️  Error during YTM extraction: {str(e)}")

        return None
