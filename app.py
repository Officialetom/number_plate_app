
import streamlit as st
import sqlite3
import requests
import base64
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


def crop_center(image, width_ratio=0.8, height_ratio=0.3):
    """Crop the central region of the image based on given ratios."""
    img_width, img_height = image.size
    new_width = int(img_width * width_ratio)
    new_height = int(img_height * height_ratio)

    left = (img_width - new_width) // 2
    top = (img_height - new_height) // 2
    right = left + new_width
    bottom = top + new_height

    return image.crop((left, top, right, bottom))

# --- OCR API ---
def google_vision_ocr(image):

    cropped_image = crop_center(image)

    buffered = io.BytesIO()
    cropped_image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    api_key = "AIzaSyDE4Rux93LTAdWI9h9sg_4ANtDRfmIsCy0"
    url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "requests": [
            {
                "image": {"content": img_str},
                "features": [{"type": "TEXT_DETECTION"}],
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload)
    result = response.json()

    try:
        full_text = result['responses'][0]['fullTextAnnotation']['text']
        # Extract plate number using regex (e.g., APP-456CV or ABC123XY)
        match = re.search(r"[A-Z]{2,3}-?\d{3}[A-Z]{2,3}", full_text.replace(" ", "").upper())
        return match.group(0) if match else "No valid plate found"
    except Exception as e:
        return f"OCR Failed: {e}"


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
        text = google_vision_ocr(image)
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
