"""
写真追加ページ - iPhoneでカテゴリを開き、写真を追加・確認・削除する画面
"""

import mimetypes
import os
import sys
from datetime import datetime

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from drive_storage import get_storage_from_streamlit


st.set_page_config(
    page_title="写真追加 | Reel Maker",
    page_icon="📥",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #0d0d1a; color: #fff; }
  [data-testid="stSidebar"] { background: #12122a; }
  [data-testid="stFileUploader"] section {
    background: #17172a; border: 2px dashed #ff5078; border-radius: 12px;
  }
  h1 { color: #ff5078 !important; font-size: 1.8rem !important; }
  h2 { color: #fff !important; font-size: 1.2rem !important; }
  h3 { color: #ff5078 !important; font-size: 1.05rem !important; }
  div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #ff5078, #c850c0);
    color: white !important; border: none; border-radius: 14px;
    padding: 0.9rem 0.7rem !important;
    font-weight: 800; font-size: 1rem !important;
    width: 100%; min-height: 56px; line-height: 1.25;
  }
  div[data-testid="stButton"] > button[kind="secondary"] {
    background: transparent !important; color: #ddd !important;
    border: 1px solid #555 !important; min-height: 42px !important;
    font-size: 0.95rem !important;
  }
  .folder-card {
    background: #1a1a2e; border: 1px solid #2f2f53; border-radius: 12px;
    padding: 12px 14px; margin-bottom: 8px;
  }
  .folder-title { color: #fff; font-weight: 800; font-size: 1.05rem; }
  .folder-count { color: #ff9ab0; font-weight: 800; }
  .notice {
    position: sticky; bottom: 0; z-index: 20;
    background: #2a1630; border: 1px solid #ff5078;
    border-radius: 12px; padding: 12px; margin-top: 18px;
    box-shadow: 0 -4px 18px rgba(0,0,0,0.35);
  }
  .thumb-name { color: #ddd; font-size: .78rem; word-break: break-all; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_storage():
    return get_storage_from_streamlit()


try:
    storage = get_storage()
except Exception as e:
    st.error(f"保存先接続エラー: {e}")
    st.stop()


def _media_files(folder_num: int):
    files = storage.list_files(f"pool_{folder_num}")
    return [
        f for f in files
        if f.get("mimeType", "").startswith(("image/", "video/"))
    ]


def _file_signature(file) -> str:
    return f"{file.name}:{file.size}:{file.type}"


def _display_media(file_info: dict):
    mime = file_info.get("mimeType", "")
    local_path = file_info.get("localPath") or file_info.get("id", "").removeprefix("local:")
    if mime.startswith("image/") and os.path.isfile(local_path):
        st.image(local_path, use_container_width=True)
    elif mime.startswith("video/") and os.path.isfile(local_path):
        st.video(local_path)
    elif mime.startswith("image/"):
        st.markdown(
            f'<img src="{storage.get_thumbnail_url(file_info["id"])}" '
            f'style="width:100%;border-radius:10px;" />',
            unsafe_allow_html=True,
        )
    else:
        st.info(f"🎬 {file_info.get('name', '動画')}")


if "selected_folder" not in st.session_state:
    st.session_state.selected_folder = None
if "uploader_version" not in st.session_state:
    st.session_state.uploader_version = 0
if "processed_uploads" not in st.session_state:
    st.session_state.processed_uploads = set()


if st.button("← ホームに戻る", type="secondary", key="back_home_top"):
    st.switch_page("main.py")

st.title("📥 写真追加")
st.caption("カテゴリを開いて、写真アプリから写真を選びます。追加後は一覧で確認できます。")

if st.session_state.selected_folder is None:
    st.markdown("### 追加するフォルダーを選ぶ")
    for n in range(1, 6):
        name = config.POOL_NAMES[n]
        count = len(_media_files(n))
        st.markdown(
            f'<div class="folder-card"><span class="folder-title">{n}. {name}</span>'
            f'<span style="float:right" class="folder-count">{count}枚</span></div>',
            unsafe_allow_html=True,
        )
        if st.button(f"{n}. {name} を開く", key=f"open_{n}"):
            st.session_state.selected_folder = n
            st.session_state.processed_uploads = set()
            st.rerun()

    st.markdown(
        '<div class="notice">全部のフォルダーに写真を入れ終わったら、'
        '上の「ホームに戻る」からリール作成へ進んでください。</div>',
        unsafe_allow_html=True,
    )
    st.stop()


folder_num = st.session_state.selected_folder
folder_name = config.POOL_NAMES[folder_num]

st.markdown(f"## {folder_num}. {folder_name}")

c1, c2 = st.columns(2)
with c1:
    if st.button("← フォルダー選択へ", type="secondary", key="back_folder"):
        st.session_state.selected_folder = None
        st.session_state.uploader_version += 1
        st.session_state.processed_uploads = set()
        st.rerun()
with c2:
    if st.button("保存して閉じる", key="save_close"):
        st.session_state.selected_folder = None
        st.session_state.uploader_version += 1
        st.session_state.processed_uploads = set()
        st.success("保存しました。次のフォルダーを選んでください。")
        st.rerun()

st.markdown("### 写真を追加")
uploaded_files = st.file_uploader(
    f"{folder_name} に入れる写真を選択",
    type=["jpg", "jpeg", "png", "heic", "heif", "webp", "mp4", "mov"],
    accept_multiple_files=True,
    key=f"uploader_{folder_num}_{st.session_state.uploader_version}",
    help="iPhoneではフォトライブラリを選んで写真を選択できます。",
)

if uploaded_files:
    new_files = [
        f for f in uploaded_files
        if _file_signature(f) not in st.session_state.processed_uploads
    ]
    if new_files:
        status = st.empty()
        progress = st.progress(0)
        added = 0
        failed = []
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        with st.spinner(f"{folder_name} に保存中..."):
            for idx, file in enumerate(new_files, start=1):
                original_name = os.path.basename(file.name)
                filename = f"{stamp}_{idx:02d}_{original_name}"
                mime_type = file.type or mimetypes.guess_type(original_name)[0] or "application/octet-stream"
                try:
                    storage.upload_bytes(file.getvalue(), filename, f"pool_{folder_num}", mime_type=mime_type)
                    st.session_state.processed_uploads.add(_file_signature(file))
                    added += 1
                    status.info(f"保存中: {idx}/{len(new_files)}")
                except Exception as e:
                    failed.append(f"{original_name}: {e}")
                progress.progress(idx / len(new_files))

        progress.empty()
        status.empty()
        if added:
            st.success(f"{folder_name} に {added}件入りました。下の一覧で確認できます。")
        if failed:
            st.error("追加できなかった写真があります。")
            for msg in failed:
                st.caption(msg)

st.markdown("---")
files = _media_files(folder_num)
st.markdown(f"### {folder_name} に入っている写真一覧（{len(files)}件）")

if not files:
    st.info("まだ写真が入っていません。上の「写真を選択」から追加してください。")
else:
    selected_for_delete = []
    for idx, file_info in enumerate(files, start=1):
        st.markdown(f"**{idx}. {file_info['name']}**")
        _display_media(file_info)
        if st.checkbox("削除対象にする", key=f"delete_check_{folder_num}_{file_info['id']}"):
            selected_for_delete.append(file_info)
        st.markdown('<div class="thumb-name">確認して、間違っていたら削除対象にしてください。</div>', unsafe_allow_html=True)
        st.markdown("---")

    if selected_for_delete:
        st.warning(f"{len(selected_for_delete)}件を削除対象にしています。")
        if st.button("選択した写真を削除する", key="delete_selected"):
            deleted = 0
            for file_info in selected_for_delete:
                try:
                    storage.delete(file_info["id"])
                    deleted += 1
                except Exception as e:
                    st.error(f"{file_info['name']} の削除に失敗: {e}")
            st.success(f"{deleted}件削除しました。")
            st.rerun()

st.markdown(
    '<div class="notice">このフォルダーの確認が終わったら「保存して閉じる」。'
    '全部のフォルダーに入れ終わったらホームへ戻ってリール作成へ進んでください。</div>',
    unsafe_allow_html=True,
)
