import streamlit as st
import sqlite3
import random
import string
import time
from datetime import datetime
import base64

# ================= SESSION =================
if "session_id" not in st.session_state:
    st.session_state.session_id = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    
    # Rooms table
    c.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            room_id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_name TEXT UNIQUE,
            room_password TEXT
        )
    """)
    
    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS active_users (
            session_id TEXT PRIMARY KEY,
            username TEXT,
            room_id INTEGER,
            last_seen INTEGER
        )
    """)
    
    # Typing
    c.execute("""
        CREATE TABLE IF NOT EXISTS typing_users (
            username TEXT PRIMARY KEY,
            room_id INTEGER,
            last_typing INTEGER
        )
    """)
    
    # Messages
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
    
    # Admin
    c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    """)
    # Default admin
    c.execute("INSERT OR IGNORE INTO admins (username,password) VALUES ('admin','admin123')")
    
    conn.commit()
    conn.close()

init_db()

# ================= ACTIVE USERS =================
def update_active_user(session_id, username, room_id):
    now = int(time.time())
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO active_users (session_id, username, room_id, last_seen)
        VALUES (?,?,?,?)
        ON CONFLICT(session_id)
        DO UPDATE SET username=excluded.username, room_id=excluded.room_id, last_seen=excluded.last_seen
    """, (session_id, username, room_id, now))
    conn.commit()
    conn.close()

def remove_inactive_users(timeout=30):
    now = int(time.time())
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("DELETE FROM active_users WHERE ? - last_seen > ?", (now, timeout))
    c.execute("DELETE FROM typing_users WHERE ? - last_typing > ?", (now, timeout))
    conn.commit()
    conn.close()

def get_online_users(room_id):
    now = int(time.time())
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        SELECT username FROM active_users
        WHERE room_id=? AND ? - last_seen <= 30
    """, (room_id, now))
    users = [r[0] for r in c.fetchall()]
    conn.close()
    return users

# ================= TYPING =================
def set_typing(username, room_id):
    now = int(time.time())
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO typing_users (username, room_id, last_typing)
        VALUES (?,?,?)
        ON CONFLICT(username)
        DO UPDATE SET last_typing=excluded.last_typing, room_id=excluded.room_id
    """, (username, room_id, now))
    conn.commit()
    conn.close()

def get_typing_users(room_id, current_user):
    now = int(time.time())
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        SELECT username FROM typing_users
        WHERE room_id=? AND ? - last_typing <= 4 AND username != ?
    """, (room_id, now, current_user))
    users = [r[0] for r in c.fetchall()]
    conn.close()
    return users

# ================= MESSAGES =================
def add_text_message(room_id, user, message):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO messages (room_id, user, message, msg_type, timestamp)
        VALUES (?,?,?,?,?)
    """, (room_id, user, message, 'text', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def add_file_message(room_id, user, file):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO messages (room_id, user, msg_type, file_name, file_data, timestamp)
        VALUES (?,?,?,?,?,?)
    """, (room_id, user, 'file', file.name, file.getvalue(), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_messages(room_id):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("""
        SELECT user, message, msg_type, file_name, file_data, timestamp
        FROM messages
        WHERE room_id=?
        ORDER BY id
    """, (room_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def clear_messages(room_id):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE room_id=?", (room_id,))
    conn.commit()
    conn.close()

# ================= ROOMS =================
def create_room(room_name, password):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("INSERT INTO rooms (room_name, room_password) VALUES (?,?)", (room_name, password))
    conn.commit()
    conn.close()

def get_rooms():
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("SELECT room_id, room_name FROM rooms ORDER BY room_name")
    rooms = c.fetchall()
    conn.close()
    return rooms

def verify_room_password(room_id, password):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("SELECT 1 FROM rooms WHERE room_id=? AND room_password=?", (room_id, password))
    valid = c.fetchone() is not None
    conn.close()
    return valid

# ================= STREAMLIT UI =================
st.set_page_config(page_title="💬 Private Team Chat", layout="wide")
remove_inactive_users()  # cleanup inactive users

st.title("💬 Private Team Chat")

# ===== Room selection / creation =====
rooms = get_rooms()
room_names = [r[1] for r in rooms]
selected_room = st.sidebar.selectbox("Select Room", ["--Create New--"] + room_names)

room_id = None
room_password_input = ""

if selected_room == "--Create New--":
    new_room_name = st.sidebar.text_input("Room Name")
    new_room_password = st.sidebar.text_input("Room Password", type="password")
    if st.sidebar.button("Create Room"):
        if new_room_name and new_room_password:
            try:
                create_room(new_room_name, new_room_password)
                st.success("Room created!")
                st.experimental_rerun()
            except:
                st.error("Room name already exists")
else:
    # Existing room
    room_id = next((r[0] for r in rooms if r[1]==selected_room), None)
    room_password_input = st.sidebar.text_input("Room Password", type="password")
    if st.sidebar.button("Join Room"):
        if room_id and verify_room_password(room_id, room_password_input):
            st.session_state['room_id'] = room_id
            st.session_state['username'] = st.sidebar.text_input("Your Name")
            st.experimental_rerun()
        else:
            st.sidebar.error("Incorrect password!")

# ===== Once room joined =====
if "room_id" in st.session_state and "username" in st.session_state and st.session_state['username']:
    room_id = st.session_state['room_id']
    username = st.session_state['username']
    
    update_active_user(st.session_state.session_id, username, room_id)
    
    st.sidebar.markdown(f"🟢 **{len(get_online_users(room_id))} Users Online**")
    for u in get_online_users(room_id):
        st.sidebar.markdown(f"• {u}")
    
    msg = st.sidebar.text_area("", placeholder="Type a message...")
    if msg.strip():
        set_typing(username, room_id)
    
    if st.sidebar.button("Send"):
        if msg.strip():
            add_text_message(room_id, username, msg)
    
    file = st.sidebar.file_uploader("Attach file", type=["png","jpg","jpeg","pdf","docx"])
    if st.sidebar.button("Send File") and file:
        add_file_message(room_id, username, file)
    
    # Typing indicator
    typing_users = get_typing_users(room_id, username)
    if typing_users:
        st.caption("✍️ " + ", ".join(typing_users) + " typing…")
    
    # Chat messages display
    msgs = get_messages(room_id)
    html = "<div style='max-width:900px;height:600px;overflow:auto;margin:auto;'>"
    for u,m,t,f,fd,ts in msgs:
        me = u==username
        bg = "#0084ff" if me else "#e5e5ea"
        col = "white" if me else "black"
        if t=="text":
            content = m
        elif f.lower().endswith(("png","jpg","jpeg")):
            img = base64.b64encode(fd).decode()
            content = f"<img src='data:image/png;base64,{img}' width=200>"
        else:
            b = base64.b64encode(fd).decode()
            content = f"<a download='{f}' href='data:;base64,{b}'>{f}</a>"
        html += f"<div style='background:{bg};color:{col};padding:10px;border-radius:14px;margin:6px;max-width:65%;{'margin-left:auto;' if me else ''}'>{u}<br>{content}<div style='font-size:10px;opacity:.6'>{ts}</div></div>"
    html += "</div><script>document.querySelector('div').scrollTop=999999</script>"
    st.components.v1.html(html, height=650)
else:
    st.info("🔒 Join a room with password to view or send messages.")
