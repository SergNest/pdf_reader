import os
import re

from flask import Flask, request, render_template, send_file, redirect, url_for, abort
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from docx import Document
import pytesseract
from pdf2image import convert_from_path
from dotenv import load_dotenv
from PIL import Image

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.getenv("UPLOAD_FOLDER", "uploads")
app.config['CONVERTED_FOLDER'] = os.getenv("CONVERTED_FOLDER", "converted_files")

allowed_ips = [ip.strip() for ip in os.getenv('MY_LIST', '').split(',') if ip.strip()]
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}


# Перевірка розширення файлу
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.before_request
def limit_remote_addr():
    print(request.remote_addr)
    if request.remote_addr not in allowed_ips:
        abort(403)  # Доступ заборонено


def extract_text_from_pdf(pdf_file: str) -> list[str]:
    with open(pdf_file, 'rb') as pdf:
        reader = PdfReader(pdf, strict=False)
        pdf_text: list[str] = [page.extract_text() for page in reader.pages]
        return pdf_text


# # Основна функція для перетворення PDF в DOCX з OCR
# def convert_pdf_to_docx(pdf_path, output_filename):
#     doc = Document()
#     images = convert_from_path(pdf_path)
#     custom_oem_psm_config = r'--oem 3 --psm 6'
#
#     for i, image in enumerate(images):
#         text = pytesseract.image_to_string(image, config=custom_oem_psm_config)
#         text = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\xA0-\uD7FF\uE000-\uFFFD]', '', text)
#         doc.add_paragraph(text)
#
#     output_path = os.path.join(CONVERTED_FOLDER, output_filename)
#     doc.save(output_path)
#     return output_path


# Функція для конвертації PDF або зображення у DOCX
def convert_to_docx(file_path, output_filename):
    doc = Document()
    _, ext = os.path.splitext(file_path)
    custom_oem_psm_config = r'--oem 3 --psm 6'

    # Обробка PDF
    if ext.lower() == '.pdf':
        images = convert_from_path(file_path)
        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image, config=custom_oem_psm_config)
            text = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\xA0-\uD7FF\uE000-\uFFFD]', '', text)
            doc.add_paragraph(text)

    # Обробка зображень
    elif ext.lower() in {'.png', '.jpg', '.jpeg'}:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        text = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\xA0-\uD7FF\uE000-\uFFFD]', '', text)
        doc.add_paragraph(text)

    output_path = str(os.path.join(app.config['CONVERTED_FOLDER'], output_filename))
    doc.save(output_path)
    return output_path


# Головна сторінка для завантаження PDF і перегляду останніх конвертованих файлів
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file part'

        file = request.files['file']

        if file.filename == '':
            return 'No selected file'

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            output_filename = f"{os.path.splitext(filename)[0]}.docx"
            output_path = convert_to_docx(file_path, output_filename)

            # Відображення списку останніх конвертованих файлів
            converted_files = sorted(os.listdir(app.config['CONVERTED_FOLDER']), reverse=True)[:5]
            return render_template('index.html', converted_files=converted_files)

    # converted_files = sorted(os.listdir(app.config['CONVERTED_FOLDER']), reverse=True)[:5]
    # return render_template('index.html', converted_files=converted_files)

    # функція для отримання останніх файлів
    converted_files = get_last_converted_files()
    return render_template('index.html', converted_files=converted_files)


# Завантаження конвертованого файлу
@app.route("/download/<filename>")
def download_file(filename):
    path = os.path.join(app.config['CONVERTED_FOLDER'], filename)
    return send_file(path, as_attachment=True)


# Отримуємо останні 5 конвертованих файлів
def get_last_converted_files():
    files = sorted(
        [(f, os.path.getmtime(os.path.join(app.config['CONVERTED_FOLDER'], f))) for f in os.listdir(app.config['CONVERTED_FOLDER'])],
        key=lambda x: x[1], reverse=True
    )
    return [f[0] for f in files[:5]]


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['CONVERTED_FOLDER'], exist_ok=True)
    app.run(debug=True, port=5006, host='0.0.0.0')






