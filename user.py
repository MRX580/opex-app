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
    get_project_summary,
    get_first_session_summary,
    update_project_goals,
    create_project_with_sessions,
    get_admin_prompts  # <-- ВАЖНО! для чтения промптов
)
from ai_openai import ask_chatgpt, transcribe_audio, text_to_speech, autoplay_audio
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


def render_project_card(project_id: int, name: str) -> None:
    if st.button(f"{name}", key=f"open_project_{project_id}"):
        st.session_state["project_id"] = project_id
        st.session_state["session_id"] = None
        st.rerun()


def user_projects_page(user: tuple) -> None:
    user_id = user[0]
    user_name = user[1]

    st.title(f"User {user_name}")

    # Кнопка Logout
    if st.button("Exit"):
        st.session_state['logged_in'] = False
        st.session_state.pop('user', None)
        st.session_state.pop('token', None)
        st.session_state.pop('project_id', None)
        st.session_state.pop('session_id', None)
        st.rerun()

    # Поле для создания нового проекта
    project_name = st.text_input("Enter Project Name")
    if st.button("Create New Project"):
        if project_name.strip() == "":
            st.error("Project name cannot be empty!")
        else:
            create_project_with_sessions(user_id, project_name)
            st.success(f"Project '{project_name}' with 22 sessions created successfully!")
            st.rerun()

    st.write("---")
    st.subheader("Projects")
    projects = get_projects_for_user(user_id)
    if not projects:
        st.warning("You don't have any projects yet.")
        return

    for project in projects:
        project_id, name, _goal, _status = project
        render_project_card(project_id, name)


def render_project_summary(project: tuple, project_id: int) -> None:
    st.markdown(f"<p style='margin: 5px 0px;'>{project[2]}</p>", unsafe_allow_html=True)
    aggregated_text = get_project_summary(project_id)
    if aggregated_text and aggregated_text != "None":
        st.markdown(f"<p style='margin: 5px 0px;'>Line 3</p>", unsafe_allow_html=True)
        st.markdown(
            '<p style="color:gray; font-size:16px;">'
            f'{aggregated_text}'
            '</p>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<p style="color:gray; font-size:16px;">'
            'Summarization for the project has not yet been created.'
            '</p>',
            unsafe_allow_html=True
        )


