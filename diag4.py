import fitz, os, arabic_reshaper
from bidi.algorithm import get_display

doc = fitz.open('template_cert.pdf')
page = doc[0]
print("=== EXACT ORIGINS FROM ORIGINAL PDF ===")
for b in page.get_text('dict')['blocks']:
    if b.get('type') != 0: continue
    for line in b['lines']:
        for span in line['spans']:
            t = span['text'].strip()
            if t:
                o = span['origin']
                r = span['bbox']
                ox,oy = round(o[0],2), round(o[1],2)
                bx0,by0,bx1,by1 = round(r[0]),round(r[1]),round(r[2]),round(r[3])
                c = span['color']
                print(f"origin=({ox},{oy})  bbox=({bx0},{by0},{bx1},{by1})  color={c}  | {repr(t)}")
doc.close()

print()
print("=== FONT COMPARISON ===")
fonts = {
    'tahoma':   r'C:\Windows\Fonts\tahoma.ttf',
    'segoeui':  r'C:\Windows\Fonts\segoeui.ttf',
    'calibri':  r'C:\Windows\Fonts\calibri.ttf',
    'arial':    r'C:\Windows\Fonts\arial.ttf',
}
word = get_display(arabic_reshaper.reshape('مرسيدس'))
for name, path in fonts.items():
    if os.path.exists(path):
        f = fitz.Font(fontfile=path)
        w = f.text_length(word, fontsize=6)
        print(f"{name}: text_length={w:.2f}pt  ascender={f.ascender:.3f}  descender={f.descender:.3f}")
    else:
        print(f"{name}: NOT FOUND")
