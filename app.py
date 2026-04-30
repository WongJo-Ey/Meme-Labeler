import streamlit as st
import pandas as pd
import os
import zipfile
import glob
import gdown
import shutil
from PIL import Image

# ----- Configuration -----
IMAGES_FOLDER = "images"
ZIP_FILE = "images.zip"
# !!! IMPORTANT: Replace 'YOUR_FILE_ID' with the ID you copied from Google Drive !!!
GOOGLE_DRIVE_FILE_ID = "10MslbXI90KbVqF8VYB9ngGQBRy5Te9GW"  # <-- Paste your file ID here
GOOGLE_DRIVE_URL = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_FILE_ID}"
ADMIN_LABELS_FILE = "admin_labels.csv"
CONTROVERSIAL_LIST_FILE = "controversial_images.csv"
FRIEND_LABELS_FOLDER = "friend_labels"

# ----- Download and extract zip file (robust version) -----
@st.cache_resource
def download_and_extract_zip():
    """Downloads the zip from Google Drive and extracts images into IMAGES_FOLDER."""
    # If images folder already has image files, skip
    if os.path.exists(IMAGES_FOLDER):
        existing_images = glob.glob(os.path.join(IMAGES_FOLDER, "*.*"))
        if existing_images:
            st.info(f"✅ Images folder already contains {len(existing_images)} files. Skipping download.")
            return True

    os.makedirs(IMAGES_FOLDER, exist_ok=True)
    zip_path = os.path.join(IMAGES_FOLDER, ZIP_FILE)

    # Download
    with st.spinner("📥 Downloading dataset from Google Drive... This may take a minute."):
        try:
            gdown.download(GOOGLE_DRIVE_URL, zip_path, quiet=False)
        except Exception as e:
            st.error(f"Download failed: {e}")
            return False

    # Extract
    with st.spinner("📦 Extracting images... This could take a few minutes for large zip files."):
        try:
            # Extract to temporary folder
            temp_extract = os.path.join(IMAGES_FOLDER, "_temp_extract")
            os.makedirs(temp_extract, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract)

            # Move all image files to the main images folder, flattening any subfolders
            moved_count = 0
            for root, dirs, files in os.walk(temp_extract):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
                        src = os.path.join(root, file)
                        dst = os.path.join(IMAGES_FOLDER, file)
                        # Handle duplicate filenames
                        if os.path.exists(dst):
                            base, ext = os.path.splitext(file)
                            counter = 1
                            while os.path.exists(os.path.join(IMAGES_FOLDER, f"{base}_{counter}{ext}")):
                                counter += 1
                            dst = os.path.join(IMAGES_FOLDER, f"{base}_{counter}{ext}")
                        shutil.move(src, dst)
                        moved_count += 1

            # Clean up
            shutil.rmtree(temp_extract, ignore_errors=True)
            os.remove(zip_path)
            st.success(f"✅ Successfully extracted {moved_count} images.")
            return True
        except Exception as e:
            st.error(f"Extraction failed: {e}")
            return False

# Run extraction when app starts
if not download_and_extract_zip():
    st.stop()

# Ensure other folders exist
os.makedirs(FRIEND_LABELS_FOLDER, exist_ok=True)

# ----- Helper functions -----
def get_all_images():
    """Return list of image filenames (sorted)"""
    return sorted(glob.glob(os.path.join(IMAGES_FOLDER, "*.*")))

def load_admin_labels():
    """Load existing admin labels or create empty DataFrame"""
    if os.path.exists(ADMIN_LABELS_FILE):
        return pd.read_csv(ADMIN_LABELS_FILE)
    else:
        images = get_all_images()
        return pd.DataFrame({"image": images, "label": ""})

def save_admin_labels(df):
    df.to_csv(ADMIN_LABELS_FILE, index=False)

def get_controversial_images():
    """Return list of images where admin label is 'controversial'"""
    df = load_admin_labels()
    controversial = df[df["label"] == "controversial"]["image"].tolist()
    return controversial

def load_friend_labels(friend_name):
    """Load labels for a specific friend"""
    file = os.path.join(FRIEND_LABELS_FOLDER, f"{friend_name}.csv")
    if os.path.exists(file):
        return pd.read_csv(file)
    else:
        controversial = get_controversial_images()
        return pd.DataFrame({"image": controversial, "label": ""})

def save_friend_labels(friend_name, df):
    file = os.path.join(FRIEND_LABELS_FOLDER, f"{friend_name}.csv")
    df.to_csv(file, index=False)

