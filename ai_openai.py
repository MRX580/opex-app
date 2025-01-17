import os
import base64
import openai
import pyttsx3
import streamlit as st
from io import BytesIO
from dotenv import find_dotenv, load_dotenv

from utils import extract_text_from_pdf
from db import get_admin_prompts, get_admin_pdf_paths
from gtts import gTTS

load_dotenv(find_dotenv())
openai.api_key = os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_KEY")


def ask_chatgpt(messages, pdf_paths=None, max_tokens=1500, temperature=0.7):
    """
    Общается с ChatGPT, включая контекст из загруженных PDF.
    """
    # Получаем кастомные промпты из БД
    prompts = get_admin_prompts()
    assistant_prompt = prompts.get("assistant_prompt", "").strip()
    file_upload_prompt = prompts.get("file_upload_prompt", "").strip()

    # Глобальные PDF-файлы
    admin_pdf_paths = get_admin_pdf_paths()
    if pdf_paths is None:
        pdf_paths = []
    all_pdf_paths = pdf_paths + admin_pdf_paths

    # Собираем содержимое всех PDF в одну строку
    if all_pdf_paths:
        pdf_content = ""
        for p in all_pdf_paths:
            pdf_content += extract_text_from_pdf(p) + "\n---\n"

        if pdf_content.strip():
            system_prompt = (
                f"{file_upload_prompt}\n\nHere are the contents of the uploaded PDFs:\n{pdf_content}"
                if file_upload_prompt
                else f"Here are the contents of the uploaded PDFs:\n{pdf_content}"
            )
            messages.insert(0, {"role": "system", "content": system_prompt})

    # Если есть общий assistant_prompt, добавляем как системное сообщение
    if assistant_prompt:
        messages.insert(0, {"role": "system", "content": assistant_prompt})

    # Запрос к ChatGPT
    # При желании поменяйте на "gpt-3.5-turbo" или "gpt-4"
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature
    )
    return response.choices[0].message["content"]


def transcribe_audio(audio_bytes: bytes) -> str:
    """
    Расшифровка аудио (Whisper).
    """
    audio_stream = BytesIO(audio_bytes)
    audio_stream.name = "audio.wav"
    transcript = openai.Audio.transcribe(
        model="whisper-1",
        file=audio_stream
    )
    return transcript["text"]


def text_to_speech(input_text: str) -> str:
    """
    Преобразует текст в речь (gTTS) и возвращает путь к mp3-файлу.
    """
    tts = gTTS(text=input_text, lang="en")  # при желании ставьте lang="ru"
    file_path = "temp_audio.mp3"
    tts.save(file_path)
    return file_path


def autoplay_audio(file_path: str, muted: bool = False):
    """
    Проигрывает audio/mp3 в режиме autoplay.
    Если muted=True, то аудио будет запущено без звука.
    """
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode("utf-8")

        # Если muted=True — добавляем атрибут "muted"
        muted_attr = "muted" if muted else ""
        print(muted_attr)
        print(True)
        md = f"""
        <audio autoplay {muted_attr}>
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        """
        st.markdown(md, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Ошибка при воспроизведении аудио: {e}")