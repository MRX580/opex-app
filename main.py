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
    st.markdown("""
        <style>
            /* Убираем стандартную стрелку */
            [data-testid="collapsedControl"]::before {
                content: '';
            }

            /* Добавляем вашу кастомную стрелку с помощью SVG */
            [data-testid="collapsedControl"] {
                background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 448 512'%3E%3Cpath fill='white' d='M207.029 381.476L8.485 203.314c-11.627-10.67-11.627-28.958 0-39.629l198.544-178.162c11.828-10.619 30.296-3.068 30.296 13.573v356.325c0 16.64-18.468 24.19-30.296 13.573z'/%3E%3C/svg%3E");
                background-size: contain;
                background-repeat: no-repeat;
                background-position: center;
                width: 24px; /* Размер стрелки */
                height: 24px;
            }
        </style>
    """, unsafe_allow_html=True)

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
