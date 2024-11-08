import os

from flask import Flask, request, render_template, send_file
from PyPDF2 import PdfReader
from docx import Document
import pytesseract
from pdf2image import convert_from_path

app = Flask(__name__)


def extract_text_from_pdf(pdf_file: str) -> list[str]:
    with open(pdf_file, 'rb') as pdf:
        reader = PdfReader(pdf, strict=False)
        pdf_text: list[str] = [page.extract_text() for page in reader.pages]
        return pdf_text


def main():
    doc = Document()
    # extracted_text: list[str] = extract_text_from_pdf('document (3).pdf')
    images = convert_from_path('WW1.pdf')

    # Проходимо по кожному зображенню і застосовуємо Tesseract для розпізнавання тексту
    for i, image in enumerate(images):
        text = pytesseract.image_to_string(image)
        # print(f"Текст на сторінці {i + 1}:\n{text}\n")

        doc.add_paragraph(text)

    doc.save("example.docx")


# Основна функція для перетворення PDF в DOCX з OCR
def convert_pdf_to_docx(pdf_path):
    doc = Document()
    images = convert_from_path(pdf_path)

    for i, image in enumerate(images):
        text = pytesseract.image_to_string(image)
        doc.add_paragraph(text)

    output_path = "output.docx"
    doc.save(output_path)
    return output_path


# Головна сторінка для завантаження PDF
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "pdf_file" not in request.files:
            return "No file part in the request"
        file = request.files["pdf_file"]

        if file.filename == "":
            return "No selected file"

        if file:
            pdf_path = os.path.join("uploads", file.filename)
            file.save(pdf_path)
            output_path = convert_pdf_to_docx(pdf_path)
            return send_file(output_path, as_attachment=True)
    return render_template("index.html")


if __name__ == '__main__':
    os.makedirs("uploads", exist_ok=True)
    app.run(debug=True)






