from playwright.sync_api import sync_playwright
import os, base64

os.makedirs('templates/assets', exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 800, "height": 900})
    
    # Navigate and wait for content
    page.goto('https://pti.saso.gov.sa/apt?plate=ZDA6890&seq=306574', wait_until='networkidle', timeout=30000)
    
    # Take screenshot
    page.screenshot(path='templates/assets/pti_page.png', full_page=True)
    print('Screenshot saved')
    
    # Get all image elements
    imgs = page.query_selector_all('img')
    for i, img in enumerate(imgs):
        src = img.get_attribute('src') or ''
        alt = img.get_attribute('alt') or ''
        print(f'IMG {i}: src={src[:80]} alt={alt}')
    
    # Get SVG elements
    svgs = page.query_selector_all('svg')
    print(f'SVG count: {len(svgs)}')
    
    # Get full HTML
    html = page.content()
    with open('templates/assets/pti_rendered.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print('HTML saved:', len(html), 'chars')
    
    browser.close()
