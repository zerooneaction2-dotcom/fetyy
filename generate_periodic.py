#!/usr/bin/env python3
"""
توليد وثيقة الفحص الفني الدوري — تعديل مباشر على ملف PDF الأصلي
المتطلبات: pip install pymupdf arabic-reshaper python-bidi flask
"""

import fitz  # PyMuPDF
import arabic_reshaper
from bidi.algorithm import get_display
import os
import io

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
# خط عربي Regular (ليس Light) ليطابق سمك الأصل
ARABIC_FONT = os.path.join(BASE_DIR, "Cairo-Regular.ttf")
if not os.path.exists(ARABIC_FONT):
    ARABIC_FONT = r"C:\Windows\Fonts\segoeui.ttf"
if not os.path.exists(ARABIC_FONT):
    ARABIC_FONT = r"C:\Windows\Fonts\tahoma.ttf"

RED       = (0.78, 0.16, 0.16)
GREEN     = (0.18, 0.49, 0.13)
CYAN      = (0.0,  0.59, 0.53)
BLACK     = (0.0,  0.0,  0.0)
WHITE     = (1.0,  1.0,  1.0)
GRAY_CELL = (0.341, 0.341, 0.341)   # لون حروف insp_date الأصلية (vector paths)
TEAL_CELL = (0.0, 0.5843, 0.7098)   # لون الـsidebar وحروف exp_date الأصلية
DARK_TEXT = (0.2549, 0.2784, 0.2431) # لون النصوص العربية في جسم الوثيقة (من التشخيص)


def ar(text):
    return get_display(arabic_reshaper.reshape(str(text)))


class PDFEditor:
    def __init__(self, path):
        self.doc  = fitz.open(path)
        self.page = self.doc[0]
        # تحميل الخط العربي كـ Font object (يعمل حتى بعد apply_redactions)
        if os.path.exists(ARABIC_FONT):
            self._font = fitz.Font(fontfile=ARABIC_FONT)
        else:
            raise RuntimeError(f"لم يُعثر على خط عربي في: {ARABIC_FONT}")
        self._fn = None  # لا نزال نحتاجه للتوافق

    def _redact(self, rects, fill=(1, 1, 1)):
        for r in rects:
            self.page.add_redact_annot(r, fill=fill)
        self.page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

    def _insert(self, point, text, fontsize, color, arabic=False):
        """إدراج نص باستخدام TextWriter لضمان عمل الخط."""
        tw   = fitz.TextWriter(self.page.rect)
        font = self._font if arabic else fitz.Font("helv")
        tw.append(point, text, font=font, fontsize=fontsize)
        tw.write_text(self.page, color=color)

    def replace(self, old, new, color=BLACK, arabic=False, bg_color=None, fontsize=None):
        """ابحث عن نص قديم وضع نصاً جديداً مكانه."""
        rects = self.page.search_for(old)
        if not rects:
            return False
        fill = bg_color if bg_color is not None else (1, 1, 1)
        self._redact(rects, fill=fill)
        rect = rects[0]
        fs   = fontsize if fontsize is not None else max(rect.height * 0.72, 6)
        text = ar(new) if arabic else str(new)
        self._insert(fitz.Point(rect.x0, rect.y1), text, fs, color, arabic)
        return True

    def replace_at(self, bbox, new, fontsize=6, color=BLACK, arabic=False):
        """استبدال نص في منطقة محددة. bbox=(x0,y0,x1,baseline_y)."""
        x0, y0, x1, baseline_y = bbox
        rect = fitz.Rect(x0, y0, x1, baseline_y + 2)  # +2 للحد السفلي (تضمين descender)
        self._redact([rect])
        if arabic:
            text  = ar(new)
            tw    = fitz.TextWriter(self.page.rect)
            font  = self._font
            text_w = font.text_length(text, fontsize=fontsize)
            # تحديد نقطة بداية النص بحيث يكون الحافة اليمنى = x1
            start_x = max(x0, x1 - text_w)
            tw.append(fitz.Point(start_x, baseline_y), text, font=font, fontsize=fontsize)
            tw.write_text(self.page, color=color)
        else:
            self._insert(fitz.Point(x0, baseline_y), str(new), fontsize, color, arabic=False)

    def get_text_blocks(self):
        """إرجاع قائمة بكل النصوص وإحداثياتها — للتشخيص."""
        blocks = []
        for b in self.page.get_text("dict")["blocks"]:
            if b.get("type") == 0:
                for line in b["lines"]:
                    for span in line["spans"]:
                        t = span["text"].strip()
                        if t:
                            blocks.append({"text": t, "bbox": span["bbox"],
                                           "size": round(span["size"], 1)})
        return blocks

    def to_bytes(self, title=""):
        if title:
            self.doc.set_metadata({"title": title, "producer": "FETIY", "creator": "FETIY"})
        buf = io.BytesIO()
        self.doc.save(buf, garbage=4, deflate=True, clean=True)
        self.doc.close()
        buf.seek(0)
        return buf.read()

    def save(self, path):
        self.doc.save(path, garbage=4, deflate=True, clean=True)
        self.doc.close()


