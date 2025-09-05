import streamlit as st
import sqlite3
from datetime import datetime

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
    return messages[::-1]  # show oldest first

# --- STREAMLIT APP ---
st.set_page_config(page_title="💬 Team Chatbox", layout="centered")
st.title("💬 Team Chatbox")

# Initialize DB
init_db()

# User input
username = st.text_input("Your Name", key="username")
message = st.text_input("Enter Message", key="message")

col1, col2 = st.columns([1,1])
with col1:
    if st.button("Send"):
        if username and message:
            add_message(username, message)
            st.rerun()

with col2:
    if st.button("Refresh"):
        st.rerun()


# Display chat history
st.subheader("📜 Chat History")
messages = get_messages()
for user, msg, ts in messages:
    st.write(f"**{user}** [{ts}]: {msg}")
