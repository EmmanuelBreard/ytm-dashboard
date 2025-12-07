#!/usr/bin/env python3
"""
Rothschild Monthly Report Downloader

Downloads the latest monthly report from Rothschild & Co fund pages.
Handles the country/profile modal automatically.
"""

import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime
from pathlib import Path
import os
import re


async def handle_cookie_consent(page):
    """
    Handle the OneTrust GDPR cookie consent banner

    This banner appears before the Rothschild modal and blocks all interactions
    """
    try:
        print("🍪 Checking for cookie consent banner...")

        # Look for OneTrust cookie consent buttons
        cookie_button_selectors = [
            '#onetrust-accept-btn-handler',  # "ACCEPT ALL COOKIES"
            'button:has-text("ACCEPT ALL COOKIES")',
            'button:has-text("Autoriser tous les cookies")',
            '#onetrust-reject-all-handler',  # Fallback: reject all
        ]

        for selector in cookie_button_selectors:
            try:
                elem = page.locator(selector).first
                if await elem.is_visible(timeout=3000):
                    await elem.click()
                    await asyncio.sleep(1)
                    print(f"  ✓ Cookie consent handled: {selector}")
                    return True
            except:
                continue

        print("  ✓ No cookie banner found - may already be dismissed")
        return True

    except Exception as e:
        print(f"  ⚠️  Cookie consent handling error: {e}")
        return True  # Continue even if cookie banner not found


async def handle_rothschild_modal(page):
    """
    Handle the Rothschild country/profile modal with custom dropdowns

    The modal requires:
    1. Select country/language from custom dropdown
    2. Select profile (Professional) from custom dropdown
    3. Check acknowledgment checkbox
    4. Click submit button
    """
    try:
        print("🔍 Checking for modal...")

        # Wait for modal to appear
        modal = page.locator('section.modal#modal_disclaimer')
        if not await modal.is_visible(timeout=5000):
            print("  ✓ No modal found - may already be dismissed")
            return True

        print("  ✓ Modal detected")

        # Step 1: Select country/language "France - Français"
        # Click on the styled dropdown to open it
        print("  → Selecting country (France - Français)...")
        await page.click('#styled_filter_country_language')
        await asyncio.sleep(0.5)

        # Click on the "France - Français" option
        await page.click('ul.select-options li[rel="fr-fr"]')
        await asyncio.sleep(0.5)
        print("    ✓ Country selected")

        # Step 2: Select profile "Professionnels"
        print("  → Selecting profile (Professionnels)...")
        await page.click('#styled_filter_user_type')
        await asyncio.sleep(0.5)

        # Click on the "Professionnels" option
        await page.click('ul.select-options li[rel="professional"]')
        await asyncio.sleep(0.5)
        print("    ✓ Profile selected")

        # Step 3: Wait for checkbox to become enabled and check it
        print("  → Checking acknowledgment checkbox...")
        await page.wait_for_selector('#i_agree:not([disabled])', timeout=5000)
        await page.check('#i_agree')
        await asyncio.sleep(0.5)
        print("    ✓ Checkbox checked")

        # Step 4: Wait for submit button to become enabled and click it
        print("  → Clicking submit button...")
        await page.wait_for_selector('button.btnSubmit:not([disabled])', timeout=5000)
        await page.click('button.btnSubmit')

        # Wait for modal to close
        await page.wait_for_selector('section.modal#modal_disclaimer', state='hidden', timeout=10000)
        print("  ✓ Modal handled successfully")

        # Wait a bit for the page to settle after modal closes
        await asyncio.sleep(2)

        return True

    except Exception as e:
        print(f"  ⚠️  Modal handling error: {e}")
        # Take screenshot for debugging
        try:
            screenshot_path = f"./screenshots/modal_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await page.screenshot(path=screenshot_path)
            print(f"  📸 Error screenshot: {screenshot_path}")
        except:
            pass
        return False


async def navigate_to_reporting(page):
    """Navigate to the Reporting section/tab"""
    try:
        print("📊 Looking for Reporting section...")

        # The Reporting section might be a tab, accordion, or direct section
        # Try multiple strategies

        # Strategy 1: Look for "Reporting" tab or link
        reporting_selectors = [
            'a:has-text("Reporting")',
            'button:has-text("Reporting")',
            '[data-tab="reporting"]',
            'a[href*="reporting"]',
            '#reporting-tab'
        ]

        for selector in reporting_selectors:
            try:
                elem = page.locator(selector).first
                if await elem.is_visible(timeout=2000):
                    await elem.click()
                    await asyncio.sleep(1)
                    print(f"  ✓ Clicked Reporting tab: {selector}")
                    return True
            except:
                continue

        # Strategy 2: Scroll to find it
        print("  → Scrolling to look for Reporting section...")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        await asyncio.sleep(1)

        # Try again after scrolling
        for selector in reporting_selectors:
            try:
                elem = page.locator(selector).first
                if await elem.is_visible(timeout=2000):
                    await elem.scroll_into_view_if_needed()
                    await elem.click()
                    await asyncio.sleep(1)
                    print(f"  ✓ Found and clicked Reporting: {selector}")
                    return True
            except:
                continue

        print("  ⚠️  Could not find Reporting tab/section")
        return False

    except Exception as e:
        print(f"  ⚠️  Error navigating to Reporting: {e}")
        return False


