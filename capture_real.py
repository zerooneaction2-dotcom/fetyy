"""Capture the real PTI verification page using Playwright."""
from playwright.sync_api import sync_playwright
import os, base64, json

os.makedirs('templates/assets', exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 900, "height": 1200})

    # Navigate to the real verification page
    url = 'https://pti.saso.gov.sa/apt?plate=ZDA6890&seq=306574'
    print(f'Navigating to {url} ...')
    page.goto(url, wait_until='networkidle', timeout=60000)

    # Wait extra for React to render
    page.wait_for_timeout(5000)

    # Take full-page screenshot
    page.screenshot(path='templates/assets/real_page.png', full_page=True)
    print('Screenshot saved: templates/assets/real_page.png')

    # Save rendered HTML
    html = page.content()
    with open('templates/assets/rendered.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'HTML saved: {len(html)} chars')

    # Extract all <img> src attributes
    imgs = page.query_selector_all('img')
    print(f'\nFound {len(imgs)} <img> elements:')
    for i, img in enumerate(imgs):
        src = img.get_attribute('src') or ''
        alt = img.get_attribute('alt') or ''
        w = img.evaluate('e => e.naturalWidth')
        h = img.evaluate('e => e.naturalHeight')
        print(f'  IMG[{i}]: {w}x{h} alt="{alt}" src={src[:120]}')

        # Save base64 images
        if src.startswith('data:'):
            header, data = src.split(',', 1)
            ext = 'png'
            if 'svg' in header:
                ext = 'svg'
            elif 'jpeg' in header or 'jpg' in header:
                ext = 'jpg'
            fname = f'templates/assets/img_{i}.{ext}'
            with open(fname, 'wb') as f:
                f.write(base64.b64decode(data))
            print(f'    -> Saved {fname}')
        elif src.startswith('http'):
            # Download external image
            import urllib.request
            fname = f'templates/assets/img_{i}.png'
            try:
                urllib.request.urlretrieve(src, fname)
                print(f'    -> Downloaded {fname}')
            except Exception as e:
                print(f'    -> Download failed: {e}')

    # Extract SVG elements
    svgs = page.query_selector_all('svg')
    print(f'\nFound {len(svgs)} <svg> elements:')
    for i, svg in enumerate(svgs):
        outer = svg.evaluate('e => e.outerHTML')
        fname = f'templates/assets/svg_{i}.svg'
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(outer)
        print(f'  SVG[{i}]: {len(outer)} chars -> {fname}')

    # Extract computed styles of key elements
    print('\n--- Page title ---')
    title = page.title()
    print(f'Title: {title}')

    # Get all stylesheets content
    styles = page.evaluate('''() => {
        const sheets = [];
        for (const s of document.styleSheets) {
            try {
                const rules = [];
                for (const r of s.cssRules) rules.push(r.cssText);
                sheets.push(rules.join('\\n'));
            } catch(e) {}
        }
        return sheets;
    }''')
    with open('templates/assets/styles.css', 'w', encoding='utf-8') as f:
        for s in styles:
            f.write(s + '\n\n')
    print(f'CSS saved: {sum(len(s) for s in styles)} chars')

    # Get background colors of key sections
    print('\n--- Key element colors ---')
    elements_info = page.evaluate('''() => {
        const info = {};
        const body = document.body;
        info.body_bg = getComputedStyle(body).backgroundColor;
        const all = document.querySelectorAll('*');
        const interesting = [];
        for (const el of all) {
            const cs = getComputedStyle(el);
            const bg = cs.backgroundColor;
            const color = cs.color;
            const text = el.textContent?.trim().slice(0, 40);
            if (text && (bg !== 'rgba(0, 0, 0, 0)' || el.tagName === 'H1' || el.tagName === 'H2')) {
                interesting.push({
                    tag: el.tagName,
                    class: el.className?.slice?.(0, 60) || '',
                    bg: bg,
                    color: color,
                    text: text,
                    fontSize: cs.fontSize,
                    fontWeight: cs.fontWeight,
                });
            }
        }
        // Return first 40 interesting items
        info.elements = interesting.slice(0, 40);
        return info;
    }''')
    with open('templates/assets/elements.json', 'w', encoding='utf-8') as f:
        json.dump(elements_info, f, ensure_ascii=False, indent=2)
    print(f'Elements info saved')

    browser.close()
    print('\nDone!')
