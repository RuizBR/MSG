import streamlit as st
import sqlite3
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import base64
import random
import string
import time

# ================= SESSION =================
if "session_id" not in st.session_state:
    st.session_state.session_id = ''.join(
        random.choices(string.ascii_letters + string.digits, k=16)
    )

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
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
    c.execute("""
        CREATE TABLE IF NOT EXISTS video_call (
            id INTEGER PRIMARY KEY,
            room_name TEXT,
            started INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS active_users (
            session_id TEXT PRIMARY KEY,
            username TEXT,
            last_seen INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS typing_users (
            username TEXT PRIMARY KEY,
            last_typing INTEGER
        )
    """)
    c.execute("SELECT COUNT(*) FROM video_call")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO video_call VALUES (1,'',0)")
    conn.commit()
    conn.close()

# ================= ACTIVE USERS =================
def update_active_user(session_id, username):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO active_users VALUES (?,?,?)
        ON CONFLICT(session_id)
        DO UPDATE SET last_seen=excluded.last_seen,
                      username=excluded.username
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

def get_online_users(timeout=10):
    now = int(time.time())
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT username
        FROM active_users
        WHERE ? - last_seen <= ?
          AND username IS NOT NULL
          AND username != ''
        ORDER BY username
    """, (now, timeout))
    users = [r[0] for r in c.fetchall()]
    conn.close()
    return users

def is_username_taken(username, session_id):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        SELECT 1 FROM active_users
        WHERE username=? AND session_id != ? AND ? - last_seen <= 10
    """, (username, session_id, int(time.time())))
    taken = c.fetchone() is not None
    conn.close()
    return taken

# ================= TYPING =================
def set_typing(username):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO typing_users VALUES (?,?)
        ON CONFLICT(username)
        DO UPDATE SET last_typing=excluded.last_typing
    """, (username, int(time.time())))
    conn.commit()
    conn.close()

def get_typing_users(timeout=4):
    now = int(time.time())
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        SELECT username FROM typing_users
        WHERE ? - last_typing <= ?
    """, (now, timeout))
    users = [r[0] for r in c.fetchall()]
    conn.close()
    return users

# ================= MESSAGES =================
def add_text_message(user, message):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO messages VALUES (NULL,?,?, 'text', NULL, NULL, ?)
    """, (user, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def add_file_message(user, file):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO messages VALUES (NULL,?,NULL,'file',?,?,?)
    """, (user, file.name, file.getvalue(),
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_messages():
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        SELECT user,message,msg_type,file_name,file_data,timestamp
        FROM messages ORDER BY id
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

# ================= VIDEO CALL =================
def get_video_call_status():
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("SELECT room_name, started FROM video_call WHERE id=1")
    r = c.fetchone()
    conn.close()
    return r

def start_video_call(room):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("UPDATE video_call SET room_name=?, started=1 WHERE id=1", (room,))
    conn.commit()
    conn.close()

def end_video_call():
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("UPDATE video_call SET room_name='', started=0 WHERE id=1")
    conn.commit()
    conn.close()

# ================= STREAMLIT =================
st.set_page_config(page_title="💬 Team Chatbox", layout="wide")
init_db()

# 🔄 AUTO REFRESH
st_autorefresh(interval=5000, key="refresh")

# ================= SIDEBAR =================
online_count = get_online_user_count()
st.sidebar.markdown(f"🟢 **{online_count} Users Online**")

st.sidebar.title("👤 User Settings")
username = st.sidebar.text_input("Your Name").strip()

if username:
    if is_username_taken(username, st.session_state.session_id):
        st.sidebar.error("❌ Username already in use")
        username = ""
    else:
        update_active_user(st.session_state.session_id, username)

# Online user list
online_list = get_online_users()
if online_list:
    st.sidebar.markdown("### 👁️ Online")
    for u in online_list:
        st.sidebar.markdown(f"🟢 {u}")

if st.sidebar.button("🗑️ Clear Chat"):
    clear_messages()
    st.rerun()

# ================= CHAT INPUT =================
msg_key = "chat_input"

if not username:
    st.sidebar.info("🔒 Read-only mode. Enter a username to chat.")
else:
    msg = st.sidebar.text_area("", key=msg_key, placeholder="Type a message...")
    if msg.strip():
        set_typing(username)

    def send():
        if st.session_state[msg_key].strip():
            add_text_message(username, st.session_state[msg_key].strip())
            st.session_state[msg_key] = ""

    st.sidebar.button("Send", on_click=send, use_container_width=True)

    file = st.sidebar.file_uploader("📎 Attach file", type=["png","jpg","jpeg","pdf","docx"])
    if st.sidebar.button("Send File"):
        if file:
            add_file_message(username, file)

# ================= MAIN CHAT =================
st.title("💬 Team Chatbox")

typing = [u for u in get_typing_users() if u != username]
if typing:
    st.caption("✍️ " + ", ".join(typing) + " typing…")

if not username:
    st.info("👤 Enter your name to view the chat.")
else:
    msgs = get_messages()
    html = "<div style='max-width:900px;height:600px;overflow:auto;margin:auto;'>"
    for u,m,t,f,fd,ts in msgs:
        me = u == username
        bg = "#0084ff" if me else "#e5e5ea"
        col = "white" if me else "black"

        if t == "text":
            content = m
        elif f.lower().endswith(("png","jpg","jpeg")):
            img = base64.b64encode(fd).decode()
            content = f"<img src='data:image/png;base64,{img}' width=200>"
        else:
            b = base64.b64encode(fd).decode()
            content = f"<a download='{f}' href='data:;base64,{b}'>{f}</a>"

        html += f"""
        <div style="background:{bg};color:{col};
        padding:10px;border-radius:14px;margin:6px;
        max-width:65%;{'margin-left:auto;' if me else ''}">
        <b>{u}</b><br>{content}
        <div style="font-size:10px;opacity:.6">{ts}</div>
        </div>
        """
    html += "</div><script>document.querySelector('div').scrollTop=999999</script>"
    st.components.v1.html(html, height=650)
