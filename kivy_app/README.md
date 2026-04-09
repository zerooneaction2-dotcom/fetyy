# Kivy Certificate Generator

This small Kivy application provides a form (Arabic-friendly) to enter certificate fields and generates a PDF that matches the supplied design, including a Code128 barcode.

Quick start

1. Create a virtual environment and activate it (recommended):

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Place an Arabic TTF font (recommended `Tajawal.ttf` or `Cairo-Regular.ttf`) next to `main.py`.

4. Run the app:

```bash
python main.py
```

5. Fill the form and press `توليد البطاقة`. The file `certificate.pdf` will be created in the project folder and opened by the system PDF viewer.

Packaging for Android

- You can convert this app to an APK using `buildozer` (on Linux) or `python-for-android`. You'll need to add the required dependencies to the buildozer spec and include the TTF font in the APK assets. Packaging mobile apps is outside the scope of this README but this app is structured to be portable.

Notes

- Arabic text rendering uses `arabic-reshaper` + `python-bidi` and requires a proper Arabic font file for best results.
- The barcode uses `python-barcode` and is rendered as a PNG then composed onto the certificate image.
