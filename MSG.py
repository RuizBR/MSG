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
    conn = sqlite3.connect(USERS_DB, check_same_thread=False)
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
        conn = sqlite3.connect(USERS_DB, check_same_thread=False)
        cur = conn.cursor()
        cur.execute("INSERT INTO users VALUES (?,?)", (username, hash_password(password)))
        conn.commit()
        conn.close()
        return True, "Registration successful!"
    except sqlite3.IntegrityError:
        return False, "Username already exists"

def login_user_db(username, password):
    conn = sqlite3.connect(USERS_DB, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if row and row[0] == hash_password(password):
        return True
    return False

init_users_db()

# ================= CHAT DB =================
CHAT_DB = "chat_fixed.db"  # fresh DB

def init_chat_db():
    conn = sqlite3.connect(CHAT_DB, check_same_thread=False)
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

# ================= DB FUNCTIONS =================
def execute_db_write(db, query, params=(), retries=10, delay=0.2):
    while retries > 0:
        try:
            conn = sqlite3.connect(db, timeout=30, check_same_thread=False)
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()
            cur.close()
            conn.close()
            break
        except sqlite3.OperationalError:
            retries -= 1
            time.sleep(delay)
    else:
        st.error("Database busy. Please refresh the page and try again.")

def execute_db_read(db, query, params=(), retries=10, delay=0.2):
    while retries > 0:
        try:
            conn = sqlite3.connect(db, timeout=30, check_same_thread=False)
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return rows
        except sqlite3.OperationalError:
            retries -= 1
            time.sleep(delay)
    return []

# ================= CHAT FUNCTIONS =================
def add_text_message(user, message, recipient=None):
    execute_db_write(
        CHAT_DB,
        "INSERT INTO messages VALUES (NULL,?,?,?, 'text', NULL, NULL, ?)",
        (user, recipient, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )

def add_file_message(user, file, recipient=None):
    execute_db_write(
        CHAT_DB,
        "INSERT INTO messages VALUES (NULL,?,?,NULL,'file',?,?,?)",
        (user, recipient, file.name, file.getvalue(),
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )

def update_active_user(session_id, username):
    execute_db_write(
        CHAT_DB,
        """
        INSERT INTO active_users VALUES (?,?,?)
        ON CONFLICT(session_id)
        DO UPDATE SET last_seen=excluded.last_seen,
                      username=excluded.username
        """,
        (session_id, username, int(time.time()))
    )

def set_typing(username):
    execute_db_write(
        CHAT_DB,
        """
        INSERT INTO typing_users VALUES (?,?)
        ON CONFLICT(username)
        DO UPDATE SET last_typing=excluded.last_typing
        """,
        (username, int(time.time()))
    )

def remove_typing(username):
    execute_db_write(CHAT_DB, "DELETE FROM typing_users WHERE username=?", (username,))

def get_online_users(timeout=10):
    now = int(time.time())
    query = """
        SELECT DISTINCT username
        FROM active_users
        WHERE ? - last_seen <= ?
          AND username IS NOT NULL
          AND username != ''
        ORDER BY username
    """
    rows = execute_db_read(CHAT_DB, query, (now, timeout))
    return [r[0] for r in rows] if rows else []

def get_typing_users(timeout=4):
    now = int(time.time())
    query = """
        SELECT username FROM typing_users
        WHERE ? - last_typing <= ?
    """
    rows = execute_db_read(CHAT_DB, query, (now, timeout))
    return [r[0] for r in rows] if rows else []

# ================= FIXED: GET MESSAGES =================
def get_messages(username):
    query = """
        SELECT user, recipient, message, msg_type, file_name, file_data, timestamp
        FROM messages
        WHERE recipient IS NULL OR recipient = ''              -- public messages
           OR recipient = ?                                     -- private messages sent to me
           OR (user = ? AND recipient IS NOT NULL)             -- private messages I sent
        ORDER BY id
    """
    rows = execute_db_read(CHAT_DB, query, (username, username))
    return rows if rows else []

# ================= STREAMLIT CONFIG =================
st.set_page_config(page_title="💬 Team Chatbox", layout="wide")
st_autorefresh(interval=2000, key="refresh")

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

    all_users = execute_db_read(USERS_DB, "SELECT username FROM users")
    all_usernames = [u[0] for u in all_users if u[0] != username]

    online_list = get_online_users()
    st.sidebar.markdown(f"🟢 Online Users ({len(online_list)})")
    for u in online_list:
        st.sidebar.markdown(f"🟢 {u}")

    recipient = st.sidebar.selectbox(
        "Send To",
        ["All (public)"] + all_usernames  # include offline users too
    )

    # Chat input
    chat_input = st.sidebar.text_area(
        "", key="chat_input", placeholder="Type a message...", height=50
    )

    if st.session_state.chat_input.strip():
        set_typing(username)
    else:
        remove_typing(username)

    def send():
        if st.session_state.chat_input.strip():
            msg_text = st.session_state.chat_input.strip()
            recipient_db = None if recipient == "All (public)" else recipient
            add_text_message(username, msg_text, recipient_db)
            st.session_state.chat_input = ""
            remove_typing(username)

    st.sidebar.button("Send", on_click=send, use_container_width=True)

    # File upload
    file = st.sidebar.file_uploader(
        "📎 Attach file",
        type=["png","jpg","jpeg","pdf","docx"]
    )
    if st.sidebar.button("Send File"):
        if file:
            recipient_db = None if recipient == "All (public)" else recipient
            add_file_message(username, file, recipient_db)
            remove_typing(username)

# ================= DISPLAY CHAT =================
st.title("💬 Team Chatbox")

if not st.session_state.logged_in:
    st.info("🔒 Please login to chat.")
else:
    msgs = get_messages(username)
    typing = [u for u in get_typing_users() if u != username]

    if typing:
        st.caption("✍️ " + ", ".join(typing) + " typing…")

    # Display messages strictly based on “Send To”
    if recipient == "All (public)":
        st.subheader("🌐 Public Chat")
        display_msgs = [msg for msg in msgs if msg[1] in (None, '')]
    else:
        st.subheader(f"🔒 Private Chat with {recipient}")
        display_msgs = [msg for msg in msgs if (msg[1] == recipient or (msg[0]==username and msg[1]==recipient))]

    for u, r, m, t, f, fd, ts in display_msgs:
        me = u == username
        bg = "#0084ff" if me else "#e5e5ea"
        col = "white" if me else "black"
        content = m if t=="text" else ""
        if t=="file" and f:
            if f.lower().endswith(("png","jpg","jpeg")):
                img = base64.b64encode(fd).decode()
                content = f"<img src='data:image/png;base64,{img}' width=200>"
            else:
                b = base64.b64encode(fd).decode()
                content = f"<a download='{f}' href='data:;base64,{b}'>{f}</a>"
        priv_label = "(private)" if recipient != "All (public)" else ""
        st.markdown(f"""
        <div style='background:{bg};color:{col};
        padding:10px;border-radius:14px;margin:6px;
        max-width:65%;{'margin-left:auto;' if me else ''}'">
        <b>{u} {priv_label}</b><br>{content}
        <div style="font-size:10px;opacity:.6">{ts}</div>
        </div>
        """, unsafe_allow_html=True)

    # Auto-scroll
    st.markdown("<div id='bottom'></div>", unsafe_allow_html=True)
    st.markdown("""
    <script>
    var element = document.getElementById("bottom");
    if(element){
        element.scrollIntoView({behavior: 'smooth'});
    }
    </script>
    """, unsafe_allow_html=True)
