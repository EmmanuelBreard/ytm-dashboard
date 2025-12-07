# Test Plan: Rothschild Monthly Report Download

## Objective
Verify that we can successfully:
1. Access Rothschild & Co fund pages (handling country/profile modal)
2. Navigate to the "Reporting" section
3. Select the latest month from the dropdown
4. Download the latest monthly report (PDF)

## Target URLs
1. **R-co Target 2028 IG** (FR): https://am.eu.rothschildandco.com/fr/nos-fonds/r-co-target-2028-ig/
2. **R-co Target 2029 IG** (EN): https://am.eu.rothschildandco.com/en/our-funds/r-co-target-2029-ig/

## Expected Results (from manual testing)
| Fund | Maturity | YTM | Rating |
|------|----------|-----|--------|
| R-co Target 2028 IG | 2028 | 2.85% | BBB |
| R-co Target 2029 IG | 2029 | 3.06% | BBB |
| R-co Target 2030 IG | 2030 | 3.31% | BBB |

---

## Phase 1: Initial Reconnaissance & Page Structure Analysis

### Step 1.1: Fetch and analyze page structure
```python
# Test basic HTTP access to both fund URLs
# Check initial page load behavior
# Identify if modal appears immediately or after interaction
# Document any redirects
```

### Step 1.2: Modal interaction analysis
Based on Notion screenshots, the Rothschild modal requires:
1. **Country selection**: Dropdown to select "France"
2. **Profile selection**: Radio buttons or dropdown for "Professional"
3. **Acknowledgment checkbox**: Must be checked to proceed
4. **Submit button**: Validate/confirm selection

```python
# Use Playwright to:
# - Load the page
# - Wait for modal to appear
# - Identify all form elements (selectors)
# - Document the exact flow
# - Capture cookies set after validation
```

### Step 1.3: Reporting section analysis
```python
# After modal dismissal:
# - Find the "Reporting" section/tab
# - Identify the month dropdown element
# - Document how to select latest month
# - Find the download button/link for the report
```

---

## Phase 2: Modal Handling Strategy

### Step 2.1: Document modal steps in detail
```
┌─────────────────────────────────────────┐
│           ROTHSCHILD MODAL              │
├─────────────────────────────────────────┤
│  1. Country:     [France ▼]             │
│                                         │
│  2. Profile:     ○ Individual           │
│                  ● Professional         │
│                  ○ Institutional        │
│                                         │
│  3. [✓] I acknowledge the above         │
│         information                     │
│                                         │
│         [Validate]                      │
└─────────────────────────────────────────┘
```

### Step 2.2: Test modal bypass approaches
```python
# Approach A: Cookie injection
# - If profile selection sets specific cookies, pre-inject them
# - Common cookie names: "user_profile", "country", "consent"

# Approach B: URL parameters
# - Check if ?country=fr&profile=pro works

# Approach C: LocalStorage manipulation
# - Some sites store preferences in localStorage

# Approach D: Full Playwright automation (most reliable)
# - Click through modal step by step
```

### Step 2.3: Implement modal acceptance
```python
async def handle_rothschild_modal(page):
    """Handle the Rothschild country/profile modal"""
    
    # Wait for modal
    await page.wait_for_selector('[class*="modal"]', timeout=10000)
    
    # Step 1: Select country "France"
    # Try different selector patterns:
    await page.select_option('select[name="country"]', 'FR')
    # OR for custom dropdown:
    # await page.click('[data-value="country"]')
    # await page.click('text=France')
    
    # Step 2: Select "Professional" profile
    await page.click('input[value="professional"]')
    # OR:
    # await page.click('text=Professional')
    # await page.click('label:has-text("Professional")')
    
    # Step 3: Check acknowledgment checkbox
    await page.check('input[type="checkbox"]')
    # OR:
    # await page.click('[class*="checkbox"]')
    
    # Step 4: Click validate/submit
    await page.click('button[type="submit"]')
    # OR:
    # await page.click('text=Validate')
    # await page.click('text=Valider')
    
    # Wait for modal to close
    await page.wait_for_selector('[class*="modal"]', state='hidden')
```

---

## Phase 3: Navigate to Reporting Section

### Step 3.1: Find and click Reporting tab/section
```python
# The "Reporting" section might be:
# - A tab in the fund page navigation
# - A section with anchor link
# - A separate page

# Try different approaches:
await page.click('text=Reporting')
# OR:
await page.click('a[href*="reporting"]')
# OR:
await page.click('[data-tab="reporting"]')
```

### Step 3.2: Handle month dropdown
```python
# The dropdown lists available months
# Need to select the LATEST (most recent) month

async def select_latest_month(page):
    # Open the dropdown
    await page.click('[class*="month-selector"]')
    # OR:
    await page.click('select[name="month"]')
    
    # Get all available options
    options = await page.query_selector_all('select option')
    # OR for custom dropdown:
    options = await page.query_selector_all('[class*="dropdown-item"]')
    
    # Select the first option (usually latest)
    # OR parse dates and find most recent
    await options[0].click()
```

