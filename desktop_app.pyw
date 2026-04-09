"""
تطبيق سطح المكتب — الفحص الفني الدوري
انقر نقراً مزدوجاً لتشغيل التطبيق
"""
import sys
import os
import threading
import webbrowser
import time
import tkinter as tk
from tkinter import messagebox

# تأكد من أن المسار الصحيح
APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

# تفعيل venv إذا موجود
venv_python = os.path.join(APP_DIR, ".venv", "Scripts", "python.exe")
if os.path.exists(venv_python) and sys.executable != venv_python:
    venv_site = os.path.join(APP_DIR, ".venv", "Lib", "site-packages")
    if os.path.exists(venv_site):
        sys.path.insert(0, venv_site)

PORT = 5000
URL = f"http://127.0.0.1:{PORT}"

server_running = False

def start_server():
    """تشغيل سيرفر Flask في الخلفية."""
    global server_running
    try:
        from app import app
        server_running = True
        app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)
    except Exception as e:
        messagebox.showerror("خطأ", f"تعذر تشغيل السيرفر:\n{e}")

def open_page(path):
    """فتح صفحة في المتصفح."""
    webbrowser.open(f"{URL}{path}")

def wait_and_open():
    """انتظر حتى يعمل السيرفر ثم افتح المتصفح."""
    import urllib.request
    for _ in range(30):
        try:
            urllib.request.urlopen(f"{URL}/form", timeout=1)
            open_page("/form")
            return
        except Exception:
            time.sleep(0.5)

def create_gui():
    """إنشاء نافذة سطح المكتب الرئيسية."""
    root = tk.Tk()
    root.title("الفحص الفني الدوري")
    root.geometry("420x500")
    root.resizable(False, False)
    root.configure(bg="#1b5e20")

    # محاولة وضع النافذة في المنتصف
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - 210
    y = (root.winfo_screenheight() // 2) - 250
    root.geometry(f"+{x}+{y}")

    # ── العنوان ──
    title_frame = tk.Frame(root, bg="#1b5e20", pady=20)
    title_frame.pack(fill="x")

    tk.Label(
        title_frame, text="الفحص الفني الدوري",
        font=("Segoe UI", 22, "bold"), fg="white", bg="#1b5e20"
    ).pack()

    tk.Label(
        title_frame, text="Vehicle Periodic Technical Inspection",
        font=("Segoe UI", 10), fg="#a5d6a7", bg="#1b5e20"
    ).pack()

    # ── حالة السيرفر ──
    status_var = tk.StringVar(value="⏳ جار تشغيل السيرفر...")
    status_label = tk.Label(
        root, textvariable=status_var,
        font=("Segoe UI", 10), fg="#fff59d", bg="#1b5e20"
    )
    status_label.pack(pady=(5, 15))

    # ── الأزرار ──
    btn_frame = tk.Frame(root, bg="#1b5e20")
    btn_frame.pack(fill="x", padx=40)

    btn_style = {
        "font": ("Segoe UI", 13, "bold"),
        "fg": "white",
        "relief": "flat",
        "cursor": "hand2",
        "width": 28,
        "height": 2,
        "bd": 0,
    }

    btn_generate = tk.Button(
        btn_frame, text="📝  توليد وثيقة فحص",
        bg="#2e7d32", activebackground="#388e3c",
        command=lambda: open_page("/form"),
        **btn_style
    )
    btn_generate.pack(pady=(0, 10))

    btn_insurance = tk.Button(
        btn_frame, text="🛡️  توليد وثيقة تأمين",
        bg="#0d47a1", activebackground="#1565c0",
        command=lambda: open_page("/insurance"),
        **btn_style
    )
    btn_insurance.pack(pady=(0, 10))

    btn_edit = tk.Button(
        btn_frame, text="✏️  تعديل ملصق موجود",
        bg="#00838f", activebackground="#00acc1",
        command=lambda: open_page("/edit"),
        **btn_style
    )
    btn_edit.pack(pady=(0, 10))

    btn_verify = tk.Button(
        btn_frame, text="🔍  صفحة التحقق",
        bg="#37474f", activebackground="#546e7a",
        command=lambda: open_page("/iv/fetyy.php?wb=112598800"),
        **btn_style
    )
    btn_verify.pack(pady=(0, 10))

    def sync_all():
        """رفع البيانات إلى GitHub + إرسالها لـ Render."""
        import json as _json, urllib.request as _req, subprocess as _sp
        status_var.set("⏳ جار رفع البيانات إلى GitHub...")
        status_label.config(fg="#fff59d")
        root.update()

        data_file = os.path.join(APP_DIR, "inspections.json")
        if not os.path.exists(data_file):
            status_var.set("⚠️ لا يوجد ملف بيانات")
            return

        # 1) رفع inspections.json إلى GitHub (محفوظ دائماً)
        try:
            _sp.run(["git", "add", "inspections.json"], cwd=APP_DIR,
                     capture_output=True, timeout=10)
            _sp.run(["git", "commit", "-m", "sync inspections data"], cwd=APP_DIR,
                     capture_output=True, timeout=10)
            result = _sp.run(["git", "push"], cwd=APP_DIR,
                              capture_output=True, timeout=30)
            git_ok = result.returncode == 0
        except Exception:
            git_ok = False

        # 2) إرسال البيانات لـ Render مباشرة (للاستخدام الفوري)
        with open(data_file, "r", encoding="utf-8") as f:
            data = _json.load(f)
        ok, fail = 0, 0
        for uid, info in data.items():
            payload = _json.dumps({"barcode_id": uid, "data": info}).encode()
            try:
                r = _req.Request("https://fetyy.onrender.com/api/save",
                                 data=payload,
                                 headers={"Content-Type": "application/json"})
                _req.urlopen(r, timeout=30)
                ok += 1
            except Exception:
                fail += 1

        # حالة النتيجة
        parts = []
        if git_ok:
            parts.append("GitHub ✅")
        else:
            parts.append("GitHub ❌")
        parts.append(f"Render {ok}/{ok+fail}")
        status_var.set(f"{'✅' if git_ok and fail==0 else '⚠️'} {' — '.join(parts)}")
        status_label.config(fg="#a5d6a7" if git_ok and fail == 0 else "#ffab00")

    def sync_threaded():
        threading.Thread(target=sync_all, daemon=True).start()

    btn_sync = tk.Button(
        btn_frame, text="🔄  مزامنة البيانات مع الموقع",
        bg="#e65100", activebackground="#f57c00",
        command=sync_threaded,
        **btn_style
    )
    btn_sync.pack(pady=(0, 10))

    def update_status():
        if server_running:
            status_var.set("✅ السيرفر يعمل — اختر ما تريد")
            status_label.config(fg="#a5d6a7")
        else:
            root.after(500, update_status)

    root.after(500, update_status)

    def on_close():
        root.destroy()
        os._exit(0)

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    # تشغيل السيرفر في thread منفصل
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # فتح المتصفح تلقائياً
    opener_thread = threading.Thread(target=wait_and_open, daemon=True)
    opener_thread.start()

    # عرض نافذة سطح المكتب
    create_gui()
