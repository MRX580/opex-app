import os
from PyPDF2 import PdfReader

def save_uploaded_file(file, upload_dir="uploads"):
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    file_path = os.path.join(upload_dir, file.name)
    with open(file_path, "wb") as f:
        f.write(file.getbuffer())
    return file_path


def extract_text_from_pdf(file_path):
    """Извлекает текст из PDF файла."""
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"Ошибка при извлечении текста из PDF: {e}")
        return ""
