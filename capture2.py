"""Capture the real PTI page and extract assets."""
from playwright.sync_api import sync_playwright
import os, base64, traceback

os.makedirs('templates/assets', exist_ok=True)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 900, "height": 1200})
        print("Browser launched")

        page.goto(
            "https://pti.saso.gov.sa/apt?plate=ZDA6890&seq=306574",
            wait_until="networkidle",
            timeout=60000,
        )
        print("Page loaded")
        page.wait_for_timeout(5000)

        page.screenshot(path="templates/assets/real_page.png", full_page=True)
        print("Screenshot saved")

        html = page.content()
        with open("templates/assets/rendered.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"HTML: {len(html)} chars")

        # Extract images
        imgs = page.query_selector_all("img")
        print(f"Images: {len(imgs)}")
        for i, img in enumerate(imgs):
            src = img.get_attribute("src") or ""
            alt = img.get_attribute("alt") or ""
            print(f"  IMG[{i}] alt={alt} src={src[:120]}")
            if src.startswith("data:"):
                header, data = src.split(",", 1)
                ext = "svg" if "svg" in header else "png"
                fname = f"templates/assets/img_{i}.{ext}"
                with open(fname, "wb") as f:
                    f.write(base64.b64decode(data))
                print(f"    -> saved {fname}")
            elif src.startswith("http"):
                import urllib.request
                fname = f"templates/assets/img_{i}.png"
                try:
                    urllib.request.urlretrieve(src, fname)
                    print(f"    -> downloaded {fname}")
                except Exception as e2:
                    print(f"    -> download failed: {e2}")

        # Extract SVGs
        svgs = page.query_selector_all("svg")
        print(f"SVGs: {len(svgs)}")
        for i, svg in enumerate(svgs):
            outer = svg.evaluate("e => e.outerHTML")
            fname = f"templates/assets/svg_{i}.svg"
            with open(fname, "w", encoding="utf-8") as f:
                f.write(outer)
            print(f"  SVG[{i}] {len(outer)} chars -> {fname}")

        # Get page title
        print(f"Page title: {page.title()}")

        # Get visible text
        body_text = page.inner_text("body")
        with open("templates/assets/page_text.txt", "w", encoding="utf-8") as f:
            f.write(body_text)
        print(f"Body text: {len(body_text)} chars")

        browser.close()
        print("Done!")

except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