---

## Phase 4: Report Download

### Step 4.1: Locate and click download
```python
# After selecting the month, find the download link/button
# Common patterns:
# - Direct PDF link
# - Download button that triggers download
# - Icon with download action

download_link = await page.query_selector('a[href$=".pdf"]:has-text("Report")')
# OR:
download_link = await page.query_selector('[class*="download"]')
# OR:
download_link = await page.query_selector('a:has-text("Monthly Report")')
```

### Step 4.2: Handle download
```python
async def download_report(page, output_dir):
    # Set up download handling
    async with page.expect_download() as download_info:
        await page.click('[class*="download"]')
    
    download = await download_info.value
    
    # Get suggested filename
    filename = download.suggested_filename
    
    # Save to output directory
    filepath = os.path.join(output_dir, filename)
    await download.save_as(filepath)
    
    return filepath
```

---

## Phase 5: Build Download Function

### Step 5.1: Create unified function
```python
async def download_rothschild_report(url: str, output_dir: str = "./reports") -> dict:
    """
    Download the latest monthly report from Rothschild fund page
    
    Args:
        url: Rothschild fund page URL
        output_dir: Directory to save downloaded reports
    
    Returns:
        {
            'fund_name': str,
            'maturity_year': int,
            'report_url': str,
            'report_path': str,
            'report_month': str,  # YYYY-MM format
            'download_date': str
        }
    """
```

