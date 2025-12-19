import streamlit as st
import sqlite3
import time
import random
import string
from datetime import datetime
import base64

# ================== CONFIG ==================
ADMIN_PASSWORD = "admin123"  # admin password
SESSION_TIMEOUT = 15          # seconds for auto logout / session expiry

# ================== SESSION ==================
if "session_id" not in st.session_state:
    st.session_state.session_id = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

# ================== DATABASE ==================
def init_db():
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()

    # Rooms table
    c.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            room_id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_name TEXT UNIQUE,
            password TEXT,
            created_at INTEGER
        )
    """)

    # Messages table
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER,
            user TEXT,
            message TEXT,
            msg_type TEXT,
            file_name TEXT,
            file_data BLOB,
            timestamp TEXT
        )
    """)

    # Active users
    c.execute("""
        CREATE TABLE IF NOT EXISTS active_users (
            session_id TEXT,
            username TEXT,
            room_id INTEGER,
            last_seen INTEGER,
            PRIMARY KEY(session_id, room_id)
        )
    """)

    # Typing indicator
    c.execute("""
        CREATE TABLE IF NOT EXISTS typing_users (
            username TEXT,
            room_id INTEGER,
            last_typing INTEGER,
            PRIMARY KEY(username, room_id)
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ================== HELPER FUNCTIONS ==================
def get_rooms():
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("SELECT room_id, room_name FROM rooms ORDER BY room_name")
    rooms = c.fetchall()
    conn.close()
    return rooms

def create_room(room_name, password):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("INSERT INTO rooms (room_name, password, created_at) VALUES (?,?,?)",
              (room_name, password, int(time.time())))
    conn.commit()
    conn.close()

def verify_room_password(room_id, password):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("SELECT password FROM rooms WHERE room_id=?", (room_id,))
    row = c.fetchone()
    conn.close()
    return row and row[0] == password

def update_active_user(session_id, username, room_id):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO active_users (session_id, username, room_id, last_seen)
        VALUES (?,?,?,?)
        ON CONFLICT(session_id, room_id)
        DO UPDATE SET last_seen=excluded.last_seen,
                      username=excluded.username
    """, (session_id, username, room_id, int(time.time())))
    conn.commit()
    conn.close()

def get_online_users(room_id, timeout=SESSION_TIMEOUT):
    now = int(time.time())
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        SELECT username FROM active_users
        WHERE room_id=? AND ? - last_seen <= ?
    """, (room_id, now, timeout))
    users = [r[0] for r in c.fetchall()]
    conn.close()
    return users

def remove_user(session_id, room_id):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("DELETE FROM active_users WHERE session_id=? AND room_id=?", (session_id, room_id))
    conn.commit()
    conn.close()

def add_text_message(room_id, user, msg):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO messages (room_id, user, message, msg_type, timestamp)
        VALUES (?,?,?,'text',?)
    """, (room_id, user, msg, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def add_file_message(room_id, user, file):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO messages (room_id, user, msg_type, file_name, file_data, timestamp)
        VALUES (?,?, 'file', ?, ?, ?)
    """, (room_id, user, file.name, file.getvalue(), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_messages(room_id):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        SELECT user,message,msg_type,file_name,file_data,timestamp
        FROM messages WHERE room_id=? ORDER BY id
    """, (room_id,))
    msgs = c.fetchall()
    conn.close()
    return msgs

def set_typing(username, room_id):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO typing_users (username, room_id, last_typing)
        VALUES (?,?,?)
        ON CONFLICT(username, room_id)
        DO UPDATE SET last_typing=excluded.last_typing
    """, (username, room_id, int(time.time())))
    conn.commit()
    conn.close()

def get_typing_users(room_id, timeout=4):
    now = int(time.time())
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        SELECT username FROM typing_users
        WHERE room_id=? AND ? - last_typing <= ?
    """, (room_id, now, timeout))
    users = [r[0] for r in c.fetchall()]
    conn.close()
    return users

# ================== STREAMLIT UI ==================
st.set_page_config(page_title="🔒 Private Team Chat", layout="wide")
st_autorefresh(interval=5000, key="refresh")

# ================== ADMIN LOGIN ==================
if not st.session_state.admin_authenticated:
    admin_pwd = st.sidebar.text_input("Admin Password", type="password")
    if st.sidebar.button("Login as Admin"):
        if admin_pwd == ADMIN_PASSWORD:
            st.session_state.admin_authenticated = True
            st.experimental_rerun()
        else:
            st.sidebar.error("Incorrect admin password")

