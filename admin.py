import streamlit as st
from db import (
    get_all_users,
    get_projects_for_user,
    get_project_by_id,
    get_sessions_for_project,
    get_session_by_id,
    get_messages_for_session,
    get_files_for_session,
    get_user_by_id,
    get_admin_prompts,
    update_admin_prompts,
    get_project_summary,
    insert_admin_pdf,
    get_admin_pdfs,
    delete_file  # <-- добавили импорт
)
from utils import save_uploaded_file


def render_project_summary(project: tuple, project_id: int) -> None:
    st.markdown(f"<p style='margin: 5px 0px;'>Project {project[2]}</p>", unsafe_allow_html=True)
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

def admin_page():
    st.title("Admin Panel")

    if 'selected_user' not in st.session_state:
        st.session_state['selected_user'] = None
    if 'selected_project' not in st.session_state:
        st.session_state['selected_project'] = None
    if 'selected_session' not in st.session_state:
        st.session_state['selected_session'] = None

    # ---------------------------
    # Шаг 1: Список пользователей + блок редактирования промптов
    if st.session_state['selected_user'] is None:
        if st.button("Exit"):
            st.session_state['logged_in'] = False
            st.session_state.pop('user', None)
            st.session_state.pop('token', None)
            st.session_state.pop('project_id', None)
            st.session_state.pop('session_id', None)
            st.rerun()

        st.subheader("Users")
        users = get_all_users()
        if not users:
            st.info("No users found.")
        else:
            for user in users:
                user_id, name, email, password_hash, role, organization = user
                if st.button(f"{name}", key=f"user_{user_id}"):
                    st.session_state['selected_user'] = user_id
                    st.rerun()

        st.write("---")
        st.markdown("### Customize Prompts")
        prompts = get_admin_prompts()

        assistant_prompt_val = st.text_area(
            "Assistant",
            value=prompts["assistant_prompt"],
            placeholder="Enter text for the 'assistant' role or any context..."
        )
        file_upload_prompt_val = st.text_area(
            "File Upload",
            value=prompts["file_upload_prompt"],
            placeholder="Enter text for how you'd like ChatGPT to handle file uploads..."
        )

        # -- Загрузка новых PDF --
        pdf_files = st.file_uploader(
            "Upload PDF files",
            type=["pdf"],
            accept_multiple_files=True
        )

        # -- Отображаем уже загруженные глобальные PDF --
        pdf_rows = get_admin_pdfs()  # [(id, file_path, file_name), ...]
        if pdf_rows:
            for pdf_id, pdf_path, pdf_name in pdf_rows:
                cols = st.columns([3,1])  # Ширина колонок: 3/1
                with cols[0]:
                    st.write(f"- **{pdf_name}** — `{pdf_path}`")
                with cols[1]:
                    # Кнопка «Delete»
                    if st.button("Delete", key=f"delete_{pdf_id}"):
                        delete_file(pdf_id)
                        st.success(f"File {pdf_name} was deleted.")
                        st.rerun()  # перезагрузим страницу
        else:
            st.write("*No global PDFs yet.*")

        project_summarization_prompt_val = st.text_area(
            "Project Summarization",
            value=prompts["project_summarization_prompt"],
            placeholder="Enter text for project summarization..."
        )
        goals_prompt_val = st.text_area(
            "Goals",
            value=prompts["goals_prompt"],
            placeholder="Enter text for goals generation..."
        )
        session_summarization_prompt_val = st.text_area(
            "Session Summarization",
            value=prompts["session_summarization_prompt"],
            placeholder="Enter text for how you'd like to summarize sessions..."
        )

        if st.button("Save Prompts"):
            # 1) Сохраняем промпты
            update_admin_prompts(
                project_summarization_prompt_val,
                goals_prompt_val,
                assistant_prompt_val,
                file_upload_prompt_val,
                session_summarization_prompt_val
            )

            # 2) Сохраняем загруженные PDF (если есть)
            if pdf_files:
                for file in pdf_files:
                    file_path = save_uploaded_file(file, "uploads")
                    insert_admin_pdf(file_path, file.name)

                st.success("Prompts saved and PDFs uploaded successfully!")
            else:
                st.success("Prompts updated successfully (no PDFs uploaded).")

        return  # Заканчиваем, пока не выбрали пользователя

    # ---------------------------
    # Шаг 2: Пользователь выбран, но проект не выбран
    if st.session_state['selected_user'] is not None and st.session_state['selected_project'] is None:
        if st.button("Back to user list"):
            st.session_state['selected_user'] = None
            st.session_state['selected_project'] = None
            st.session_state['selected_session'] = None
            st.rerun()

        st.markdown(
            f"""
            <h3>
                User: <span style='font-weight:400;'>
                    {get_user_by_id(st.session_state['selected_user'])[1]}
                </span>
            </h3>
            """,
            unsafe_allow_html=True
        )

        st.subheader("Projects")
        projects = get_projects_for_user(st.session_state['selected_user'])
        if not projects:
            st.warning("No projects found for this user.")
        else:
            for project in projects:
                project_id, p_name, p_goal, p_status = project
                if st.button(f"{p_name}", key=f"project_{project_id}"):
                    st.session_state['selected_project'] = project_id
                    st.rerun()
        return

    # ---------------------------
    # Шаг 3: Пользователь и проект выбраны, но сессия не выбрана
    if (
        st.session_state['selected_user'] is not None
        and st.session_state['selected_project'] is not None
        and st.session_state['selected_session'] is None
    ):
        if st.button("Back to projects"):
            st.session_state['selected_project'] = None
            st.session_state['selected_session'] = None
            st.rerun()

        project = get_project_by_id(st.session_state['selected_project'])
        if project:
            proj_id, user_id_db, proj_name, proj_goal, proj_status = project
            st.subheader(f"{proj_name}")
            render_project_summary(project, proj_id)

            render_project_progress()
            st.markdown("**Goals**")
            if proj_goal and proj_goal.strip() and proj_goal != "None":
                st.markdown(f'<p style="color:gray; font-size:16px;">{proj_goal}</p>', unsafe_allow_html=True)
            else:
                st.markdown(
                    '<p style="color:gray; font-size:16px;">Goals not set</p>',
                    unsafe_allow_html=True
                )

            st.markdown("**Next Action:**")
            st.markdown(
                """
                <p style="color:gray; font-size:16px;">
                [GPT will automatically propose the next action from the project's content. 
                User will have access to editing the Next Action field if needed]
                </p>
                """,
                unsafe_allow_html=True
            )

        st.write("---")
        st.subheader("Sessions")
        sessions = get_sessions_for_project(st.session_state['selected_project'])
        if not sessions:
            st.warning("No sessions found for this project.")
        else:
            for s in sessions:
                session_id, session_number, s_status, s_summary, session_name = s
                display_name = session_name if session_name and session_name != "None" else f"Session {session_number}"
                if st.button(f"{display_name}", key=f"session_{session_id}"):
                    st.session_state['selected_session'] = session_id
                    st.rerun()
        return

    # ---------------------------
    # Шаг 4: Просмотр конкретной сессии (read-only)
    if (
        st.session_state['selected_user'] is not None
        and st.session_state['selected_project'] is not None
        and st.session_state['selected_session'] is not None
    ):
        if st.button("Back to sessions"):
            st.session_state['selected_session'] = None
            st.rerun()

        admin_session_view(st.session_state['selected_session'])
        return


