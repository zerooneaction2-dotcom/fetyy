"""Download real logos and navigate to verification result page."""
from playwright.sync_api import sync_playwright
import os, base64, urllib.request

os.makedirs('templates/assets', exist_ok=True)
BASE = 'https://pti.saso.gov.sa/apt/'

# Step 1: Download known logos from server
logos = [
    'content/images/layout/logo.svg',
    'content/images/layout/footer-logo.svg',
    'content/images/layout/thiqa-white.png',
    'content/images/layout/digitalCov.svg',
    'content/images/icons/lang-icon.svg',
    'content/images/icons/login-icon.svg',
    'content/images/home/bg.png',
]
headers = {'User-Agent': 'Mozilla/5.0'}
for path in logos:
    url = BASE + path
    fname = 'templates/assets/' + path.replace('/', '_')
    req = urllib.request.Request(url, headers=headers)
    try:
        r = urllib.request.urlopen(req, timeout=10)
        data = r.read()
        with open(fname, 'wb') as f:
            f.write(data)
        print(f'OK {path} -> {fname} ({len(data)} bytes)')
    except Exception as e:
        print(f'FAIL {path}: {e}')

# Step 2: Navigate to inquiry page and get result
print('\n--- Playwright: navigating to inquiry ---')
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 900, "height": 1200})

        # Go to main page
        page.goto(BASE, wait_until='networkidle', timeout=60000)
        page.wait_for_timeout(3000)

        # Click on "استعلام عن حالة الفحص"
        inquiry_link = page.get_by_text('استعلام عن حالة الفحص').first
        if inquiry_link:
            print('Found inquiry link, clicking...')
            inquiry_link.click()
            page.wait_for_timeout(3000)
            page.screenshot(path='templates/assets/inquiry_page.png', full_page=True)
            print('Inquiry page screenshot saved')

            # Get URL
            print(f'Current URL: {page.url}')

            # Save HTML
            html = page.content()
            with open('templates/assets/inquiry.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print(f'Inquiry HTML: {len(html)} chars')

            # Look for form fields
            inputs = page.query_selector_all('input')
            print(f'Input fields: {len(inputs)}')
            for inp in inputs:
                name = inp.get_attribute('name') or ''
                placeholder = inp.get_attribute('placeholder') or ''
                typ = inp.get_attribute('type') or ''
                print(f'  input: name={name} type={typ} placeholder={placeholder}')

            # Try to fill plate number and sequence
            # Look for specific input fields
            all_text = page.inner_text('body')
            with open('templates/assets/inquiry_text.txt', 'w', encoding='utf-8') as f:
                f.write(all_text)

        browser.close()
        print('Done!')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
