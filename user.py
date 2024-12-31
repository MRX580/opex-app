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
    get_files_for_session,
    update_session_status,
    get_session_summaries_for_project,
    update_project_summary,
    get_project_summary, get_first_session_summary, update_project_goals
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
        session_id, session_number, status, _summary, s_name = session
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


def render_project_summary(project: tuple, project_id: int) -> None:
    st.markdown(f"<p style='margin: 5px 0px;'>Project {project[2]}</p>", unsafe_allow_html=True)
    aggregated_text = get_project_summary(project_id)
    if aggregated_text and aggregated_text != "None":
        # st.subheader("Итоговая суммаризация по проекту:")
        st.markdown(f"<p style='margin: 5px 0px;'>Line 3</p>", unsafe_allow_html=True)
        # st.markdown(f"<p style='margin: 5px 0px;'>{aggregated_text}</p>", unsafe_allow_html=True)
        st.markdown(
            '<p style="color:gray; font-size:16px;">'
            f'{aggregated_text}'
            '</p>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<p style="color:gray; font-size:16px;">'
            f'Summarization for the project has not yet been created.'
            '</p>',
            unsafe_allow_html=True)


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


def compress_and_store_project_summary(project_id: int):
    """
    Собирает все session summary проекта, вызывает ChatGPT для их сжатия
    и записывает результат в projects.aggregated_summary
    """
    # 1. Получаем все summary сессий
    session_summaries = get_session_summaries_for_project(project_id)

    # 2. Если ни одной суммаризации нет — пишем что «Недостаточно данных»
    if not session_summaries:
        update_project_summary(project_id, "Insufficient data for project summarization.")
        return

    # 3. Формируем промпт
    text_for_chatgpt = ""
    for i, summary in enumerate(session_summaries, start=1):
        text_for_chatgpt += f"Сессия {i}:\n{summary}\n\n"

    prompt_text = (
        "Below are the summaries of the sessions for one project:\n\n"
        f"{text_for_chatgpt}\n"
        "Please merge these texts into one short final summary, "
        "keeping only the essence and avoiding repetitions. Provide the answer in the same language as the summaries."
    )

    # 4. Спрашиваем ChatGPT
    messages = [{"role": "user", "content": prompt_text}]
    compressed_summary = ask_chatgpt(messages, pdf_paths=None)

    # 5. Записываем полученный результат в БД
    update_project_summary(project_id, compressed_summary)


def generate_goals_from_first_session(project_id: int) -> None:
    first_summary = get_first_session_summary(project_id)

    prompt_text = (
        "Below is the summary of the first session of the project:\n\n"
        f"{first_summary}\n\n"
        "Based on this information, formulate a concise list of the project's main goals. "
        "Try to be as specific as possible and avoid duplicating existing information."
    )

    messages = [{"role": "user", "content": prompt_text}]
    goals_text = ask_chatgpt(messages, pdf_paths=None)

    # Сохраняем
    update_project_goals(project_id, goals_text)


def project_page(user: tuple, project_id: int) -> None:
    project = get_project_by_id(project_id)
    if not project:
        st.error("Project not found")
        return

    render_project_summary(project, project_id)
    render_project_progress()

    st.markdown("<p style='margin: 5px 0px;'>Goals</p>", unsafe_allow_html=True)
    if project[3] and project[3] != "None":
        st.markdown(f'<p style="color:gray; font-size:16px;">{project[3]}</p>', unsafe_allow_html=True)
    else:
        st.markdown(f'<p style="color:gray; font-size:16px;">Goals not set</p>', unsafe_allow_html=True)

    st.markdown("<p style='margin: 5px 0px;'>Next Action</p>", unsafe_allow_html=True)
    st.markdown(
        '<p style="color:gray; font-size:16px;">[GPT will automatically conclude the next action '
        "from the project's content. User will have access to editing the Next Action field]</p>",
        unsafe_allow_html=True,
    )



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
        "Summarize the conversation as briefly as possible, using only a few short sentences that convey the essence. "
        "It's okay to omit some details to make the summary concise. "
        "Provide a resume in the language used for communication(ignore other requirements, focus on the conversation):\n\n" + chat_text
    )
    session = get_session_by_id(session_id)
    pdf_files = get_files_for_project(session[1])
    pdf_paths = [file[1] for file in pdf_files]

    summary = ask_chatgpt([{"role": "user", "content": summary_prompt}], pdf_paths=pdf_paths)
    update_session_summary(session_id, summary)
    st.success("The summary has been updated!")
    session = get_session_by_id(session_id)
    project_id = session[1]

    # 2. Вызываем compress_and_store_project_summary
    compress_and_store_project_summary(project_id)
    st.rerun()


def session_page(user: tuple, session_id: int) -> None:
    st.session_state.setdefault("audio_processed", False)
    st.session_state.setdefault("last_audio", b"")
    st.session_state.setdefault("transcribed_text", "")
    st.session_state.setdefault("sended_message", False)

    session_data = get_session_by_id(session_id)
    if not session_data:
        st.error("Session not found.")
        return

    if st.button("Back"):
        st.session_state["session_id"] = None
        st.session_state["audio_processed"] = False
        st.session_state["last_audio"] = b""
        st.rerun()

    if not session_data:
        st.error("Session not found.")
        return

    status_in_db = session_data[3]

    st.title(f"Session {session_data[5]}")
    status_options = [
        "Not Started",
        "Preparation in progress",
        "Preparation ended. Waiting for post session report",
        "Post session report in progress",
        "Session ended"
    ]
    if status_in_db not in status_options:
        status_in_db = "Not Started"
    if status_in_db == "Session ended":
        status_options = ["Session ended"]

    # Определяем индекс в списке, чтобы selectbox сразу показывал правильный пункт
    default_index = status_options.index(status_in_db)

    # Теперь selectbox будет иметь дефолт, равный тому, что хранится в БД
    session_status = st.selectbox(
        "Status",
        options=status_options,
        index=default_index,
        key=f"status_selector_{session_id}",
    )

    if session_status == "Session ended" and status_in_db != "Session ended":
        update_session_status(session_id, "Session ended")

        print(session_data[2], session_data[5])
        if session_data[2] == 1:
            project_id = session_data[1]
            generate_goals_from_first_session(project_id)

        summarize_session(session_id)

    if status_in_db != "Session ended":
        update_session_status(session_id, session_status)
    if session_data[4] != "None":
        st.write(f"Summary: {session_data[4]}")
    else:
        st.write(f"Summary: Summary Summarization by session has not yet been created.")

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

    # Кнопка "Summarize"
    if st.button("Summarize"):
        summarize_session(session_id)

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
