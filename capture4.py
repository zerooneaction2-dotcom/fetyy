"""Fill inquiry form and capture the result page."""
from playwright.sync_api import sync_playwright
import os

os.makedirs('templates/assets', exist_ok=True)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 900, "height": 1200})

        # Go to inquiry page
        page.goto('https://pti.saso.gov.sa/apt/InspectionQuery', wait_until='networkidle', timeout=60000)
        page.wait_for_timeout(3000)
        print(f'Page loaded: {page.url}')

        # Fill VIN
        vin_input = page.query_selector('input[placeholder*="الهيكل"]')
        if vin_input:
            vin_input.fill('WDB65256215901608')
            print('VIN filled')

        # Fill serial number
        seq_input = page.query_selector('input[placeholder*="التسلسلي"]')
        if seq_input:
            seq_input.fill('306574')
            print('Serial filled')

        page.wait_for_timeout(1000)
        page.screenshot(path='templates/assets/form_filled.png', full_page=True)

        # Look for submit button
        buttons = page.query_selector_all('button')
        for btn in buttons:
            text = btn.inner_text().strip()
            print(f'  Button: "{text}"')

        # Click search/submit button
        search_btn = page.get_by_text('استعلام').first
        if not search_btn:
            search_btn = page.get_by_text('بحث').first
        if not search_btn:
            search_btn = page.get_by_role('button').last

        if search_btn:
            print(f'Clicking button...')
            search_btn.click()
            page.wait_for_timeout(8000)

            print(f'Result URL: {page.url}')
            page.screenshot(path='templates/assets/result_page.png', full_page=True)
            print('Result screenshot saved')

            html = page.content()
            with open('templates/assets/result.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print(f'Result HTML: {len(html)} chars')

            body_text = page.inner_text('body')
            with open('templates/assets/result_text.txt', 'w', encoding='utf-8') as f:
                f.write(body_text)
            print(f'Result text: {len(body_text)} chars')

            # Check for card/result elements
            all_elems = page.query_selector_all('[class*="result"], [class*="card"], [class*="status"], [class*="pass"], [class*="fail"]')
            print(f'Result-like elements: {len(all_elems)}')
            for el in all_elems:
                cls = el.get_attribute('class') or ''
                text = el.inner_text().strip()[:60]
                print(f'  .{cls}: {text}')

        browser.close()
        print('Done!')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
