import streamlit as st
import sqlite3
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import base64
import random
import string
import time

# ================= SESSION ID =================
if "session_id" not in st.session_state:
    st.session_state.session_id = ''.join(
        random.choices(string.ascii_letters + string.digits, k=16)
    )

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()

    # Messages table
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            message TEXT,
            msg_type TEXT,
            file_name TEXT,
            file_data BLOB,
            timestamp TEXT
        )
    """)

    # Video call table
    c.execute("""
        CREATE TABLE IF NOT EXISTS video_call (
            id INTEGER PRIMARY KEY,
            room_name TEXT,
            started INTEGER
        )
    """)

    # Active users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS active_users (
            session_id TEXT PRIMARY KEY,
            username TEXT,
            last_seen INTEGER
        )
    """)

    c.execute("SELECT COUNT(*) FROM video_call")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO video_call (id, room_name, started) VALUES (1, '', 0)")

    conn.commit()
    conn.close()

# ================= ACTIVE USER FUNCTIONS =================
def update_active_user(session_id, username):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO active_users (session_id, username, last_seen)
        VALUES (?, ?, ?)
        ON CONFLICT(session_id)
        DO UPDATE SET last_seen = excluded.last_seen,
                      username = excluded.username
    """, (session_id, username, int(time.time())))
    conn.commit()
    conn.close()

def get_online_user_count(timeout=10):
    now = int(time.time())
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(DISTINCT session_id)
        FROM active_users
        WHERE ? - last_seen <= ?
    """, (now, timeout))
    count = c.fetchone()[0]
    conn.close()
    return count

# ================= MESSAGE FUNCTIONS =================
def add_text_message(user, message):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO messages (user, message, msg_type, timestamp)
        VALUES (?, ?, 'text', ?)
    """, (user, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def add_file_message(user, file):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO messages (user, msg_type, file_name, file_data, timestamp)
        VALUES (?, 'file', ?, ?, ?)
    """, (user, file.name, file.getvalue(), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_messages():
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        SELECT user, message, msg_type, file_name, file_data, timestamp
        FROM messages
        ORDER BY id ASC
    """)
    rows = c.fetchall()
    conn.close()
    return rows

def clear_messages():
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("DELETE FROM messages")
    conn.commit()
    conn.close()

# ================= VIDEO CALL FUNCTIONS =================
def start_video_call(room_name):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("UPDATE video_call SET room_name = ?, started = 1 WHERE id = 1", (room_name,))
    conn.commit()
    conn.close()

def end_video_call():
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("UPDATE video_call SET room_name = '', started = 0 WHERE id = 1")
    conn.commit()
    conn.close()

def get_video_call_status():
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("SELECT room_name, started FROM video_call WHERE id = 1")
    row = c.fetchone()
    conn.close()
    return row

# ================= STREAMLIT SETUP =================
st.set_page_config(page_title="💬 Team Chatbox", layout="wide")
init_db()

# ================= AUTO REFRESH =================
st_autorefresh(interval=5000, limit=None, key="chat_refresh")

# ================= SIDEBAR =================
online_users = get_online_user_count()

st.sidebar.markdown(
    f"""
    <div style="text-align:center; padding:8px; border-radius:10px;
                background:#f0f2f6; margin-bottom:6px;">
        🟢 <b style="font-size:18px;">{online_users}</b>
        <span style="font-size:8px;">Users Online</span>
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.title("👤 User Settings")

username = st.sidebar.text_input("Your Name", placeholder="Enter your name...")

if username:
    update_active_user(st.session_state.session_id, username)

if st.sidebar.button("🗑️ Clear Chat"):
    clear_messages()
    st.rerun()

st.sidebar.markdown("### 💬 Message")
msg_key = "chat_input"

msg_text = st.sidebar.text_area(
    "",
    key=msg_key,
    label_visibility="collapsed",
    placeholder="Type a message...",
    height=70
)

def send_message():
    if username and st.session_state[msg_key].strip():
        add_text_message(username, st.session_state[msg_key].strip())
        st.session_state[msg_key] = ""

st.sidebar.button("Send", use_container_width=True, on_click=send_message)

uploaded_file = st.sidebar.file_uploader(
    "📎 Attach image or file",
    type=["png", "jpg", "jpeg", "pdf", "docx"]
)

if st.sidebar.button("Send File"):
    if username and uploaded_file:
        add_file_message(username, uploaded_file)

# ================= VIDEO CALL =================
st.title("💬 Team Chatbox")
room_name, started = get_video_call_status()

if started == 0:
    if st.button("📹 Start Video Call"):
        room_name = "TeamChat_" + ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        start_video_call(room_name)
        st.components.v1.html(
            f"<script>window.open('https://meet.jit.si/{room_name}', '_blank')</script>",
            height=0
        )
else:
    st.markdown(f"### 📹 Video Call Active: `{room_name}`")
    st.markdown(f"[Join Video Call](https://meet.jit.si/{room_name})", unsafe_allow_html=True)
    if st.button("❌ End Video Call"):
        end_video_call()

# ================= CHAT DISPLAY =================
messages = get_messages()

chat_html = """
<style>
.chat-box { max-width:900px; height:600px; margin:auto; padding:14px;
border:1px solid #ddd; border-radius:14px; overflow-y:auto; background:white; }
.message { padding:10px 14px; border-radius:18px; max-width:65%; margin:6px 0; }
.me { background:#0084ff; color:white; margin-left:auto; }
.other { background:#e5e5ea; color:black; margin-right:auto; }
.timestamp { font-size:10px; opacity:.6; text-align:right; }
</style>
<div class="chat-box" id="chatBox">
"""

for user, msg, mtype, fname, fdata, ts in messages:
    is_me = user == username
    cls = "me" if is_me else "other"

    if mtype == "text":
        content = msg
    elif fname.lower().endswith(("png", "jpg", "jpeg")):
        img64 = base64.b64encode(fdata).decode()
        content = f'<img src="data:image/png;base64,{img64}" style="max-width:260px;">'
    else:
        file64 = base64.b64encode(fdata).decode()
        content = f'<a download="{fname}" href="data:application/octet-stream;base64,{file64}">{fname}</a>'

    chat_html += f"""
    <div class="message {cls}">
        <b>{user}</b><br>{content}
        <div class="timestamp">{ts}</div>
    </div>
    """

chat_html += """
</div>
<script>
const box = document.getElementById("chatBox");
box.scrollTop = box.scrollHeight;
</script>
"""

st.components.v1.html(chat_html, height=650)

