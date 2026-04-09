"""Capture Vision 2030 and SASO logos from pti.saso.gov.sa footer."""
from playwright.sync_api import sync_playwright
import os

os.makedirs('static', exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 900, "height": 1200})

    # The target page at soehoe-uss has the logos
    # Let's try fetching from the original barcode link
    page.goto('https://soehoe-uss.ct.ws/iv/fetyy.php?wb=112598800&i=1', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(3000)

    print(f'URL: {page.url}')
    print(f'Title: {page.title()}')

    # Get all images
    imgs = page.query_selector_all('img')
    print(f'Images: {len(imgs)}')
    import base64
    for i, img in enumerate(imgs):
        src = img.get_attribute('src') or ''
        alt = img.get_attribute('alt') or ''
        w = img.evaluate('e => e.naturalWidth')
        h = img.evaluate('e => e.naturalHeight')
        print(f'  IMG[{i}]: {w}x{h} alt="{alt}" src={src[:150]}')

        if src.startswith('data:'):
            header, data = src.split(',', 1)
            ext = 'png'
            if 'svg' in header: ext = 'svg'
            elif 'jpeg' in header: ext = 'jpg'
            fname = f'static/target_img_{i}.{ext}'
            with open(fname, 'wb') as f:
                f.write(base64.b64decode(data))
            print(f'    -> saved {fname}')
        elif src.startswith('http'):
            import urllib.request
            try:
                fname = f'static/target_img_{i}.png'
                if src.endswith('.svg'): fname = f'static/target_img_{i}.svg'
                req = urllib.request.Request(src, headers={'User-Agent':'Mozilla/5.0'})
                r = urllib.request.urlopen(req, timeout=10)
                with open(fname, 'wb') as f:
                    f.write(r.read())
                print(f'    -> downloaded {fname}')
            except Exception as e:
                print(f'    -> FAIL: {e}')
        elif src and not src.startswith('#'):
            # Relative URL
            full_url = page.evaluate(f'(el) => el.src', img)
            print(f'    full: {full_url}')
            try:
                import urllib.request
                fname = f'static/target_img_{i}.png'
                if full_url.endswith('.svg'): fname = f'static/target_img_{i}.svg'
                req = urllib.request.Request(full_url, headers={'User-Agent':'Mozilla/5.0'})
                r = urllib.request.urlopen(req, timeout=10)
                with open(fname, 'wb') as f:
                    f.write(r.read())
                print(f'    -> downloaded {fname}')
            except Exception as e:
                print(f'    -> FAIL: {e}')

    # Screenshot
    page.screenshot(path='static/target_page.png', full_page=True)
    print('Screenshot saved')

    # Save HTML
    html = page.content()
    with open('static/target_page.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'HTML: {len(html)} chars')

    browser.close()
    print('Done!')
