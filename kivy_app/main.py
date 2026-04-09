#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kivy application that collects certificate fields and generates a PDF with barcode.

Dependencies (install in your venv):
  pip install kivy pillow python-barcode arabic-reshaper python-bidi

Place an Arabic font file (e.g. Tajawal.ttf) next to this script for proper Arabic rendering.

Run in VS Code: `python main.py` (it opens a Kivy window on desktop).
"""
import os
import io
import tempfile
import webbrowser
from functools import partial

from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.core.window import Window

from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

import barcode
from barcode.writer import ImageWriter


# default canvas size for landscape A4 at 150 dpi
CANVAS_W = 3508  # width (landscape A4 at ~300dpi) - large for quality
CANVAS_H = 2480


def shape_ar(text: str) -> str:
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def load_font(name='Tajawal.ttf', size=28):
    # try provided font, then common fallbacks
    candidates = [name, 'Cairo-Regular.ttf', 'DejaVuSans.ttf']
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def create_barcode_image(value, out_path=None):
    Code128 = barcode.get_barcode_class('code128')
    writer = ImageWriter()
    # generate without text below
    options = {
        'module_height': 15.0,
        'module_width': 0.4,
        'font_size': 10,
        'text_distance': 1.0,
        'quiet_zone': 2.0,
    }
    code = Code128(value or '000', writer=writer)
    if out_path:
        filename = code.save(out_path, options)
        return filename + '.png' if not filename.lower().endswith('.png') else filename
    else:
        bio = io.BytesIO()
        code.write(bio, options)
        bio.seek(0)
        return Image.open(bio)


def compose_certificate_image(data: dict, font_name='Tajawal.ttf'):
    # Create large RGBA canvas
    img = Image.new('RGB', (CANVAS_W, CANVAS_H), 'white')
    draw = ImageDraw.Draw(img)

    maroon = '#7a1424'
    # top stripe
    stripe_h = 60
    draw.rectangle([(0, 0), (CANVAS_W, stripe_h)], fill=maroon)

    # Title (right aligned)
    title_font = load_font(font_name, 72)
    title = shape_ar('شهادة بيان المعدات الثقيلة المسجلة وحالتها')
    w, h = draw.textsize(title, font=title_font)
    draw.text((CANVAS_W - 60 - w, stripe_h + 20), title, fill=maroon, font=title_font)

    # Certificate meta on right side
    meta_font = load_font(font_name, 30)
    small_font = load_font(font_name, 22)
    meta_x = CANVAS_W - 60
    meta_y = stripe_h + 120
    for label, key in [('Certificate No.', 'cert_no'), ('Issue Date:', 'issue_date'), ('Expiry:', 'expiry')]:
        text = f"{label} {data.get(key, '')}"
        # render LTR label + Arabic value; we'll just show as-is
        draw.text((meta_x - draw.textsize(text, font=small_font)[0], meta_y), text, fill='black', font=small_font)
        meta_y += 34

    # Barcode at left area
    bc_img = None
    try:
        bc = create_barcode_image(data.get('cert_no') or data.get('vin') or '000')
        if isinstance(bc, str):
            bc_img = Image.open(bc)
        else:
            bc_img = bc
    except Exception:
        bc_img = None

    if bc_img:
        bc_w = 420
        bc_h = int(bc_img.height * (bc_w / bc_img.width))
        bc_resized = bc_img.resize((bc_w, bc_h))
        img.paste(bc_resized, (60, stripe_h + 30))

    # Personal info boxes
    box_y = stripe_h + 220
    box_h = 120
    box_w = (CANVAS_W - 240) // 3
    x0 = 60
    labels = [('الاسم', 'name'), ('رقم السجل التجاري / رقم الهوية', 'id_no'), ('رقم الهاتف', 'phone')]
    for i, (lbl, key) in enumerate(labels):
        x = x0 + i * (box_w + 20)
        draw.rectangle([(x, box_y), (x + box_w, box_y + box_h)], fill='#f3f4f6')
        lbl_t = shape_ar(lbl)
        val_t = shape_ar(data.get(key, ''))
        lf = load_font(font_name, 20)
        vf = load_font(font_name, 28)
        # label at top-right of the box
        lw, lh = draw.textsize(lbl_t, font=lf)
        draw.text((x + box_w - 12 - lw, box_y + 8), lbl_t, fill='#6b7280', font=lf)
        vw, vh = draw.textsize(val_t, font=vf)
        draw.text((x + box_w - 12 - vw, box_y + 40), val_t, fill='black', font=vf)

    # City and address
    row_y = box_y + box_h + 40
    draw.text((CANVAS_W - 80 - draw.textsize(shape_ar('المدينة | Region'), font=small_font)[0], row_y), shape_ar('المدينة | Region'), fill='#6b7280', font=small_font)
    draw.text((CANVAS_W - 80 - draw.textsize(shape_ar(data.get('city','')), font=meta_font)[0], row_y + 30), shape_ar(data.get('city','')), fill='black', font=meta_font)
    draw.text((CANVAS_W - 400 - draw.textsize(shape_ar('العنوان الوطني'), font=small_font)[0], row_y), shape_ar('العنوان الوطني'), fill='#6b7280', font=small_font)
    draw.text((CANVAS_W - 400 - draw.textsize(shape_ar(data.get('address','')), font=meta_font)[0], row_y + 30), shape_ar(data.get('address','')), fill='black', font=meta_font)

    # Table header
    table_y = row_y + 120
    headers = ['نوع العدة', 'رقم التسجيل', 'الرقم التسلسلي / Vin / SN #', 'سنة الصنع', 'الماركة', '#']
    cols = 6
    col_w = (CANVAS_W - 120) // cols
    tx = 60
    draw.rectangle([(tx, table_y - 20), (CANVAS_W - 60, table_y + 40)], fill='#f8fafc')
    for i, h in enumerate(headers):
        hx = CANVAS_W - 60 - (i + 1) * col_w + 12
        draw.text((hx, table_y), shape_ar(h), fill='#4b5563', font=small_font)

    # Table row
    row_vals = [data.get('type',''), data.get('reg_no',''), data.get('vin',''), data.get('year',''), data.get('brand',''), '01']
    for i, v in enumerate(row_vals):
        vx = CANVAS_W - 60 - (i + 1) * col_w + 12
        draw.text((vx, table_y + 50), shape_ar(v), fill='black', font=meta_font)

    # Optional plate at bottom center
    if data.get('plate'):
        pf = load_font(font_name, 36)
        plate_text = shape_ar('رقم اللوحة: ' + data.get('plate'))
        pw, ph = draw.textsize(plate_text, font=pf)
        draw.rectangle(((CANVAS_W//2 - pw//2 - 12, CANVAS_H - 140), (CANVAS_W//2 + pw//2 + 12, CANVAS_H - 80)), fill=maroon)
        draw.text((CANVAS_W//2 + pw//2 - pw - 6, CANVAS_H - 132), plate_text, fill='white', font=pf)

    return img


class CertForm(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 1
        self.padding = 12
        self.spacing = 8

        self.fields = {}
        # list of tuples(label, key)
        items = [
            ('الاسم', 'name'),
            ('رقم الهوية / السجل التجاري', 'id_no'),
            ('رقم الهاتف', 'phone'),
            ('المدينة', 'city'),
            ('العنوان الوطني', 'address'),
            ('رقم الشهادة', 'cert_no'),
            ('تاريخ الإصدار', 'issue_date'),
            ('تاريخ الانتهاء', 'expiry'),
            ('نوع العدة', 'type'),
            ('رقم التسجيل', 'reg_no'),
            ('الرقم التسلسلي / Vin / SN', 'vin'),
            ('سنة الصنع', 'year'),
            ('الماركة', 'brand'),
            ('رقم اللوحة (اختياري)', 'plate')
        ]

        for label, key in items:
            box = BoxLayout(orientation='vertical', size_hint_y=None, height=72)
            lbl = Label(text=label, halign='right', size_hint_y=None, height=24)
            ti = TextInput(multiline=False, halign='right')
            box.add_widget(lbl)
            box.add_widget(ti)
            self.add_widget(box)
            self.fields[key] = ti

        btn = Button(text='توليد البطاقة', size_hint_y=None, height=48)
        btn.bind(on_release=self.on_generate)
        self.add_widget(btn)

    def on_generate(self, *args):
        data = {k: v.text.strip() for k, v in self.fields.items()}
        # basic validation
        if not data.get('name'):
            Popup(title='خطأ', content=Label(text='الاسم مطلوب'), size_hint=(0.6, 0.3)).open()
            return

        # compose image
        try:
            img = compose_certificate_image(data)
            out_pdf = os.path.join(os.getcwd(), 'certificate.pdf')
            # save as PDF
            img_rgb = img.convert('RGB')
            img_rgb.save(out_pdf, 'PDF', resolution=300.0)
            Popup(title='تم', content=Label(text=f'تم إنشاء {out_pdf}'), size_hint=(0.7, 0.3)).open()
            # open file
            try:
                if os.name == 'nt':
                    os.startfile(out_pdf)
                else:
                    webbrowser.open('file://' + out_pdf)
            except Exception:
                pass
        except Exception as e:
            Popup(title='خطأ', content=Label(text=str(e)), size_hint=(0.8, 0.4)).open()


class CertificateApp(App):
    def build(self):
        Window.size = (900, 700)
        root = ScrollView()
        form = CertForm(size_hint_y=None)
        form.bind(minimum_height=form.setter('height'))
        root.add_widget(form)
        return root


if __name__ == '__main__':
    CertificateApp().run()