# ── منطق التعديل ─────────────────────────────────────────────────────────────

def build_cert(inp: dict) -> bytes:
    """عدّل template_cert.pdf وأعد المحتوى كـ bytes."""
    path = os.path.join(BASE_DIR, "template_cert.pdf")
    if not os.path.exists(path):
        raise FileNotFoundError("template_cert.pdf غير موجود")

    ed = PDFEditor(path)

    # ── حقول قابلة للتعديل (موجودة في طبقة النص) ──────────────────────────
    # التواريخ — يجب استبدالها كسلسلة كاملة قبل أي شيء آخر
    # تاريخ الفحص: خلفية TEAL (لون الـsidebar الأصلي) + نص رمادي كالحروف الأصلية
    ed.replace("2026-04-08", inp.get("insp_date", ""), GRAY_CELL,
               bg_color=TEAL_CELL, fontsize=6.0)
    # تاريخ الانتهاء: خلفية بيضاء (صندوق التحقق) + نص فيروزي كالحروف الأصلية
    ed.replace("2027-04-08", inp.get("exp_date",   ""), TEAL_CELL,
               bg_color=WHITE, fontsize=7.2)

    # بيانات المركبة الرقمية — كلها بلون DARK_TEXT (0x41473E) مطابق للأصل
    ed.replace("Z D A 6890",        inp.get("plate",    ""), DARK_TEXT)
    ed.replace("306574",            inp.get("seq_no",   ""), RED)
    ed.replace("WDB65256215901608", inp.get("vin",      ""), DARK_TEXT)
    ed.replace("2011",              inp.get("year",     ""), DARK_TEXT)
    ed.replace("112598800",         inp.get("odometer", ""), DARK_TEXT)

    # ── حقول عربية مجزأة (لا تعمل معها search_for) — replace_at مع محاذاة يمين ──
    # الشركة الصانعة: x0=309 x1=339  baseline=134.73 (origin.y من الPDF الأصلي)
    if inp.get("maker"):
        ed.replace_at((309, 128, 339, 134.73), inp["maker"], fontsize=6.0, color=DARK_TEXT, arabic=True)
    # نوع السيارة: x0=329 x1=339  baseline=144.33 (origin.y من الPDF الأصلي)
    if inp.get("car_type"):
        ed.replace_at((309, 138, 339, 144.33), inp["car_type"], fontsize=6.0, color=DARK_TEXT, arabic=True)
    # اللون: x0=163 x1=189  baseline=143.73 (origin.y من الPDF الأصلي)
    if inp.get("color"):
        ed.replace_at((155, 137, 189, 143.73), inp["color"], fontsize=6.0, color=DARK_TEXT, arabic=True)

    # ── ملاحظة: الحقول التالية مخزّنة كصور لا يمكن تعديلها ──
    # الرقم التسلسلي للوثيقة، رقم المسار، رقم الفاحص، رقم البندكرة،
    # رقم المحاولة، موقع الفحص

    return ed.to_bytes(title="Vehicle Inspection Certificate")


