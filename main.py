import streamlit as st
from db import init_db, store_user_token, get_user_by_token, get_projects_for_user, get_sessions_for_project
from auth import authenticate
from admin import admin_page
from user import user_projects_page, project_page, session_page
import uuid

def login_page():
    """Login page."""
    st.title("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("continue"):
        user = authenticate(email, password)
        if user:
            # Generate a token, store it in DB and session
            token = str(uuid.uuid4())
            store_user_token(user[0], token)
            st.session_state['logged_in'] = True
            st.session_state['user'] = user
            st.session_state['token'] = token
            st.query_params.token = token
            st.rerun()
        else:
            st.error("Invalid login or password")

def main():
    st.set_page_config(page_title="OPEX MVP", layout="wide")
    init_db()

    # Кнопка в сайдбаре для входа в админку
    st.sidebar.write("Admin demo")
    if st.sidebar.button("Open"):
        # Выбираем «режим» admin
        st.session_state['session_id'] = "admin"
        st.rerun()

    # Проверяем: если session_id == "admin", идём в admin_page()
    if 'session_id' in st.session_state and st.session_state['session_id'] == "admin":
        admin_page()
        return

    # Иначе — обычная логика
    project_id = 1
    sessions = get_sessions_for_project(project_id)
    st.sidebar.write("Sessions")
    for s in sessions:
        s_id, s_num, s_status, s_summary, s_name = s
        if st.sidebar.button(f"Session {s_name if str(s_name) != 'None' else s_num}"):
            st.session_state['session_id'] = s_id
            st.rerun()

    if 'session_id' in st.session_state and st.session_state['session_id'] is not None:
        if st.session_state['session_id'] != "admin":
            # Показываем пользовательскую страницу для сессии
            session_page(None, st.session_state['session_id'])
    else:
        # По умолчанию показываем project_page
        project_page(None, project_id)


if __name__ == "__main__":
    main()
