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
GOOGLE_DRIVE_FILE_ID = "10MslbXI90KbVqF8VYB9ngGQBRy5Te9GW"  # <-- Paste your file ID here
GOOGLE_DRIVE_URL = f"https://drive.google.com/uc?id={GOOGLE_DRIVE_FILE_ID}"
ADMIN_LABELS_FILE = "admin_labels.csv"
CONTROVERSIAL_LIST_FILE = "controversial_images.csv"
FRIEND_LABELS_FOLDER = "friend_labels"

# ----- Download and extract zip -----
@st.cache_resource
def download_and_extract_zip():
    if os.path.exists(IMAGES_FOLDER):
        existing_images = glob.glob(os.path.join(IMAGES_FOLDER, "*.*"))
        if existing_images:
            st.info(f"✅ Images folder already contains {len(existing_images)} files. Skipping download.")
            return True

    os.makedirs(IMAGES_FOLDER, exist_ok=True)
    zip_path = os.path.join(IMAGES_FOLDER, ZIP_FILE)

    with st.spinner("📥 Downloading dataset from Google Drive..."):
        try:
            gdown.download(GOOGLE_DRIVE_URL, zip_path, quiet=False)
        except Exception as e:
            st.error(f"Download failed: {e}")
            return False

    with st.spinner("📦 Extracting images..."):
        try:
            temp_extract = os.path.join(IMAGES_FOLDER, "_temp_extract")
            os.makedirs(temp_extract, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract)

            moved_count = 0
            for root, _, files in os.walk(temp_extract):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
                        src = os.path.join(root, file)
                        dst = os.path.join(IMAGES_FOLDER, file)
                        if os.path.exists(dst):
                            base, ext = os.path.splitext(file)
                            counter = 1
                            while os.path.exists(os.path.join(IMAGES_FOLDER, f"{base}_{counter}{ext}")):
                                counter += 1
                            dst = os.path.join(IMAGES_FOLDER, f"{base}_{counter}{ext}")
                        shutil.move(src, dst)
                        moved_count += 1

            shutil.rmtree(temp_extract, ignore_errors=True)
            os.remove(zip_path)
            st.success(f"✅ Extracted {moved_count} images.")
            return True
        except Exception as e:
            st.error(f"Extraction failed: {e}")
            return False

if not download_and_extract_zip():
    st.stop()

os.makedirs(FRIEND_LABELS_FOLDER, exist_ok=True)

# ----- Helper functions -----
def get_all_images():
    return sorted(glob.glob(os.path.join(IMAGES_FOLDER, "*.*")))

def load_admin_labels():
    if os.path.exists(ADMIN_LABELS_FILE):
        df = pd.read_csv(ADMIN_LABELS_FILE)
        df["label"] = df["label"].fillna("")
        return df
    else:
        images = get_all_images()
        return pd.DataFrame({"image": images, "label": ""})

def save_admin_labels(df):
    df.to_csv(ADMIN_LABELS_FILE, index=False)

def get_controversial_images():
    df = load_admin_labels()
    return df[df["label"] == "controversial"]["image"].tolist()

def load_friend_labels(friend_name):
    file = os.path.join(FRIEND_LABELS_FOLDER, f"{friend_name}.csv")
    if os.path.exists(file):
        df = pd.read_csv(file)
        df["label"] = df["label"].fillna("")
        return df
    else:
        controversial = get_controversial_images()
        return pd.DataFrame({"image": controversial, "label": ""})

def save_friend_labels(friend_name, df):
    file = os.path.join(FRIEND_LABELS_FOLDER, f"{friend_name}.csv")
    df.to_csv(file, index=False)

# ----- UI -----
st.set_page_config(page_title="Hate Speech Labeler", layout="wide")
st.title("🚀 Fast Hate Speech Labeling")

mode = st.radio("Choose mode:", ["👑 Admin (You)", "👥 Friend"])

