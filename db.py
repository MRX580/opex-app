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
        aggregated_summary TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_prompts (
            id INTEGER PRIMARY KEY,
            project_summarization_prompt TEXT,
            goals_prompt TEXT,
            assistant_prompt TEXT,
            file_upload_prompt TEXT,
            session_summarization_prompt TEXT
        )
    ''')

    # Таблица сессий (10 сессий на проект)
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        session_number INTEGER,
        status TEXT,
        summary TEXT,
        session_name TEXT,
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

    c.execute("SELECT id FROM admin_prompts WHERE id = 1")
    row = c.fetchone()
    if not row:
        c.execute("""
                INSERT INTO admin_prompts(
                    id,
                    project_summarization_prompt,
                    goals_prompt,
                    assistant_prompt,
                    file_upload_prompt,
                    session_summarization_prompt
                ) VALUES (1, '', '', '', '', '')
            """)
    conn.commit()
    conn.close()

def get_admin_prompts() -> dict:
    """
    Возвращает словарь с промптами из таблицы admin_prompts (строка с id=1).
    Если такой строки нет, вернёт None.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT
            project_summarization_prompt,
            goals_prompt,
            assistant_prompt,
            file_upload_prompt,
            session_summarization_prompt
        FROM admin_prompts
        WHERE id=1
    """)
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "project_summarization_prompt": row[0] or "",
            "goals_prompt": row[1] or "",
            "assistant_prompt": row[2] or "",
            "file_upload_prompt": row[3] or "",
            "session_summarization_prompt": row[4] or ""
        }
    else:
        return None

def update_admin_prompts(
    project_summarization_prompt: str,
    goals_prompt: str,
    assistant_prompt: str,
    file_upload_prompt: str,
    session_summarization_prompt: str
):
    """
    Обновляет запись с id=1 в admin_prompts.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE admin_prompts
        SET
            project_summarization_prompt=?,
            goals_prompt=?,
            assistant_prompt=?,
            file_upload_prompt=?,
            session_summarization_prompt=?
        WHERE id=1
    """, (
        project_summarization_prompt,
        goals_prompt,
        assistant_prompt,
        file_upload_prompt,
        session_summarization_prompt
    ))
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
        session_name = f"Session {i}"
        c.execute("INSERT INTO sessions (project_id, session_number, status, session_name) VALUES (?,?,?,?)",
                  (project_id, i, 'Not Started', session_name))
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
    c.execute("SELECT id, session_number, status, summary, session_name FROM sessions WHERE project_id=?", (project_id,))
    sessions = c.fetchall()
    conn.close()
    return sessions


def get_session_by_id(session_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, project_id, session_number, status, summary, session_name FROM sessions WHERE id=?", (session_id,))
    session = c.fetchone()
    conn.close()
    return session


def update_session_summary(session_id, summary):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE sessions SET summary=? WHERE id=?", (summary, session_id))
    conn.commit()
    conn.close()


def update_session_name(session_id, session_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE sessions SET session_name=? WHERE id=?", (session_name, session_id))
    conn.commit()
    conn.close()


def update_session_status(session_id, session_status):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE sessions SET status=? WHERE id=?", (session_status, session_id))
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


def insert_file(session_id: int, file_path: str, file_name: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO files (session_id, file_path, file_name) VALUES (?,?,?)",
              (session_id, file_path, file_name))
    conn.commit()
    conn.close()

def get_files_for_session(session_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, file_path, file_name FROM files WHERE session_id=?", (session_id,))
    files = c.fetchall()
    conn.close()
    return files


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


def get_user_by_id(id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""SELECT u.id, u.name, u.email, u.password_hash, u.role, u.organization 
                 FROM tokens t 
                 JOIN users u ON u.id = t.user_id
                 WHERE u.id=?""", (id,))
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


def get_session_summaries_for_project(project_id: int):
    """
    Возвращает список (непустых) summary всех сессий проекта.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT summary FROM sessions WHERE project_id=?", (project_id,))
    rows = c.fetchall()
    conn.close()
    summaries = [row[0] for row in rows if row[0] and row[0].strip()]
    return summaries

def update_project_summary(project_id: int, summary: str):
    """
    Обновляет (записывает) в таблицу projects поле aggregated_summary.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE projects SET aggregated_summary=? WHERE id=?", (summary, project_id))
    conn.commit()
    conn.close()


def get_project_summary(project_id: int) -> str:
    """
    Возвращает текущее значение поля aggregated_summary для проекта.
    Если нет, вернёт None.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT aggregated_summary FROM projects WHERE id=?", (project_id,))
    result = c.fetchone()
    conn.close()
    if result:
        return result[0]
    return None


def get_first_session_summary(project_id: int) -> str:
    """
    Возвращает summary из первой сессии проекта (где session_number=1).
    Если нет такой сессии или там нет summary, вернёт None.
    """
    conn = get_connection()
    c = conn.cursor()
    # Ищем ту сессию, у которой project_id=? И session_number=1
    c.execute("SELECT summary FROM sessions WHERE project_id=? AND session_number=1", (project_id,))
    row = c.fetchone()
    conn.close()

    if row and row[0] and row[0].strip():
        return row[0]
    else:
        return None


def update_project_goals(project_id: int, new_goals: str) -> None:
    """
    Записывает в таблицу `projects` значение поля `goal`.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE projects SET goal=? WHERE id=?", (new_goals, project_id))
    conn.commit()
    conn.close()


def get_first_session_summary(project_id: int) -> str:
    """
    Возвращает summary из первой сессии проекта (где session_number=1).
    Если нет такой сессии или там нет summary, вернёт None.
    """
    conn = get_connection()
    c = conn.cursor()
    # Ищем ту сессию, у которой project_id=? И session_number=1
    c.execute("SELECT summary FROM sessions WHERE project_id=? AND session_number=1", (project_id,))
    row = c.fetchone()
    conn.close()

    if row and row[0] and row[0].strip():
        return row[0]
    else:
        return None


def update_project_goals(project_id: int, new_goals: str) -> None:
    """
    Записывает в таблицу `projects` значение поля `goal`.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE projects SET goal=? WHERE id=?", (new_goals, project_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, email, password_hash, role, organization FROM users")
    users = c.fetchall()
    conn.close()
    return users

def create_project_with_sessions(user_id: int, project_name: str) -> None:
    """
    Создает новый проект с заданным названием и 22 сессии для него.
    """
    conn = get_connection()
    c = conn.cursor()

    # Создаем новый проект
    c.execute(
        "INSERT INTO projects (user_id, name, goal, status) VALUES (?, ?, ?, ?)",
        (user_id, project_name, "Define the goals of this project", "Not Started"),
    )
    project_id = c.lastrowid

    # Создаем 22 сессии
    session_templates = [
        "Project Kickoff",
        "1 - Preparation",
        "1 - Post-Session Report",
        "2 - Preparation",
        "2 - Post-Session Report",
        "3 - Preparation",
        "3 - Post-Session Report",
        "4 - Preparation",
        "4 - Post-Session Report",
        "5 - Preparation",
        "5 - Post-Session Report",
        "6 - Preparation",
        "6 - Post-Session Report",
        "7 - Preparation",
        "7 - Post-Session Report",
        "8 - Preparation",
        "8 - Post-Session Report",
        "9 - Preparation",
        "9 - Post-Session Report",
        "10 - Preparation",
        "10 - Post-Session Report",
        "Project Closure",
    ]

    for index, session_name in enumerate(session_templates):
        c.execute(
            "INSERT INTO sessions (project_id, session_number, status, summary, session_name) VALUES (?, ?, ?, ?, ?)",
            (project_id, index + 1, "Not Started", None, session_name),
        )

    conn.commit()
    conn.close()


def insert_admin_pdf(file_path: str, file_name: str):
    """
    Сохраняет PDF как «глобальный» (не привязанный ни к проекту, ни к сессии).
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO files (project_id, session_id, file_path, file_name)
        VALUES (NULL, NULL, ?, ?)
    """, (file_path, file_name))
    conn.commit()
    conn.close()


def get_admin_pdf_paths():
    """
    Возвращает список путей (file_path) всех «глобальных» PDF-файлов.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT file_path FROM files WHERE project_id IS NULL AND session_id IS NULL")
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

def get_admin_pdfs():
    """
    Возвращает список глобальных (админских) PDF-файлов.
    Каждый элемент списка: (id, file_path, file_name).
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT id, file_path, file_name
        FROM files
        WHERE project_id IS NULL AND session_id IS NULL
    """)
    rows = c.fetchall()
    conn.close()
    return rows

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
