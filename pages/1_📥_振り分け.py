"""
写真追加ページ - iPhoneでカテゴリを開き、写真を追加・確認・削除する画面
"""

import mimetypes
import os
import sys
from datetime import datetime
from hashlib import md5

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
  .grid-caption {
    color: #ddd; font-size: .74rem; line-height: 1.2;
    min-height: 2.1em; word-break: break-all;
  }
  .grid-box {
    background: #151528; border: 1px solid #2a2a4a;
    border-radius: 10px; padding: 6px; margin-bottom: 8px;
  }
  .grid-box img {
    width: 100%; aspect-ratio: 1 / 1; object-fit: cover;
    border-radius: 8px; display: block;
  }
  .video-tile {
    width: 100%; aspect-ratio: 1 / 1; border-radius: 8px;
    background: #252542; display:flex; align-items:center; justify-content:center;
    color:#fff; font-weight:800;
  }
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


def _safe_key(value: str) -> str:
    return md5(value.encode("utf-8")).hexdigest()


def _render_grid_media(file_info: dict):
    mime = file_info.get("mimeType", "")
    local_path = file_info.get("localPath") or file_info.get("id", "").removeprefix("local:")
    if mime.startswith("image/") and os.path.isfile(local_path):
        mtime = os.path.getmtime(local_path)
        st.markdown(
            f'<div class="grid-box"><img src="data:image/jpeg;base64,{_image_b64(local_path, mtime)}" /></div>',
            unsafe_allow_html=True,
        )
    elif mime.startswith("image/"):
        st.markdown(
            f'<div class="grid-box"><img src="{storage.get_thumbnail_url(file_info["id"])}" /></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="grid-box"><div class="video-tile">動画</div></div>', unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def _image_b64(path: str, mtime: float) -> str:
    import base64
    from io import BytesIO
    from PIL import Image, ImageOps

    try:
        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img)
            img.thumbnail((220, 220))
            canvas = Image.new("RGB", (220, 220), (18, 18, 36))
            img = img.convert("RGB")
            x = (220 - img.width) // 2
            y = (220 - img.height) // 2
            canvas.paste(img, (x, y))
            buffer = BytesIO()
            canvas.save(buffer, format="JPEG", quality=58, optimize=True)
            return base64.b64encode(buffer.getvalue()).decode("ascii")
    except Exception:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")


if "selected_folder" not in st.session_state:
    st.session_state.selected_folder = None
if "uploader_version" not in st.session_state:
    st.session_state.uploader_version = 0
if "processed_uploads" not in st.session_state:
    st.session_state.processed_uploads = set()
if "delete_selection" not in st.session_state:
    st.session_state.delete_selection = {}
if "gallery_page" not in st.session_state:
    st.session_state.gallery_page = {}


if st.button("← ホームに戻る", type="secondary", key="back_home_top"):
    st.switch_page("main.py")

st.title("📥 写真追加")
st.caption("カテゴリを開いて、写真アプリから写真を選びます。追加後は一覧で確認できます。")

if st.session_state.selected_folder is None:
    st.markdown("### 追加するフォルダーを選ぶ")
    for n in range(1, 6):
        name = config.POOL_NAMES[n]
        st.markdown(
            f'<div class="folder-card"><span class="folder-title">{n}. {name}</span>'
            f'<span style="float:right" class="folder-count">開く</span></div>',
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
with st.form(f"upload_form_{folder_num}_{st.session_state.uploader_version}", clear_on_submit=True):
    uploaded_files = st.file_uploader(
        f"{folder_name} に入れる写真を選択",
        type=["jpg", "jpeg", "png", "heic", "heif", "webp", "mp4", "mov"],
        accept_multiple_files=True,
        help="iPhoneではフォトライブラリを選んで写真を選択できます。",
    )
    upload_submit = st.form_submit_button("選んだ写真をこのフォルダーに入れる")

if upload_submit:
    if not uploaded_files:
        st.warning("先に写真を選択してください。")
    else:
        new_files = [
            f for f in uploaded_files
            if _file_signature(f) not in st.session_state.processed_uploads
        ]
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
                progress.progress(idx / max(len(new_files), 1))

        progress.empty()
        status.empty()
        st.session_state.uploader_version += 1
        st.session_state.gallery_page[folder_num] = 0
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
    page_size = 15
    current_page = st.session_state.gallery_page.get(folder_num, 0)
    max_page = max((len(files) - 1) // page_size, 0)
    current_page = min(current_page, max_page)
    st.session_state.gallery_page[folder_num] = current_page
    start = current_page * page_size
    visible_files = files[start:start + page_size]

    if len(files) > page_size:
        p1, p2, p3 = st.columns([1, 1, 1])
        with p1:
            if st.button("前へ", type="secondary", disabled=current_page == 0, key=f"prev_{folder_num}"):
                st.session_state.gallery_page[folder_num] = max(current_page - 1, 0)
                st.rerun()
        with p2:
            st.markdown(
                f"<div style='text-align:center;padding:.55rem'>{current_page + 1}/{max_page + 1}</div>",
                unsafe_allow_html=True,
            )
        with p3:
            if st.button("次へ", type="secondary", disabled=current_page >= max_page, key=f"next_{folder_num}"):
                st.session_state.gallery_page[folder_num] = min(current_page + 1, max_page)
                st.rerun()

    selected_for_delete = []
    with st.form(f"delete_form_{folder_num}_{current_page}"):
        for row_start in range(0, len(visible_files), 3):
            cols = st.columns(3)
            for offset, col in enumerate(cols):
                idx = row_start + offset
                if idx >= len(visible_files):
                    continue
                absolute_idx = start + idx
                file_info = visible_files[idx]
                file_id = file_info["id"]
                check_key = f"del_{folder_num}_{_safe_key(file_id)}"
                with col:
                    _render_grid_media(file_info)
                    st.markdown(
                        f'<div class="grid-caption">{absolute_idx + 1}. {file_info["name"]}</div>',
                        unsafe_allow_html=True,
                    )
                    checked = st.checkbox("削除", key=check_key)
                    if checked:
                        selected_for_delete.append(file_info)

        delete_submit = st.form_submit_button("チェックした写真を削除する")

    if delete_submit:
        if not selected_for_delete:
            st.warning("削除する写真にチェックを入れてください。")
        else:
            deleted = 0
            for file_info in selected_for_delete:
                try:
                    storage.delete(file_info["id"])
                    deleted += 1
                except Exception as e:
                    st.error(f"{file_info['name']} の削除に失敗: {e}")
            st.success(f"{deleted}件削除しました。")
            for key in list(st.session_state.keys()):
                if key.startswith(f"del_{folder_num}_"):
                    del st.session_state[key]
            st.rerun()

st.markdown(
    '<div class="notice">このフォルダーの確認が終わったら「保存して閉じる」。'
    '全部のフォルダーに入れ終わったらホームへ戻ってリール作成へ進んでください。</div>',
    unsafe_allow_html=True,
)
