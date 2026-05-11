"""
振り分けページ - Drive API版・モバイル最適化
カメラロールから直接アップロード or inboxの写真を1枚ずつ表示してフォルダに振り分け
"""

import os
import sys
import io
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from drive_storage import get_storage_from_streamlit
import config

st.set_page_config(
    page_title="振り分け | Reel Maker",
    page_icon="📸",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  [data-testid="stAppViewContainer"] {
    background: linear-gradient(160deg, #0d0d1a 0%, #1a0d2e 100%);
    color: #fff;
  }
  [data-testid="stSidebar"] { background: #12122a; }
  h1 { color: #ff5078 !important; font-size: 1.8rem !important; }
  h3 { color: #ff9ab0 !important; }

  /* 振り分けボタン（大きめ、フォルダ名表示） */
  .sort-btn div[data-testid="stButton"] > button {
    background: #1e1e3a;
    color: white; border: 2px solid #3a2a5a;
    border-radius: 14px; padding: 0.8rem 0.3rem;
    font-weight: 800; font-size: 1.1rem;
    width: 100%; min-height: 76px;
    line-height: 1.3;
  }
  .sort-btn div[data-testid="stButton"] > button:hover {
    background: linear-gradient(135deg, #ff5078, #c850c0);
    border-color: #ff5078; transform: scale(1.03);
  }

  div[data-testid="stButton"] > button[kind="secondary"] {
    background: transparent !important; color: #aaa !important;
    border: 1px solid #555 !important; min-height: 40px !important;
    font-size: 0.95rem !important;
  }
  .secondary-row div[data-testid="stButton"] > button {
    background: #333; font-size: 0.9rem; min-height: 50px;
  }
  .progress-bar {
    background: #2a2a4a; border-radius: 10px; height: 8px;
    overflow: hidden; margin: 10px 0;
  }
  .progress-fill {
    background: linear-gradient(90deg, #ff5078, #c850c0); height: 100%;
  }

  /* アップロードエリア */
  [data-testid="stFileUploader"] {
    background: #1a1a2e; border: 2px dashed #3a2a5a;
    border-radius: 16px; padding: 1rem;
  }
  [data-testid="stFileUploader"] label {
    color: #ff9ab0 !important; font-weight: 700;
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

st.title("📸 写真振り分け")

# ═══════════════════════════════════════════════════════════════════════
# タブ：カメラロールアップロード  /  inbox振り分け
# ═══════════════════════════════════════════════════════════════════════
tab_upload, tab_sort = st.tabs(["📱 カメラロールから追加", "📂 振り分け"])

# ────────────────────────────────────────────────────────────────────────
# タブ1: カメラロール / ファイルから直接アップロード
# ────────────────────────────────────────────────────────────────────────
with tab_upload:
    st.markdown("### 写真・動画を選択")
    st.caption("iPhoneのカメラロール・Macの写真アプリから直接選べます")

    uploaded_files = st.file_uploader(
        "写真・動画を選択（複数OK）",
        type=["jpg", "jpeg", "png", "webp", "heic", "mp4", "mov", "gif"],
        accept_multiple_files=True,
        key="file_uploader",
        label_visibility="collapsed",
    )

    if uploaded_files:
        st.markdown(f"**{len(uploaded_files)}枚** 選択されました")

        # どのフォルダに入れるか選択
        st.markdown("#### 振り分け先フォルダを選択")
        folder_options = {f"{n}. {config.POOL_NAMES[n]}": n for n in range(1, 6)}
        folder_options["📥 未分類（inbox）"] = 0

        selected_folder_label = st.selectbox(
            "フォルダを選択",
            list(folder_options.keys()),
            label_visibility="collapsed",
        )
        target_folder_num = folder_options[selected_folder_label]

        # 優先モード
        priority = st.checkbox("⭐ 優先（0_プレフィックスを付ける）", value=False)

        # プレビュー表示
        cols_preview = st.columns(min(len(uploaded_files), 3))
        for i, f in enumerate(uploaded_files[:3]):
            with cols_preview[i]:
                if f.type.startswith("image/"):
                    st.image(f, use_container_width=True)
                else:
                    st.info(f"🎬 {f.name}")

        if len(uploaded_files) > 3:
            st.caption(f"… 他 {len(uploaded_files) - 3}件")

        if st.button("☁️ Driveにアップロード", type="primary", key="do_upload"):
            target_folder = f"pool_{target_folder_num}" if target_folder_num > 0 else "inbox"
            progress_bar = st.progress(0)
            status_text = st.empty()
            success_count = 0

            for i, f in enumerate(uploaded_files):
                file_name = f.name
                if priority and not file_name.startswith("0_"):
                    file_name = "0_" + file_name

                status_text.text(f"アップロード中... {i+1}/{len(uploaded_files)}: {f.name}")
                try:
                    file_bytes = f.read()
                    storage.upload_bytes(
                        file_bytes=file_bytes,
                        filename=file_name,
                        folder_name=target_folder,
                        mime_type=f.type,
                    )
                    success_count += 1
                except Exception as e:
                    st.warning(f"❌ {f.name}: {e}")

                progress_bar.progress((i + 1) / len(uploaded_files))

            status_text.empty()
            progress_bar.empty()

            if success_count > 0:
                folder_label = selected_folder_label
                st.success(f"✅ {success_count}枚を **{folder_label}** にアップロードしました！")
                st.cache_resource.clear()
                st.rerun()

# ────────────────────────────────────────────────────────────────────────
# タブ2: inbox の写真を1枚ずつ振り分け
# ────────────────────────────────────────────────────────────────────────
with tab_sort:

    # 0番モード切替
    if "priority_mode" not in st.session_state:
        st.session_state.priority_mode = False

    priority_sort = st.toggle(
        "⭐ 0番モード（優先ファイルとして最前列に）",
        value=st.session_state.priority_mode,
    )
    st.session_state.priority_mode = priority_sort

    st.markdown("---")

    # inbox 取得
    photos = storage.list_files("inbox")
    IMG_MIMES = ("image/", "video/")
    photos = [f for f in photos if any(f.get("mimeType", "").startswith(m) for m in IMG_MIMES)]
    skipped = st.session_state.get("skipped_ids", set())
    non_skipped = [f for f in photos if f["id"] not in skipped]
    skipped_list = [f for f in photos if f["id"] in skipped]
    photos = non_skipped + skipped_list

    if not photos:
        st.info("📭 振り分け待ちの写真はありません")
        st.markdown("""
        **📱 カメラロールから追加するには**
        「カメラロールから追加」タブで写真を選択してください。
        """)
        if st.button("🔄 再読み込み", key="reload_sort"):
            st.cache_resource.clear()
            st.rerun()
        st.stop()

    # プログレス
    total = len(photos) + st.session_state.get("sorted_count", 0)
    sorted_n = st.session_state.get("sorted_count", 0)
    pct = int((sorted_n / total) * 100) if total > 0 else 0
    st.markdown(
        f'<div class="progress-bar"><div class="progress-fill" style="width:{pct}%"></div></div>'
        f'<div style="text-align:center; color:#aaa; margin-bottom:1rem;">'
        f'残り {len(photos)}枚 / 全{total}枚</div>',
        unsafe_allow_html=True,
    )

    # 現在の写真を表示
    photo = photos[0]
    photo_id = photo["id"]
    photo_name = photo["name"]
    mime = photo.get("mimeType", "")

    thumb_url = storage.get_thumbnail_url(photo_id)

    if mime.startswith("video/"):
        st.info(f"🎬 動画: {photo_name}")
    else:
        st.markdown(
            f'<img src="{thumb_url}" style="width:100%;border-radius:14px;'
            f'box-shadow:0 4px 24px rgba(200,80,192,0.3);" />',
            unsafe_allow_html=True,
        )

    st.caption(f"📄 {photo_name}")

    # ── 振り分けボタン（フォルダ名付き） ────────────────────────────────
    st.markdown("### どのフォルダに入れますか？")
    st.markdown('<div class="sort-btn">', unsafe_allow_html=True)
    cols = st.columns(5)
    for i, col in enumerate(cols, start=1):
        folder_name = config.POOL_NAMES[i]
        with col:
            if st.button(f"{i}\n{folder_name}", key=f"sort_{i}"):
                new_name = photo_name
                if priority_sort and not new_name.startswith("0_"):
                    new_name = "0_" + new_name
                try:
                    storage.move(photo_id, f"pool_{i}",
                                 new_name=new_name if new_name != photo_name else None)
                    st.session_state.sorted_count = sorted_n + 1
                    st.rerun()
                except Exception as e:
                    st.error(f"移動失敗: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

    # スキップ・削除
    st.markdown('<div class="secondary-row">', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("⏭️ スキップ", key="skip"):
            skipped = st.session_state.get("skipped_ids", set())
            skipped.add(photo_id)
            st.session_state.skipped_ids = skipped
            st.rerun()
    with c2:
        if st.button("🗑️ 削除", key="delete"):
            try:
                storage.delete(photo_id)
                st.rerun()
            except Exception as e:
                st.error(f"削除失敗: {e}")
    st.markdown('</div>', unsafe_allow_html=True)
