import streamlit as st
import pandas as pd
import os
import zipfile
import glob
import gdown  # <-- This is the new import
from PIL import Image

# ----- Configuration -----
IMAGES_FOLDER = "images"
ZIP_FILE = "images.zip"
GOOGLE_DRIVE_FILE_ID = "10MslbXI90KbVqF8VYB9ngGQBRy5Te9GW"  # <-- Paste your file ID here
GOOGLE_DRIVE_URL = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_FILE_ID}"
ADMIN_LABELS_FILE = "admin_labels.csv"
CONTROVERSIAL_LIST_FILE = "controversial_images.csv"
FRIEND_LABELS_FOLDER = "friend_labels"

# ----- Download and extract zip file -----
@st.cache_resource  # This ensures the file is downloaded and cached only once
def download_and_extract_zip():
    """Downloads the zip from Google Drive and extracts it into the IMAGES_FOLDER."""
    if not os.path.exists(IMAGES_FOLDER):
        os.makedirs(IMAGES_FOLDER, exist_ok=True)
        zip_path = os.path.join(IMAGES_FOLDER, ZIP_FILE)
        with st.spinner("Downloading dataset... This may take a moment on first run."):
            # Download the zip file directly into the images folder
            gdown.download(GOOGLE_DRIVE_URL, zip_path, quiet=False)
        with st.spinner("Extracting images..."):
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Extract to the IMAGES_FOLDER, but ensure files are not inside a subfolder
                for file_info in zip_ref.infolist():
                    # Handle potential nested folders: extract the file's base name directly
                    if not file_info.is_dir():
                        file_name = os.path.basename(file_info.filename)
                        if file_name:  # Only process files, not directories
                            target_path = os.path.join(IMAGES_FOLDER, file_name)
                            with zip_ref.open(file_info) as source, open(target_path, 'wb') as target:
                                target.write(source.read())
            # Remove the zip file after extraction to save space
            os.remove(zip_path)
            return True
    return False

# Call the function when the app starts
download_successful = download_and_extract_zip()
if not download_successful:
    st.info("Images folder already exists. Skipping download and extraction.")

# ... the rest of your code remains unchanged ...
