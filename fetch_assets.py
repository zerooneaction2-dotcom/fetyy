import urllib.request, re, os

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"}

# Download JS
req = urllib.request.Request("https://pti.saso.gov.sa/apt/main.984a7b68.js", headers=headers)
r = urllib.request.urlopen(req, timeout=20)
js = r.read().decode("utf-8", "ignore")
print("JS size:", len(js))

# Find image hashes / filenames
imgs = re.findall(r'["\'](static/media/[^"\']+\.(png|svg|jpg|jpeg|gif|webp))["\']', js)
print("Found images:", len(imgs))
for i in imgs:
    print(i[0])

# Also look for data:image/svg
svgs = re.findall(r'data:image/svg\+xml[;,][^"\']{0,200}', js)
print("\nSVG data URIs:", len(svgs))
for s in svgs[:5]:
    print(s[:100])
