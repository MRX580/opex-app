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
    """Main application function."""
    st.set_page_config(page_title="OPEX MVP", layout="wide")

    init_db()

    # Предположим, что проект известен заранее или захардкожен
    project_id = 1  # Замените на нужный ID проекта

    # Отображаем список сессий
    sessions = get_sessions_for_project(project_id)
    st.sidebar.write("Sessions")
    for s in sessions:
        s_id, s_num, s_status, s_summary = s
        if st.sidebar.button(f"Session {s_num}"):
            st.session_state['session_id'] = s_id
            st.rerun()

    # Отображаем выбранную сессию
    if 'session_id' in st.session_state and st.session_state['session_id'] is not None:
        session_page(None, st.session_state['session_id'])
    else:
        project_page(123, 1)


if __name__ == "__main__":
    main()
