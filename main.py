import streamlit as st
import pandas as pd
import os
try:
    import bcrypt
except ImportError as e:
    st.error(f"Không thể import bcrypt: {e}")
from io import StringIO
try:
    from sqlalchemy import create_engine, exc, text
except ImportError as e:
    st.error(f"Không thể import sqlalchemy: {e}")
from PIL import Image
from datetime import datetime

# Set the title of the web app
st.set_page_config(page_title="Ứng Dụng Nghe Nhạc", page_icon="🎵", layout="wide")
st.title("🎵 Ứng Dụng Nghe Nhạc Cao Cấp 🎵")

# Custom CSS
st.markdown("""
    <style>
    .main {
        background-color: #f0f2f6;
    }
    .sidebar .sidebar-content {
        background-color: #2e3b4e;
        color: white;
    }
    .sidebar .sidebar-content a {
        color: #f0f2f6;
    }
    .sidebar .sidebar-content a:hover {
        color: #ff4b4b;
    }
    .stButton>button {
        background-color: #ff4b4b;
        color: white;
        border-radius: 5px;
    }
    .stButton>button:hover {
        background-color: #ff1a1a;
    }
    .stTextInput>div>div>input {
        border-radius: 5px;
    }
    .stCheckbox>div>div>input {
        border-radius: 5px;
    }
    .stImage>img {
        border-radius: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# Database connection
DATABASE_URL = "sqlite:///music_app.db"
try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                full_name TEXT,
                email TEXT,
                username TEXT PRIMARY KEY,
                password TEXT,
                avatar TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS playlists (
                username TEXT,
                playlist_name TEXT,
                songs TEXT,
                public BOOLEAN
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS activity_log (
                username TEXT,
                activity TEXT,
                timestamp TEXT
            )
        """))
except exc.SQLAlchemyError as e:
    st.error(f"Không thể kết nối đến cơ sở dữ liệu: {e}")

# Ensure avatar folder exists
AVATAR_FOLDER = "avatars"
if not os.path.exists(AVATAR_FOLDER):
    os.makedirs(AVATAR_FOLDER)

# Define media files
IMAGE_FILE = "BuonHayVui.jpg"
AUDIO_FILE = "buonhayvui.mp3"

# Load user data
def load_user_data():
    try:
        return pd.read_sql("SELECT * FROM users", engine)
    except exc.SQLAlchemyError as e:
        st.error(f"Lỗi khi tải dữ liệu người dùng: {e}")
        return pd.DataFrame(columns=["full_name", "email", "username", "password", "avatar"])

# Save user data
def save_user_data(data):
    try:
        data.to_sql("users", engine, if_exists="replace", index=False)
    except exc.SQLAlchemyError as e:
        st.error(f"Lỗi khi lưu dữ liệu người dùng: {e}")

# Load playlist data
def load_playlist_data():
    try:
        return pd.read_sql("SELECT * FROM playlists", engine)
    except exc.SQLAlchemyError as e:
        st.error(f"Lỗi khi tải dữ liệu playlist: {e}")
        return pd.DataFrame(columns=["username", "playlist_name", "songs", "public"])

# Save playlist data
def save_playlist_data(data):
    try:
        data.to_sql("playlists", engine, if_exists="replace", index=False)
    except exc.SQLAlchemyError as e:
        st.error(f"Lỗi khi lưu dữ liệu playlist: {e}")

# Load activity log
def load_activity_log():
    try:
        return pd.read_sql("SELECT * FROM activity_log", engine)
    except exc.SQLAlchemyError as e:
        st.error(f"Lỗi khi tải dữ liệu nhật ký hoạt động: {e}")
        return pd.DataFrame(columns=["username", "activity", "timestamp"])

# Save activity log
def save_activity_log(data):
    try:
        data.to_sql("activity_log", engine, if_exists="replace", index=False)
    except exc.SQLAlchemyError as e:
        st.error(f"Lỗi khi lưu dữ liệu nhật ký hoạt động: {e}")

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

# User authentication   
user_data = load_user_data()
playlist_data = load_playlist_data()
activity_log = load_activity_log()