async def select_latest_month(page):
    """Select the latest month from the dropdown"""
    try:
        print("📅 Looking for month dropdown...")

        # Standard select dropdown
        month_selectors = [
            'select[name*="month"]',
            'select[name*="date"]',
            'select[name*="period"]',
            '[class*="month-selector"] select',
            '[class*="date-selector"] select'
        ]

        for selector in month_selectors:
            try:
                elem = await page.query_selector(selector)
                if elem:
                    # Get first option (usually the latest)
                    options = await page.query_selector_all(f'{selector} option')
                    if options and len(options) > 1:  # Skip placeholder option
                        first_value = await options[1].get_attribute('value')
                        first_text = await options[1].inner_text()
                        await page.select_option(selector, value=first_value)
                        await asyncio.sleep(1)
                        print(f"  ✓ Selected month: {first_text}")
                        return first_text
            except:
                continue

        # Custom dropdown (like the modal dropdowns)
        custom_selectors = [
            '[class*="month-selector"]',
            '[class*="date-selector"]',
            '[class*="period-select"]'
        ]

        for selector in custom_selectors:
            try:
                elem = page.locator(selector).first
                if await elem.is_visible(timeout=2000):
                    await elem.click()
                    await asyncio.sleep(0.5)
                    # Click first option
                    await page.click(f'{selector} ul li:nth-child(2)')  # Skip placeholder
                    await asyncio.sleep(1)
                    print("  ✓ Selected latest month (custom dropdown)")
                    return "latest"
            except:
                continue

        print("  ⚠️  No month dropdown found - may not be required")
        return None

    except Exception as e:
        print(f"  ⚠️  Error selecting month: {e}")
        return None


async def find_and_download_report(page, output_dir):
    """Find the monthly report download link and download it"""
    try:
        print("⬇️  Looking for monthly report download...")

        # Look for PDF links related to monthly reports
        pdf_selectors = [
            'a[href$=".pdf"]:has-text("Mensuel")',
            'a[href$=".pdf"]:has-text("Monthly")',
            'a[href$=".pdf"]:has-text("Rapport")',
            'a[href$=".pdf"]:has-text("Report")',
            'a[download][href$=".pdf"]'
        ]

        report_url = None
        report_description = None

        for selector in pdf_selectors:
            try:
                elem = page.locator(selector).first
                if await elem.is_visible(timeout=2000):
                    report_url = await elem.get_attribute('href')
                    report_description = await elem.inner_text()
                    print(f"  ✓ Found report link: {report_description}")
                    break
            except:
                continue

        # If not found with text, look for all PDF links
        if not report_url:
            print("  → Checking all PDF links...")
            pdf_links = await page.query_selector_all('a[href$=".pdf"]')

            for link in pdf_links:
                try:
                    href = await link.get_attribute('href')
                    text = await link.inner_text()

                    # Look for monthly report keywords
                    if any(kw in text.lower() for kw in ['mensuel', 'monthly', 'rapport', 'report']):
                        report_url = href
                        report_description = text
                        print(f"  ✓ Found PDF: {text[:50]}")
                        break
                except:
                    continue

        if not report_url:
            raise Exception("Could not find monthly report download link")

        # Make URL absolute if needed
        if report_url.startswith('/'):
            report_url = f"https://am.eu.rothschildandco.com{report_url}"
        elif not report_url.startswith('http'):
            current_url = page.url
            base_url = '/'.join(current_url.split('/')[:3])
            report_url = f"{base_url}/{report_url}"

        # Download using API method (like Sycomore)
        print(f"  → Downloading from: {report_url}")

        try:
            response = await page.request.get(report_url)

            if response.ok:
                content = await response.body()

                # Check if it's a PDF
                if content.startswith(b'%PDF'):
                    return report_url, content, report_description
                else:
                    print(f"  ⚠️  Response is not a PDF (starts with: {content[:20]})")
                    raise Exception("Not a PDF")
            else:
                print(f"  ⚠️  API request failed: {response.status}")
                raise Exception(f"HTTP {response.status}")

        except Exception as e:
            print(f"  ⚠️  API download failed: {e}")
            print("  → Trying navigation download method...")

            # Method 2: Navigate and wait for download
            async with page.expect_download(timeout=15000) as download_info:
                await page.goto(report_url)

            download = await download_info.value
            content = await download.read_all_bytes()

            return report_url, content, report_description

    except Exception as e:
        raise Exception(f"Download failed: {e}")


