import streamlit as st
import sqlite3
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import base64

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

uploaded_file = st.sidebar.file_uploader(
    "📎 Attach image or file",
    type=["png", "jpg", "jpeg", "pdf", "docx"]
)

# ================= AUTO REFRESH =================
st_autorefresh(interval=4000, key="chat_refresh")

# ================= CHAT DISPLAY =================
st.title("💬 Team Chatbox")
messages = get_messages()

chat_html = """
<style>
.chat-wrapper {
    display: flex;
    justify-content: center;
}
.chat-box {
    width: 100%;
    max-width: 900px;
    height: 550px;
    padding: 14px;
    border: 1px solid #ddd;
    border-radius: 14px;
    background: #ffffff;
    font-family: Segoe UI;
    overflow-y: auto;
}
.message {
    margin: 6px 0;
    padding: 10px 14px;
    border-radius: 18px;
    max-width: 75%;
    font-size: 14px;
    line-height: 1.4;
}
.user {
    background: #0084ff;
    color: white;
    margin-left: auto;
}
.other {
    background: #e5e5ea;
    color: black;
    margin-right: auto;
}
.timestamp {
    font-size: 10px;
    opacity: 0.6;
    margin-top: 4px;
}
</style>

<div class="chat-wrapper">
<div class="chat-box" id="chatBox">
"""

for user, msg, mtype, fname, fdata, ts in messages:
    cls = "user" if user == username else "other"

    if mtype == "text":
        content = msg
    else:
        if fname.lower().endswith(("png", "jpg", "jpeg")):
            img64 = base64.b64encode(fdata).decode()
            content = f"""
            <img src="data:image/png;base64,{img64}"
                 style="max-width:260px;border-radius:12px;">
            """
        else:
            file64 = base64.b64encode(fdata).decode()
            content = f"""
            <a download="{fname}"
               href="data:application/octet-stream;base64,{file64}">
               📎 {fname}
            </a>
            """

    chat_html += f"""
    <div class="message {cls}">
        <b>{user}</b><br>
        {content}
        <div class="timestamp">{ts}</div>
    </div>
    """

chat_html += """
</div>
</div>

<script>
const chatBox = document.getElementById("chatBox");
if (chatBox) {
    const nearBottom =
        chatBox.scrollHeight - chatBox.scrollTop - chatBox.clientHeight < 120;
    if (nearBottom) {
        chatBox.scrollTop = chatBox.scrollHeight;
    }
}
</script>
"""

st.components.v1.html(chat_html, height=600, scrolling=False)

# ================= FIXED INPUT BAR =================
st.markdown("<hr>", unsafe_allow_html=True)

input_col, send_col = st.columns([6, 1])

with input_col:
    st.text_input(
        "",
        placeholder="Type a message...",
        key="chat_msg",
        label_visibility="collapsed"
    )

with send_col:
    if st.button("Send", use_container_width=True):
        if username and st.session_state.chat_msg.strip():
            add_text_message(username, st.session_state.chat_msg.strip())
            st.session_state.chat_msg = ""
            st.rerun()

# ================= ENTER = SEND =================
st.markdown("""
<script>
const input = window.parent.document.querySelector('input');
if (input) {
    input.addEventListener('keydown', e => {
        if (e.key === 'Enter') {
            e.preventDefault();
            document.querySelector('button').click();
        }
    });
}
</script>
""", unsafe_allow_html=True)
