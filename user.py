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
    delete_file,
    get_files_for_session
)
from ai_openai import ask_chatgpt, transcribe_audio
from utils import save_uploaded_file
from audio_recorder_streamlit import audio_recorder
from pydub import AudioSegment
from io import BytesIO


def validate_audio_length(audio_bytes: bytes, min_length_seconds: float = 0.1) -> bool:
    try:
        audio = AudioSegment.from_file(BytesIO(audio_bytes), format="wav")
        duration_seconds = len(audio) / 1000.0
        return duration_seconds >= min_length_seconds
    except Exception as e:
        st.error(f"Error processing audio: {e}")
        return False


def render_project_card(project_id: int, name: str, user_id: int) -> None:
    if st.button(f"Open {name}"):
        st.session_state["project_id"] = project_id
        st.session_state["session_id"] = None
        st.rerun()


def render_project_sessions(project_id: int) -> None:
    sessions = get_sessions_for_project(project_id)[:10]
    for session in sessions:
        session_id, session_number, status, _summary = session
        st.write(f"- Session {session_number}: {status}")


def user_projects_page(user: tuple) -> None:
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
    st.markdown(f"<p style='margin: 5px 0px;'>Project {project[2]}</p>", unsafe_allow_html=True)
    st.markdown("<p style='margin: 5px 0px;'>Line 3 setup</p>", unsafe_allow_html=True)
    st.markdown(
        '<p style="color:gray; font-size:16px;">'
        'Line 3 is a bottle neck. Reducing its setup time will enable 180% production growth'
        '</p>',
        unsafe_allow_html=True,
    )


def render_project_progress() -> None:
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


def upload_pdf_file_for_session(session_id: int) -> None:
    uploaded_file = st.file_uploader("Select a PDF file for this session", type=["pdf"])
    if uploaded_file is not None:
        existing_files = get_files_for_session(session_id)
        existing_file_names = {f[2] for f in existing_files}
        if uploaded_file.name not in existing_file_names:
            file_path = save_uploaded_file(uploaded_file)
            insert_file(session_id, file_path, uploaded_file.name)
            st.success("The file has been uploaded!")
        else:
            st.warning("A file with this name already exists for this session!")


def render_uploaded_files_for_session(session_id: int) -> None:
    files = get_files_for_session(session_id)
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


def render_uploaded_files(project_id: int) -> None:
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
    project = get_project_by_id(project_id)
    if not project:
        st.error("Project not found")
        return

    render_project_summary(project)
    render_project_progress()

    st.markdown("<p style='margin: 5px 0px;'>Goals</p>", unsafe_allow_html=True)
    st.markdown(f'<p style="color:gray; font-size:16px;">{project[3]}</p>', unsafe_allow_html=True)

    st.markdown("<p style='margin: 5px 0px;'>Next Action</p>", unsafe_allow_html=True)
    st.markdown(
        '<p style="color:gray; font-size:16px;">[GPT will automatically conclude the next action '
        "from the project's content. User will have access to editing the Next Action field]</p>",
        unsafe_allow_html=True,
    )


# def process_audio_input() -> None:
#     audio_bytes = audio_recorder(
#         text="",
#         pause_threshold=2.0,
#         sample_rate=41_000,
#         icon_size="2x"
#     )
#     if audio_bytes and (audio_bytes != st.session_state.get("last_audio", b"")) \
#             and not st.session_state.get("audio_processed", False):
#         if validate_audio_length(audio_bytes):
#             transcribed_text = transcribe_audio(audio_bytes)
#             if transcribed_text.strip():
#                 st.session_state["transcribed_text"] = transcribed_text
#                 st.session_state["last_audio"] = audio_bytes
#                 st.session_state["audio_processed"] = False
#                 st.rerun()
#             else:
#                 st.error("Transcribed message is empty. Please try again.")


def send_user_message(session_id: int, user_message: str) -> None:
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

    st.session_state["audio_processed"] = False
    st.session_state["last_audio"] = b""
    st.session_state["transcribed_text"] = ""
    st.session_state["sended_message"] = True
    st.rerun()


def summarize_session(session_id: int) -> None:
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
    st.session_state.setdefault("audio_processed", False)
    st.session_state.setdefault("last_audio", b"")
    st.session_state.setdefault("transcribed_text", "")
    st.session_state.setdefault("sended_message", False)

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
    option = st.selectbox(
        "Status",
        (
            "Not Started",
            "Preparation in progress",
            "Preparation ended. Waiting for post session report",
            "Post session report in progress",
            "Session ended"
        ),
    )
    st.write(f"Summary: {session_data[4]}")

    # История сообщений
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

    upload_pdf_file_for_session(session_id)
    render_uploaded_files_for_session(session_id)

    # Сначала обрабатываем аудио
    audio_bytes = audio_recorder(
        text="",
        pause_threshold=2.0,
        sample_rate=41_000,
        icon_size="2x"
    )
    if audio_bytes and (audio_bytes != st.session_state.get("last_audio", b"")) \
            and not st.session_state.get("audio_processed", False):
        if validate_audio_length(audio_bytes):
            transcribed_text = transcribe_audio(audio_bytes)
            if transcribed_text.strip():
                st.session_state["transcribed_text"] = transcribed_text
                st.session_state["last_audio"] = audio_bytes
                st.session_state["audio_processed"] = False
                st.rerun()
            else:
                st.error("Transcribed message is empty. Please try again.")

    # Если есть расшифрованный текст — показываем его
    if st.session_state["transcribed_text"] and not st.session_state["sended_message"]:
        js_snippet = f"""
        <script>
            function insertText(dummy_var_to_force_repeat_execution) {{
                var chatInput = parent.document.querySelector('textarea[data-testid="stChatInputTextArea"]');
                if (chatInput) {{
                    var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLTextAreaElement.prototype,
                        "value"
                    ).set;
                    nativeInputValueSetter.call(chatInput, "{st.session_state['transcribed_text']}");
                    var event = new Event('input', {{ bubbles: true }});
                    chatInput.dispatchEvent(event);
                }}
            }}
            insertText({len(st.session_state)});
        </script>
        """
        st.components.v1.html(js_snippet, height=0, width=0, scrolling=False)
    else:
        st.session_state["sended_message"] = False
    # Поле ввода сообщения
    user_message = st.chat_input("Your question...")

    # Обработка отправки текста
    if user_message:
        send_user_message(session_id, user_message)

    # Кнопка "Summarize"
    if st.button("Summarize"):
        summarize_session(session_id)
