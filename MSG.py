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
    c.execute("INSERT INTO messages (user, message, timestamp) VALUES (?, ?, ?)",
              (user, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_messages():
    conn = sqlite3.connect("chatbox.db")
    c = conn.cursor()
    c.execute("SELECT user, message, timestamp FROM messages ORDER BY id DESC LIMIT 50")
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

# Sidebar for username
st.sidebar.title("👤 User Settings")
username = st.sidebar.text_input("Your Name", key="username", placeholder="Enter your name...")

if st.sidebar.button("🗑️ Clear Chat"):
    clear_messages()
    st.rerun()

# Auto-refresh every 5 seconds
st_autorefresh(interval=5000, limit=None, key="chat_refresh")

# Initialize DB
init_db()

st.title("💬 Team Chatbox")

# --- Chat History ---
messages = get_messages()
chat_html = """
<style>
.chat-box {
    height: 450px;
    overflow-y: auto;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 10px;
    background-color: #f9f9f9;
    display: flex;
    flex-direction: column;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
.message {
    margin: 8px;
    padding: 10px 14px;
    border-radius: 15px;
    max-width: 70%;
    word-wrap: break-word;
    font-size: 15px;
}
.message.user {
    background-color: #0084ff;
    color: white;
    align-self: flex-end;
    text-align: right;
}
.message.other {
    background-color: #e5e5ea;
    color: black;
    align-self: flex-start;
    text-align: left;
}
.timestamp {
    font-size: 10px;
    color: gray;
    margin-top: 4px;
}
</style>
<div class="chat-box">
"""

for user, msg, ts in messages:
    if user == username:
        chat_html += f"""
        <div class="message user">
            {msg}
            <div class="timestamp">{ts}</div>
        </div>
        """
    else:
        chat_html += f"""
        <div class="message other">
            <b>{user}</b><br>{msg}
            <div class="timestamp">{ts}</div>
        </div>
        """

chat_html += """
<div id="end"></div>
<script>
    var chatBox = window.parent.document.querySelector('.chat-box');
    if (chatBox) { chatBox.scrollTop = chatBox.scrollHeight; }
</script>
</div>
"""

st.components.v1.html(chat_html, height=450, scrolling=True)

# --- Input at Bottom ---
st.markdown("### 💬 Type a message")
input_col1, input_col2 = st.columns([6,1])
with input_col1:
    message = st.text_input("Message", key="message", label_visibility="collapsed", placeholder="Type your message...")
with input_col2:
    if st.button("Send"):
        if username and message.strip():
            add_message(username, message.strip())
            st.rerun()
