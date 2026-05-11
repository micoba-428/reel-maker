"""
写真追加ページ - 写真アプリ/端末内の写真を選択してpool 1〜5へ直接追加
"""

import mimetypes
import os
import sys
from datetime import datetime
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from drive_storage import get_storage_from_streamlit

st.set_page_config(
    page_title="振り分け | Reel Maker",
    page_icon="📥",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #0d0d1a; color: #fff; }
  [data-testid="stSidebar"] { background: #12122a; }
  h1 { color: #ff5078 !important; font-size: 1.8rem !important; }
  h3 { color: #fff !important; }

  div[data-testid="stButton"] > button {
    background: #2a2a4a; color: white; border: 2px solid #3a3a5a;
    border-radius: 14px; padding: 1rem 0.4rem;
    font-weight: 800; font-size: 1.5rem;
    width: 100%; min-height: 70px;
  }
  div[data-testid="stButton"] > button:hover {
    background: linear-gradient(135deg, #ff5078, #c850c0);
    border-color: #ff5078; transform: scale(1.03);
  }
  div[data-testid="stButton"] > button[kind="secondary"] {
    background: transparent !important; color: #aaa !important;
    border: 1px solid #555 !important; min-height: 40px !important;
    font-size: 0.95rem !important;
  }
  .secondary-row div[data-testid="stButton"] > button {
    background: #444; font-size: 0.9rem; min-height: 50px;
  }
  .progress-bar {
    background: #2a2a4a; border-radius: 10px; height: 8px;
    overflow: hidden; margin: 10px 0;
  }
  .progress-fill {
    background: linear-gradient(90deg, #ff5078, #c850c0); height: 100%;
  }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_storage():
    return get_storage_from_streamlit()

try:
    storage = get_storage()
except Exception as e:
    st.error(f"Drive接続エラー: {e}")
    st.stop()


# ── 戻るボタン ───────────────────────────────────────────────────────────────
if st.button("← ホームに戻る", type="secondary", key="back"):
    st.switch_page("main.py")

st.title("📥 写真追加")
st.caption("写真アプリ/端末内の写真を選んで、直接Poolへ追加します")

# ── 0番モード切替 ────────────────────────────────────────────────────────────
if "priority_mode" not in st.session_state:
    st.session_state.priority_mode = False

priority = st.toggle(
    "⭐ 0番モード（次に振り分ける写真を最優先に）",
    value=st.session_state.priority_mode,
)
st.session_state.priority_mode = priority

st.markdown("---")

st.markdown("### 追加先のPool")
pool_num = st.radio(
    "追加先",
    options=[1, 2, 3, 4, 5],
    horizontal=True,
    format_func=lambda n: f"Pool {n}",
    label_visibility="collapsed",
)

uploaded_files = st.file_uploader(
    "写真を選択",
    type=["jpg", "jpeg", "png", "heic", "heif", "webp", "mp4", "mov"],
    accept_multiple_files=True,
    help="iPhoneなら「フォトライブラリ」、Macなら写真ファイルを選択できます。",
)

if uploaded_files:
    st.markdown(f"### 選択中: {len(uploaded_files)}件")
    preview = uploaded_files[0]
    mime = preview.type or mimetypes.guess_type(preview.name)[0] or ""
    if mime.startswith("image/"):
        st.image(preview, use_container_width=True)
    else:
        st.info(f"🎬 {preview.name}")

    if st.button(f"Pool {pool_num} に追加する", key="upload"):
        added = 0
        failed = []
        progress = st.progress(0)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for idx, file in enumerate(uploaded_files, start=1):
            original_name = os.path.basename(file.name)
            prefix = "0_" if priority and not original_name.startswith("0_") else ""
            filename = f"{prefix}{stamp}_{idx:02d}_{original_name}"
            mime_type = file.type or mimetypes.guess_type(original_name)[0] or "application/octet-stream"
            try:
                storage.upload_bytes(file.getvalue(), filename, f"pool_{pool_num}", mime_type=mime_type)
                added += 1
            except Exception as e:
                failed.append(f"{original_name}: {e}")
            progress.progress(idx / len(uploaded_files))

        if added:
            st.success(f"Pool {pool_num} に {added}件追加しました")
        if failed:
            st.error("追加できなかったファイルがあります")
            for msg in failed:
                st.caption(msg)
        st.cache_resource.clear()

st.markdown("---")
st.markdown("### 現在のPool状況")
for n in range(1, 6):
    files = storage.list_files(f"pool_{n}")
    files = [f for f in files if f.get("mimeType", "").startswith(("image/", "video/"))]
    st.markdown(f"Pool {n}: **{len(files)}件**")

if st.button("🔄 再読み込み", key="reload"):
    st.cache_resource.clear()
    st.rerun()