def extract_fund_info(url: str) -> dict:
    """Extract fund name and maturity year from URL"""
    # Pattern: r-co-target-YYYY-ig
    match = re.search(r'r-co-target-(\d{4})-ig', url.lower())

    if match:
        maturity_year = int(match.group(1))
        fund_name = f"R-co Target {maturity_year} IG"
    else:
        fund_name = "R-co Target IG"
        maturity_year = None

    return {
        'fund_name': fund_name,
        'maturity_year': maturity_year
    }


async def download_rothschild_report(url: str, output_dir: str = "./reports", headless: bool = False) -> dict:
    """
    Download the latest monthly report from Rothschild fund page

    Args:
        url: Rothschild fund page URL
        output_dir: Directory to save downloaded reports
        headless: Run browser in headless mode

    Returns:
        {
            'url': str,
            'fund_name': str,
            'maturity_year': int,
            'report_url': str,
            'report_path': str,
            'report_description': str,
            'download_date': str,
            'success': bool,
            'error': Optional[str]
        }
    """
    result = {
        'url': url,
        'fund_name': None,
        'maturity_year': None,
        'report_url': None,
        'report_path': None,
        'report_description': None,
        'download_date': datetime.now().isoformat(),
        'success': False,
        'error': None
    }

    try:
        print(f"\n{'='*60}")
        print(f"Processing: {url}")
        print(f"{'='*60}")

        # Extract fund info from URL
        fund_info = extract_fund_info(url)
        result['fund_name'] = fund_info['fund_name']
        result['maturity_year'] = fund_info['maturity_year']

        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(
                headless=headless,
                args=['--disable-blink-features=AutomationControlled']
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                locale='fr-FR',
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                accept_downloads=True
            )

            page = await context.new_page()

            try:
                # 1. Navigate to fund page
                print("📄 Loading page...")
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(2)

                # 2. Handle GDPR cookie consent banner (appears first)
                await handle_cookie_consent(page)

                # 3. Handle Rothschild modal (country/profile selection)
                modal_handled = await handle_rothschild_modal(page)
                if not modal_handled:
                    result['error'] = "Failed to handle modal"
                    return result

                # 4. Verify we're on the fund page (modal might redirect)
                current_url = page.url
                if url.lower() not in current_url.lower():
                    print(f"  → Redirected to: {current_url}")
                    print(f"  → Navigating back to fund page...")
                    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    await asyncio.sleep(2)

                # 5. Navigate to Reporting section (if exists)
                await navigate_to_reporting(page)

                # 6. Select latest month (if dropdown exists)
                await select_latest_month(page)

                # 7. Find and download the report
                report_url, content, description = await find_and_download_report(page, output_dir)

                result['report_url'] = report_url
                result['report_description'] = description

                # Save the PDF
                timestamp = datetime.now().strftime('%Y%m')
                safe_fund_name = result['fund_name'].lower().replace(' ', '_').replace('-', '_')
                report_filename = f"{safe_fund_name}_report_{timestamp}.pdf"
                report_path = os.path.join(output_dir, report_filename)

                with open(report_path, 'wb') as f:
                    f.write(content)

                result['report_path'] = report_path
                result['success'] = True

                file_size = os.path.getsize(report_path)
                print(f"✅ Download successful!")
                print(f"   Path: {report_path}")
                print(f"   Size: {file_size:,} bytes")

            finally:
                await browser.close()

    except PlaywrightTimeoutError as e:
        result['error'] = f"Timeout error: {str(e)}"
        print(f"❌ {result['error']}")
    except Exception as e:
        result['error'] = f"Unexpected error: {str(e)}"
        print(f"❌ {result['error']}")

    return result


async def test_all_funds():
    """Test report download for all Rothschild funds"""

    urls = [
        'https://am.eu.rothschildandco.com/fr/nos-fonds/r-co-target-2028-ig/',
        'https://am.eu.rothschildandco.com/en/our-funds/r-co-target-2029-ig/'
    ]

    print("\n" + "="*60)
    print("ROTHSCHILD MONTHLY REPORT DOWNLOAD TEST")
    print("="*60)

    results = []

    for url in urls:
        result = await download_rothschild_report(url, headless=False)
        results.append(result)

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"\n{status} {result['fund_name']}")
        print(f"   URL: {result['url']}")

        if result['success']:
            print(f"   Report: {result['report_path']}")
            print(f"   Description: {result['report_description']}")
        else:
            print(f"   Error: {result['error']}")

    success_count = sum(1 for r in results if r['success'])
    print(f"\n📊 Success rate: {success_count}/{len(results)}")

    return results


if __name__ == "__main__":
    results = asyncio.run(test_all_funds())
