#!/usr/bin/env python3
"""
Sycomore Monthly Report Downloader

Downloads the latest monthly report from Sycomore fund pages.
Uses cookie-based authentication to bypass the investor profile modal.
"""

import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime
from pathlib import Path
import os


async def download_sycomore_report(url: str, output_dir: str = "./reports", headless: bool = False) -> dict:
    """
    Download the latest monthly report from Sycomore fund page

    Args:
        url: Sycomore fund page URL
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
        if "2030" in url:
            result['fund_name'] = "Sycoyield 2030"
            result['maturity_year'] = 2030
        elif "2032" in url:
            result['fund_name'] = "Sycoyield 2032"
            result['maturity_year'] = 2032

        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        async with async_playwright() as p:
            # Launch browser with stealth settings
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

            # INJECT THE GUEST_PROFILE COOKIE TO BYPASS MODAL
            print("🍪 Injecting guest_profile cookie...")
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
            print("  ✓ Cookie injected - modal should be bypassed")

            page = await context.new_page()

            # Navigate to page (modal should not appear due to cookie)
            print("📄 Loading page...")
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)

            # Check if modal appeared (it shouldn't)
            try:
                modal = page.locator('text="Configurer mon profil"')
                if await modal.is_visible(timeout=2000):
                    print("  ⚠️  Modal still appeared despite cookie")
                else:
                    print("  ✓ No modal - cookie worked!")
            except:
                print("  ✓ No modal - cookie worked!")

            # Now search for report download links
            print("📊 Searching for monthly report...")

            # Scroll to Documentation section
            try:
                doc_section = page.locator('text="Documentation"').first
                await doc_section.scroll_into_view_if_needed()
                await asyncio.sleep(1)
                print("  ✓ Found Documentation section")
            except:
                print("  ⚠️  Could not find Documentation section")

            # Strategy 1: Look for "Voir le dernier reporting" button
            # This is the button that downloads the latest report
            try:
                report_button = page.locator('a:has-text("Voir le dernier reporting")').first
                if await report_button.is_visible(timeout=3000):
                    href = await report_button.get_attribute('href')
                    print(f"  ✓ Found 'Voir le dernier reporting' button")
                    print(f"    URL: {href}")

                    result['report_url'] = href
                    result['report_description'] = "Dernier reporting mensuel"
                else:
                    print("  ⚠️  'Voir le dernier reporting' button not visible")
            except Exception as e:
                print(f"  ⚠️  Error finding reporting button: {str(e)[:100]}")

            # Strategy 2: Look for direct reporting download URLs
            if not result['report_url']:
                print("  → Looking for reporting download links...")
                try:
                    # The pattern is: /telecharger/reporting/{fund_id}/{variant_id}
                    reporting_links = await page.locator('a[href*="/telecharger/reporting/"]').all()
                    if reporting_links:
                        first_link = reporting_links[0]
                        href = await first_link.get_attribute('href')
                        text = await first_link.inner_text()
                        print(f"  ✓ Found reporting link: {text.strip()}")
                        result['report_url'] = href
                        result['report_description'] = text.strip()
                except Exception as e:
                    print(f"  ⚠️  Error: {e}")

            # Strategy 2: Look for any clickable elements in Documentation section
            if not result['report_description']:
                print("  → Looking for clickable document cards...")

                try:
                    # Look for all clickable elements with download icons or buttons
                    download_buttons = await page.locator('[class*="download"], a[download], button:has-text("Télécharger")').all()
                    print(f"  Found {len(download_buttons)} download elements")

                    for btn in download_buttons[:5]:  # Check first 5
                        try:
                            text = await btn.inner_text()
                            if text.strip():
                                print(f"    - {text.strip()[:50]}")
                        except:
                            pass
                except:
                    pass

            # Strategy 3: Look for direct PDF links (might appear after scrolling)
            pdf_links = await page.locator('a[href$=".pdf"]').all()
            print(f"  Found {len(pdf_links)} PDF links")

            if pdf_links and not result['report_url']:
                for link in pdf_links:
                    try:
                        href = await link.get_attribute('href')
                        text = await link.inner_text()

                        # Look for monthly report keywords
                        if any(keyword in text.lower() for keyword in ['mensuel', 'monthly']):
                            print(f"  ✓ Found PDF: {text.strip()}")
                            result['report_url'] = href if href.startswith('http') else f"https://fr.sycomore-am.com{href}"
                            result['report_description'] = text.strip()
                            break
                    except:
                        continue

            if not result['report_url']:
                result['error'] = "Could not find report download link"
                print(f"❌ {result['error']}")

                # Take debug screenshot
                screenshot_path = f"debug_cookie_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"📸 Debug screenshot: {screenshot_path}")

                await browser.close()
                return result

            # Download the PDF
            print(f"⬇️  Downloading: {result['report_url']}")

            try:
                # Generate filename
                timestamp = datetime.now().strftime('%Y%m')
                safe_fund_name = result['fund_name'].lower().replace(' ', '_')
                report_filename = f"{safe_fund_name}_report_{timestamp}.pdf"
                report_path = os.path.join(output_dir, report_filename)

                # Method 1: Try using Playwright's page.request to download with cookies
                try:
                    print("  → Attempting direct API download...")
                    response = await page.request.get(result['report_url'])

                    if response.ok:
                        content = await response.body()

                        # Check if it's a PDF (starts with %PDF)
                        if content.startswith(b'%PDF'):
                            with open(report_path, 'wb') as f:
                                f.write(content)

                            result['report_path'] = report_path
                            result['success'] = True

                            file_size = os.path.getsize(report_path)
                            print(f"✅ Download successful (API method)!")
                            print(f"   Path: {report_path}")
                            print(f"   Size: {file_size:,} bytes")
                        else:
                            print(f"  ⚠️  Response is not a PDF (starts with: {content[:20]})")
                            print("  → Trying navigation download method...")
                            raise Exception("Not a PDF")
                    else:
                        print(f"  ⚠️  API request failed: {response.status}")
                        raise Exception(f"HTTP {response.status}")

                except Exception as e:
                    print(f"  ⚠️  API download failed: {e}")

                    # Method 2: Navigate and wait for download
                    if not result['success']:
                        print("  → Trying navigation download method...")
                        download_page = await context.new_page()

                        try:
                            async with download_page.expect_download(timeout=10000) as download_info:
                                await download_page.goto(result['report_url'])

                            download = await download_info.value
                            await download.save_as(report_path)

                            result['report_path'] = report_path
                            result['success'] = True

                            file_size = os.path.getsize(report_path)
                            print(f"✅ Download successful (navigation method)!")
                            print(f"   Path: {report_path}")
                            print(f"   Size: {file_size:,} bytes")

                        except Exception as nav_error:
                            result['error'] = f"Both download methods failed: {nav_error}"
                            print(f"❌ {result['error']}")

            except Exception as e:
                result['error'] = f"Download failed: {str(e)}"
                print(f"❌ {result['error']}")

            await browser.close()

    except PlaywrightTimeoutError as e:
        result['error'] = f"Timeout error: {str(e)}"
        print(f"❌ {result['error']}")
    except Exception as e:
        result['error'] = f"Unexpected error: {str(e)}"
        print(f"❌ {result['error']}")

    return result


async def test_all_funds():
    """Test report download for all Sycomore funds"""

    urls = [
        'https://fr.sycomore-am.com/fonds/53/sycoyield-2030/169',
        'https://fr.sycomore-am.com/fonds/58/sycoyield-2032/187'
    ]

    print("\n" + "="*60)
    print("SYCOMORE MONTHLY REPORT DOWNLOAD TEST (COOKIE METHOD)")
    print("="*60)

    results = []

    for url in urls:
        result = await download_sycomore_report(url, headless=False)
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