def login(username, password):
    user = user_data[(user_data["username"] == username)]
    if not user.empty and bcrypt.checkpw(password.encode(), user.iloc[0]["password"].encode()):
        st.session_state.logged_in = True
        st.session_state.username = username
        log_activity(username, "Đăng nhập")
        return True
    return False

def register(full_name, email, username, password):
    if username in user_data["username"].values:
        return False
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    new_user = pd.DataFrame([[full_name, email, username, hashed_password, ""]], columns=["full_name", "email", "username", "password", "avatar"])
    updated_user_data = pd.concat([user_data, new_user], ignore_index=True)
    save_user_data(updated_user_data)
    log_activity(username, "Đăng ký")
    return True

def create_playlist(username, playlist_name, public=False):
    if not playlist_name:
        st.error("Tên playlist không được để trống.")
        return False
    if playlist_name in playlist_data[playlist_data["username"] == username]["playlist_name"].values:
        return False
    new_playlist = pd.DataFrame([[username, playlist_name, "", public]], columns=["username", "playlist_name", "songs", "public"])
    updated_playlist_data = pd.concat([playlist_data, new_playlist], ignore_index=True)
    save_playlist_data(updated_playlist_data)
    log_activity(username, f"Tạo playlist '{playlist_name}'")
    return True

def add_song_to_playlist(username, playlist_name, song):
    if not song:
        st.error("Tên bài hát không được để trống.")
        return False
    playlist = playlist_data[(playlist_data["username"] == username) & (playlist_data["playlist_name"] == playlist_name)]
    if not playlist.empty:
        songs = playlist.iloc[0]["songs"]
        if songs:
            songs += f",{song}"
        else:
            songs = song
        playlist_data.loc[(playlist_data["username"] == username) & (playlist_data["playlist_name"] == playlist_name), "songs"] = songs
        save_playlist_data(playlist_data)
        log_activity(username, f"Thêm bài hát '{song}' vào playlist '{playlist_name}'")
        return True
    return False

def delete_playlist(username, playlist_name):
    global playlist_data
    playlist_data = playlist_data[~((playlist_data["username"] == username) & (playlist_data["playlist_name"] == playlist_name))]
    save_playlist_data(playlist_data)
    log_activity(username, f"Xóa playlist '{playlist_name}'")

def share_playlist(username, playlist_name):
    # Dummy share function, replace with actual share logic
    return f"https://example.com/share/{username}/{playlist_name}"

def edit_playlist(username, playlist_name, new_name, public):
    if not new_name:
        st.error("Tên playlist không được để trống.")
        return
    playlist_data.loc[(playlist_data["username"] == username) & (playlist_data["playlist_name"] == playlist_name), ["playlist_name", "public"]] = new_name, public
    save_playlist_data(playlist_data)
    log_activity(username, f"Chỉnh sửa playlist '{playlist_name}'")

def download_playlist(username, playlist_name):
    playlist = playlist_data[(playlist_data["username"] == username) & (playlist_data["playlist_name"] == playlist_name)]
    if not playlist.empty:
        csv = playlist.to_csv(index=False)
        st.download_button(label="Tải xuống playlist", data=csv, file_name=f"{playlist_name}.csv", mime="text/csv")

def search_songs(query):
    # Integrate with a real music API like Spotify or YouTube
    # Dummy search function, replace with actual search logic
    return ["Song 1", "Song 2", "Song 3"]

def log_activity(username, activity):
    new_log = pd.DataFrame([[username, activity, datetime.now().isoformat()]], columns=["username", "activity", "timestamp"])
    updated_activity_log = pd.concat([activity_log, new_log], ignore_index=True)
    save_activity_log(updated_activity_log)

def recommend_songs(username):
    # Integrate with a real music API like Spotify or YouTube
    # Dummy recommendation function, replace with actual recommendation logic
    return ["Recommended Song 1", "Recommended Song 2", "Recommended Song 3"]

# User interface
if st.session_state.logged_in:
    st.sidebar.success(f"Đăng nhập thành công! Xin chào, {st.session_state.username}")
    st.sidebar.write(f"Tài khoản: {st.session_state.username}")
    if st.sidebar.button("Đăng Xuất"):
        log_activity(st.session_state.username, "Đăng xuất")
        st.session_state.logged_in = False
        st.session_state.username = ""
