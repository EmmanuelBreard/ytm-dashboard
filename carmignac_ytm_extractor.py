#!/usr/bin/env python3
"""
Carmignac Yield to Maturity Extractor

Extracts Yield to Maturity data from Carmignac fund pages, handling the 2-step modal process.
Supports both French and English pages.
"""

import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime
import re
from typing import Dict, Optional


async def extract_carmignac_ytm(url: str, headless: bool = True) -> Dict:
    """
    Extract Yield to Maturity from Carmignac fund URL

    Args:
        url: Carmignac fund page URL
        headless: Run browser in headless mode (default: True)

    Returns:
        {
            'url': str,
            'fund_name': str,
            'maturity_year': int,
            'yield_to_maturity': float,
            'extraction_date': str,
            'success': bool,
            'error': Optional[str]
        }
    """
    result = {
        'url': url,
        'fund_name': None,
        'maturity_year': None,
        'yield_to_maturity': None,
        'extraction_date': datetime.now().isoformat(),
        'success': False,
        'error': None
    }

    try:
        async with async_playwright() as p:
            # Phase 1: Launch browser and setup
            print(f"\n{'='*60}")
            print(f"Processing: {url}")
            print(f"{'='*60}")

            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()

            # Navigate to fund page
            print("📄 Loading page...")
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # Phase 2: Handle the 2-step modal
            print("🔓 Handling modals...")
            await handle_modals(page)

            # Wait for page to settle after modal acceptance
            await asyncio.sleep(2)

            # Phase 3: Extract fund name and maturity year from URL/page
            print("📊 Extracting fund details...")
            fund_name_match = re.search(r'carmignac-credit-(\d{4})', url.lower())
            if fund_name_match:
                result['maturity_year'] = int(fund_name_match.group(1))
                result['fund_name'] = f"Carmignac Crédit {fund_name_match.group(1)}"

            # Phase 3: Extract Yield to Maturity
            print("🎯 Searching for Yield to Maturity...")
            ytm_value = await extract_ytm_value(page)

            if ytm_value:
                result['yield_to_maturity'] = ytm_value
                result['success'] = True
                print(f"✅ Successfully extracted: {ytm_value}%")
            else:
                result['error'] = "Could not find Yield to Maturity value"
                print(f"❌ {result['error']}")

            await browser.close()

    except PlaywrightTimeoutError as e:
        result['error'] = f"Timeout error: {str(e)}"
        print(f"❌ {result['error']}")
    except Exception as e:
        result['error'] = f"Unexpected error: {str(e)}"
        print(f"❌ {result['error']}")

    return result


async def handle_modals(page) -> None:
    """
    Handle the 2-step modal process on Carmignac pages

    Step 1: Accept data usage terms
    Step 2: Confirm professional investor profile
    """
    try:
        # Wait a bit for modals to appear
        await asyncio.sleep(1)

        # Common modal button selectors to try
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

        # Try to click through up to 3 modal steps (accounting for cookie + 2-step process)
        for step in range(3):
            modal_clicked = False

            for selector in modal_selectors:
                try:
                    button = page.locator(selector).first
                    if await button.is_visible(timeout=2000):
                        print(f"  → Modal step {step + 1}: Clicking '{selector}'")
                        await button.click(timeout=5000)
                        modal_clicked = True
                        await asyncio.sleep(1)  # Wait for modal transition
                        break
                except:
                    continue

            if not modal_clicked:
                # No more modals found
                break

        print("  ✓ Modal handling complete")

    except Exception as e:
        print(f"  ⚠️  Modal handling warning: {str(e)}")
        # Continue anyway - page might not have modals


