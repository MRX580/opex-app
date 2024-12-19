import streamlit as st
from db import get_projects_for_user, get_project_by_id, get_sessions_for_project, get_session_by_id
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
        st.write(f"Summary {session[4]}")

        # Отобразить историю сообщений
        msgs = get_messages_for_session(session_id)
        for m in msgs:
            sender, content, timestamp = m
            st.write(f"**{sender}** [{timestamp}]: {content}")

        # Получить пути к загруженным PDF для проекта
        project_id = session[1]
        pdf_files = get_files_for_project(project_id)
        pdf_paths = [file[1] for file in pdf_files]  # Индекс 1 соответствует `file_path`

        # Отправить сообщение ChatGPT
        user_msg = st.text_input("Your question for ChatGPT:")
        if st.button("Send"):
            if user_msg.strip() != "":
                # Собираем контекст
                all_msgs = get_messages_for_session(session_id)
                messages_format = []
                for mm in all_msgs:
                    sender, content, _ = mm
                    role = "user" if sender == "user" else "assistant"
                    messages_format.append({"role": role, "content": content})

                messages_format.append({"role": "user", "content": user_msg})

                # Включаем PDF в контекст
                reply = ask_chatgpt(messages_format, pdf_paths=pdf_paths)
                insert_message(session_id, "user", user_msg)
                insert_message(session_id, "assistant", reply)
                st.rerun()
            else:
                st.error("Please enter a message.")
    else:
        st.error("Session not found")