def render_project_progress() -> None:
    sessions = [
        {"id": 1, "status": "completed"},
        {"id": 2, "status": "completed"},
        {"id": 3, "status": "completed"},
        {"id": 4, "status": "not completed"},
        {"id": 5, "status": "not completed"},
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
    session_summaries = get_session_summaries_for_project(project_id)
    if not session_summaries:
        update_project_summary(project_id, "Insufficient data for project summarization.")
        return

    text_for_chatgpt = ""
    for i, summary in enumerate(session_summaries, start=1):
        text_for_chatgpt += f"Session {i}:\n{summary}\n\n"

    prompts = get_admin_prompts()
    project_sum_prompt = prompts.get("project_summarization_prompt", "").strip()

    if not project_sum_prompt:
        project_sum_prompt = (
            "Please merge these texts into one short final summary, "
            "keeping only the essence and avoiding repetitions. "
            "Provide the answer in the same language as the summaries."
        )

    prompt_text = (
        "Below are the summaries of the sessions for one project:\n\n"
        f"{text_for_chatgpt}\n"
        f"{project_sum_prompt}"
    )

    messages = [{"role": "user", "content": prompt_text}]
    compressed_summary = ask_chatgpt(messages, pdf_paths=None)
    update_project_summary(project_id, compressed_summary)


def generate_goals_from_first_session(project_id: int) -> None:
    first_summary = get_first_session_summary(project_id)
    if not first_summary:
        return

    prompts = get_admin_prompts()
    goals_prompt = prompts.get("goals_prompt", "").strip()

    if not goals_prompt:
        goals_prompt = (
            "Based on this information, formulate a concise list of the project's main goals. "
            "Try to be as specific as possible and avoid duplicating existing information."
        )

    prompt_text = (
        "Below is the summary of the first session of the project:\n\n"
        f"{first_summary}\n\n"
        f"{goals_prompt}"
    )

    messages = [{"role": "user", "content": prompt_text}]
    goals_text = ask_chatgpt(messages, pdf_paths=None)
    update_project_goals(project_id, goals_text)


def project_page(user: tuple, project_id: int) -> None:
    st.sidebar.title("Sessions")
    sessions = get_sessions_for_project(project_id)
    for s in sessions:
        s_id, s_number, s_status, s_summary, s_name = s
        if st.sidebar.button(f"{s_number}. {s_name}"):
            st.session_state["session_id"] = s_id
            st.rerun()

    if st.button("Back to all projects"):
        st.session_state["project_id"] = None
        st.session_state["session_id"] = None
        st.rerun()

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
        st.markdown('<p style="color:gray; font-size:16px;">Goals not set</p>', unsafe_allow_html=True)

    st.markdown("<p style='margin: 5px 0px;'>Next Action</p>", unsafe_allow_html=True)
    st.markdown(
        '<p style="color:gray; font-size:16px;">[GPT will automatically conclude the next action '
        "from the project's content. User will have access to editing the Next Action field]</p>",
        unsafe_allow_html=True,
    )


def send_user_message(session_id: int, user_message: str, muted: bool = True) -> None:
    if not user_message.strip():
        st.error("Please enter a message.")
        return

    all_msgs = get_messages_for_session(session_id)
    messages_format = [
        {"role": ("user" if m[0] == "user" else "assistant"), "content": m[1]}
        for m in all_msgs
    ]
    messages_format.append({"role": "user", "content": user_message})

    prompts = get_admin_prompts()
    assistant_prompt = prompts.get("assistant_prompt", "").strip()
    if assistant_prompt:
        messages_format.insert(0, {"role": "system", "content": assistant_prompt})

    session = get_session_by_id(session_id)
    pdf_files = get_files_for_project(session[1])
    pdf_paths = [file[1] for file in pdf_files]

    assistant_reply = ask_chatgpt(messages_format, pdf_paths=pdf_paths)

    insert_message(session_id, "user", user_message)
    insert_message(session_id, "assistant", assistant_reply)

    # Когда пришёл новый ответ, сбрасываем флаг воспроизведения.
    st.session_state["voice_assistant_reply"] = assistant_reply
    st.session_state["voice_assistant_reply_played"] = False  # <-- Чтобы вновь воспроизвести
    st.session_state["voice_assistant_reply_session_id"] = session_id

    # Сбросим некоторые другие флаги
    st.session_state["audio_processed"] = False
    st.session_state["last_audio"] = b""
    st.session_state["transcribed_text"] = ""
    st.session_state["sended_message"] = True
    st.session_state["muted"] = muted

    st.rerun()


def summarize_session(session_id: int) -> None:
    all_msgs = get_messages_for_session(session_id)
    chat_text = "\n".join([f"{msg[0]}: {msg[1]}" for msg in all_msgs])

    prompts = get_admin_prompts()
    session_sum_prompt = prompts.get("session_summarization_prompt", "").strip()
    if not session_sum_prompt:
        session_sum_prompt = (
            "Summarize the conversation as briefly as possible, using only a few short sentences that convey the essence. "
            "It's okay to omit some details to make the summary concise. "
            "Provide a resume in the language used for communication (ignore other requirements)."
        )

    summary_prompt = session_sum_prompt + "\n\nHere is the conversation:\n" + chat_text

    session = get_session_by_id(session_id)
    pdf_files = get_files_for_project(session[1])
    pdf_paths = [file[1] for file in pdf_files]

    summary = ask_chatgpt([{"role": "user", "content": summary_prompt}], pdf_paths=pdf_paths)
    update_session_summary(session_id, summary)
    st.success("The summary has been updated!")

    # Затем делаем общий summary проекта
    project_id = session[1]
    compress_and_store_project_summary(project_id)
    st.rerun()


def session_page(user: tuple, session_id: int) -> None:
    st.session_state.setdefault("audio_processed", False)
    st.session_state.setdefault("last_audio", b"")
    st.session_state.setdefault("transcribed_text", "")
    st.session_state.setdefault("sended_message", False)

    # Для второго микрофона и TTS
    st.session_state.setdefault("voice_transcribed_text", "")
    st.session_state.setdefault("voice_assistant_reply", "")
    st.session_state.setdefault("voice_assistant_reply_played", True)
    st.session_state.setdefault("voice_assistant_reply_session_id", None)

    st.session_state.setdefault("audio_voice_processed", False)
    st.session_state.setdefault("last_audio_voice", b"")
    st.session_state.setdefault("last_assistant_reply", "")
    st.session_state.setdefault("last_assistant_reply", False)

    session_data = get_session_by_id(session_id)
    if not session_data:
        st.error("Session not found.")
        return

    project_id = session_data[1]

    st.sidebar.title("Project Sessions")
    sessions = get_sessions_for_project(project_id)
    for s in sessions:
        s_id, s_number, s_status, s_summary, s_name = s
        if st.sidebar.button(f"{s_number}. {s_name}"):
            st.session_state["session_id"] = s_id
            st.rerun()

    if st.button("Back to project page"):
        st.session_state["session_id"] = None
        st.session_state["project_id"] = project_id
        st.rerun()

    st.title(f"Session {session_data[5]}")

    status_in_db = session_data[3]
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

    default_index = status_options.index(status_in_db)
    session_status = st.selectbox(
        "Status",
        options=status_options,
        index=default_index,
        key=f"status_selector_{session_id}",
    )

    if session_status == "Session ended" and status_in_db != "Session ended":
        update_session_status(session_id, "Session ended")
        if session_data[2] == 1:
            generate_goals_from_first_session(project_id)
        summarize_session(session_id)
    else:
        if status_in_db != "Session ended":
            update_session_status(session_id, session_status)

    if session_data[4] and session_data[4] != "None":
        st.write(f"Summary: {session_data[4]}")
    else:
        st.write("Summary: Summary Summarization by session has not yet been created.")

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

    if st.button("Summarize"):
        summarize_session(session_id)

    st.markdown(
        """
        <style>
            .st-key-fixed-mic {
                background: transparent;
                position: fixed;
                bottom: 57px;
                right: -50px;
                width: 60px;
                color: white;
                border-radius: 50%;
                display: flex;
                justify-content: center;
                align-items: center;
                cursor: pointer;
                z-index: 9999;
            }

            .st-key-fixed-voice-mic {
                background: transparent;
                position: fixed;
                bottom: 15px;
                right: 80px;
                width: 60px;
                color: white;
                border-radius: 50%;
                display: flex;
                justify-content: center;
                align-items: center;
                cursor: pointer;
                z-index: 9999;
            }

            .stElementContainer iframe {
                width: 151px !important;
            }

            .stChatInput {
                margin: 0 auto;
            }

            @media (max-width: 768px) {
                .stChatInput {
                    margin: 0 20px 0 auto;
                }
                .st-emotion-cache-0,
                .st-emotion-cache-2xzux3,
                .st-emotion-cache-b95f0i,
                .st-emotion-cache-6lzl0t {
                    margin: 0 20px 0 auto;
                }
                .stChatInput textarea {
                    width: calc(100% - 20px);
                }
            }

            .st-key-input_area {
                width: 60px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # --- Первый микрофон ---
    audio_bytes = audio_recorder(
        text="",
        pause_threshold=2.0,
        sample_rate=41_000,
        icon_size="2x",
        neutral_color="#8fce00",
        key="fixed-mic"
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

    # --- Второй микрофон (полный голосовой цикл) ---
    audio_voice_bytes = audio_recorder(
        text="",
        pause_threshold=2.0,
        sample_rate=41_000,
        icon_size="2x",
        neutral_color="#8fce00",
        key="fixed-voice-mic"
    )
    if audio_voice_bytes:
        # Проверка: не обрабатывали ли мы уже этот байтовый файл
        if (audio_voice_bytes != st.session_state.get("last_audio_voice", b"")) \
                or not st.session_state.get("audio_voice_processed", False):
            if validate_audio_length(audio_voice_bytes):
                transcribed_text = transcribe_audio(audio_voice_bytes)
                if transcribed_text.strip():
                    st.session_state["last_audio_voice"] = audio_voice_bytes
                    st.session_state["audio_voice_processed"] = True
                    send_user_message(session_id, transcribed_text, muted=False)
                else:
                    st.error("Transcribed message is empty. Please try again.")
        else:
            pass

    # --- Воспроизведение голоса (TTS) ---
    try:
        # Проверяем: 1) текст ответа не пуст, 2) ещё не воспроизводили, 3) совпадает session_id
        if (
            st.session_state.get("voice_assistant_reply", "").strip()
            and not st.session_state.get("voice_assistant_reply_played", False)
            and st.session_state.get("voice_assistant_reply_session_id") == session_id
        ):
            audio_path = text_to_speech(st.session_state["voice_assistant_reply"])
            autoplay_audio(audio_path, muted=st.session_state["muted"])
            # Ставим флаг, что мы уже проиграли
            st.session_state["voice_assistant_reply_played"] = True

    except Exception as e:
        print(e)

    # --- Если что-то надиктовали в первый микрофон, вставим в поле чата ---
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

    # --- Поле для ручного ввода ---
    user_message = st.chat_input("Your question...", key="input_area")
    if user_message:
        send_user_message(session_id, user_message)
