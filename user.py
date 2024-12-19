import streamlit as st
from streamlit.components.v1 import html
from db import get_projects_for_user, get_project_by_id, get_sessions_for_project, get_session_by_id, update_session_summary
from db import insert_message, get_messages_for_session, insert_file, get_files_for_project, delete_file
from chat import ask_chatgpt
from utils import save_uploaded_file

def svg_button_input():
    send_svg = """
    <svg xmlns="http://www.w3.org/2000/svg" fill="#ffffff" height="24px" viewBox="0 0 24 24" width="24px">
        <path d="M0 0h24v24H0z" fill="none"/>
        <path d="M2 21l21-9L2 3v7l15 2-15 2z"/>
    </svg>
    """
    custom_input = f"""
    <div style="display: flex; align-items: center; gap: 5px; width: 100%; background-color: #1e1e1e; padding: 5px; border-radius: 5px;">
        <input id="user_input" type="text" placeholder="Your question..." 
               style="flex: 1; padding: 10px; font-size: 16px; border: 1px solid #333; border-radius: 5px; background-color: #2a2a2a; color: #ffffff;" />
        <button id="send_button" style="padding: 10px; background-color: #444444; border: none; 
                border-radius: 5px; cursor: pointer;">
            {send_svg}
        </button>
    </div>
    <script>
        document.getElementById("send_button").onclick = function() {{
            let userInput = document.getElementById("user_input").value;
            if (userInput.trim() !== "") {{
                const searchParams = new URLSearchParams(window.location.search);
                searchParams.set('SEND_MESSAGE', encodeURIComponent(userInput));
                // Перенаправляем на новый URL, тем самым вызывая перезагрузку с параметром
                window.location.href = window.location.pathname + '?' + searchParams.toString();
            }} else {{
                alert("Please enter a message.");
            }}
        }};
    </script>
    """
    html(custom_input, height=80)


def user_projects_page(user):
    st.title("My projects")

    projects = get_projects_for_user(user[0])
    for p in projects:
        project_id, name, goal, status = p
        if st.button(f"Open {name}"):
            st.session_state['project_id'] = project_id
            st.session_state['session_id'] = None
            st.rerun()
        sessions = get_sessions_for_project(project_id)[:10]
        for s in sessions:
            s_id, s_num, s_status, s_summary = s
            st.write(f"- Session {s_num}: {s_status}")

def project_page(user, project_id):
    project = get_project_by_id(project_id)
    if project:
        st.markdown("<p style='margin: 5px 0px;'>Project summary</p>", unsafe_allow_html=True)
        st.markdown("<p style='margin: 5px 0px;'>Line 3 setup</p>", unsafe_allow_html=True)
        st.markdown(
            f'<p style="color:gray; font-size:16px;">Line 3 is a bottle neck. Reducing its setup time will enable 180% production growth</p>',
            unsafe_allow_html=True,
        )

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
            color = "#4CAF50" if session["status"] == "completed" else "#FF5722"
            progress_html += (
                f"<div style='width: 20px; height: 20px; background-color: {color}; border-radius: 3px;'></div>"
            )
        progress_html += "</div>"

        st.markdown(progress_html, unsafe_allow_html=True)

        st.markdown("<p style='margin: 5px 0px;'>Goals</p>", unsafe_allow_html=True)
        st.markdown(
            f'<p style="color:gray; font-size:16px;">{project[3]}</p>',
            unsafe_allow_html=True,
        )

        uploaded_file = st.file_uploader("Select a PDF file", type=["pdf"])

        if "file_uploaded" not in st.session_state:
            st.session_state["file_uploaded"] = False

        if uploaded_file is not None and not st.session_state["file_uploaded"]:
            file_path = save_uploaded_file(uploaded_file)
            insert_file(project_id, file_path, uploaded_file.name)
            st.success("The file has been uploaded!")
            st.session_state["file_uploaded"] = True
            st.rerun()

        st.write("Uploaded files")
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

    else:
        st.error("Project not found")


def session_page(user, session_id):
    session = get_session_by_id(session_id)
    if st.button("Back"):
        st.session_state['session_id'] = None
        st.rerun()

    if session:
        st.title(f"Session {session[2]}")
        st.write(f"Status: {session[3]}")
        st.write(f"Summary: {session[4]}")

        # Отображение сообщений
        msgs = get_messages_for_session(session_id)
        for sender, content, _ in msgs:
            if sender == "user":
                st.markdown(
                    f"<div style='background-color: #2a2a2a; color: #ececec; padding: 10px; margin: 10px 0px 0px 0px; border-radius: 5px; float: right'>{content}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div style='color: #ececec; margin: 0px 0px 20px 0px; border-radius: 5px;'>{content}</div>",
                    unsafe_allow_html=True
                )

        st.markdown("---")

        # Размещаем поле ввода и кнопку рядом
        col1, col2 = st.columns([4, 1])
        with col1:
            user_msg = st.text_input("Your question...", key="user_message_input")
        with col2:
            if st.button("Send"):
                if user_msg.strip():
                    # Обработка сообщения
                    all_msgs = get_messages_for_session(session_id)
                    messages_format = [
                        {"role": "user" if m[0] == "user" else "assistant", "content": m[1]}
                        for m in all_msgs
                    ]
                    messages_format.append({"role": "user", "content": user_msg})
                    pdf_files = get_files_for_project(session[1])
                    pdf_paths = [file[1] for file in pdf_files]
                    reply = ask_chatgpt(messages_format, pdf_paths=pdf_paths)
                    insert_message(session_id, "user", user_msg)
                    insert_message(session_id, "assistant", reply)
                    st.rerun()
                else:
                    st.error("Please enter a message.")

        if st.button("Summarize"):
            all_msgs = get_messages_for_session(session_id)
            chat_text = "\n".join([f"{m[0]}: {m[1]}" for m in all_msgs])
            summary_prompt = f"Summarize the conversation, don't use a lot of text, try to summarize as briefly as possible:\n\n{chat_text}"
            pdf_files = get_files_for_project(session[1])
            pdf_paths = [file[1] for file in pdf_files]
            summary = ask_chatgpt([{"role": "user", "content": summary_prompt}], pdf_paths=pdf_paths)
            update_session_summary(session_id, summary)
            st.success("The summary has been updated!")
            st.rerun()

    else:
        st.error("Session not found.")


