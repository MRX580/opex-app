import sqlite3
import os


def get_connection():
    conn = sqlite3.connect('database.db', check_same_thread=False)
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()
    # Таблица пользователей
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password_hash TEXT,
        role TEXT,
        organization TEXT
    )''')

    # Таблица проектов
    c.execute('''CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        goal TEXT,
        status TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    # Таблица сессий (10 сессий на проект)
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        session_number INTEGER,
        status TEXT,
        summary TEXT,
        FOREIGN KEY(project_id) REFERENCES projects(id)
    )''')

    # Таблица сообщений (история чата)
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER,
        sender TEXT,
        content TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(session_id) REFERENCES sessions(id)
    )''')

    # Таблица файлов
    c.execute('''CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        file_path TEXT,
        file_name TEXT,
        FOREIGN KEY(project_id) REFERENCES projects(id)
    )''')

    # Таблица токенов
    c.execute('''CREATE TABLE IF NOT EXISTS tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        token TEXT UNIQUE,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    conn.commit()
    conn.close()


def get_user_by_email(email):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, email, password_hash, role, organization FROM users WHERE email=?", (email,))
    user = c.fetchone()
    conn.close()
    return user


def create_user(name, email, password_hash, role, org):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO users (name, email, password_hash, role, organization) VALUES (?,?,?,?,?)",
              (name, email, password_hash, role, org))
    conn.commit()
    conn.close()


def email_exists(email):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email=?", (email,))
    user = c.fetchone()
    conn.close()
    return user is not None


def get_projects_for_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, goal, status FROM projects WHERE user_id=?", (user_id,))
    projects = c.fetchall()
    conn.close()
    return projects


def create_project(user_id, name, goal):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO projects (user_id, name, goal, status) VALUES (?,?,?,?)", (user_id, name, goal, 'active'))
    project_id = c.lastrowid
    # Создаем 10 сессий
    for i in range(1, 11):
        c.execute("INSERT INTO sessions (project_id, session_number, status) VALUES (?,?,?)",
                  (project_id, i, 'Not Started'))
    conn.commit()
    conn.close()


def get_project_by_id(project_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, user_id, name, goal, status FROM projects WHERE id=?", (project_id,))
    project = c.fetchone()
    conn.close()
    return project


def get_sessions_for_project(project_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, session_number, status, summary FROM sessions WHERE project_id=?", (project_id,))
    sessions = c.fetchall()
    conn.close()
    return sessions


def get_session_by_id(session_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, project_id, session_number, status, summary FROM sessions WHERE id=?", (session_id,))
    session = c.fetchone()
    conn.close()
    return session


def update_session_summary(session_id, summary):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE sessions SET summary=? WHERE id=?", (summary, session_id))
    conn.commit()
    conn.close()


def insert_message(session_id, sender, content):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO messages (session_id, sender, content) VALUES (?,?,?)",
              (session_id, sender, content))
    conn.commit()
    conn.close()


def get_messages_for_session(session_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT sender, content, timestamp FROM messages WHERE session_id=? ORDER BY id ASC", (session_id,))
    msgs = c.fetchall()
    conn.close()
    return msgs


def insert_file(project_id, file_path, file_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO files (project_id, file_path, file_name) VALUES (?,?,?)", (project_id, file_path, file_name))
    conn.commit()
    conn.close()


def get_files_for_project(project_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, file_path, file_name FROM files WHERE project_id=?", (project_id,))
    files = c.fetchall()
    conn.close()
    return files


def store_user_token(user_id, token):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO tokens (user_id, token) VALUES (?,?)", (user_id, token))
    conn.commit()
    conn.close()


def get_user_by_token(token):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""SELECT u.id, u.name, u.email, u.password_hash, u.role, u.organization 
                 FROM tokens t 
                 JOIN users u ON u.id = t.user_id
                 WHERE t.token=?""", (token,))
    user = c.fetchone()
    conn.close()
    return user


def remove_token(token):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM tokens WHERE token=?", (token,))
    conn.commit()
    conn.close()

def delete_file(file_id):
    """Удаляет файл из базы данных и файловой системы."""
    conn = get_connection()
    c = conn.cursor()

    # Получаем путь файла
    c.execute("SELECT file_path FROM files WHERE id=?", (file_id,))
    result = c.fetchone()
    if result:
        file_path = result[0]
        # Удаляем файл из файловой системы, если он существует
        if os.path.exists(file_path):
            os.remove(file_path)

        # Удаляем запись из базы данных
        c.execute("DELETE FROM files WHERE id=?", (file_id,))
        conn.commit()

    conn.close()


def update_session_summary(session_id, summary):
    """
    Обновляет резюме (summary) для заданной сессии.

    :param session_id: ID сессии, которую нужно обновить.
    :param summary: Текст резюме для записи в базу данных.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE sessions SET summary=? WHERE id=?", (summary, session_id))
    conn.commit()
    conn.close()
