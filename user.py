import os
import streamlit as st
from db import (
    get_projects_for_user, get_project_by_id, get_sessions_for_project, get_session_by_id,
    update_session_summary, insert_message, get_messages_for_session,
    insert_file, get_files_for_project, delete_file
)
from ai_openai import ask_chatgpt, transcribe_audio
from utils import save_uploaded_file
from audio_recorder_streamlit import audio_recorder
from pydub import AudioSegment
from io import BytesIO

def validate_audio_length(audio_bytes: bytes, min_length_seconds: float = 0.1) -> bool:
    """Проверяем, что длина аудио не слишком мала."""
    try:
        audio = AudioSegment.from_file(BytesIO(audio_bytes), format="wav")
        duration_seconds = len(audio) / 1000.0
        return duration_seconds >= min_length_seconds
    except Exception as e:
        st.error(f"Error processing audio: {e}")
        return False

def user_projects_page(user):
    st.title("My projects")
    projects = get_projects_for_user(user[0])
    for p in projects:
        project_id, name, goal, status = p
        if st.button(f"Open {name}"):
            st.session_state["project_id"] = project_id
            st.session_state["session_id"] = None
            st.rerun()
        sessions = get_sessions_for_project(project_id)[:10]
        for s in sessions:
            s_id, s_num, s_status, s_summary = s
            st.write(f"- Session {s_num}: {s_status}")

def project_page(user, project_id):
    project = get_project_by_id(project_id)
    if not project:
        st.error("Project not found.")
        return

    st.markdown(f"**Project:** {project[1]}")
    st.markdown(f"**Goal:** {project[2]}")

    uploaded_file = st.file_uploader("Select a PDF file", type=["pdf"])
    if uploaded_file is not None:
        existing_files = get_files_for_project(project_id)
        existing_file_names = {f[2] for f in existing_files}
        if uploaded_file.name not in existing_file_names:
            file_path = save_uploaded_file(uploaded_file)
            insert_file(project_id, file_path, uploaded_file.name)
            st.success("The file has been uploaded!")
            st.rerun()

    st.write("Uploaded files:")
    files = get_files_for_project(project_id)
    for f_ in files:
        fid, fpath, fname = f_
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(fname)
        with col2:
            if st.button("Delete", key=f"delete_{fid}"):
                delete_file(fid)
                st.success(f"File {fname} has been deleted!")
                st.rerun()

def session_page(user, session_id):
    # Инициализация состояния
    if "audio_processed" not in st.session_state:
        st.session_state["audio_processed"] = False
    if "rerun" not in st.session_state:
        st.session_state["rerun"] = False
    if "user_message_input" not in st.session_state:
        st.session_state["user_message_input"] = ""
    if "last_audio" not in st.session_state:
        st.session_state["last_audio"] = b""

    session = get_session_by_id(session_id)
    if st.button("Back"):
        st.session_state["session_id"] = None
        # Сброс флагов при уходе
        st.session_state["audio_processed"] = False
        st.session_state["last_audio"] = b""
        st.rerun()

    if not session:
        st.error("Session not found.")
        return

    st.title(f"Session {session[2]}")
    st.write(f"Status: {session[3]}")
    st.write(f"Summary: {session[4]}")

    # Отображаем историю сообщений
    msgs = get_messages_for_session(session_id)
    for sender, content, _ in msgs:
        if sender == "user":
            st.markdown(
                f"<div style='background-color: #2a2a2a; color: #ececec;"
                f"padding: 10px; margin: 10px 0px 0px 0px;"
                f"border-radius: 5px; float: right'>{content}</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div style='color: #ececec; margin: 0px 0px 20px 0px; border-radius: 5px;'>{content}</div>",
                unsafe_allow_html=True
            )

    st.markdown("---")

    col1, col2 = st.columns([3, 1])
    with col1:
        user_msg = st.text_input(
            "Your question...",
            value=st.session_state["user_message_input"]
        )

    # Виджет записи аудио (микрофон)
    with col1:
        audio_bytes = audio_recorder(
            text="",
            pause_threshold=2.0,
            sample_rate=41_000,
            icon_size="2x"
        )
    # Если новое аудио и ещё не обработали
    if audio_bytes and (audio_bytes != st.session_state["last_audio"]) and not st.session_state["audio_processed"]:
        if not st.session_state["rerun"]:
            if validate_audio_length(audio_bytes):
                transcribed_text = transcribe_audio(audio_bytes)
                if transcribed_text.strip():
                    # Подставляем в поле — НЕ отправляем
                    st.session_state["user_message_input"] = transcribed_text

                    # Запоминаем, чтобы не повторять
                    st.session_state["last_audio"] = audio_bytes
                    st.session_state["audio_processed"] = True
                    # Рерун, чтобы снова показать окно доступа к микрофону
                    st.rerun()
                else:
                    st.error("Transcribed message is empty. Please try again.")
        else:
            st.session_state["rerun"] = False

    # Кнопка "Send" для ручной отправки
    with col2:
        if st.button("Send"):
            if user_msg.strip():
                # Формируем историю
                all_msgs = get_messages_for_session(session_id)
                messages_format = [
                    {"role": "user" if m[0] == "user" else "assistant", "content": m[1]}
                    for m in all_msgs
                ]
                messages_format.append({"role": "user", "content": user_msg})

                pdf_files = get_files_for_project(session[1])
                pdf_paths = [file[1] for file in pdf_files]

                # Отправляем в ChatGPT
                reply = ask_chatgpt(messages_format, pdf_paths=pdf_paths)
                insert_message(session_id, "user", user_msg)
                insert_message(session_id, "assistant", reply)

                # Очищаем поле и флаги
                st.session_state["user_message_input"] = ""
                st.session_state["audio_processed"] = False
                st.session_state["last_audio"] = b""
                st.session_state["rerun"] = True
                st.rerun()
            else:
                st.error("Please enter a message.")

    # Summarize
    if st.button("Summarize"):
        all_msgs = get_messages_for_session(session_id)
        chat_text = "\n".join([f"{m[0]}: {m[1]}" for m in all_msgs])
        summary_prompt = (
            "Summarize the conversation, don't use a lot of text, "
            "try to summarize as briefly as possible:\n\n" + chat_text
        )
        pdf_files = get_files_for_project(session[1])
        pdf_paths = [file[1] for file in pdf_files]
        summary = ask_chatgpt([{"role": "user", "content": summary_prompt}], pdf_paths=pdf_paths)
        update_session_summary(session_id, summary)
        st.success("The summary has been updated!")
        st.rerun()