async def extract_ytm_value(page) -> Optional[float]:
    """
    Extract Yield to Maturity value from page
    Handles both English and French labels and number formats
    """
    # Search terms for both languages
    search_terms = [
        "Yield to Maturity",
        "yield to maturity",
        "Rendement à maturité",
        "rendement à maturité",
        "YTM",
    ]

    try:
        # Get page content
        content = await page.content()

        # Try to find YTM using various strategies

        # Strategy 1: Look for text containing the label followed by percentage
        for term in search_terms:
            # Pattern: "Label: X.XX%" or "Label X.XX%" or "Label</span>X.XX%"
            patterns = [
                rf'{term}[:\s]*([0-9]+[.,][0-9]+)\s*%',
                rf'{term}.*?([0-9]+[.,][0-9]+)\s*%',
            ]

            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                if match:
                    value_str = match.group(1).replace(',', '.')
                    return float(value_str)

        # Strategy 2: Use Playwright locators to find elements
        for term in search_terms:
            try:
                # Find element containing the term
                label_element = page.locator(f'text="{term}"').first
                if await label_element.count() > 0:
                    # Try to find nearby percentage value
                    parent = label_element.locator('xpath=..')
                    parent_text = await parent.inner_text()

                    # Extract percentage from parent text
                    match = re.search(r'([0-9]+[.,][0-9]+)\s*%', parent_text)
                    if match:
                        value_str = match.group(1).replace(',', '.')
                        return float(value_str)
            except:
                continue

        # Strategy 3: Search all elements with percentage values near YTM-related text
        percentage_elements = await page.locator('text=/%/').all()
        for elem in percentage_elements:
            try:
                # Get surrounding context
                text = await elem.inner_text()
                parent = elem.locator('xpath=../..')
                context_text = await parent.inner_text()

                # Check if context mentions yield/maturity
                if any(term.lower() in context_text.lower() for term in search_terms):
                    match = re.search(r'([0-9]+[.,][0-9]+)\s*%', text)
                    if match:
                        value_str = match.group(1).replace(',', '.')
                        return float(value_str)
            except:
                continue

        # Strategy 4: Take screenshot for debugging
        await page.screenshot(path=f'debug_screenshot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
        print("  📸 Debug screenshot saved")

    except Exception as e:
        print(f"  ⚠️  Error during YTM extraction: {str(e)}")

    return None


async def test_all_funds():
    """
    Test extraction on all three Carmignac Credit funds
    """
    urls = [
        'https://www.carmignac.com/fr-fr/nos-fonds-notre-gestion/carmignac-credit-2027-FR00140081Y1-a-eur-acc',
        'https://www.carmignac.com/en/our-funds/carmignac-credit-2029-FR001400KAV4-a-eur-acc/documents',
        'https://www.carmignac.com/fr-fr/nos-fonds-notre-gestion/carmignac-credit-2031-FR001400U4S3-a-eur-acc',
    ]

    expected_values = {
        2027: 3.90,
        2029: 4.60,
        2031: 5.10,
    }

    print("\n" + "="*60)
    print("CARMIGNAC YIELD TO MATURITY EXTRACTION TEST")
    print("="*60)

    results = []
    for url in urls:
        result = await extract_carmignac_ytm(url, headless=False)  # Set to True for production
        results.append(result)

        # Validate against expected values
        if result['success'] and result['maturity_year']:
            expected = expected_values.get(result['maturity_year'])
            if expected:
                match = abs(result['yield_to_maturity'] - expected) < 0.01
                status = "✅ MATCH" if match else "❌ MISMATCH"
                print(f"\nValidation: {status}")
                print(f"  Expected: {expected}%")
                print(f"  Extracted: {result['yield_to_maturity']}%")

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    for result in results:
        status = "✅" if result['success'] else "❌"
        ytm = f"{result['yield_to_maturity']}%" if result['yield_to_maturity'] else "N/A"
        print(f"{status} {result['fund_name']}: {ytm}")
        if result['error']:
            print(f"   Error: {result['error']}")

    success_count = sum(1 for r in results if r['success'])
    print(f"\nSuccess rate: {success_count}/{len(results)}")

    return results


if __name__ == "__main__":
    # Run the test
    results = asyncio.run(test_all_funds())
