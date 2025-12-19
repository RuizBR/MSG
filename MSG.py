import streamlit as st
import sqlite3
from datetime import datetime
import base64
import random
import string
import time
import hashlib
from streamlit_autorefresh import st_autorefresh

# ================= SESSION =================
if "session_id" not in st.session_state:
    st.session_state.session_id = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

# ================= UTILS =================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ================= USERS DB =================
USERS_DB = "users.db"

def init_users_db():
    conn = sqlite3.connect(USERS_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT
        )
    """)
    conn.commit()
    conn.close()

def register_user(username, password):
    try:
        conn = sqlite3.connect(USERS_DB)
        cur = conn.cursor()
        cur.execute("INSERT INTO users VALUES (?,?)", (username, hash_password(password)))
        conn.commit()
        conn.close()
        return True, "Registration successful!"
    except sqlite3.IntegrityError:
        return False, "Username already exists"

def login_user_db(username, password):
    conn = sqlite3.connect(USERS_DB)
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if row and row[0] == hash_password(password):
        return True
    return False

init_users_db()

# ================= CHAT DB =================
CHAT_DB = "chatbox.db"

def init_chat_db():
    conn = sqlite3.connect(CHAT_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            recipient TEXT,
            message TEXT,
            msg_type TEXT,
            file_name TEXT,
            file_data BLOB,
            timestamp TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS active_users (
            session_id TEXT PRIMARY KEY,
            username TEXT,
            last_seen INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS typing_users (
            username TEXT PRIMARY KEY,
            last_typing INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_chat_db()

# ================= CHAT FUNCTIONS =================
def execute_db_write(query, params=(), retries=5):
    """Executes a write operation with retry logic for SQLite busy errors."""
    while retries > 0:
        try:
            conn = sqlite3.connect(CHAT_DB, timeout=5)
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()
            conn.close()
            break
        except sqlite3.OperationalError:
            retries -= 1
            time.sleep(0.1)
    else:
        st.error("Database busy. Please refresh the page and try again.")

def add_text_message(user, message, recipient=None):
    execute_db_write(
        "INSERT INTO messages VALUES (NULL,?,?,?, 'text', NULL, NULL, ?)",
        (user, recipient, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )

def add_file_message(user, file, recipient=None):
    execute_db_write(
        "INSERT INTO messages VALUES (NULL,?,?,NULL,'file',?,?,?)",
        (user, recipient, file.name, file.getvalue(),
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )

def update_active_user(session_id, username):
    execute_db_write("""
        INSERT INTO active_users VALUES (?,?,?)
        ON CONFLICT(session_id)
        DO UPDATE SET last_seen=excluded.last_seen,
                      username=excluded.username
    """, (session_id, username, int(time.time())))

def set_typing(username):
    execute_db_write("""
        INSERT INTO typing_users VALUES (?,?)
        ON CONFLICT(username)
        DO UPDATE SET last_typing=excluded.last_typing
    """, (username, int(time.time())))

def get_online_users(timeout=10):
    conn = sqlite3.connect(CHAT_DB)
    cur = conn.cursor()
    now = int(time.time())
    cur.execute("""
        SELECT DISTINCT username
        FROM active_users
        WHERE ? - last_seen <= ?
          AND username IS NOT NULL
          AND username != ''
        ORDER BY username
    """, (now, timeout))
    users = [r[0] for r in cur.fetchall()]
    conn.close()
    return users

def get_typing_users(timeout=4):
    conn = sqlite3.connect(CHAT_DB)
    cur = conn.cursor()
    now = int(time.time())
    cur.execute("""
        SELECT username FROM typing_users
        WHERE ? - last_typing <= ?
    """, (now, timeout))
    users = [r[0] for r in cur.fetchall()]
    conn.close()
    return users

def get_messages(username):
    conn = sqlite3.connect(CHAT_DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT user, recipient, message, msg_type, file_name, file_data, timestamp
        FROM messages
        WHERE recipient IS NULL
           OR recipient = ?
           OR user = ?
        ORDER BY id
    """, (username, username))
    rows = cur.fetchall()
    conn.close()
    return rows

# ================= STREAMLIT =================
st.set_page_config(page_title="💬 Team Chatbox", layout="wide")
st_autorefresh(interval=3000, key="refresh")

# ================= LOGIN / REGISTER =================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

st.sidebar.title("👤 Login / Register")
login_tab, register_tab = st.tabs(["Login", "Register"])

with login_tab:
    login_user_input = st.text_input("Username", key="login_user")
    login_pass_input = st.text_input("Password", type="password", key="login_pass")
    if st.button("Login"):
        if login_user_db(login_user_input, login_pass_input):
            st.session_state.logged_in = True
            st.session_state.username = login_user_input
            st.success(f"Logged in as {login_user_input}")
        else:
            st.error("Invalid username or password")

with register_tab:
    reg_user_input = st.text_input("New Username", key="reg_user")
    reg_pass_input = st.text_input("New Password", type="password", key="reg_pass")
    if st.button("Register"):
        success, msg = register_user(reg_user_input, reg_pass_input)
        if success:
            st.success(msg)
        else:
            st.error(msg)

# ================= CHAT =================
if st.session_state.logged_in:
    username = st.session_state.username
    update_active_user(st.session_state.session_id, username)

    st.sidebar.markdown(f"🟢 Online Users ({len(get_online_users())})")
    online_list = get_online_users()
    for u in online_list:
        st.sidebar.markdown(f"🟢 {u}")

    recipient = st.sidebar.selectbox(
        "Send To",
        ["All (public)"] + [u for u in online_list if u != username]
    )

    msg = st.sidebar.text_area("", key="chat_input", placeholder="Type a message...")
    if msg.strip():
        set_typing(username)

    def send():
        if st.session_state["chat_input"].strip():
            add_text_message(username, st.session_state["chat_input"].strip(),
                             None if recipient=="All (public)" else recipient)
            st.session_state["chat_input"] = ""

    st.sidebar.button("Send", on_click=send, use_container_width=True)

    file = st.sidebar.file_uploader("📎 Attach file",
        type=["png","jpg","jpeg","pdf","docx"])
    if st.sidebar.button("Send File"):
        if file:
            add_file_message(username, file,
                             None if recipient=="All (public)" else recipient)

# ================= DISPLAY CHAT =================
st.title("💬 Team Chatbox")

if not st.session_state.logged_in:
    st.info("🔒 Please login to chat.")
else:
    msgs = get_messages(username)
    typing = [u for u in get_typing_users() if u != username]
    if typing:
        st.caption("✍️ " + ", ".join(typing) + " typing…")

    for u, r, m, t, f, fd, ts in msgs:
        if r and r != username and u != username:
            continue

        me = u == username
        bg = "#0084ff" if me else "#e5e5ea"
        col = "white" if me else "black"
        priv_label = "(private)" if r else ""

        if t == "text":
            content = m
        elif f.lower().endswith(("png","jpg","jpeg")):
            img = base64.b64encode(fd).decode()
            content = f"<img src='data:image/png;base64,{img}' width=200>"
        else:
            b = base64.b64encode(fd).decode()
            content = f"<a download='{f}' href='data:;base64,{b}'>{f}</a>"

        st.markdown(f"""
        <div style='background:{bg};color:{col};
        padding:10px;border-radius:14px;margin:6px;
        max-width:65%;{'margin-left:auto;' if me else ''}'>
        <b>{u} {priv_label}</b><br>{content}
        <div style="font-size:10px;opacity:.6">{ts}</div>
        </div>
        """, unsafe_allow_html=True)
