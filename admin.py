import streamlit as st
from db import (
    get_all_users,
    get_projects_for_user,
    get_project_by_id,
    get_sessions_for_project,
    get_session_by_id,
    get_messages_for_session,
    get_files_for_session
)

def admin_page():
    """
    Многошаговая админ-панель (read-only):
      1) Список пользователей -> клик "Open user"
      2) Список проектов -> клик "Open project"
      3) Показываем проект (название, описание, статус, goals, next action - всё read-only), список сессий
      4) Просмотр конкретной сессии (название, статус, summary, файлы, чат) - read-only
    """
    st.title("Admin Panel (Read-Only)")

    # Храним состояние «куда мы провалились»
    if 'selected_user' not in st.session_state:
        st.session_state['selected_user'] = None
    if 'selected_project' not in st.session_state:
        st.session_state['selected_project'] = None
    if 'selected_session' not in st.session_state:
        st.session_state['selected_session'] = None

    # ---------------------------
    # Шаг 1: Если не выбран пользователь -> список всех пользователей
    if st.session_state['selected_user'] is None:
        st.subheader("Users")
        users = get_all_users()
        if not users:
            st.info("No users found.")
        else:
            for user in users:
                user_id, name, email, password_hash, role, organization = user
                if st.button(f"Open user: {name} (ID {user_id})", key=f"user_{user_id}"):
                    st.session_state['selected_user'] = user_id
                    st.rerun()
        return  # Останавливаемся, пока не выбрали пользователя

    # ---------------------------
    # Шаг 2: Пользователь выбран, но проект не выбран -> показываем проекты
    if st.session_state['selected_user'] is not None and st.session_state['selected_project'] is None:
        # Кнопка "Back to user list"
        if st.button("Back to user list"):
            st.session_state['selected_user'] = None
            st.session_state['selected_project'] = None
            st.session_state['selected_session'] = None
            st.rerun()

        st.subheader(f"Projects for user_id={st.session_state['selected_user']}")
        projects = get_projects_for_user(st.session_state['selected_user'])
        if not projects:
            st.warning("No projects found for this user.")
        else:
            for project in projects:
                project_id, p_name, p_goal, p_status = project
                if st.button(f"Open project: {p_name} (ID {project_id})", key=f"project_{project_id}"):
                    st.session_state['selected_project'] = project_id
                    st.rerun()
        return  # Ждём выбора проекта

    # ---------------------------
    # Шаг 3: Пользователь и проект выбраны, но сессия не выбрана -> показываем детали проекта + список сессий
    if (
        st.session_state['selected_user'] is not None
        and st.session_state['selected_project'] is not None
        and st.session_state['selected_session'] is None
    ):
        # Кнопка "Back to projects"
        if st.button("Back to projects"):
            st.session_state['selected_project'] = None
            st.session_state['selected_session'] = None
            st.rerun()

        # Отображаем детали проекта: название, описание/goal, статус, Goals, Next Action
        project = get_project_by_id(st.session_state['selected_project'])
        if project:
            # project = (id, user_id, name, goal, status)
            proj_id, user_id_db, proj_name, proj_goal, proj_status = project

            st.subheader(f"Project: {proj_name} (ID {proj_id})")
            st.markdown(f"**Status:** {proj_status}")

            # Goals (в БД это поле goal)
            st.markdown("**Goals**")
            if proj_goal and proj_goal.strip() and proj_goal != "None":
                st.markdown(f'<p style="color:gray; font-size:16px;">{proj_goal}</p>', unsafe_allow_html=True)
            else:
                st.markdown(f'<p style="color:gray; font-size:16px;">Goals not set</p>', unsafe_allow_html=True)

            # Next Action (пока что заглушка)
            st.markdown("**Next Action:**")
            st.markdown(f'<p style="color:gray; font-size:16px;">[GPT will automatically conclude the next action from the project\'s content. User will have access to editing the Next Action field]</p>', unsafe_allow_html=True)

        st.write("---")

        # Выводим список сессий для проекта
        st.subheader("Sessions")
        sessions = get_sessions_for_project(st.session_state['selected_project'])
        if not sessions:
            st.warning("No sessions found for this project.")
        else:
            for s in sessions:
                session_id, session_number, s_status, s_summary, session_name = s
                display_name = session_name if session_name and session_name != "None" else f"Session {session_number}"
                if st.button(f"Open session: {display_name} (ID {session_id})", key=f"session_{session_id}"):
                    st.session_state['selected_session'] = session_id
                    st.rerun()
        return  # Ждём выбора сессии

    # ---------------------------
    # Шаг 4: Просмотр конкретной сессии (read-only)
    if (
        st.session_state['selected_user'] is not None
        and st.session_state['selected_project'] is not None
        and st.session_state['selected_session'] is not None
    ):
        # Кнопка «Back to sessions»
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

    # session_data = (id, project_id, session_number, status, summary, session_name)
    s_id, proj_id, s_number, s_status, s_summary, s_name = session_data
    display_name = s_name if s_name and s_name != "None" else f"Session {s_number}"

    # Название, статус
    st.subheader(f"{display_name} (session_id={s_id})")
    st.markdown(f"**Status:** {s_status}")

    # Суммаризация
    if s_summary and s_summary.strip() != "None":
        st.markdown(f"**Session Summary:** {s_summary}")
    else:
        st.markdown("**Session Summary:** *not yet created*")

    st.write("---")

    # Файлы, загруженные для этой сессии (read-only)
    from db import get_files_for_session
    files = get_files_for_session(s_id)
    if files:
        st.markdown("**Uploaded files for this session (read-only):**")
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

    # Вывод сообщений «пузырями»
    for sender, content, _timestamp in msgs:
        if sender == "user":
            # «Пузырь» справа
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
            # «Пузырь» слева (assistant или system)
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
