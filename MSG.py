import streamlit as st
import sqlite3
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import base64
import random
import string

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect("chatbox.db", check_same_thread=False)
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
    
    # Ensure a default row exists for video call
    c.execute("SELECT COUNT(*) FROM video_call")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO video_call (id, room_name, started) VALUES (1, '', 0)")
    
    conn.commit()
    conn.close()

# ================= MESSAGE FUNCTIONS =================
def add_text_message(user, message):
    conn = sqlite3.connect("chatbox.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("""
        INSERT INTO messages (user, message, msg_type, timestamp)
        VALUES (?, ?, 'text', ?)
    """, (user, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def add_file_message(user, file):
    conn = sqlite3.connect("chatbox.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("""
        INSERT INTO messages (user, msg_type, file_name, file_data, timestamp)
        VALUES (?, 'file', ?, ?, ?)
    """, (user, file.name, file.getvalue(), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_messages():
    conn = sqlite3.connect("chatbox.db", check_same_thread=False)
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
    conn = sqlite3.connect("chatbox.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM messages")
    conn.commit()
    conn.close()

# ================= VIDEO CALL FUNCTIONS =================
def start_video_call(room_name):
    conn = sqlite3.connect("chatbox.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("UPDATE video_call SET room_name = ?, started = 1 WHERE id = 1", (room_name,))
    conn.commit()
    conn.close()

def end_video_call():
    conn = sqlite3.connect("chatbox.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("UPDATE video_call SET room_name = '', started = 0 WHERE id = 1")
    conn.commit()
    conn.close()

def get_video_call_status():
    conn = sqlite3.connect("chatbox.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT room_name, started FROM video_call WHERE id = 1")
    row = c.fetchone()
    conn.close()
    return row

# ================= STREAMLIT SETUP =================
st.set_page_config(page_title="Team Chatbox", layout="wide")
init_db()

# ================= SIDEBAR =================
st.sidebar.title("User Settings")
username = st.sidebar.text_input("Your Name", placeholder="Enter your name...")

if st.sidebar.button("Clear Chat"):
    clear_messages()
    st.experimental_rerun()

st.sidebar.markdown("### Message")

# ---------------- Textbox ----------------
msg_text = st.sidebar.text_area(
    "",
    height=60,
    key="chat_msg",
    placeholder="Type message..."
)

# ---------------- Send button ----------------
if st.sidebar.button("Send", use_container_width=True):
    if username and msg_text.strip():
        add_text_message(username, msg_text.strip())
        st.session_state.chat_msg = ""
        st.experimental_rerun()

# ---------------- File uploader ----------------
uploaded_file = st.sidebar.file_uploader(
    "Attach image or file",
    type=["png", "jpg", "jpeg", "pdf", "docx"]
)

if st.sidebar.button("Send File"):
    if username and uploaded_file:
        add_file_message(username, uploaded_file)
        st.experimental_rerun()

# ================= AUTO REFRESH =================
st_autorefresh(interval=3000, key="chat_refresh")

# ================= VIDEO CALL =================
st.title("Team Chatbox")
room_name, started = get_video_call_status()

if started == 0:
    if st.button("Start Video Call"):
        room_name = "TeamChat_" + ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        start_video_call(room_name)
        js = f"window.open('https://meet.jit.si/{room_name}', '_blank')"
        st.components.v1.html(f"<script>{js}</script>", height=0)
else:
    st.markdown(f"### Video Call Active: Room `{room_name}`")
    st.markdown(f"[Join Video Call in New Tab](https://meet.jit.si/{room_name})", unsafe_allow_html=True)
    st.info("Click the link to join the video call in a new tab.")
    if st.button("End Video Call"):
        end_video_call()
        st.experimental_rerun()

# ================= CHAT DISPLAY =================
messages = get_messages()

chat_html = """
<style>
.chat-container { display: flex; justify-content: center; }
.chat-box { width: 100%; max-width: 900px; height: 600px; padding: 14px; border: 1px solid #ddd; border-radius: 14px; background: #ffffff; font-family: Segoe UI; overflow-y: auto; }
.message-wrapper { display: flex; align-items: flex-start; margin: 6px 0; }
.message-wrapper.right { justify-content: flex-end; }
.message-wrapper.left { justify-content: flex-start; }
.message { padding: 10px 14px; border-radius: 18px; max-width: 65%; font-size: 14px; line-height: 1.4; word-wrap: break-word; }
.user { background: #0084ff; color: white; border-bottom-right-radius: 0; }
.other { background: #e5e5ea; color: black; border-bottom-left-radius: 0; }
.timestamp { font-size: 10px; opacity: 0.6; margin-top: 4px; text-align: right; }
.user-icon { width: 32px; height: 32px; border-radius: 50%; background: #ccc; color: white; font-weight: bold; display: flex; align-items: center; justify-content: center; margin: 0 8px; flex-shrink: 0; }
</style>

<div class="chat-container">
<div class="chat-box" id="chatBox">
"""

for user, msg, mtype, fname, fdata, ts in messages:
    is_me = user == username
    wrapper_cls = "right" if is_me else "left"
    msg_cls = "user" if is_me else "other"
    initials = "".join([x[0] for x in user.split()][:2]).upper()

    if mtype == "text":
        content = msg
    else:
        if fname.lower().endswith(("png", "jpg", "jpeg")):
            img64 = base64.b64encode(fdata).decode()
            content = f'<img src="data:image/png;base64,{img64}" style="max-width:260px;border-radius:12px;">'
        else:
            file64 = base64.b64encode(fdata).decode()
            content = f'<a download="{fname}" href="data:application/octet-stream;base64,{file64}">Download {fname}</a>'

    if is_me:
        chat_html += f"""
        <div class="message-wrapper {wrapper_cls}">
            <div class="message {msg_cls}">
                <b>{user}</b><br>{content}
                <div class="timestamp">{ts}</div>
            </div>
            <div class="user-icon">{initials}</div>
        </div>
        """
    else:
        chat_html += f"""
        <div class="message-wrapper {wrapper_cls}">
            <div class="user-icon">{initials}</div>
            <div class="message {msg_cls}">
                <b>{user}</b><br>{content}
                <div class="timestamp">{ts}</div>
            </div>
        </div>
        """

chat_html += """
<div id="end"></div>
</div>
</div>

<script>
const chatBox = document.getElementById("chatBox");
if (chatBox) {
    chatBox.scrollTop = chatBox.scrollHeight;
    const observer = new MutationObserver(() => {
        chatBox.scrollTop = chatBox.scrollHeight;
    });
    observer.observe(chatBox, { childList: true, subtree: true });
}
</script>
"""

st.components.v1.html(chat_html, height=650, scrolling=False)
