import fitz

doc = fitz.open('template_cert.pdf')
page = doc[0]

tests = ['مرسدس', 'مرسيدس', 'رأس', 'سيدان', 'أخضر', 'ازرق', 'أزرق', 'ازرق', 'Z D A']
for t in tests:
    r = page.search_for(t)
    print(f"search_for({repr(t)}) -> {r}")

doc.close()
