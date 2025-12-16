# ================= VIDEO CALL =================
st.title("💬 Team Chatbox")

# Check video call status
room_name, started = get_video_call_status()

if started == 0:
    if st.button("📹 Start Video Call"):
        # Generate random room name
        room_name = "TeamChat_" + ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        start_video_call(room_name)
        # Open the room in a new tab
        js = f"window.open('https://meet.jit.si/{room_name}', '_blank')"
        st.components.v1.html(f"<script>{js}</script>", height=0)
else:
    st.markdown(f"### 📹 Video Call Active: Room `{room_name}`")
    st.markdown(
        f"[Join Video Call in New Tab](https://meet.jit.si/{room_name})",
        unsafe_allow_html=True
    )
    st.info(f"Click the link to join the video call in a new tab.")

    # End call button
    if st.button("🛑 End Call"):
        # Reset video call status in DB
        conn = sqlite3.connect("chatbox.db", check_same_thread=False)
        c = conn.cursor()
        c.execute("UPDATE video_call SET started = 0, room_name = '' WHERE id = 1")
        conn.commit()
        conn.close()
        st.experimental_rerun()

