"""Download Vision 2030 and SASO logos."""
import urllib.request, os

os.makedirs('static', exist_ok=True)

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# Vision 2030 logo - official Saudi government 
urls = [
    ('https://www.vision2030.gov.sa/media/f4hlpo3j/logo-en.svg', 'vision2030.svg'),
    ('https://www.vision2030.gov.sa/media/opnhqkug/logo-ar.svg', 'vision2030_ar.svg'),
    ('https://upload.wikimedia.org/wikipedia/commons/5/5b/Saudi_Vision_2030_logo.svg', 'vision2030_wiki.svg'),
    ('https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Saudi_Vision_2030_logo.svg/512px-Saudi_Vision_2030_logo.svg.png', 'vision2030.png'),
    ('https://www.saso.gov.sa/themes/custom/saso/images/logo.svg', 'saso_logo.svg'),
    ('https://upload.wikimedia.org/wikipedia/commons/6/6a/Saudi_Standards%2C_Metrology_and_Quality_Org_%28SASO%29_Logo.svg', 'saso_wiki.svg'),
]

for url, fname in urls:
    path = f'static/{fname}'
    req = urllib.request.Request(url, headers=headers)
    try:
        r = urllib.request.urlopen(req, timeout=15)
        data = r.read()
        with open(path, 'wb') as f:
            f.write(data)
        print(f'OK {fname} ({len(data)} bytes)')
    except Exception as e:
        print(f'FAIL {fname}: {e}')