# ================== ROOM SELECTION ==================
if "room_id" not in st.session_state:
    st.session_state.room_id = None

st.sidebar.title("👥 Rooms")
rooms = get_rooms()
room_names = [r[1] for r in rooms]

# Create new room
new_room_name = st.sidebar.text_input("Create Room")
new_room_pwd = st.sidebar.text_input("Room Password", type="password")
if st.sidebar.button("Create Room"):
    if new_room_name.strip() and new_room_pwd.strip():
        create_room(new_room_name.strip(), new_room_pwd.strip())
        st.experimental_rerun()

# Join existing room
selected_room = st.sidebar.selectbox("Select Room", ["-- Join --"] + room_names)
if selected_room != "-- Join --":
    room_id = [r[0] for r in rooms if r[1]==selected_room][0]
    pwd = st.sidebar.text_input(f"Password for {selected_room}", type="password", key="room_pwd")
    if st.sidebar.button("Join Room"):
        if verify_room_password(room_id, pwd):
            st.session_state.authenticated = True
            st.session_state.room_id = room_id
            st.experimental_rerun()
        else:
            st.sidebar.error("Incorrect room password")

# ================== LOGOUT ==================
if st.session_state.authenticated and st.sidebar.button("🚪 Logout / Lock Chat"):
    remove_user(st.session_state.session_id, st.session_state.room_id)
    st.session_state.username = None
    st.session_state.authenticated = False
    st.session_state.room_id = None
    st.experimental_rerun()

# ================== USER LOGIN ==================
if st.session_state.authenticated and st.session_state.room_id:
    st.sidebar.title("👤 User Settings")
    username = st.sidebar.text_input("Your Name").strip()
    if username:
        update_active_user(st.session_state.session_id, username, st.session_state.room_id)
else:
    st.stop()  # block chat until room + password + username

# ================== ONLINE USERS ==================
st.sidebar.markdown("### 👁️ Online Users")
online_users = get_online_users(st.session_state.room_id)
for u in online_users:
    st.sidebar.markdown(f"🟢 {u}")

# ================== TYPING INDICATOR ==================
msg_input = st.sidebar.text_area("Type your message", key="msg_input")
if msg_input.strip():
    set_typing(username, st.session_state.room_id)

if st.sidebar.button("Send"):
    if msg_input.strip():
        add_text_message(st.session_state.room_id, username, msg_input.strip())
        st.session_state.msg_input = ""

file = st.sidebar.file_uploader("Attach File", type=["png","jpg","jpeg","pdf","docx"])
if st.sidebar.button("Send File"):
    if file:
        add_file_message(st.session_state.room_id, username, file)

# ================== MAIN CHAT ==================
st.title(f"💬 Room Chat")

typing_users = [u for u in get_typing_users(st.session_state.room_id) if u != username]
if typing_users:
    st.caption("✍️ " + ", ".join(typing_users) + " typing…")

msgs = get_messages(st.session_state.room_id)
html = "<div style='max-width:900px;height:600px;overflow:auto;margin:auto;'>"
for u, m, t, f, fd, ts in msgs:
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
    <div style="background:{bg};color:{col};padding:10px;border-radius:14px;margin:6px;
    max-width:65%;{'margin-left:auto;' if me else ''}">
    <b>{u}</b><br>{content}
    <div style="font-size:10px;opacity:.6">{ts}</div>
    </div>
    """
html += "</div><script>document.querySelector('div').scrollTop=999999</script>"
st.components.v1.html(html, height=650)

# ================== ADMIN PANEL ==================
if st.session_state.admin_authenticated:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🛠 Admin Panel")
    if st.sidebar.button("Clear All Messages"):
        conn = sqlite3.connect("chatbox.db")
        c = conn.cursor()
        c.execute("DELETE FROM messages")
        conn.commit()
        conn.close()
        st.sidebar.success("All messages cleared")
    for r in rooms:
        new_pwd = st.sidebar.text_input(f"Change Password {r[1]}", type="password", key=f"pwd_{r[0]}")
        if st.sidebar.button(f"Update Password {r[1]}", key=f"btn_{r[0]}"):
            conn = sqlite3.connect("chatbox.db")
            c = conn.cursor()
            c.execute("UPDATE rooms SET password=? WHERE room_id=?", (new_pwd, r[0]))
            conn.commit()
            conn.close()
            st.sidebar.success(f"Password updated for {r[1]}")
