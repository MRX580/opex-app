import streamlit as st
from db import get_projects_for_user, get_project_by_id, get_sessions_for_project, get_session_by_id, update_session_summary
from db import insert_message, get_messages_for_session, insert_file, get_files_for_project, delete_file
from chat import ask_chatgpt
from utils import save_uploaded_file

def user_projects_page(user):
    st.title("My projects")

    projects = get_projects_for_user(user[0])
    for p in projects:
        project_id, name, goal, status = p
        # st.write(f"**Project:** {name} ({status})")
        # Кнопка для перехода к проекту
        if st.button(f"Open {name}"):
            st.session_state['project_id'] = project_id
            st.session_state['session_id'] = None
            st.rerun()
        # Отобразить первые 10 сессий
        sessions = get_sessions_for_project(project_id)[:10]
        for s in sessions:
            s_id, s_num, s_status, s_summary = s
            st.write(f"- Session {s_num}: {s_status}")


def project_page(user, project_id):
    project = get_project_by_id(project_id)

    # if st.button("Back"):
    #     st.session_state['project_id'] = None
    #     st.session_state['session_id'] = None
    #     st.rerun()

    if project:
        st.markdown("<p style='margin: 5px 0px;'>Project summary</p>", unsafe_allow_html=True)
        st.markdown("<p style='margin: 5px 0px;'>Line 3 setup</p>", unsafe_allow_html=True)
        st.markdown(
            f'<p style="color:gray; font-size:16px;">Line 3 is a bottle neck. Reducing its setup time will enable 180% production growth</p>',
            unsafe_allow_html=True,
        )
        # st.write(f"Status: {project[4]}")

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

        # sessions = get_sessions_for_project(project_id)
        # for s in sessions:
        #     s_id, s_num, s_status, s_summary = s
        #     st.write(f"Session {s_num}: {s_status}")
        #     if st.button(f"Open session {s_num}"):
        #         st.session_state['session_id'] = s_id
        #         st.rerun()

        # Загрузка файлов
        uploaded_file = st.file_uploader("Select a PDF file", type=["pdf"])

        if "file_uploaded" not in st.session_state:
            st.session_state["file_uploaded"] = False

        if uploaded_file is not None and not st.session_state["file_uploaded"]:
            file_path = save_uploaded_file(uploaded_file)
            insert_file(project_id, file_path, uploaded_file.name)
            st.success("The file has been uploaded!")
            st.session_state["file_uploaded"] = True
            st.rerun()

        # Список файлов проекта с кнопками удаления
        st.write("Uploaded files")
        files = get_files_for_project(project_id)
        for f_ in files:
            fid, fpath, fname = f_
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(fname)
            with col2:
                if st.button("Delete", key=f"delete_{fid}"):
                    delete_file(fid)  # Удаляем файл из базы данных
                    st.success(f"File {fname} has been deleted!")
                    st.rerun()

    else:
        st.error("Project not found")


def session_page(user, session_id):
    session = get_session_by_id(session_id)
    # Кнопка "Назад" для возврата к странице проекта
    if st.button("Back"):
        st.session_state['session_id'] = None
        st.rerun()

    if session:
        st.title(f"Session {session[2]}")
        st.write(f"Status {session[3]}")
        st.write(f"Summary {session[4]}")  # Здесь отображается резюме

        # Стилизация сообщений
        st.markdown("""
        <style>
        .user-message, .assistant-message {
            padding: 15px;
            border-radius: 10px;
            max-width: 100%;
            word-wrap: break-word;
            font-size: 16px;
            line-height: 1.5;
        }
        .user-message {
            background-color: #2a2a2a;
            color: rgb(236, 236, 236);
            text-align: right;
        }
        .assistant-message {
            background-color: #3a3a3a;
            color: rgb(236, 236, 236);
            text-align: left;
        }
        </style>
        """, unsafe_allow_html=True)

        # Отображение сообщений
        msgs = get_messages_for_session(session_id)
        for sender, content, _ in msgs:
            if sender == "user":
                st.markdown(f"""
                <div class="user-message">
                    {content}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="assistant-message">
                    {content}
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Загрузка файлов и отправка сообщений
        project_id = session[1]
        pdf_files = get_files_for_project(project_id)
        pdf_paths = [file[1] for file in pdf_files]  # Индекс 1 соответствует `file_path`

        st.markdown("---")
        col1, col2 = st.columns([4, 1])
        with col1:
            user_msg = st.text_input("Your question:", key="user_input")
        with col2:
            if st.button("Send"):
                if user_msg.strip() != "":
                    all_msgs = get_messages_for_session(session_id)
                    messages_format = [
                        {"role": "user" if m[0] == "user" else "assistant", "content": m[1]}
                        for m in all_msgs
                    ]
                    messages_format.append({"role": "user", "content": user_msg})
                    reply = ask_chatgpt(messages_format, pdf_paths=pdf_paths)
                    insert_message(session_id, "user", user_msg)
                    insert_message(session_id, "assistant", reply)
                    st.rerun()
                else:
                    st.error("Please enter a message.")

        # Кнопка "Резюмировать"
        if st.button("Summarize"):
            all_msgs = get_messages_for_session(session_id)
            chat_text = "\n".join([f"{m[0]}: {m[1]}" for m in all_msgs])
            summary_prompt = f"Please summarize the following conversation:\n\n{chat_text}"
            summary = ask_chatgpt([{"role": "user", "content": summary_prompt}], pdf_paths=pdf_paths)

            # Обновление резюме в базе данных
            update_session_summary(session_id, summary)  # Обновление резюме в БД

            st.success("The resume has been successfully updated!")
            st.rerun()

    else:
        st.error("Session not found.")





