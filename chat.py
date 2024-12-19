import openai
import os
from utils import extract_text_from_pdf
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

openai.api_key = os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_KEY")


def ask_chatgpt(messages, pdf_paths=None, max_tokens=1500, temperature=0.7):
    """
    Общается с ChatGPT, включая контекст из загруженных PDF.

    :param messages: список сообщений.
    :param pdf_paths: список путей к загруженным PDF-файлам.
    :param max_tokens: максимальное количество токенов.
    :param temperature: температура генерации текста.
    :return: ответ модели.
    """
    # Добавляем содержимое PDF в контекст
    if pdf_paths:
        pdf_content = ""
        for pdf_path in pdf_paths:
            pdf_content += extract_text_from_pdf(pdf_path) + "\n---\n"

        if pdf_content.strip():
            # Добавляем PDF-контекст как сообщение с ролью "системы"
            messages.insert(0, {
                "role": "system",
                "content": f"Here are the contents of the downloaded PDFs to consider when responding:\n\n{pdf_content}"
            })

    # Отправляем запрос в ChatGPT
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature
    )
    return response.choices[0].message['content']

