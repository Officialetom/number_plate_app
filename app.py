
import streamlit as st
import sqlite3
import requests
from PIL import Image
import os
from io import BytesIO

# --- DB Setup ---
conn = sqlite3.connect('plate_data.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS plates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image BLOB,
    characters TEXT
)''')
conn.commit()

# --- OCR API ---
def ocr_space_image(image):
    api_key = "K82429890588957"  # Demo API key, replace with your own for production
    url_api = "https://api.ocr.space/parse/image"
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    buffered.seek(0)
    response = requests.post(
        url_api,
        files={"filename": buffered},
        data={"apikey": api_key, "language": "eng"}
    )
    result = response.json()
    st.write(result)
    try:
        return result["ParsedResults"][0]["ParsedText"].strip()
    except Exception:
        return "OCR Failed"

# --- Session State Init ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- Login Page ---
def login():
    st.title("Admin Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == "admin" and password == "1234":
            st.session_state.logged_in = True
            st.success("Login successful")
            st.rerun()
        else:
            st.error("Invalid credentials")

# --- Dashboard Page ---
def dashboard():
    st.title("Dashboard")
    st.write("Welcome, admin 👋")
    cursor.execute("SELECT COUNT(*) FROM plates")
    count = cursor.fetchone()[0]
    st.metric("Number of Images Processed", count)

# --- Upload Page ---
def upload():
    st.title("Upload Plate Image")
    uploaded_file = st.file_uploader("Choose an image", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_container_width=True)

        if st.button("Process Image"):
            text = ocr_space_image(image)
            cursor.execute("INSERT INTO plates (image, characters) VALUES (?, ?)", 
                           (uploaded_file.read(), text))
            conn.commit()
            st.success(f"Image processed and stored. Extracted Text: {text}")

# --- History Page ---
def history():
    st.title("History")
    cursor.execute("SELECT * FROM plates")
    records = cursor.fetchall()

    if not records:
        st.info("No records found.")
        return

    for i, (id, img_blob, chars) in enumerate(records, start=1):
        col1, col2, col3, col4 = st.columns([1, 2, 3, 2])
        with col1:
            st.write(f"{i}")
        with col2:
            st.image(Image.open(BytesIO(img_blob)), width=100)
        with col3:
            st.write(chars)
        with col4:
            if st.button("Delete", key=f"del_{id}"):
                cursor.execute("DELETE FROM plates WHERE id=?", (id,))
                conn.commit()
                st.success("Entry deleted.")
                st.rerun()

# --- Logout ---
def logout():
    st.session_state.logged_in = False
    st.success("Logged out successfully")
    st.rerun()

# --- Main App Routing ---
def main():
    if not st.session_state.logged_in:
        login()
    else:
        menu = ["Dashboard", "Upload Image", "History", "Logout"]
        choice = st.sidebar.selectbox("Navigate", menu)

        if choice == "Dashboard":
            dashboard()
        elif choice == "Upload Image":
            upload()
        elif choice == "History":
            history()
        elif choice == "Logout":
            logout()

if __name__ == "__main__":
    main()
