import os
import re

from flask import Flask, request, render_template, send_file, redirect, url_for, abort
from PyPDF2 import PdfReader
from docx import Document
import pytesseract
from pdf2image import convert_from_path

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
CONVERTED_FOLDER = "converted_files"


ALLOWED_IP = ["20.50.0.152", "65.109.159.113"]


@app.before_request
def limit_remote_addr():
    print(request.remote_addr)
    if request.remote_addr not in ALLOWED_IP:
        abort(403)  # Доступ заборонено


def extract_text_from_pdf(pdf_file: str) -> list[str]:
    with open(pdf_file, 'rb') as pdf:
        reader = PdfReader(pdf, strict=False)
        pdf_text: list[str] = [page.extract_text() for page in reader.pages]
        return pdf_text


# Основна функція для перетворення PDF в DOCX з OCR
def convert_pdf_to_docx(pdf_path, output_filename):
    doc = Document()
    images = convert_from_path(pdf_path)
    custom_oem_psm_config = r'--oem 3 --psm 6'

    for i, image in enumerate(images):
        text = pytesseract.image_to_string(image, config=custom_oem_psm_config)
        text = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\xA0-\uD7FF\uE000-\uFFFD]', '', text)
        doc.add_paragraph(text)

    output_path = os.path.join(CONVERTED_FOLDER, output_filename)
    doc.save(output_path)
    return output_path


# Головна сторінка для завантаження PDF і перегляду останніх конвертованих файлів
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "pdf_file" not in request.files:
            return "No file part in the request"

        file = request.files["pdf_file"]

        if file.filename == "":
            return "No selected file"

        if file:
            # Зберігаємо PDF файл
            pdf_filename = file.filename
            pdf_path = os.path.join(UPLOAD_FOLDER, pdf_filename)
            file.save(pdf_path)

            # Ім'я для вихідного DOCX файла
            output_filename = os.path.splitext(pdf_filename)[0] + ".docx"
            output_path = convert_pdf_to_docx(pdf_path, output_filename)

            # Повертаємось на головну сторінку після конвертації
            return redirect(url_for("index"))

    # Отримуємо останні 5 конвертованих файлів для відображення на сторінці
    last_files = get_last_converted_files()
    return render_template("index.html", last_files=last_files)


# Завантаження конвертованого файлу
@app.route("/download/<filename>")
def download_file(filename):
    path = os.path.join(CONVERTED_FOLDER, filename)
    return send_file(path, as_attachment=True)


# Отримуємо останні 5 конвертованих файлів
def get_last_converted_files():
    files = sorted(
        [(f, os.path.getmtime(os.path.join(CONVERTED_FOLDER, f))) for f in os.listdir(CONVERTED_FOLDER)],
        key=lambda x: x[1], reverse=True
    )
    return [f[0] for f in files[:5]]


if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(CONVERTED_FOLDER, exist_ok=True)
    app.run(debug=True, port=5006, host='0.0.0.0')