# ----- UI -----
st.set_page_config(page_title="Hate Speech Labeler", layout="wide")
st.title("🚀 Fast Hate Speech Labeling")

# Mode selection
mode = st.radio("Choose mode:", ["👑 Admin (You)", "👥 Friend"])

if mode == "👑 Admin (You)":
    st.subheader("Admin Mode – Pre‑label all images")
    st.info("✅ Default is **Non‑Hate Speech**. Click 'Hate Speech' or 'Controversial' if needed. Progress auto‑saves.")
    
    images = get_all_images()
    if not images:
        st.error("No images found. Make sure your zip contains image files (jpg, png, etc.)")
        st.stop()
    
    df = load_admin_labels()
    
    # Find first unlabeled image
    unlabeled = df[df["label"] == ""]
    if len(unlabeled) == 0:
        st.success("🎉 All images labeled! Export the controversial list below.")
    else:
        idx = unlabeled.index[0]
        current_img = df.loc[idx, "image"]
        
        # Display image
        try:
            img = Image.open(current_img)
            st.image(img, use_column_width=True)
        except Exception as e:
            st.error(f"Could not load image: {e}")
            st.stop()
        
        # Label selection with default "non_hate_speech"
        if "admin_choice" not in st.session_state:
            st.session_state.admin_choice = "non_hate_speech"
        
        selected = st.radio(
            "Select label:",
            ["non_hate_speech", "hate_speech", "controversial"],
            index=["non_hate_speech", "hate_speech", "controversial"].index(st.session_state.admin_choice),
            horizontal=True
        )
        st.session_state.admin_choice = selected
        
        if st.button("💾 Save & Next", type="primary"):
            df.loc[idx, "label"] = st.session_state.admin_choice
            save_admin_labels(df)
            st.session_state.admin_choice = "non_hate_speech"
            st.rerun()
    
    # Export controversial list
    st.divider()
    if st.button("📤 Export controversial images list"):
        controversial = get_controversial_images()
        if len(controversial) == 0:
            st.warning("No controversial images yet.")
        else:
            pd.DataFrame({"image": controversial}).to_csv(CONTROVERSIAL_LIST_FILE, index=False)
            st.success(f"Saved {len(controversial)} controversial images to {CONTROVERSIAL_LIST_FILE}")

elif mode == "👥 Friend":
    st.subheader("Friend Mode – Label only the controversial images")
    
    # Ask for friend's name
    friend_name = st.text_input("Enter your name (e.g., John):")
    if not friend_name:
        st.stop()
    
    # Load controversial list
    if not os.path.exists(CONTROVERSIAL_LIST_FILE):
        st.error("Admin hasn't exported the controversial list yet. Ask them to run Admin mode and click 'Export controversial images list'.")
        st.stop()
    
    controversial_df = pd.read_csv(CONTROVERSIAL_LIST_FILE)
    if controversial_df.empty:
        st.warning("No controversial images to label.")
        st.stop()
    
    # Load friend's progress
    friend_df = load_friend_labels(friend_name)
    # Ensure all controversial images are in friend_df
    all_controversial = controversial_df["image"].tolist()
    for img in all_controversial:
        if img not in friend_df["image"].values:
            friend_df = pd.concat([friend_df, pd.DataFrame({"image": [img], "label": [""]})], ignore_index=True)
    
    # Find first unlabeled
    unlabeled_idx = friend_df[friend_df["label"] == ""].index
    if len(unlabeled_idx) == 0:
        st.success(f"✅ Great job, {friend_name}! You've labeled all controversial images.")
        st.download_button("📥 Download your labels", data=friend_df.to_csv(index=False), file_name=f"{friend_name}_labels.csv")
    else:
        idx = unlabeled_idx[0]
        current_img = friend_df.loc[idx, "image"]
        
        # Display image
        try:
            img = Image.open(current_img)
            st.image(img, use_column_width=True)
        except Exception as e:
            st.error(f"Could not load image: {e}")
            st.stop()
        
        # Two large buttons for labeling
        col1, col2 = st.columns(2)
        if col1.button("❌ Non-Hate Speech", use_container_width=True):
            friend_df.loc[idx, "label"] = "non_hate_speech"
            save_friend_labels(friend_name, friend_df)
            st.rerun()
        if col2.button("⚠️ Hate Speech", use_container_width=True):
            friend_df.loc[idx, "label"] = "hate_speech"
            save_friend_labels(friend_name, friend_df)
            st.rerun()
        
        st.caption(f"Progress: {friend_df[friend_df['label']!=''].shape[0]} / {len(friend_df)}")