def admin_session_view(session_id: int) -> None:
    """
    Показывает сессию (название, статус, summary, файлы) и чат (read-only).
    """
    session_data = get_session_by_id(session_id)
    if not session_data:
        st.error("Session not found.")
        return

    s_id, proj_id, s_number, s_status, s_summary, s_name = session_data
    display_name = s_name if s_name and s_name != "None" else f"Session {s_number}"

    st.subheader(f"{display_name}")
    st.markdown(f"**Status:** {s_status}")

    if s_summary and s_summary.strip() != "None":
        st.markdown(f"**Session Summary:** {s_summary}")
    else:
        st.markdown("**Session Summary:** *not yet created*")

    st.write("---")

    files = get_files_for_session(s_id)
    if files:
        st.markdown("**Uploaded files for this session:**")
        for f_id, f_path, f_name in files:
            st.write(f"- {f_name} (ID {f_id}) — {f_path}")
    else:
        st.write("*No files for this session.*")

    st.write("---")
    st.markdown("### Chat History")

    msgs = get_messages_for_session(s_id)
    if not msgs:
        st.info("No messages in this session.")
        return

    for sender, content, _timestamp in msgs:
        if sender == "user":
            st.markdown(
                f"""
                <div style='background-color: #2a2a2a; color: #ececec; 
                            padding: 10px; margin: 10px 0px; 
                            border-radius: 5px; float: right; max-width: 60%; clear: both;'>
                    {content}
                </div>
                <div style='clear: both;'></div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div style='background-color: #444; color: #ececec; 
                            padding: 10px; margin: 10px 0px; 
                            border-radius: 5px; float: left; max-width: 60%; clear: both;'>
                    {content}
                </div>
                <div style='clear: both;'></div>
                """,
                unsafe_allow_html=True
            )
    st.write("---")
    st.info("Read-only mode: You cannot send or edit any messages here.")