### Step 5.2: Full implementation
```python
# rothschild_report_downloader.py

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import os
from pathlib import Path
import re

# Configuration
COUNTRY = "France"  # or "FR"
PROFILE = "Professional"  # or "professional", "pro"

async def handle_rothschild_modal(page):
    """Handle the Rothschild country/profile modal"""
    try:
        # Wait for modal (with timeout - may not appear if cookies set)
        modal = await page.wait_for_selector('[class*="modal"], [class*="popup"], [role="dialog"]', timeout=5000)
        
        if modal:
            print("Modal detected, handling...")
            
            # Step 1: Select country "France"
            # Try multiple selector strategies
            country_selectors = [
                'select[name*="country"]',
                '[class*="country"] select',
                '#country',
                '[data-field="country"]'
            ]
            for selector in country_selectors:
                try:
                    await page.select_option(selector, label='France', timeout=2000)
                    break
                except:
                    continue
            
            # Step 2: Select "Professional" profile
            profile_selectors = [
                'input[value*="professional" i]',
                'input[value*="pro" i]',
                'label:has-text("Professional")',
                'label:has-text("Professionnel")',
                '[data-profile="professional"]'
            ]
            for selector in profile_selectors:
                try:
                    await page.click(selector, timeout=2000)
                    break
                except:
                    continue
            
            # Step 3: Check acknowledgment checkbox
            checkbox_selectors = [
                'input[type="checkbox"]',
                '[class*="checkbox"]',
                '[class*="acknowledge"]'
            ]
            for selector in checkbox_selectors:
                try:
                    await page.check(selector, timeout=2000)
                    break
                except:
                    continue
            
            # Step 4: Click validate/submit
            submit_selectors = [
                'button[type="submit"]',
                'button:has-text("Validate")',
                'button:has-text("Valider")',
                'button:has-text("Confirm")',
                '[class*="submit"]'
            ]
            for selector in submit_selectors:
                try:
                    await page.click(selector, timeout=2000)
                    break
                except:
                    continue
            
            # Wait for modal to close
            await page.wait_for_selector('[class*="modal"]', state='hidden', timeout=5000)
            print("Modal handled successfully")
            
        return True
        
    except Exception as e:
        print(f"Modal handling: {e} (may already be dismissed)")
        return True  # Continue even if modal not found

async def navigate_to_reporting(page):
    """Navigate to the Reporting section"""
    reporting_selectors = [
        'a:has-text("Reporting")',
        '[data-tab="reporting"]',
        'a[href*="reporting"]',
        'button:has-text("Reporting")',
        '#reporting-tab'
    ]
    
    for selector in reporting_selectors:
        try:
            await page.click(selector, timeout=3000)
            await page.wait_for_timeout(1000)  # Wait for section to load
            print(f"Clicked Reporting tab with selector: {selector}")
            return True
        except:
            continue
    
    print("Warning: Could not find Reporting tab, may already be on correct page")
    return False

async def select_latest_month(page):
    """Select the latest month from the dropdown"""
    # First, try to find and open the month dropdown
    dropdown_selectors = [
        'select[name*="month"]',
        'select[name*="date"]',
        '[class*="month-selector"]',
        '[class*="date-selector"]',
        '[class*="period-selector"]'
    ]
    
    for selector in dropdown_selectors:
        try:
            dropdown = await page.query_selector(selector)
            if dropdown:
                # Get all options
                options = await page.query_selector_all(f'{selector} option')
                if options and len(options) > 0:
                    # Select first option (usually latest)
                    first_value = await options[0].get_attribute('value')
                    await page.select_option(selector, value=first_value)
                    print(f"Selected month: {first_value}")
                    return first_value
        except:
            continue
    
    # Try custom dropdown (non-select element)
    custom_dropdown_selectors = [
        '[class*="dropdown"]:has-text("month")',
        '[class*="dropdown"]:has-text("mois")',
        '[class*="select-period"]'
    ]
    
    for selector in custom_dropdown_selectors:
        try:
            await page.click(selector, timeout=2000)
            await page.wait_for_timeout(500)
            # Click first item
            await page.click('[class*="dropdown-item"]:first-child')
            return "latest"
        except:
            continue
    
    print("Warning: Could not find month dropdown")
    return None

async def find_and_download_report(page, context, output_dir):
    """Find the monthly report download link and download it"""
    
    # Possible selectors for the monthly report download
    report_selectors = [
        'a[href$=".pdf"]:has-text("Monthly")',
        'a[href$=".pdf"]:has-text("Mensuel")',
        'a[href$=".pdf"]:has-text("Report")',
        'a[href$=".pdf"]:has-text("Rapport")',
        '[class*="download"]:has-text("Monthly")',
        '[class*="download"]:has-text("Report")',
        'a[href*="monthly"]',
        'a[href*="reporting"]',
        '[data-document-type="monthly-report"]'
    ]
    
    for selector in report_selectors:
        try:
            download_link = await page.query_selector(selector)
            if download_link:
                href = await download_link.get_attribute('href')
                print(f"Found report link: {href}")
                
                # Start download
                async with page.expect_download(timeout=30000) as download_info:
                    await download_link.click()
                
                download = await download_info.value
                
                # Save file
                filename = download.suggested_filename or f"rothschild_report_{datetime.now().strftime('%Y%m%d')}.pdf"
                filepath = os.path.join(output_dir, filename)
                await download.save_as(filepath)
                
                print(f"Downloaded: {filepath}")
                return filepath, href
                
        except Exception as e:
            print(f"Selector {selector} failed: {e}")
            continue
    
    # If no direct download, try to find PDF link and download separately
    pdf_links = await page.query_selector_all('a[href$=".pdf"]')
    if pdf_links:
        for link in pdf_links:
            text = await link.inner_text()
            if any(kw in text.lower() for kw in ['monthly', 'mensuel', 'report', 'rapport']):
                href = await link.get_attribute('href')
                
                # Make URL absolute if needed
                if href.startswith('/'):
                    href = f"https://am.eu.rothschildandco.com{href}"
                
                # Download via new page
                download_page = await context.new_page()
                async with download_page.expect_download() as download_info:
                    await download_page.goto(href)
                
                download = await download_info.value
                filename = download.suggested_filename or f"rothschild_report.pdf"
                filepath = os.path.join(output_dir, filename)
                await download.save_as(filepath)
                await download_page.close()
                
                return filepath, href
    
    raise Exception("Could not find monthly report download link")

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

async def download_rothschild_report(url: str, output_dir: str = "./reports") -> dict:
    """
    Download the latest monthly report from Rothschild fund page
    
    Args:
        url: Rothschild fund page URL
        output_dir: Directory to save downloaded reports
    
    Returns:
        dict with download details
    """
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Extract fund info from URL
    fund_info = extract_fund_info(url)
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)  # Set True for production
        context = await browser.new_context(
            accept_downloads=True,
            locale='fr-FR'
        )
        page = await context.new_page()
        
        try:
            # 1. Navigate to fund page
            print(f"Navigating to: {url}")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # 2. Handle modal (country + profile + checkbox)
            await handle_rothschild_modal(page)
            
            # 3. Wait for page to fully load after modal
            await page.wait_for_timeout(2000)
            
            # 4. Navigate to Reporting section
            await navigate_to_reporting(page)
            await page.wait_for_timeout(1000)
            
            # 5. Select latest month from dropdown
            selected_month = await select_latest_month(page)
            await page.wait_for_timeout(1000)
            
            # 6. Find and download the report
            report_path, report_url = await find_and_download_report(page, context, output_dir)
            
            result = {
                'url': url,
                'fund_name': fund_info['fund_name'],
                'maturity_year': fund_info['maturity_year'],
                'report_url': report_url,
                'report_path': report_path,
                'report_month': selected_month,
                'download_date': datetime.now().isoformat()
            }
            
            return result
            
        finally:
            await browser.close()

async def test_all_rothschild_funds():
    """Test report download for all Rothschild funds"""
    urls = [
        'https://am.eu.rothschildandco.com/fr/nos-fonds/r-co-target-2028-ig/',
        'https://am.eu.rothschildandco.com/en/our-funds/r-co-target-2029-ig/'
    ]
    
    results = []
    for url in urls:
        print(f"\n{'='*60}")
        print(f"Processing: {url}")
        print('='*60)
        
        try:
            result = await download_rothschild_report(url)
            results.append(result)
            print(f"✅ Success: {result['fund_name']}")
            print(f"   Report saved: {result['report_path']}")
        except Exception as e:
            print(f"❌ Failed: {e}")
            results.append({
                'url': url,
                'error': str(e)
            })
    
    return results

# Run the test
if __name__ == "__main__":
    results = asyncio.run(test_all_rothschild_funds())
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for r in results:
        if 'error' in r:
            print(f"❌ {r['url']}: {r['error']}")
        else:
            print(f"✅ {r['fund_name']}: {r['report_path']}")
```

