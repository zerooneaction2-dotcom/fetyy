#!/usr/bin/env python3
"""
توليد وثيقة تأمين المركبات — تعديل مباشر على ملف PDF الأصلي
"""

import fitz
import arabic_reshaper
from bidi.algorithm import get_display
import os
import io

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
ARABIC_FONT = os.path.join(BASE_DIR, "Cairo-Regular.ttf")
if not os.path.exists(ARABIC_FONT):
    ARABIC_FONT = r"C:\Windows\Fonts\segoeui.ttf"
if not os.path.exists(ARABIC_FONT):
    ARABIC_FONT = r"C:\Windows\Fonts\tahoma.ttf"


def ar(text):
    return get_display(arabic_reshaper.reshape(str(text)))


class PDFEditor:
    def __init__(self, path):
        self.doc  = fitz.open(path)
        self.page = self.doc[0]
        if os.path.exists(ARABIC_FONT):
            self._font = fitz.Font(fontfile=ARABIC_FONT)
        else:
            raise RuntimeError(f"لم يُعثر على خط عربي في: {ARABIC_FONT}")
        self._fn = None

    def _redact(self, rects, fill=(1, 1, 1)):
        for r in rects:
            self.page.add_redact_annot(r, fill=fill)
        self.page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

    def _insert(self, point, text, fontsize=11, color=(0, 0, 0), arabic=False):
        tw = fitz.TextWriter(self.page.rect)
        display = ar(text) if arabic else text
        tw.append(point, display, font=self._font, fontsize=fontsize)
        tw.write_text(self.page, color=color)

    def replace(self, search, new_text, fontsize=11, color=(0, 0, 0), arabic=False):
        """بحث عن نص واستبداله."""
        quads = self.page.search_for(search)
        if not quads:
            return False
        rects = [fitz.Rect(q) for q in quads]
        self._redact(rects)
        r = rects[0]
        if arabic:
            self._insert(fitz.Point(r.x1, r.y1 - 2), new_text,
                         fontsize=fontsize, color=color, arabic=True)
        else:
            self._insert(fitz.Point(r.x0, r.y1 - 2), new_text,
                         fontsize=fontsize, color=color, arabic=False)
        return True

    def replace_at(self, rect_tuple, new_text, fontsize=11, color=(0, 0, 0), arabic=False):
        """استبدال في منطقة محددة."""
        r = fitz.Rect(rect_tuple)
        self._redact([r])
        if arabic:
            tw = fitz.TextWriter(self.page.rect)
            display = ar(new_text)
            tw.append(fitz.Point(r.x1, r.y1 - 2), display,
                      font=self._font, fontsize=fontsize)
            tw.write_text(self.page, color=color)
        else:
            tw = fitz.TextWriter(self.page.rect)
            tw.append(fitz.Point(r.x0, r.y1 - 2), new_text,
                      font=self._font, fontsize=fontsize)
            tw.write_text(self.page, color=color)

    def to_bytes(self, title=""):
        if title:
            self.doc.set_metadata({"title": title, "producer": "FETIY", "creator": "FETIY"})
        buf = io.BytesIO()
        self.doc.save(buf, garbage=4, deflate=True, clean=True)
        self.doc.close()
        buf.seek(0)
        return buf.read()


# ── الحقول وإحداثياتها ───────────────────────────────────────────────────────
# كل حقل: (rect_to_clear, insert_point_or_rect, is_arabic)

