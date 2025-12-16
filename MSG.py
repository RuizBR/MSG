import streamlit as st
import sqlite3
from datetime import datetime
import base64
import hashlib
from streamlit_autorefresh import st_autorefresh

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect("chatbox.db", check_same_thread=False)
    c = conn.cursor()
    
    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    
    # Messages table (private conversations)
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            receiver TEXT,
            message TEXT,
            msg_type TEXT,
            file_name TEXT,
            file_data BLOB,
            timestamp TEXT
        )
    """)
    
    conn.commit()
    conn.close()

init_db()

# ================= AUTH FUNCTIONS =================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    conn = sqlite3.connect("chatbox.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect("chatbox.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    return result and result[0] == hash_password(password)

# ================= MESSAGE FUNCTIONS =================
def send_message(sender, receiver, message, msg_type="text", file=None):
    conn = sqlite3.connect("chatbox.db", check_same_thread=False)
    c = conn.cursor()
    if msg_type == "text":
        c.execute("""INSERT INTO messages 
                     (sender, receiver, message, msg_type, timestamp)
                     VALUES (?, ?, ?, ?, ?)""",
                  (sender, receiver, message, msg_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    elif msg_type == "file" and file:
        c.execute("""INSERT INTO messages 
                     (sender, receiver, msg_type, file_name, file_data, timestamp)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (sender, receiver, msg_type, file.name, file.getvalue(), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_conversation(user1, user2):
    conn = sqlite3.connect("chatbox.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("""SELECT sender, message, msg_type, file_name, file_data, timestamp 
                 FROM messages 
                 WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?)
                 ORDER BY id ASC""", (user1, user2, user2, user1))
    rows = c.fetchall()
    conn.close()
    return rows

# ================= STREAMLIT SETUP =================
st.set_page_config(page_title="💬 Private Chatbox", layout="wide")

# ================= SESSION STATE =================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
if 'just_logged_in' not in st.session_state:
    st.session_state.just_logged_in = False

# ================= SIDEBAR =================
st.sidebar.title("💬 Private Chatbox")

# ---------------- LOGOUT ----------------
if st.session_state.logged_in:
    if st.sidebar.button("🔓 Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.experimental_rerun()

# ---------------- LOGIN / REGISTER ----------------
if not st.session_state.logged_in:
    mode = st.sidebar.radio("Mode", ["Login", "Register"])
    username_input = st.sidebar.text_input("Username")
    password_input = st.sidebar.text_input("Password", type="password")

    if st.sidebar.button(mode):
        if username_input and password_input:
            if mode == "Register":
                if register_user(username_input, password_input):
                    st.sidebar.success("Registered successfully! You can now login.")
                else:
                    st.sidebar.error("Username already exists.")
            elif mode == "Login":
                if login_user(username_input, password_input):
                    st.session_state.logged_in = True
                    st.session_state.username = username_input
                    st.session_state.just_logged_in = True  # trigger next run safely
                else:
                    st.sidebar.error("Invalid username or password.")

# ---------------- AFTER LOGIN SAFE ----------------
if st.session_state.get("just_logged_in", False):
    st.session_state.just_logged_in = False  # reset flag
    st.experimental_rerun()  # safe rerun after session state update

# ---------------- CHAT INTERFACE ----------------
if st.session_state.logged_in:
    st.sidebar.info(f"Logged in as: {st.session_state.username}")
    
    # List users to chat with
    conn = sqlite3.connect("chatbox.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE username != ?", (st.session_state.username,))
    users = [row[0] for row in c.fetchall()]
    conn.close()
    
    if not users:
        st.warning("No other users available to chat.")
    else:
        chat_with = st.sidebar.selectbox("Chat with:", users)
        
        # Textbox + Send button under
        msg_text = st.sidebar.text_area("", height=60, key="chat_msg")
        if st.sidebar.button("Send"):
            if msg_text.strip():
                send_message(st.session_state.username, chat_with, msg_text.strip())
                st.experimental_rerun()
        
        # File uploader + Send File
        uploaded_file = st.sidebar.file_uploader("📎 Attach image or file", type=["png","jpg","jpeg","pdf","docx"])
        if st.sidebar.button("Send File"):
            if uploaded_file:
                send_message(st.session_state.username, chat_with, None, msg_type="file", file=uploaded_file)
                st.experimental_rerun()
        
        # ================= AUTO REFRESH =================
        st_autorefresh(interval=3000, key="chat_refresh")
        
        # ================= CHAT DISPLAY =================
        st.title(f"💬 Chat with {chat_with}")
        messages = get_conversation(st.session_state.username, chat_with)
        
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
        <div class="chat-container"><div class="chat-box" id="chatBox">
        """
        
        for sender, msg, mtype, fname, fdata, ts in messages:
            is_me = sender == st.session_state.username
            wrapper_cls = "right" if is_me else "left"
            msg_cls = "user" if is_me else "other"
            initials = "".join([x[0] for x in sender.split()][:2]).upper()
            
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
                        <b>{sender}</b><br>{content}
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
                        <b>{sender}</b><br>{content}
                        <div class="timestamp">{ts}</div>
                    </div>
                </div>
                """
        
        chat_html += """
        <div id="end"></div></div></div>
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
