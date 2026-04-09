"""
خادم Flask — واجهة ويب لتوليد وثيقة الفحص الفني الدوري
تشغيل: python app.py
ثم افتح المتصفح على: http://127.0.0.1:5000
"""
from flask import Flask, render_template, request, send_file, jsonify, url_for, redirect
import io
import os
import json
from generate_periodic import build_cert, build_sticker, get_blocks

app = Flask(__name__, template_folder="templates", static_folder="static")

# ── تخزين بيانات الفحوصات في ملف JSON (تبقى بعد إعادة التشغيل) ──────────────
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inspections.json")

def _load_inspections():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "112598800": {
            "plate": "Z D A 6890", "vin": "WDB65256215901608",
            "maker": "مرسيدس", "car_type": "رأس", "color": "أخضر/أزرق",
            "year": "2011", "odometer": "112598800", "seq_no": "306574",
            "insp_date": "2026-04-08", "exp_date": "2027-04-08",
        }
    }

def _save_inspection(barcode_id, data):
    inspections = _load_inspections()
    inspections[barcode_id] = data
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(inspections, f, ensure_ascii=False, indent=2)


@app.route("/")
def index():
    return redirect("/iv/fetyy.php?wb=112598800")


@app.route("/form")
def form():
    return render_template("periodic_form.html")


@app.route("/generate/cert", methods=["POST"])
def gen_cert():
    inp = request.get_json(force=True)
    try:
        # حفظ بيانات الفحص للباركود
        barcode_id = inp.get("odometer", "000000")
        _save_inspection(barcode_id, inp)
        pdf_bytes = build_cert(inp)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name="وثيقة_فحص_المركبة.pdf",
        )
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/generate/sticker", methods=["POST"])
def gen_sticker():
    inp = request.get_json(force=True)
    try:
        # حفظ بيانات الفحص للباركود
        barcode_id = inp.get("odometer", "000000")
        _save_inspection(barcode_id, inp)
        pdf_bytes = build_sticker(inp)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name="ملصق_الفحص_الفني_الدوري.pdf",
        )
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/generate/both", methods=["POST"])
def gen_both():
    """توليد كلا الملفين وإرجاعهما كـ ZIP."""
    inp = request.get_json(force=True)
    import zipfile
    try:
        # حفظ بيانات الفحص للباركود
        barcode_id = inp.get("odometer", "000000")
        _save_inspection(barcode_id, inp)
        cert_bytes    = build_cert(inp)
        sticker_bytes = build_sticker(inp)
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("وثيقة_فحص_المركبة.pdf",       cert_bytes)
            z.writestr("ملصق_الفحص_الفني_الدوري.pdf", sticker_bytes)
        zip_buf.seek(0)
        return send_file(
            zip_buf,
            mimetype="application/zip",
            as_attachment=True,
            download_name="وثيقة_الفحص_الفني_الدوري.zip",
        )
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/iv/fetyy.php")
def verify():
    """صفحة نتيجة الفحص — تظهر عند مسح الباركود."""
    barcode_id = request.args.get("wb", "")
    compressed = request.args.get("d", "")
    data = None
    if compressed:
        import json, base64, zlib
        try:
            raw = zlib.decompress(base64.urlsafe_b64decode(compressed))
            d = json.loads(raw)
            data = {
                "plate": d.get("p", ""), "vin": d.get("v", ""),
                "maker": d.get("m", ""), "car_type": d.get("t", ""),
                "color": d.get("c", ""), "year": d.get("y", ""),
                "insp_date": d.get("i", ""), "exp_date": d.get("e", ""),
                "center": d.get("n", ""),
            }
        except Exception:
            data = None
    if not data:
        data = _load_inspections().get(barcode_id)
    return render_template("verify.html", data=data, barcode_id=barcode_id)


@app.route("/blocks/<filename>")
def blocks(filename):
    """عرض مواضع النصوص في PDF (للتشخيص)."""
    safe = os.path.basename(filename)
    try:
        data = get_blocks(safe)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