else:
    auth_mode = st.sidebar.selectbox("Chọn chế độ", ["Đăng Nhập", "Đăng Ký"])

    if auth_mode == "Đăng Nhập":
        st.sidebar.header("Đăng Nhập")
        username = st.sidebar.text_input("Tên đăng nhập")
        password = st.sidebar.text_input("Mật khẩu", type="password")
        if st.sidebar.button("Đăng Nhập"):
            if login(username, password):
                st.sidebar.success(f"Đăng nhập thành công! Xin chào, {username}")
            else:
                st.sidebar.error("Tên đăng nhập hoặc mật khẩu không đúng.")
    else:
        st.sidebar.header("Đăng Ký")
        full_name = st.sidebar.text_input("Họ và tên")
        email = st.sidebar.text_input("Email")
        new_username = st.sidebar.text_input("Tên đăng nhập mới")
        new_password = st.sidebar.text_input("Mật khẩu mới", type="password")
        if st.sidebar.button("Đăng Ký"):
            if register(full_name, email, new_username, new_password):
                st.sidebar.success(f"Đăng ký thành công! Xin chào, {full_name}")
            else:
                st.sidebar.error("Tên đăng nhập đã tồn tại.")

# Home section
if st.session_state.logged_in:
    st.header("🎧 Chào Mừng Đến Với Ứng Dụng Nghe Nhạc 🎧")
    st.write("Khám phá âm nhạc mới mỗi ngày!")

    # Display music player with image
    if os.path.exists(IMAGE_FILE):
        st.image(IMAGE_FILE, caption='BuonHayVui - Obito', use_container_width=True)
    else:
        st.warning(f"Hình ảnh '{IMAGE_FILE}' không tồn tại.")
    
    if os.path.exists(AUDIO_FILE):
        st.audio(AUDIO_FILE)
    else:
        st.warning(f"Tệp âm thanh '{AUDIO_FILE}' không tồn tại.")

    # Playlist management
    st.subheader("Quản Lý Playlist")
    playlist_name = st.text_input("Tên Playlist Mới")
    public = st.checkbox("Công khai")
    if st.button("Tạo Playlist"):
        if create_playlist(st.session_state.username, playlist_name, public):
            st.success(f"Playlist '{playlist_name}' đã được tạo.")
        else:
            st.error("Tên playlist đã tồn tại hoặc không hợp lệ.")

    st.subheader("Thêm Bài Hát Vào Playlist")
    selected_playlist = st.selectbox("Chọn Playlist", playlist_data[playlist_data["username"] == st.session_state.username]["playlist_name"].unique())
    song_name = st.text_input("Tên Bài Hát")
    if st.button("Thêm Bài Hát"):
        if add_song_to_playlist(st.session_state.username, selected_playlist, song_name):
            st.success(f"Bài hát '{song_name}' đã được thêm vào playlist '{selected_playlist}'.")
        else:
            st.error("Không thể thêm bài hát vào playlist.")

    st.subheader("Chỉnh Sửa Playlist")
    if selected_playlist:
        new_playlist_name = st.text_input("Tên Playlist Mới", value=selected_playlist)
        playlist_public = playlist_data[(playlist_data["username"] == st.session_state.username) & (playlist_data["playlist_name"] == selected_playlist)]
        if not playlist_public.empty:
            new_public = st.checkbox("Công khai", value=playlist_public["public"].values[0])
        else:
            new_public = st.checkbox("Công khai")
        if st.button("Chỉnh Sửa Playlist"):
            edit_playlist(st.session_state.username, selected_playlist, new_playlist_name, new_public)
            st.success(f"Playlist '{selected_playlist}' đã được chỉnh sửa.")

    st.subheader("Chia Sẻ Playlist")
    if selected_playlist and st.button("Chia Sẻ Playlist"):
        share_link = share_playlist(st.session_state.username, selected_playlist)
        st.write(f"Liên kết chia sẻ: {share_link}")

    st.subheader("Xóa Playlist")
    if selected_playlist and st.button("Xóa Playlist"):
        delete_playlist(st.session_state.username, selected_playlist)
        st.success(f"Playlist '{selected_playlist}' đã được xóa.")

    st.subheader("Tải Xuống Playlist")
    if selected_playlist and st.button("Tải Xuống Playlist"):
        download_playlist(st.session_state.username, selected_playlist)

    # Display playlists
    st.subheader("Playlists Của Bạn")
    user_playlists = playlist_data[playlist_data["username"] == st.session_state.username]
    if user_playlists.empty:
        st.info("Bạn chưa có playlist nào. Hãy tạo playlist mới!")
    else:
        for _, row in user_playlists.iterrows():
            st.write(f"**{row['playlist_name']}**: {row['songs']}")

    # Song search
    st.subheader("Tìm Kiếm Bài Hát")
    search_query = st.text_input("Nhập tên bài hát hoặc nghệ sĩ")
    if st.button("Tìm Kiếm"):
        search_results = search_songs(search_query)
        if search_results:
            st.write("Kết quả tìm kiếm:")
            for song in search_results:
                st.write(f"- {song}")
        else:
            st.info("Không tìm thấy bài hát nào.")

    # Song recommendations
    st.subheader("Gợi Ý Bài Hát")
    recommendations = recommend_songs(st.session_state.username)
    if recommendations:
        st.write("Bài hát gợi ý:")
        for song in recommendations:
            st.write(f"- {song}")
    else:
        st.info("Không có gợi ý bài hát nào.")

    # User profile management
    st.subheader("Thông Tin Cá Nhân")
    user_info = user_data[user_data["username"] == st.session_state.username].iloc[0]
    st.write(f"Họ và tên: {user_info['full_name']}")
    st.write(f"Email: {user_info['email']}")
    avatar_path = user_info.get('avatar', "")
    if avatar_path:
        st.markdown(f"<div style='text-align: center;'><img src='{os.path.join(AVATAR_FOLDER, avatar_path)}' alt='Avatar của bạn' style='width: 150px; border-radius: 15px;'></div>", unsafe_allow_html=True)
    uploaded_avatar = st.file_uploader("Tải lên ảnh đại diện mới", type=["jpg", "jpeg", "png"])
    if uploaded_avatar is not None:
        if uploaded_avatar.size > 5 * 1024 * 1024:
            st.error("Kích thước tệp quá lớn. Vui lòng tải lên tệp nhỏ hơn 5MB.")
        else:
            try:
                img = Image.open(uploaded_avatar)
                img = img.resize((150, 150))
                avatar_filename = f"{st.session_state.username}_{uploaded_avatar.name}"
                avatar_filepath = os.path.join(AVATAR_FOLDER, avatar_filename)
                img.save(avatar_filepath)
                user_data.loc[user_data["username"] == st.session_state.username, "avatar"] = avatar_filename
                save_user_data(user_data)
                st.success("Ảnh đại diện đã được cập nhật.")
            except Exception as e:
                st.error(f"Lỗi khi xử lý ảnh: {e}")
    if st.button("Cập Nhật Thông Tin"):
        new_full_name = st.text_input("Họ và tên mới", value=user_info['full_name'])
        new_email = st.text_input("Email mới", value=user_info['email'])
        if st.button("Lưu Thay Đổi"):
            user_data.loc[user_data["username"] == st.session_state.username, ["full_name", "email"]] = new_full_name, new_email
            save_user_data(user_data)
            st.success("Thông tin cá nhân đã được cập nhật.")

    # Activity log
    st.subheader("Nhật Ký Hoạt Động")
    user_activities = activity_log[activity_log["username"] == st.session_state.username]
    if user_activities.empty:
        st.info("Chưa có hoạt động nào.")
    else:
        for _, row in user_activities.iterrows():
            st.write(f"{row['timestamp']}: {row['activity']}")

else:
    st.header("🎧 Vui lòng đăng nhập để nghe nhạc 🎧")

# Footer
st.markdown("""
    <div style='text-align: center;'>
        <p>© 2024 - Bản quyền thuộc về <a href="https://www.facebook.com/profile.php?id=100073017864297" target="_blank">Ngvan</a></p>
    </div>
""", unsafe_allow_html=True)
