import os
import streamlit as st
from db import (
    get_projects_for_user,
    get_project_by_id,
    get_sessions_for_project,
    get_session_by_id,
    update_session_summary,
    insert_message,
    get_messages_for_session,
    insert_file,
    get_files_for_project,
    delete_file
)
from ai_openai import ask_chatgpt, transcribe_audio
from utils import save_uploaded_file
from audio_recorder_streamlit import audio_recorder
from pydub import AudioSegment
from io import BytesIO


def validate_audio_length(audio_bytes: bytes, min_length_seconds: float = 0.1) -> bool:
    """
    Проверяет, что длина аудио не слишком мала.
    """
    try:
        audio = AudioSegment.from_file(BytesIO(audio_bytes), format="wav")
        duration_seconds = len(audio) / 1000.0
        return duration_seconds >= min_length_seconds
    except Exception as e:
        st.error(f"Error processing audio: {e}")
        return False


def render_project_card(project_id: int, name: str, user_id: int) -> None:
    """
    Отрисовывает карточку проекта с кнопкой 'Open'.
    """
    if st.button(f"Open {name}"):
        st.session_state["project_id"] = project_id
        st.session_state["session_id"] = None
        st.rerun()


def render_project_sessions(project_id: int) -> None:
    """
    Отрисовывает последние 10 сессий проекта.
    """
    sessions = get_sessions_for_project(project_id)[:10]
    for session in sessions:
        session_id, session_number, status, _summary = session
        st.write(f"- Session {session_number}: {status}")


def user_projects_page(user: tuple) -> None:
    """
    Страница со списком проектов пользователя.
    """
    st.title("My projects")
    user_id = user[0]

    projects = get_projects_for_user(user_id)
    if not projects:
        st.warning("У вас пока нет проектов.")
        return

    for project in projects:
        project_id, name, _goal, _status = project
        render_project_card(project_id, name, user_id)
        render_project_sessions(project_id)


def render_project_summary(project: tuple) -> None:
    """
    Отрисовывает краткую информацию о проекте (пример статичного описания).
    """
    st.markdown("<p style='margin: 5px 0px;'>Project summary</p>", unsafe_allow_html=True)
    st.markdown("<p style='margin: 5px 0px;'>Line 3 setup</p>", unsafe_allow_html=True)
    st.markdown(
        '<p style="color:gray; font-size:16px;">'
        'Line 3 is a bottle neck. Reducing its setup time will enable 180% production growth'
        '</p>',
        unsafe_allow_html=True,
    )


def render_project_progress() -> None:
    """
    Отрисовывает прогресс по сессиям в виде цветных квадратиков (пример статичной структуры).
    """
    sessions = [
        {"id": 1, "status": "completed"},
        {"id": 2, "status": "completed"},
        {"id": 3, "status": "completed"},
        {"id": 4, "status": "not completed"},
        {"id": 5, "status": "not completed"},
        {"id": 6, "status": "not completed"},
        {"id": 7, "status": "not completed"},
        {"id": 8, "status": "not completed"},
        {"id": 9, "status": "not completed"},
        {"id": 10, "status": "not completed"},
    ]
    progress_html = "<div style='display: flex; gap: 5px; margin-bottom: 10px;'>"
    for session in sessions:
        color = "#4CAF50" if session["status"] == "completed" else "#777"
        progress_html += (
            f"<div style='width: 20px; height: 20px; background-color: {color}; "
            f"border-radius: 3px;'></div>"
        )
    progress_html += "</div>"
    st.markdown(progress_html, unsafe_allow_html=True)


def upload_pdf_file(project_id: int) -> None:
    """
    Виджет загрузки PDF-файла и сохранение в БД.
    """
    uploaded_file = st.file_uploader("Select a PDF file", type=["pdf"])
    if uploaded_file is not None:
        existing_files = get_files_for_project(project_id)
        existing_file_names = {f[2] for f in existing_files}
        if uploaded_file.name not in existing_file_names:
            file_path = save_uploaded_file(uploaded_file)
            insert_file(project_id, file_path, uploaded_file.name)
            st.success("The file has been uploaded!")
        else:
            st.warning("Файл с таким именем уже загружен!")


def render_uploaded_files(project_id: int) -> None:
    """
    Отрисовывает список загруженных файлов и даёт возможность их удалить.
    """
    st.write("Uploaded files")
    files = get_files_for_project(project_id)
    for file_data in files:
        file_id, file_path, file_name = file_data
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(file_name)
        with col2:
            if st.button("Delete", key=f"delete_{file_id}"):
                delete_file(file_id)
                st.success(f"File {file_name} has been deleted!")
                st.rerun()


def project_page(user: tuple, project_id: int) -> None:
    """
    Страница конкретного проекта.
    """
    project = get_project_by_id(project_id)
    if not project:
        st.error("Project not found")
        return

    render_project_summary(project)
    render_project_progress()

    st.markdown("<p style='margin: 5px 0px;'>Goals</p>", unsafe_allow_html=True)
    st.markdown(f'<p style="color:gray; font-size:16px;">{project[3]}</p>', unsafe_allow_html=True)

    upload_pdf_file(project_id)
    render_uploaded_files(project_id)


