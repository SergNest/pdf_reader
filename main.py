import os
import re
from typing import List, Tuple

from flask import Flask, request, render_template, send_file, redirect, url_for, abort
from werkzeug.utils import secure_filename
from docx import Document
import pytesseract
from pdf2image import convert_from_path
from dotenv import load_dotenv
from PIL import Image

import openai
from openai import OpenAI

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.getenv("UPLOAD_FOLDER", "uploads")
app.config['CONVERTED_FOLDER'] = os.getenv("CONVERTED_FOLDER", "converted_files")

allowed_ips = [ip.strip() for ip in os.getenv('MY_LIST', '').split(',') if ip.strip()]
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

client = OpenAI(
    # This is the default and can be omitted
    api_key=os.getenv("YOUR_API_KEY", "api_key"),
)


# Перевірка розширення файлу
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.before_request
def limit_remote_addr():
    print(request.remote_addr)
    if request.remote_addr not in allowed_ips:
        abort(403)  # Доступ заборонено


# Функція для конвертації PDF або зображення у DOCX
def convert_to_docx(file_path, output_filename, use_ai=False):
    """
    Конвертує PDF або зображення в DOCX, опціонально використовуючи AI для корекції тексту.

    Args:
        file_path: Шлях до вхідного файлу.
        output_filename: Назва вихідного DOCX файлу.
        use_ai: Флаг, що вказує, чи використовувати AI для корекції тексту.
    """
    doc = Document()
    _, ext = os.path.splitext(file_path)
    custom_oem_psm_config = r'--oem 3 --psm 6'

    if ext.lower() == '.pdf':
        images = convert_from_path(file_path)
        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image, config=custom_oem_psm_config)
            text = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\xA0-\uD7FF\uE000-\uFFFD]', '', text)
            if use_ai:
                text = correct_text_with_ai(text)
            doc.add_paragraph(text)

    elif ext.lower() in {'.png', '.jpg', '.jpeg'}:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        text = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\xA0-\uD7FF\uE000-\uFFFD]', '', text)
        if use_ai:
            text = correct_text_with_ai(text)
        doc.add_paragraph(text)

    output_path = str(os.path.join(app.config['CONVERTED_FOLDER'], output_filename))
    doc.save(output_path)
    return output_path


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
            use_ai = request.form.get('use_ai') == 'on'  # Отримання значення checkbox
            convert_to_docx(file_path, output_filename, use_ai=use_ai)  # Передача use_ai

    # Якщо метод GET, або якщо файл не було завантажено
    converted_files = get_last_converted_files()
    return render_template('index.html', converted_files=converted_files)


# Завантаження конвертованого файлу
@app.route("/download/<filename>")
def download_file(filename):
    path = os.path.join(app.config['CONVERTED_FOLDER'], filename)
    return send_file(path, as_attachment=True)


def get_last_converted_files(converted_folder: str = app.config['CONVERTED_FOLDER'], num_files: int = 5) -> List[str]:
    """
    Повертає список останніх конвертованих файлів у заданій папці.

    Args:
        converted_folder: Шлях до папки з конвертованими файлами.
        num_files: Кількість останніх файлів для повернення (за замовчуванням 5).

    Returns:
        Список шляхів до останніх конвертованих файлів, відсортованих за часом модифікації.
        Повертає порожній список, якщо папка не існує або немає файлів.
    """

    if not os.path.exists(converted_folder):
        return []

    files_with_time: List[Tuple[str, float]] = []
    for entry in os.scandir(converted_folder):  # Використовуємо os.scandir для кращої продуктивності
        if entry.is_file():
            try:
                mtime = entry.stat().st_mtime
                files_with_time.append((entry.name, mtime))
            except OSError as e:
                print(f"Помилка при отриманні часу модифікації для файлу {entry.path}: {e}")
                continue  # Пропускаємо файл, якщо виникла помилка

    # Сортуємо за часом модифікації, від найновіших до найстаріших
    files_with_time.sort(key=lambda x: x[1], reverse=True)

    # Повертаємо список останніх файлів
    return [f[0] for f in files_with_time[:num_files]]


def correct_text_with_ai(text):
    """Коригує текст за допомогою OpenAI API."""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Модель, яку хочете використовувати
            messages=[
                {"role": "system", "content": "Ви - помічник, який коригує текст."},
                {"role": "user", "content": f"Correct the following text:\n\n{text}"}
            ],
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()  # Правильний доступ до content
    except openai.APIConnectionError as e:
        print(f"Помилка OpenAI API: {e}")
        return text  # Повертаємо оригінальний текст у разі помилки


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['CONVERTED_FOLDER'], exist_ok=True)
    app.run(debug=True, port=5006, host='0.0.0.0')






