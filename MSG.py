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
    conn.commit()
    conn.close()


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
    """, (
        user,
        file.name,
        file.getvalue(),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
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


# ================= STREAMLIT SETUP =================
st.set_page_config(page_title="💬 Team Chatbox", layout="wide")
init_db()

# ================= SIDEBAR =================
st.sidebar.title("👤 User Settings")
username = st.sidebar.text_input("Your Name", placeholder="Enter your name...")

if st.sidebar.button("🗑️ Clear Chat"):
    clear_messages()
    st.rerun()

st.sidebar.markdown("### 💬 Message")
st.text_area(
    "",
    placeholder="Type message...",
    height=70,
    key="chat_msg"
)

uploaded_file = st.sidebar.file_uploader(
    "📎 Attach image or file",
    type=["png", "jpg", "jpeg", "pdf", "docx"]
)

def send_text():
    if username and st.session_state.chat_msg.strip():
        add_text_message(username, st.session_state.chat_msg.strip())
        st.session_state.chat_msg = ""

def send_file():
    if username and uploaded_file:
        add_file_message(username, uploaded_file)

c1, c2 = st.sidebar.columns(2)
c1.button("Send", on_click=send_text, use_container_width=True)
c2.button("Send File", on_click=send_file, use_container_width=True)

# ================= AUTO REFRESH =================
st_autorefresh(interval=4000, key="chat_refresh")

# ================= VIDEO CALL =================
st.sidebar.markdown("---")
st.sidebar.markdown("### 📹 Video Call")

# Persistent video call state
if "video_call_started" not in st.session_state:
    st.session_state.video_call_started = False

if "jitsi_room" not in st.session_state:
    st.session_state.jitsi_room = "TeamChat_" + "".join(
        random.choices(string.ascii_letters + string.digits, k=6)
    )

# Button to start video call
if st.sidebar.button("Start Video Call"):
    st.session_state.video_call_started = True

# Show video call iframe if started
if st.session_state.video_call_started:
    room_name = st.session_state.jitsi_room
    st.sidebar.markdown(f"""
    <iframe src="https://meet.jit.si/{room_name}" 
            style="width:100%; height:400px; border:0;">
    </iframe>
    """, unsafe_allow_html=True)
    st.sidebar.info(f"Video call started in room: {room_name}")

# ================= CHAT DISPLAY =================
st.title("💬 Team Chatbox")
messages = get_messages()

chat_html = """
<style>
.chat-container { display: flex; justify-content: center; }
.chat-box {
    width: 100%;
    max-width: 900px;
    height: 600px;
    padding: 14px;
    border: 1px solid #ddd;
    border-radius: 14px;
    background: #ffffff;
    font-family: Segoe UI;
    overflow-y: auto;
}
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
            content = f'<a download="{fname}" href="data:application/octet-stream;base64,{file64}">📎 {fname}</a>'

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

    let isUserScrolling = false;
    chatBox.addEventListener('scroll', () => {
        const nearBottom = chatBox.scrollHeight - chatBox.scrollTop - chatBox.clientHeight < 50;
        isUserScrolling = !nearBottom;
    });

    const observer = new MutationObserver(() => {
        if (!isUserScrolling) return;
        chatBox.scrollTop = chatBox.scrollHeight;
    });

    observer.observe(chatBox, { childList: true, subtree: true });
}
</script>
"""

st.components.v1.html(chat_html, height=650, scrolling=False)

# ================= ENTER = SEND =================
st.markdown("""
<script>
const textarea = window.parent.document.querySelector('textarea');
if (textarea) {
    textarea.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            document.querySelector('button').click();
        }
    });
}
</script>
""", unsafe_allow_html=True)
