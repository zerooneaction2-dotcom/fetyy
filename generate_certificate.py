#!/usr/bin/env python3
"""
Generate a certificate PDF resembling the provided design.

Dependencies:
  pip install reportlab pillow arabic-reshaper python-bidi

Usage: run the script and follow prompts. The script will create `certificate.pdf` in the
current folder. If you want better Arabic rendering, place an Arabic-capable TTF (e.g. Cairo,
Amiri, or DejaVuSans) named `arabic.ttf` next to this script, otherwise the script will try
to use a default font.
"""
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.graphics.barcode import code128

from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)


def get_input(prompt, default=''):
    v = input(f"{prompt} [{default}]: ").strip()
    return v if v else default


def load_font(preferred='arabic.ttf', size=24):
    # Try to load user-provided Arabic font, else fall back to DejaVuSans or default
    candidates = [preferred, 'DejaVuSans.ttf']
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
    # Last resort: use default PIL font
    return ImageFont.load_default()


def render_arabic_text(text, font, fill=(0, 0, 0)):
    # reshape and bidi for correct Arabic shaping
    reshaped = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped)
    # measure
    dummy = Image.new('RGBA', (10, 10), (255, 255, 255, 0))
    d = ImageDraw.Draw(dummy)
    w, h = d.textsize(bidi_text, font=font)
    img = Image.new('RGBA', (w + 8, h + 8), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    d.text((4, 4), bidi_text, font=font, fill=fill)
    return img


def draw_arabic(canvas_obj, text, x, y, font_path, font_size, align='right'):
    # Create PIL text image and draw onto canvas at (x,y) where y is from bottom
    font = load_font(font_path, font_size)
    img = render_arabic_text(text, font)
    ir = ImageReader(img)
    w, h = img.size
    # reportlab uses points; PIL image pixels approximated as points (OK for typical fonts)
    draw_x = x - w if align == 'right' else x
    canvas_obj.drawImage(ir, draw_x, y - h, width=w, height=h, mask='auto')


def main():
    print('أدخل بيانات الشهادة. اضغط Enter لتقبل القيمة الافتراضية بين الأقواس.')
    name = get_input('الاسم', 'بندر محمد مانع السبيعي')
    id_no = get_input('رقم الهوية/السجل التجاري', '1015824316')
    phone = get_input('رقم الهاتف', '+9666553379497')
    city = get_input('المدينة', 'الرياض')
    address = get_input('العنوان الوطني', '14514')
    cert_no = get_input('رقم الشهادة', 'H-A0000316')
    issue_date = get_input('تاريخ الإصدار', '07/12/2025')
    expiry = get_input('تاريخ الانتهاء', '06/01/2026')

    equip_type = get_input('نوع العدة', 'راسمة ومخراج طرق (Puma bullet)')
    reg_no = get_input('رقم التسجيل', 'H0000109')
    vin = get_input('الرقم التسلسلي / Vin / SN', 'H-A0000316')
    year = get_input('سنة الصنع', '2008')
    brand = get_input('الماركة', 'Rullet')
    plate = get_input('رقم اللوحة (اختياري)', '')

    # Prepare PDF
    c = canvas.Canvas('certificate.pdf', pagesize=landscape(A4))

    # background
    c.setFillColor(colors.white)
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)

    # top maroon stripe
    maroon = colors.HexColor('#7a1424')
    c.setFillColor(maroon)
    c.rect(0, PAGE_HEIGHT - 36, PAGE_WIDTH, 12, fill=True, stroke=False)

    # Header texts (English small + title Arabic)
    # Title (Arabic) on right
    draw_arabic(c, 'شهادة بيان المعدات الثقيلة المسجلة وحالتها', PAGE_WIDTH - 40, PAGE_HEIGHT - 70, 'arabic.ttf', 28, align='right')
    # Subtitle English
    c.setFont('Helvetica', 10)
    c.setFillColor(colors.grey)
    c.drawRightString(PAGE_WIDTH - 40, PAGE_HEIGHT - 90, 'Certificate of Registration and Condition of Heavy Equipment')

    # Certificate meta (right block)
    c.setFont('Helvetica-Bold', 10)
    c.setFillColor(colors.black)
    c.drawRightString(PAGE_WIDTH - 40, PAGE_HEIGHT - 120, f'Certificate No. {cert_no}')
    c.setFont('Helvetica', 9)
    c.setFillColor(colors.grey)
    c.drawRightString(PAGE_WIDTH - 40, PAGE_HEIGHT - 135, f'Issue Date: {issue_date}')
    c.drawRightString(PAGE_WIDTH - 40, PAGE_HEIGHT - 150, f'Expiry: {expiry}')

    # Left barcode area -- use Code128
    bc = code128.Code128(cert_no or vin or '000', barHeight=40, barWidth=1.2)
    bc_x = 40
    bc_y = PAGE_HEIGHT - 180
    bc.drawOn(c, bc_x, bc_y)

    # Personal info boxes
    box_y = PAGE_HEIGHT - 220
    box_h = 50
    box_w = (PAGE_WIDTH - 160) / 3
    start_x = 80
    texts = [
        ('الاسم', name),
        ('رقم السجل التجاري / رقم الهوية', id_no),
        ('رقم الهاتف', phone)
    ]
    for i, (label, value) in enumerate(texts):
        x = start_x + i * (box_w + 10)
        # box background
        c.setFillColor(colors.HexColor('#f8f8f9'))
        c.roundRect(x, box_y - box_h, box_w, box_h, 6, fill=True, stroke=False)
        # label Arabic small
        draw_arabic(c, label, x + box_w - 10, box_y - 18, 'arabic.ttf', 12, align='right')
        # value bold
        draw_arabic(c, value, x + box_w - 10, box_y - 36, 'arabic.ttf', 16, align='right')

    # City / address row
    row_y = box_y - 80
    left_x = start_x
    draw_arabic(c, 'المدينة | Region', PAGE_WIDTH - 40, row_y + 10, 'arabic.ttf', 12, align='right')
    draw_arabic(c, city, PAGE_WIDTH - 40, row_y - 10, 'arabic.ttf', 14, align='right')
    draw_arabic(c, 'العنوان الوطني', PAGE_WIDTH - 300, row_y + 10, 'arabic.ttf', 12, align='right')
    draw_arabic(c, address, PAGE_WIDTH - 300, row_y - 10, 'arabic.ttf', 14, align='right')

    # Table header
    table_y = row_y - 80
    c.setFillColor(colors.HexColor('#f3f4f6'))
    c.rect(40, table_y - 30, PAGE_WIDTH - 80, 28, fill=True, stroke=False)
    c.setFillColor(colors.grey)
    c.setFont('Helvetica-Bold', 9)
    # columns (right-to-left): Type, RegNo, Vin, Year, Brand, #
    col_xs = [PAGE_WIDTH - 140, PAGE_WIDTH - 260, PAGE_WIDTH - 420, PAGE_WIDTH - 520, PAGE_WIDTH - 640, PAGE_WIDTH - 700]
    headers = ['نوع العدة', 'رقم التسجيل', 'الرقم التسلسلي / Vin / SN #', 'سنة الصنع', 'الماركة', '#']
    for x, h in zip(col_xs[::-1], headers[::-1]):
        draw_arabic(c, h, x, table_y - 16, 'arabic.ttf', 11, align='right')

    # Table row values
    row_values = [equip_type, reg_no, vin, year, brand, '01']
    for x, v in zip(col_xs[::-1], row_values[::-1]):
        draw_arabic(c, v, x, table_y - 48, 'arabic.ttf', 12, align='right')

    # Optional plate show
    if plate:
        draw_arabic(c, f'رقم اللوحة: {plate}', PAGE_WIDTH / 2 + 100, 60, 'arabic.ttf', 16, align='right')

    # Footer note
    draw_arabic(c, 'التحقق من صحة الشهادة عبر منصة مركز تنظيم المعدات الثقيلة', 60 + 400, 30, 'arabic.ttf', 10, align='right')

    c.showPage()
    c.save()
    print('تم إنشاء الملف certificate.pdf')


if __name__ == '__main__':
    main()
