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

# ── تخزين بيانات الفحوصات ─────────────────────────────────────────────────────
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inspections.json")
GITHUB_RAW = "https://raw.githubusercontent.com/zerooneaction2-dotcom/fetyy/master/inspections.json"
GITHUB_API = "https://api.github.com/repos/zerooneaction2-dotcom/fetyy/contents/inspections.json"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")  # يُضبط في Render Dashboard

import threading, time as _time, urllib.request, urllib.error, base64, hashlib

_last_github_fetch = 0        # آخر وقت جلب من GitHub
_GITHUB_REFRESH_SEC = 300     # أعد الجلب كل 5 دقائق
_github_sha = None            # آخر SHA للملف على GitHub (لتحديث بدون تعارض)
_github_push_lock = threading.Lock()


def _fetch_github_data():
    """جلب البيانات من GitHub (مع Cache-Busting)."""
    global _last_github_fetch
    for attempt in range(3):
        try:
            url = GITHUB_RAW + f"?_t={int(_time.time())}"
            req = urllib.request.Request(url, headers={
                "Cache-Control": "no-cache, no-store",
                "Pragma": "no-cache",
            })
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read().decode("utf-8"))
            _last_github_fetch = _time.time()
            return data
        except Exception:
            if attempt < 2:
                _time.sleep(2)
    return {}


def _push_to_github(all_data):
    """رفع inspections.json إلى GitHub عبر API (يعمل على Render بدون git)."""
    global _github_sha
    if not GITHUB_TOKEN:
        return False
    with _github_push_lock:
        try:
            # 1) جلب SHA الحالي
            req = urllib.request.Request(GITHUB_API, headers={
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            })
            resp = urllib.request.urlopen(req, timeout=15)
            info = json.loads(resp.read().decode("utf-8"))
            sha = info["sha"]

            # 2) دمج مع البيانات الموجودة على GitHub (حتى لا نفقد بيانات)
            remote_data = json.loads(base64.b64decode(info["content"]).decode("utf-8"))
            merged = {**remote_data, **all_data}

            # 3) رفع الملف المحدث
            content_b64 = base64.b64encode(
                json.dumps(merged, ensure_ascii=False, indent=2).encode("utf-8")
            ).decode("ascii")
            payload = json.dumps({
                "message": "auto-sync inspections",
                "content": content_b64,
                "sha": sha,
            }).encode("utf-8")
            req2 = urllib.request.Request(GITHUB_API, data=payload, method="PUT", headers={
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
            })
            resp2 = urllib.request.urlopen(req2, timeout=20)
            result = json.loads(resp2.read().decode("utf-8"))
            _github_sha = result["content"]["sha"]
            return True
        except Exception:
            return False


def _load_inspections(force_github=False):
    """تحميل البيانات: محلي + GitHub (دمج). force_github يفرض الجلب."""
    global _last_github_fetch
    local = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                local = json.load(f)
        except Exception:
            local = {}

    # جلب من GitHub إذا: أول مرة، أو مر وقت طويل، أو force
    need_fetch = force_github or (_time.time() - _last_github_fetch > _GITHUB_REFRESH_SEC)
    if need_fetch:
        github_data = _fetch_github_data()
        if github_data:
            merged = {**github_data, **local}
            if merged != local:
                with open(DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(merged, f, ensure_ascii=False, indent=2)
            return merged
    return local


# ── جلب مسبق عند بدء التشغيل ─────────────────────────────────────────────────
_load_inspections(force_github=True)


def _save_inspection(barcode_id, data):
    inspections = _load_inspections()
    inspections[barcode_id] = data
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(inspections, f, ensure_ascii=False, indent=2)
    # مزامنة: إرسال لـ Render + رفع لـ GitHub
    _sync_to_remote(barcode_id, data)
    _async_push_github(inspections)


def _async_push_github(all_data):
    """رفع البيانات لـ GitHub في الخلفية."""
    def _do():
        _push_to_github(all_data)
    threading.Thread(target=_do, daemon=True).start()


def _sync_to_remote(barcode_id, data):
    """إرسال البيانات إلى Render حتى تكون متاحة عند مسح الباركود."""
    def _send():
        payload = json.dumps({"barcode_id": barcode_id, "data": data}).encode()
        for attempt in range(4):
            try:
                req = urllib.request.Request(
                    f"{REMOTE_URL}/api/save",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )
                urllib.request.urlopen(req, timeout=30)
                return
            except Exception:
                if attempt < 3:
                    _time.sleep(5 * (attempt + 1))
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
        # رفع تلقائي لـ GitHub لضمان عدم ضياع البيانات
        _async_push_github(inspections)
        return jsonify({"ok": True})
    return jsonify({"error": "missing data"}), 400


@app.route("/health")
def health():
    """نقطة فحص — يستخدمها UptimeRobot لإبقاء السيرفر + تحديث البيانات."""
    # كل 5 دقائق أعد جلب البيانات من GitHub (حماية من فقدانها)
    _load_inspections()  # يجلب من GitHub تلقائياً إذا مر وقت كافٍ
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
    # مزامنة مع Render + GitHub
    _sync_to_remote(uid, inspections[uid])
    _async_push_github(inspections)
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
    # إذا لم تُوجد البيانات، أعد الجلب من GitHub (ربما أُضيفت مؤخراً)
    if not data and barcode_id:
        data = _load_inspections(force_github=True).get(barcode_id)
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
