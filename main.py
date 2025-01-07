import streamlit as st
from db import init_db, store_user_token, get_user_by_token, get_user_by_id, get_all_users
# from auth import authenticate  # Закомментировано, так как авторизация отключена
from admin import admin_page
from user import user_projects_page, project_page, session_page
import uuid


def login_page():
    """Login page."""
    # Отключена авторизация
    st.title("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Continue"):
        user = authenticate(email, password)
        if user:
            # Generate a token, store it in DB and session
            token = str(uuid.uuid4())
            store_user_token(user[0], token)
            st.session_state['logged_in'] = True
            st.session_state['user'] = user
            st.session_state['token'] = token
            st.query_params.token = token  # Set token in URL params
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Invalid login or password")


def select_user_page():
    """Initial page with two buttons: Normal User and Admin."""
    st.title("Choose user/admin mod")

    # Получаем всех пользователей из БД
    users = get_all_users()

    if not users or len(users) < 2:
        # st.error("Необходимо, чтобы в базе данных было как минимум два пользователя.")
        return

    # Предполагаем, что первый пользователь — обычный, второй — админ
    normal_user = users[0]
    admin_user = users[1]

    col1, col2 = st.columns(2)

    with col1:
        if st.button("User"):
            st.session_state['logged_in'] = True
            st.session_state['user'] = normal_user
            # st.success(f"Выполнен вход как {normal_user[1]} (Пользователь)")
            st.rerun()

    with col2:
        if st.button("Admin"):
            st.session_state['logged_in'] = True
            st.session_state['user'] = admin_user
            # st.success(f"Выполнен вход как {admin_user[1]} (Админ)")
            st.rerun()


def main():
    st.set_page_config(page_title="OPEX MVP", layout="wide")
    init_db()

    # Проверяем, есть ли пользовательский токен в URL
    # token = st.query_params.get("token")
    # if token and "logged_in" not in st.session_state:
    #     user = get_user_by_token(token)
    #     if user:
    #         st.session_state['logged_in'] = True
    #         st.session_state['user'] = user
    #         st.session_state['token'] = token

    # Если пользователь не вошёл, показываем начальную страницу с выбором типа пользователя
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        select_user_page()
        return

    # --- Если пользователь является админом, переходим в админку ---
    if st.session_state["user"][4] == "admin":
        admin_page()  # Показываем admin_page из admin.py
        return

    # --- Иначе (не админ) — обычный пользовательский сценарий ---
    if "session_id" in st.session_state and st.session_state["session_id"]:
        session_page(st.session_state["user"], st.session_state["session_id"])
    elif "project_id" in st.session_state and st.session_state["project_id"]:
        project_page(st.session_state["user"], st.session_state["project_id"])
    else:
        user_projects_page(st.session_state["user"])


if __name__ == "__main__":
    main()
