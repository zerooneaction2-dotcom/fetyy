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
from generate_insurance import build_insurance

app = Flask(__name__, template_folder="templates", static_folder="static")

REMOTE_URL = "https://fetyy.onrender.com"

# ── تخزين بيانات الفحوصات في ملف JSON (تبقى بعد إعادة التشغيل) ──────────────
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inspections.json")
GITHUB_RAW = "https://raw.githubusercontent.com/zerooneaction2-dotcom/fetyy/master/inspections.json"

def _fetch_github_data():
    """جلب البيانات من GitHub عند بداية التشغيل (للحفاظ عليها بعد إعادة تشغيل Render)."""
    import urllib.request
    for attempt in range(3):
        try:
            req = urllib.request.Request(GITHUB_RAW, headers={"Cache-Control": "no-cache"})
            resp = urllib.request.urlopen(req, timeout=15)
            return json.loads(resp.read().decode("utf-8"))
        except Exception:
            import time as _t
            if attempt < 2:
                _t.sleep(2)
    return {}

_github_fetched = False

def _load_inspections():
    global _github_fetched
    local = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                local = json.load(f)
        except Exception:
            local = {}
    # عند أول تحميل على Render، ادمج بيانات GitHub مع المحلية
    if not _github_fetched:
        _github_fetched = True
        github_data = _fetch_github_data()
        if github_data:
            # بيانات GitHub تُدمج (المحلي يأخذ الأولوية إن وجد)
            merged = {**github_data, **local}
            if merged != local:
                with open(DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(merged, f, ensure_ascii=False, indent=2)
            return merged
    return local

# ── جلب مسبق عند بدء التشغيل (لا ينتظر أول طلب HTTP) ────────────────────
_load_inspections()

def _save_inspection(barcode_id, data):
    inspections = _load_inspections()
    inspections[barcode_id] = data
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(inspections, f, ensure_ascii=False, indent=2)
    # مزامنة البيانات مع السيرفر البعيد (Render)
    _sync_to_remote(barcode_id, data)

def _sync_to_remote(barcode_id, data):
    """إرسال البيانات إلى Render حتى تكون متاحة عند مسح الباركود."""
    import threading, urllib.request, urllib.error, time as _time
    def _send():
        payload = json.dumps({"barcode_id": barcode_id, "data": data}).encode()
        for attempt in range(4):  # 4 محاولات
            try:
                req = urllib.request.Request(
                    f"{REMOTE_URL}/api/save",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )
                urllib.request.urlopen(req, timeout=30)
                return  # نجحت
            except Exception:
                if attempt < 3:
                    _time.sleep(5 * (attempt + 1))  # انتظر 5, 10, 15 ثانية
    threading.Thread(target=_send, daemon=True).start()


@app.route("/api/save", methods=["POST"])
def api_save():
    """استقبال بيانات الفحص من التطبيق المحلي."""
    body = request.get_json(force=True)
    barcode_id = body.get("barcode_id", "")
    data = body.get("data", {})
    if barcode_id and data:
        inspections = _load_inspections()
        inspections[barcode_id] = data
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(inspections, f, ensure_ascii=False, indent=2)
        return jsonify({"ok": True})
    return jsonify({"error": "missing data"}), 400


@app.route("/health")
def health():
    """نقطة فحص خفيفة — يستخدمها UptimeRobot لإبقاء السيرفر شغّالاً."""
    return "ok", 200

@app.route("/")
def index():
    return redirect("/iv/fetyy.php?wb=112598800")


@app.route("/form")
def form():
    return render_template("periodic_form.html")


@app.route("/edit")
def edit_page():
    """صفحة تعديل بيانات ملصق موجود."""
    return render_template("edit.html", inspections=_load_inspections())


@app.route("/api/update", methods=["POST"])
def api_update():
    """تعديل بيانات ملصق موجود بدون توليد جديد."""
    body = request.get_json(force=True)
    uid = body.get("uid", "")
    data = body.get("data", {})
    if not uid:
        return jsonify({"error": "لم يتم تحديد الملصق"}), 400
    inspections = _load_inspections()
    if uid not in inspections:
        return jsonify({"error": "الملصق غير موجود"}), 404
    inspections[uid].update(data)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(inspections, f, ensure_ascii=False, indent=2)
    # مزامنة مع Render
    _sync_to_remote(uid, inspections[uid])
    return jsonify({"ok": True})


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
            download_name="inspection_certificate.pdf",
        )
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/generate/sticker", methods=["POST"])
def gen_sticker():
    inp = request.get_json(force=True)
    try:
        pdf_bytes = build_sticker(inp)
        # حفظ بيانات الفحص بالمعرّف الفريد (يُضاف بواسطة build_sticker)
        unique_id = inp.get("_uid", inp.get("odometer", "000000"))
        _save_inspection(unique_id, inp)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name="inspection_sticker.pdf",
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
        cert_bytes    = build_cert(inp)
        sticker_bytes = build_sticker(inp)
        # حفظ بيانات الفحص بالمعرّف الفريد
        unique_id = inp.get("_uid", inp.get("odometer", "000000"))
        _save_inspection(unique_id, inp)
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("inspection_certificate.pdf", cert_bytes)
            z.writestr("inspection_sticker.pdf",     sticker_bytes)
        zip_buf.seek(0)
        return send_file(
            zip_buf,
            mimetype="application/zip",
            as_attachment=True,
            download_name="inspection_documents.zip",
        )
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── مولّد وثيقة التأمين ──────────────────────────────────────────────────────

@app.route("/insurance")
def insurance_form():
    return render_template("insurance_form.html")


@app.route("/generate/insurance", methods=["POST"])
def gen_insurance():
    inp = request.get_json(force=True)
    try:
        pdf_bytes = build_insurance(inp)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name="insurance_certificate.pdf",
        )
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/iv/fetyy.php")
def verify():
    """صفحة نتيجة الفحص — تظهر عند مسح الباركود."""
    barcode_id = request.args.get("wb", "")
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