# ---------- ADMIN MODE ----------
if mode == "👑 Admin (You)":
    st.subheader("Admin Mode – Pre‑label all images")
    st.info("✅ Default is **Non‑Hate Speech**. Click 'Hate Speech' or 'Controversial' if needed.")

    # --- Sidebar Admin Tools ---
    with st.sidebar:
        st.markdown("## ⚙️ Admin Tools")
        
        # 1. Upload previous admin labels
        st.markdown("#### 📂 Restore Labels")
        uploaded_labels = st.file_uploader("Upload admin_labels.csv", type="csv", key="admin_restore")
        if uploaded_labels is not None:
            try:
                existing_df = pd.read_csv(uploaded_labels)
                existing_df["label"] = existing_df["label"].fillna("")
                current_df = load_admin_labels()
                for _, row in existing_df.iterrows():
                    current_df.loc[current_df["image"] == row["image"], "label"] = row["label"]
                save_admin_labels(current_df)
                st.success("✅ Labels restored! Refresh the page.")
            except Exception as e:
                st.error(f"Error: {e}")
        
        st.markdown("---")
        
        # 2. Download master report of all friends
        st.markdown("#### 📥 Collect Friend Data")
        if st.button("🔄 Generate Master Report"):
            if os.path.exists(FRIEND_LABELS_FOLDER):
                all_data = []
                for fname in os.listdir(FRIEND_LABELS_FOLDER):
                    if fname.endswith(".csv"):
                        df_friend = pd.read_csv(os.path.join(FRIEND_LABELS_FOLDER, fname))
                        df_friend["annotator"] = fname.replace(".csv", "")
                        all_data.append(df_friend)
                if all_data:
                    master = pd.concat(all_data, ignore_index=True)
                    master_csv = master.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download Master Report", master_csv, "all_friend_labels.csv", "text/csv")
                else:
                    st.info("No friend labels found yet.")
            else:
                st.info("Friend labels folder not found.")

    # --- Main labeling interface ---
    images = get_all_images()
    if not images:
        st.error("No images found.")
        st.stop()

    df = load_admin_labels()
    unlabeled = df[df["label"] == ""]

    if len(unlabeled) == 0:
        st.success("🎉 All images labeled!")
    else:
        idx = unlabeled.index[0]
        current_img = df.loc[idx, "image"]
        try:
            img = Image.open(current_img)
            st.image(img, use_column_width=True)
        except Exception as e:
            st.error(f"Cannot load image: {e}")
            st.stop()

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

    st.divider()
    if st.button("📤 Export controversial images list"):
        controversial = get_controversial_images()
        if not controversial:
            st.warning("No controversial images.")
        else:
            pd.DataFrame({"image": controversial}).to_csv(CONTROVERSIAL_LIST_FILE, index=False)
            st.success(f"Exported {len(controversial)} controversial images.")

    # Admin download own labels
    if os.path.exists(ADMIN_LABELS_FILE):
        with open(ADMIN_LABELS_FILE, "r") as f:
            st.download_button("📥 Download Your Admin Labels", f.read(), "admin_labels.csv", "text/csv")

# ---------- FRIEND MODE ----------
elif mode == "👥 Friend":
    st.subheader("Friend Mode – Label only controversial images")
    friend_name = st.text_input("Enter your name:")
    if not friend_name:
        st.stop()

    if not os.path.exists(CONTROVERSIAL_LIST_FILE):
        st.error("Admin hasn't exported the controversial list yet.")
        st.stop()

    controversial_df = pd.read_csv(CONTROVERSIAL_LIST_FILE)
    if controversial_df.empty:
        st.warning("No controversial images to label.")
        st.stop()

    friend_df = load_friend_labels(friend_name)
    all_controversial = controversial_df["image"].tolist()
    for img in all_controversial:
        if img not in friend_df["image"].values:
            friend_df = pd.concat([friend_df, pd.DataFrame({"image": [img], "label": [""]})], ignore_index=True)

    unlabeled_idx = friend_df[friend_df["label"] == ""].index
    if len(unlabeled_idx) == 0:
        st.success(f"✅ Done, {friend_name}!")
        csv_data = friend_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Your Labels", csv_data, f"{friend_name}_labels.csv", "text/csv")
    else:
        idx = unlabeled_idx[0]
        current_img = friend_df.loc[idx, "image"]
        try:
            img = Image.open(current_img)
            st.image(img, use_column_width=True)
        except Exception as e:
            st.error(f"Cannot load image: {e}")
            st.stop()

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
        if friend_df[friend_df['label']!=''].shape[0] > 0:
            csv_data = friend_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Partial Progress", csv_data, f"{friend_name}_partial.csv", "text/csv")
