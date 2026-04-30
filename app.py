import streamlit as st
import pandas as pd
import os
from PIL import Image
import glob

# ----- Configuration -----
IMAGES_FOLDER = "images"
ADMIN_LABELS_FILE = "admin_labels.csv"
CONTROVERSIAL_LIST_FILE = "controversial_images.csv"
FRIEND_LABELS_FOLDER = "friend_labels"

# Ensure folders exist
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
    df = load_admin_labels()
    
    # Find first unlabeled image
    unlabeled = df[df["label"] == ""]
    if len(unlabeled) == 0:
        st.success("🎉 All images labeled! Export the controversial list below.")
    else:
        idx = unlabeled.index[0]
        current_img = df.loc[idx, "image"]
        
        # Display image
        img = Image.open(current_img)
        st.image(img, use_column_width=True)
        
        # Buttons (default is non-hate speech)
        col1, col2, col3 = st.columns(3)
        
        # We'll use session state to remember choice
        if "admin_choice" not in st.session_state:
            st.session_state.admin_choice = "non_hate_speech"
        
        # Display selected value
        selected = st.radio("Select label:", 
                            ["non_hate_speech", "hate_speech", "controversial"],
                            index=["non_hate_speech","hate_speech","controversial"].index(st.session_state.admin_choice),
                            horizontal=True)
        st.session_state.admin_choice = selected
        
        if st.button("💾 Save & Next", type="primary"):
            df.loc[idx, "label"] = st.session_state.admin_choice
            save_admin_labels(df)
            st.session_state.admin_choice = "non_hate_speech"  # reset default
            st.rerun()
    
    # Show export button for controversial images
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
        img = Image.open(current_img)
        st.image(img, use_column_width=True)
        
        # Label choice (no default to force conscious decision, but you can add default)
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