import streamlit as st
import sqlite3
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            message TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_message(user, message):
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (user, message, timestamp) VALUES (?, ?, ?)",
        (user, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

def get_messages():
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute(
        "SELECT user, message, timestamp FROM messages ORDER BY id DESC LIMIT 50"
    )
    messages = c.fetchall()
    conn.close()
    return messages[::-1]

def clear_messages():
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("DELETE FROM messages")
    conn.commit()
    conn.close()

# --- STREAMLIT APP ---
st.set_page_config(page_title="💬 Team Chatbox", layout="wide")

# --- Sidebar: user settings + input ---
st.sidebar.title("👤 User Settings")
username = st.sidebar.text_input("Your Name", key="username", placeholder="Enter your name...")

if st.sidebar.button("🗑️ Clear Chat"):
    clear_messages()
    st.rerun()

st.sidebar.markdown("### 💬 Type a message")
msg_key = "chat_input"
message = st.sidebar.text_area(
    "",
    key=msg_key,
    label_visibility="collapsed",
    placeholder="Type a message... (Enter = Send, Shift+Enter = New Line)",
    height=70
)

def send_message():
    if username and st.session_state[msg_key].strip():
        add_message(username, st.session_state[msg_key].strip())
        st.session_state[msg_key] = ""
        

st.sidebar.button("Send", key="send_button", use_container_width=True, on_click=send_message)

# --- Auto-refresh chat ---
st_autorefresh(interval=5000, limit=None, key="chat_refresh")

# --- Initialize DB ---
init_db()

st.title("💬 Team Chatbox")

# --- Chat History on main page ---
messages = get_messages()
chat_html = """
<style>
.chat-container {
    display: flex;
    flex-direction: column;
}
.chat-box {
    padding: 6px;
    border: 1px solid #ddd;
    border-radius: 10px;
    background-color: #ffffff;
    display: flex;
    flex-direction: column;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
.message {
    display: flex;
    align-items: flex-start;
    margin: 4px 0;
    padding: 8px 12px;
    border-radius: 15px;
    max-width: 85%;
    word-wrap: break-word;
    font-size: 14px;
    line-height: 1.3;
}
.message.user {
    background-color: #0084ff;
    color: white;
    align-self: flex-end;
    text-align: right;
    flex-direction: row-reverse;
}
.message.other {
    background-color: #e5e5ea;
    color: black;
    align-self: flex-start;
    text-align: left;
}
.user-icon {
    display: inline-block;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background-color: #888;
    color: white;
    text-align: center;
    line-height: 24px;
    font-size: 14px;
    margin-right: 8px;
}
.message.user .user-icon {
    margin-left: 8px;
    margin-right: 0;
}
.timestamp {
    font-size: 10px;
    color: gray;
    margin-top: 2px;
}
</style>

<div class="chat-container">
    <div class="chat-box" id="chatBox">
"""

for idx, (user, msg, ts) in enumerate(messages):
    icon = user[0].upper() if user else "?"
    if user == username:
        chat_html += f"""
        <div class="message user" id="msg-{idx}">
            <span class="user-icon">{icon}</span>
            {msg}
            <div class="timestamp">{ts}</div>
        </div>
        """
    else:
        chat_html += f"""
        <div class="message other" id="msg-{idx}">
            <span class="user-icon">{icon}</span>
            <b>{user}</b><br>{msg}
            <div class="timestamp">{ts}</div>
        </div>
        """

chat_html += """
        <div id="end"></div>
    </div>
</div>
<script>
let chatBox = document.getElementById("chatBox");
let endMarker = document.getElementById("end");
endMarker.scrollIntoView({behavior: "smooth", block: "end"});
</script>
"""

st.components.v1.html(chat_html, height=800, scrolling=False)  # main page expands naturally

# --- JS for Enter = Send in sidebar ---
st.markdown("""
<script>
const textarea = window.parent.document.querySelector('textarea');
if (textarea) {
    textarea.addEventListener('keydown', function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            const sendBtn = window.parent.document.querySelector('button[kind="secondary"]');
            if (sendBtn) sendBtn.click();
        }
    });
}
</script>
""", unsafe_allow_html=True)
