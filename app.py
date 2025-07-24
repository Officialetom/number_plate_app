
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
    api_key = "K82429890588957"
    url_api = "https://api.ocr.space/parse/image"
    # Crop middle portion (manually tweak values if needed)
    width, height = image.size
    top = int(height * 0.3)
    bottom = int(height * 0.85)
    cropped_image = image.crop((0, top, width, bottom))
    
    buffered = BytesIO()
    cropped_image.save(buffered, format="JPEG")
    buffered.seek(0)

    files = {
        'file': ('plate.jpg', buffered, 'image/jpeg')
    }
    data = {
        'apikey': api_key,
        'language': 'eng'
    }

    response = requests.post(url_api, files=files, data=data)
    result = response.json()
    try:
        return result["ParsedResults"][0]["ParsedText"].strip()
    except Exception:
        st.write(result)  # Optional: view detailed error
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
        image_data = uploaded_file.getvalue()
        image = Image.open(BytesIO(image_data))
        st.image(image, caption="Uploaded Image", use_container_width=True)

    if st.button("Process Image"):
        text = ocr_space_image(image)
        st.write(f"OCR Extracted Text: {text}")  # Debug: see the actual OCR output
        cursor.execute("INSERT INTO plates (image, characters) VALUES (?, ?)",
                       (image_data, text))
        conn.commit()
        st.success("Image processed and stored.")



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
            try:
                image = Image.open(BytesIO(img_blob))
                st.image(image, width=100)
            except Exception as e:
                st.warning("Could not load image")
                st.text(f"{e}")
        with col3:
            st.write(chars if chars else "No text extracted")
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