---

## Phase 6: Validation & Error Handling

### Step 6.1: Validate downloaded reports
```python
def validate_pdf(filepath):
    """Verify the downloaded file is a valid PDF"""
    import PyPDF2
    
    # Check file exists
    if not os.path.exists(filepath):
        return False, "File does not exist"
    
    # Check file size (should be > 10KB)
    size = os.path.getsize(filepath)
    if size < 10 * 1024:
        return False, f"File too small: {size} bytes"
    
    # Check PDF magic bytes
    with open(filepath, 'rb') as f:
        header = f.read(4)
        if header != b'%PDF':
            return False, "Not a valid PDF file"
    
    # Try to open and read PDF
    try:
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            num_pages = len(reader.pages)
            if num_pages < 1:
                return False, "PDF has no pages"
        return True, f"Valid PDF with {num_pages} pages"
    except Exception as e:
        return False, f"PDF parsing error: {e}"
```

### Step 6.2: Error handling considerations
```python
# Handle:
# - Network timeouts (increase timeout for slow connections)
# - Modal not appearing (cookies already set)
# - Modal variations (different form fields per locale)
# - Reporting tab not found (different page structure)
# - Month dropdown not found (different implementation)
# - Download failures (network issues, rate limiting)
# - PDF corruption (retry download)
# - Rate limiting (add delays between requests)
# - Language variations (FR: "Mensuel", EN: "Monthly")
# - Dynamic content loading (wait for JavaScript)
```

---

## Success Metrics

- ✅ Successfully access both Rothschild fund pages
- ✅ Automatically handle the country/profile modal
  - Select France as country
  - Select Professional as profile
  - Check acknowledgment checkbox
  - Click validate
- ✅ Navigate to the "Reporting" section
- ✅ Select the latest month from dropdown
- ✅ Download PDF reports for both funds
- ✅ PDFs are valid and readable
- ✅ Script runs without manual intervention
- ✅ Execution time < 90 seconds for both funds

---

## Comparison: All Three Providers

| Aspect | Carmignac | Sycomore | Rothschild |
|--------|-----------|----------|------------|
| **Modal type** | 2-step: data usage + investor profile | Investor type + Country | Country + Profile + Checkbox |
| **Modal complexity** | Medium | Simple | Medium-High |
| **Data location** | On-page (YTM visible) | In PDF report | In PDF report |
| **Report access** | Direct on page | Download PDF | Reporting section → Dropdown → Download |
| **Language** | FR + EN URLs | FR only | FR + EN URLs |
| **Extra step** | None | None | Month dropdown selection |
| **Expected YTM** | 3.90% - 5.10% | 4.90% | 2.85% - 3.31% |

---

## Key Notes for Rothschild

1. **Modal has 3 components**: Country dropdown, Profile selection, AND acknowledgment checkbox - all must be completed
2. **Reporting section**: Not immediately visible - need to navigate to a specific tab/section
3. **Month dropdown**: Critical step - must select the latest month before downloading
4. **Two languages**: FR URLs use "nos-fonds", EN URLs use "our-funds" - selectors may vary
5. **Session persistence**: Consider saving cookies after modal to speed up subsequent runs
6. **Professional profile**: Required to access institutional-grade reports

---

## Debugging Tips

```python
# If modal handling fails, capture screenshot
await page.screenshot(path='debug_modal.png')

# If Reporting section not found, print page content
content = await page.content()
with open('debug_page.html', 'w') as f:
    f.write(content)

# If download fails, log all PDF links found
pdf_links = await page.query_selector_all('a[href$=".pdf"]')
for link in pdf_links:
    href = await link.get_attribute('href')
    text = await link.inner_text()
    print(f"PDF: {text} -> {href}")
```
