# ai_openai.py

import openai
import os
from utils import extract_text_from_pdf
from dotenv import find_dotenv, load_dotenv
from io import BytesIO
from db import get_admin_prompts  # Импортируем функцию для получения промптов

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
    # Получаем промпты из БД
    prompts = get_admin_prompts()
    assistant_prompt = prompts.get("assistant_prompt", "").strip()
    file_upload_prompt = prompts.get("file_upload_prompt", "").strip()

    # Добавляем содержимое PDF в контекст
    if pdf_paths:
        pdf_content = ""
        for pdf_path in pdf_paths:
            pdf_content += extract_text_from_pdf(pdf_path) + "\n---\n"

        # Добавляем текст про Charlie как системное сообщение, если есть
        if pdf_content.strip():
            # Используем 'file_upload_prompt' из БД вместо жестко прописанного
            if file_upload_prompt:
                system_prompt = f"Here are the contents of the downloaded PDFs to consider when responding:\n\n{pdf_content}"
            else:
                # Fallback, если промпт не задан
                system_prompt = f"Here are the contents of the downloaded PDFs to consider when responding:\n\n{pdf_content}"

            messages.insert(0, {
                "role": "system",
                "content": system_prompt
            })

    # Добавляем 'assistant_prompt' как системное сообщение, если задан
    if assistant_prompt:
        messages.insert(0, {
            "role": "system",
            "content": assistant_prompt
        })

    # Отправляем запрос в ChatGPT
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # Убедитесь, что используете корректную модель
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature
    )
    return response.choices[0].message['content']


def transcribe_audio(audio_bytes: bytes) -> str:
    """
    Отправляет аудиоданные на Whisper API и возвращает расшифрованный текст.
    """
    audio_stream = BytesIO(audio_bytes)  # Преобразуем аудиобайты в поток
    audio_stream.name = "audio.wav"  # Whisper требует указания имени файла
    transcript = openai.Audio.transcribe(
        model="whisper-1",
        file=audio_stream,
        # prompt="Введите описание, если нужно",
        # language="ru"
    )
    return transcript["text"]