def build_sticker(inp: dict, base_url: str = "https://fetyy.onrender.com") -> bytes:
    """عدّل template_sticker.pdf وأعد المحتوى كـ bytes."""
    path = os.path.join(BASE_DIR, "template_sticker.pdf")
    if not os.path.exists(path):
        raise FileNotFoundError("template_sticker.pdf غير موجود")

    ed = PDFEditor(path)
    barcode_id = inp.get("odometer", "000000")
    ed.replace("112598800", barcode_id, BLACK)

    # ── معرّف فريد لكل توليد (عدّاد + رقم عشوائي) ──
    import random
    unique_id = f"{barcode_id}_{random.randint(100000, 999999)}"
    inp["_uid"] = unique_id  # يُحفظ مع البيانات للمزامنة

    # ── بناء رابط التحقق بمعرّف فريد ──
    verify_url = f"{base_url}/iv/fetyy.php?wb={unique_id}"

    # ── توليد QR Code جديد بالرابط القصير ──
    import qrcode
    from PIL import Image as PILImage
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=2)
    qr.add_data(verify_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("L")
    # تغيير حجم الصورة لتطابق الأصلية 155x155
    qr_img = qr_img.resize((155, 155), PILImage.NEAREST)
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)

    # استبدال QR Code القديم (bbox≈113,197,324,408)
    qr_rect = fitz.Rect(113.06, 197.79, 324.0, 408.73)
    # حذف صورة QR القديمة (xref=11, 155x155) عبر استبدالها بصورة بيضاء صغيرة
    for img in ed.page.get_images(full=True):
        xref = img[0]
        info = ed.doc.extract_image(xref)
        if info and info["width"] == 155 and info["height"] == 155:
            # استبدال الصورة القديمة بصورة بيضاء 1x1
            from PIL import Image as PILImage2
            blank = PILImage2.new("L", (1, 1), 255)
            blank_buf = io.BytesIO()
            blank.save(blank_buf, format="PNG")
            ed.doc._deleteObject(xref)
            break
    ed.page.add_redact_annot(qr_rect, fill=(1, 1, 1))
    ed.page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
    ed.page.insert_image(qr_rect, stream=qr_buf.read())

    # ── توليد باركود خطي جديد واستبدال القديم ──
    import barcode as barcode_lib
    from barcode.writer import ImageWriter
    Code128 = barcode_lib.get_barcode_class('code128')
    bc_writer = ImageWriter()
    bc_opts = {
        'module_height': 15.0,
        'module_width': 0.33,
        'font_size': 0,
        'text_distance': 0,
        'quiet_zone': 2.0,
        'write_text': False,
        'dpi': 300,
    }
    bc = Code128(barcode_id, writer=bc_writer)
    bc_buf = io.BytesIO()
    bc.write(bc_buf, options=bc_opts)
    bc_buf.seek(0)
    # تغيير حجم الصورة لتطابق الأصلية 196x80
    bc_img = PILImage.open(bc_buf).convert("L").resize((196, 80), PILImage.NEAREST)
    bc_buf2 = io.BytesIO()
    bc_img.save(bc_buf2, format="PNG")
    bc_buf2.seek(0)

    # استبدال باركود خطي القديم (bbox≈392,407,487,449)
    bc_rect = fitz.Rect(392.06, 407.41, 486.98, 449.60)
    # حذف صورة الباركود القديمة (196x80)
    for img in ed.page.get_images(full=True):
        xref = img[0]
        info = ed.doc.extract_image(xref)
        if info and info["width"] == 196 and info["height"] == 80:
            ed.doc._deleteObject(xref)
            break
    ed.page.add_redact_annot(bc_rect, fill=(1, 1, 1))
    ed.page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
    ed.page.insert_image(bc_rect, stream=bc_buf2.read())

    # ربط منطقة QR Code برابط التحقق
    link_rect = fitz.Rect(113, 197, 530, 475)
    link = {"kind": fitz.LINK_URI, "from": link_rect, "uri": verify_url}
    ed.page.insert_link(link)

    return ed.to_bytes(title="Vehicle Inspection Sticker")


def get_blocks(filename: str) -> list:
    path = os.path.join(BASE_DIR, filename)
    ed = PDFEditor(path)
    blocks = ed.get_text_blocks()
    ed.doc.close()
    return blocks


# ── واجهة سطر الأوامر (للاختبار السريع) ─────────────────────────────────────

if __name__ == "__main__":
    def gi(prompt, default=""):
        v = input(f"  {prompt} [{default}]: ").strip()
        return v or default

    inp = {
        "serial":    gi("الرقم التسلسلي",    "11-002-8263-92584"),
        "insp_date": gi("تاريخ الفحص",       "2026-04-08"),
        "exp_date":  gi("تاريخ الانتهاء",    "2027-04-08"),
        "location":  gi("موقع الفحص",        "الرياض"),
        "lane":      gi("رقم المسار",         "08"),
        "inspector": gi("رقم الفاحص",         "023"),
        "plate":     gi("رقم اللوحة",         "Z D A 6890"),
        "vin":       gi("رقم الهيكل",         "WDB65256215901608"),
        "maker":     gi("الشركة الصانعة",     "مرسدس"),
        "car_type":  gi("نوع السيارة",        "رأس"),
        "seq_no":    gi("الرقم التسلسلي",     "306574"),
        "year":      gi("سنة الصنع",          "2011"),
        "color":     gi("اللون",              "أخضر/ ازرق"),
        "odometer":  gi("قراءة العداد",       "112598800"),
    }
    with open("output_cert.pdf", "wb") as f:
        f.write(build_cert(inp))
    with open("output_sticker.pdf", "wb") as f:
        f.write(build_sticker(inp))
    print("✅ output_cert.pdf  |  output_sticker.pdf")