def process_audio_input() -> None:
    """
    Обрабатывает аудиовход и помещает результат расшифровки
    в st.session_state["transcribed_text"].
    """
    audio_bytes = audio_recorder(
        text="",
        pause_threshold=2.0,
        sample_rate=41_000,
        icon_size="2x"
    )
    if audio_bytes and (audio_bytes != st.session_state.get("last_audio", b"")) \
            and not st.session_state.get("audio_processed", False):
        if not st.session_state.get("rerun", False):
            if validate_audio_length(audio_bytes):
                transcribed_text = transcribe_audio(audio_bytes)
                if transcribed_text.strip():
                    # Сохраняем расшифрованный текст в отдельную переменную
                    st.session_state["transcribed_text"] = transcribed_text
                    st.session_state["last_audio"] = audio_bytes
                    st.session_state["audio_processed"] = True
                    st.rerun()
                else:
                    st.error("Transcribed message is empty. Please try again.")
        else:
            st.session_state["rerun"] = False


def send_user_message(session_id: int, user_message: str) -> None:
    """
    Отправляет сообщение пользователя в ChatGPT и сохраняет ответ.
    """
    if not user_message.strip():
        st.error("Please enter a message.")
        return

    all_msgs = get_messages_for_session(session_id)
    messages_format = [
        {"role": "user" if m[0] == "user" else "assistant", "content": m[1]}
        for m in all_msgs
    ]
    messages_format.append({"role": "user", "content": user_message})

    session = get_session_by_id(session_id)
    pdf_files = get_files_for_project(session[1])
    pdf_paths = [file[1] for file in pdf_files]

    assistant_reply = ask_chatgpt(messages_format, pdf_paths=pdf_paths)

    insert_message(session_id, "user", user_message)
    insert_message(session_id, "assistant", assistant_reply)

    # Сброс состояний
    st.session_state["audio_processed"] = False
    st.session_state["last_audio"] = b""
    st.session_state["transcribed_text"] = ""
    st.session_state["rerun"] = True
    st.rerun()


def summarize_session(session_id: int) -> None:
    """
    Генерирует краткое резюме переписки с помощью ChatGPT и сохраняет результат.
    """
    all_msgs = get_messages_for_session(session_id)
    chat_text = "\n".join([f"{msg[0]}: {msg[1]}" for msg in all_msgs])
    summary_prompt = (
        "Summarize the conversation, don't use a lot of text, "
        "try to summarize as briefly as possible:\n\n" + chat_text
    )
    session = get_session_by_id(session_id)
    pdf_files = get_files_for_project(session[1])
    pdf_paths = [file[1] for file in pdf_files]

    summary = ask_chatgpt([{"role": "user", "content": summary_prompt}], pdf_paths=pdf_paths)
    update_session_summary(session_id, summary)
    st.success("The summary has been updated!")
    st.rerun()


def session_page(user: tuple, session_id: int) -> None:
    """
    Страница конкретной сессии.
    """
    # Инициализация session_state (не используем key='...' у chat_input)
    st.session_state.setdefault("audio_processed", False)
    st.session_state.setdefault("rerun", False)
    st.session_state.setdefault("last_audio", b"")
    st.session_state.setdefault("transcribed_text", "")

    session_data = get_session_by_id(session_id)

    if st.button("Back"):
        st.session_state["session_id"] = None
        st.session_state["audio_processed"] = False
        st.session_state["last_audio"] = b""
        st.rerun()

    if not session_data:
        st.error("Session not found.")
        return

    st.title(f"Session {session_data[2]}")
    st.write(f"Status: {session_data[3]}")
    st.write(f"Summary: {session_data[4]}")

    # Отображаем историю сообщений
    msgs = get_messages_for_session(session_id)
    for sender, content, _ in msgs:
        if sender == "user":
            st.markdown(
                f"<div style='background-color: #2a2a2a; color: #ececec; "
                f"padding: 10px; margin: 10px 0px 0px 0px; "
                f"border-radius: 5px; float: right'>{content}</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div style='color: #ececec; margin: 0px 0px 20px 0px; "
                f"border-radius: 5px;'>{content}</div>",
                unsafe_allow_html=True
            )

    st.markdown("---")

    # Сначала обрабатываем аудио
    process_audio_input()

    # Если есть расшифрованный текст — показываем его, чтобы пользователь мог скопировать/отправить
    # if st.session_state["transcribed_text"]:
    #     st.info(f"Transcribed text: {st.session_state['transcribed_text']}")

    # Поле ввода сообщения (без ключа). Отправляется при нажатии Enter
    user_message = st.chat_input("Your question...")
    if user_message:
        send_user_message(session_id, user_message)

    # Кнопка "Summarize"
    if st.button("Summarize"):
        summarize_session(session_id)
