# ai_openai.py

import openai
import os
from utils import extract_text_from_pdf
from dotenv import find_dotenv, load_dotenv
from io import BytesIO
from db import get_admin_prompts, get_admin_pdf_paths  # Импортируем функцию для получения промптов

load_dotenv(find_dotenv())

openai.api_key = os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_KEY")


def ask_chatgpt(messages, pdf_paths=None, max_tokens=1500, temperature=0.7):
    """
    Общается с ChatGPT, включая контекст из загруженных PDF.

    :param messages: список сообщений.
    :param pdf_paths: список путей к загруженным PDF-файлам (если есть).
    :param max_tokens: макс. кол-во токенов.
    :param temperature: "температура" генерации.
    :return: ответ модели.
    """
    # Получаем промпты из БД
    prompts = get_admin_prompts()
    assistant_prompt = prompts.get("assistant_prompt", "").strip()
    file_upload_prompt = prompts.get("file_upload_prompt", "").strip()

    # Берём глобальные PDF от админа
    admin_pdf_paths = get_admin_pdf_paths()  # список путей

    # Если вызов пришёл с дополнительными pdf_paths, комбинируем их
    if pdf_paths is None:
        pdf_paths = []
    all_pdf_paths = pdf_paths + admin_pdf_paths

    # 1) Добавляем содержимое PDF в контекст
    if all_pdf_paths:
        pdf_content = ""
        for p in all_pdf_paths:
            pdf_content += extract_text_from_pdf(p) + "\n---\n"

        if pdf_content.strip():
            # Если есть file_upload_prompt, используем его, иначе fallback
            if file_upload_prompt:
                system_prompt = (
                    f"{file_upload_prompt}\n\n"
                    f"Here are the contents of the uploaded PDFs:\n{pdf_content}"
                )
            else:
                system_prompt = (
                    f"Here are the contents of the uploaded PDFs:\n{pdf_content}"
                )

            messages.insert(0, {
                "role": "system",
                "content": system_prompt
            })

    # 2) Добавляем 'assistant_prompt' как системное сообщение, если он задан
    if assistant_prompt:
        messages.insert(0, {
            "role": "system",
            "content": assistant_prompt
        })

    # 3) Запрашиваем ChatGPT
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # или другая ваша модель
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
