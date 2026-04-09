import fitz

doc = fitz.open('template_cert.pdf')
page = doc[0]

print('=== Colored Rects ===')
for p in page.get_drawings():
    fill = p.get('fill')
    if fill and fill != (1,1,1):
        r = p['rect']
        print(f"  ({round(r.x0)},{round(r.y0)},{round(r.x1)},{round(r.y1)})  fill={fill}")

print()
print('=== Date/field spans with origin ===')
targets = ['2026-04', '2027-04', '306574', '6890', 'WDB', '2011', '112598']
for b in page.get_text('dict')['blocks']:
    if b.get('type') != 0:
        continue
    for line in b['lines']:
        for span in line['spans']:
            t = span['text'].strip()
            if any(x in t for x in targets):
                color_int = span['color']
                r = span['bbox']
                o = span['origin']
                print(f"  origin=({round(o[0],1)},{round(o[1],1)})  bbox=({round(r[0],1)},{round(r[1],1)},{round(r[2],1)},{round(r[3],1)})  sz={span['size']}  color={color_int}  text={repr(t)}")

doc.close()