def build_insurance(inp: dict) -> bytes:
    """عدّل template_insurance.pdf وأعد المحتوى كـ bytes."""
    path = os.path.join(BASE_DIR, "template_insurance.pdf")
    if not os.path.exists(path):
        raise FileNotFoundError("لم يُعثر على template_insurance.pdf")

    ed = PDFEditor(path)
    page = ed.page
    font = ed._font
    BLACK = (0, 0, 0)

    rects_to_clear = []
    texts_to_add = []  # (text_area_rect, text, fontsize, color, is_arabic)

    def sfind(text, idx=0):
        """بحث نصي → إرجاع Rect بالترتيب idx أو None."""
        quads = page.search_for(text)
        return fitz.Rect(quads[idx]) if len(quads) > idx else None

    def plan(clear_r, text_r, text, fontsize=11, color=BLACK, arabic=False):
        """تسجيل منطقة محو + منطقة نص."""
        rects_to_clear.append(fitz.Rect(clear_r))
        texts_to_add.append((fitz.Rect(text_r), text, fontsize, color, arabic))

    # ── 1. التاريخ — بحث عن النص الأصلي بالضبط ──────────────────────────
    if inp.get("ins_date"):
        r = sfind("28/03/2026     11:12 AM")
        if r:
            plan(r, r, inp["ins_date"])

    # ── 2. سطر "إلى" + الاسم — span واحد [387.3, 108.7 → 563.6, 121.0] ──
    if inp.get("insured_name"):
        r = fitz.Rect(387.3, 108.7, 563.6, 121.0)
        plan(r, r, "إلى " + inp["insured_name"], arabic=True)

    # ── 3. اسم المؤمن له — الجدول [313.5→413.6] / التسمية تبدأ عند 509 ──
    if inp.get("insured_name"):
        clear_r = fitz.Rect(313.5, 208.8, 413.6, 221.1)
        text_r  = fitz.Rect(313.5, 208.8, 505, 221.1)   # مساحة أوسع للنص
        plan(clear_r, text_r, inp["insured_name"], arabic=True)

    # ── 4. رقم الهوية — بحث نصي ──────────────────────────────────────────
    if inp.get("national_id"):
        r = sfind("1137221345")
        if r:
            plan(r, r, inp["national_id"])

    # ── 5. العنوان — [224.4→413.8] ───────────────────────────────────────
    if inp.get("address"):
        clear_r = fitz.Rect(224.4, 257.6, 413.8, 268.6)
        plan(clear_r, clear_r, inp["address"], fontsize=9)

    # ── 6. الرقم التسلسلي — بحث نصي ──────────────────────────────────────
    if inp.get("seq_no"):
        r = sfind("229206700")
        if r:
            plan(r, r, inp["seq_no"])

    # ── 7. رقم اللوحة — بحث نصي ──────────────────────────────────────────
    if inp.get("plate"):
        r = sfind("1259 EBA")
        if r:
            plan(r, r, inp["plate"])

    # ── 8. نوع المركبة — التسمية والقيمة في span مشترك ─────────────────
    #    مسح كامل السطر (314→564) وإعادة كتابة التسمية + القيمة
    if inp.get("make_name"):
        rects_to_clear.append(fitz.Rect(314, 316, 564, 329))
        # إعادة كتابة التسمية "نوع المركبة" بموقعها الأصلي (x≈521→563)
        texts_to_add.append((fitz.Rect(521, 316, 564, 329),
                             "نوع المركبة", 11, BLACK, True))
        # كتابة القيمة الجديدة (x=314→516)
        texts_to_add.append((fitz.Rect(314, 316, 516, 329),
                             inp["make_name"], 11, BLACK, True))

    # ── 9. موديل المركبة — بحث نصي ───────────────────────────────────────
    if inp.get("model_year"):
        r = sfind("2010")
        if r:
            plan(r, r, inp["model_year"])

    # ── 10. رقم الهيكل — بحث نصي ─────────────────────────────────────────
    if inp.get("chassis"):
        r = sfind("WDB65803815440418")
        if r:
            plan(r, r, inp["chassis"])

    # ── 11. رمز المنتج — بحث نصي ─────────────────────────────────────────
    if inp.get("product_code"):
        r = sfind("A-RAJH-1-B-15-007")
        if r:
            plan(r, r, inp["product_code"])

    # ── 12. رقم الوثيقة العلوي — بحث نصي (أول تطابق) ─────────────────────
    if inp.get("policy_no"):
        r = sfind("P1223-MTI-MDBS-087456325", idx=0)
        if r:
            plan(r, r, inp["policy_no"], fontsize=12)

    # ── 13. رقم الوثيقة — السطر الإنجليزي [41.6→296.9] ───────────────────
    if inp.get("policy_no"):
        clear_r = fitz.Rect(41.6, 153.9, 296.9, 164.9)
        plan(clear_r, clear_r,
             "enclosed Policy Number (" + inp["policy_no"] + "),")

    # ── 14. تاريخ بداية التغطية — [240→373] بدون لمس التسمية العربية ──────
    if inp.get("ins_date"):
        clear_r = fitz.Rect(240, 399.4, 373, 410.5)
        plan(clear_r, clear_r, inp["ins_date"])

    # ── 15. تاريخ نهاية التغطية — [249→404] بدون لمس التسمية العربية ──────
    if inp.get("exp_date"):
        clear_r = fitz.Rect(249, 412.9, 404, 423.9)
        plan(clear_r, clear_r, inp["exp_date"])

    # ── تطبيق كل المحو مرة واحدة ────────────────────────────────────────
    for r in rects_to_clear:
        page.add_redact_annot(r, fill=(1, 1, 1))
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

    # ── كتابة النصوص الجديدة — تقليص تلقائي + محاذاة يمين للعربي ─────────
    for text_r, text, fontsize, color, is_arabic in texts_to_add:
        display = ar(text) if is_arabic else text
        # تقليص الخط تلقائياً إذا تجاوز العرض المتاح
        fs = fontsize
        avail = text_r.width
        while fs > 6:
            w = font.text_length(display, fontsize=fs)
            if w <= avail:
                break
            fs -= 0.5
        # دائماً نبدأ من x0 (الحافة اليسرى) — نفس طريقة الملف الأصلي
        pt = fitz.Point(text_r.x0, text_r.y1 - 2)
        tw = fitz.TextWriter(page.rect)
        tw.append(pt, display, font=font, fontsize=fs)
        tw.write_text(page, color=color)

    return ed.to_bytes(title="Insurance Certificate")
