import fitz
doc = fitz.open('template_cert.pdf')
page = doc[0]
for b in page.get_text('dict')['blocks']:
    if b.get('type') != 0:
        continue
    for line in b['lines']:
        for span in line['spans']:
            t = span['text'].strip()
            if t:
                r = span['bbox']
                x0,y0,x1,y1 = round(r[0]),round(r[1]),round(r[2]),round(r[3])
                sz = round(span['size'],1)
                print(f"({x0},{y0},{x1},{y1}) sz={sz} | {repr(t)}")
doc.close()
