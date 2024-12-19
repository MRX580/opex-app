import streamlit as st
from db import get_connection


def admin_page():
    st.title("Admin Panel")
    st.write("Features: view users, projects and activity.")

    conn = get_connection()
    c = conn.cursor()
    # Просмотр пользователей
    c.execute("SELECT id, name, email, role, organization FROM users")
    users = c.fetchall()
    st.subheader("Users:")
    for u in users:
        st.write(f"ID: {u[0]}, Имя: {u[1]}, Email: {u[2]}, Роль: {u[3]}, Организация: {u[4]}")

    # Просмотр проектов
    c.execute("SELECT p.id, p.name, u.name FROM projects p JOIN users u ON p.user_id = u.id")
    projects = c.fetchall()
    st.subheader("Projects:")
    for p in projects:
        st.write(f"ID: {p[0]}, Name: {p[1]}, User: {p[2]}")

    # Просмотр токенов (опционально)
    # c.execute("SELECT * FROM tokens")
    # tokens = c.fetchall()
    # st.subheader("Токены:")
    # for t in tokens:
    #     st.write(t)

    conn.close()
