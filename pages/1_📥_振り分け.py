"""
振り分けページ - Drive API版・モバイル最適化
inboxの写真を1枚ずつ大きく表示してpool 1〜5に振り分け
"""

import os
import sys
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

st.title("📥 写真振り分け")

# ── 0番モード切替 ────────────────────────────────────────────────────────────
if "priority_mode" not in st.session_state:
    st.session_state.priority_mode = False

priority = st.toggle(
    "⭐ 0番モード（次に振り分ける写真を最優先に）",
    value=st.session_state.priority_mode,
)
st.session_state.priority_mode = priority

st.markdown("---")

# ── inbox 取得 ────────────────────────────────────────────────────────────
photos = storage.list_files("inbox")
# 画像/動画のみ（modifiedTimeで古い順）
IMG_MIMES = ("image/", "video/")
photos = [f for f in photos if any(f.get("mimeType", "").startswith(m) for m in IMG_MIMES)]
# スキップ済みは末尾に回す
skipped = st.session_state.get("skipped_ids", set())
non_skipped = [f for f in photos if f["id"] not in skipped]
skipped_list = [f for f in photos if f["id"] in skipped]
photos = non_skipped + skipped_list

if not photos:
    st.info("📭 inboxは空です")
    st.markdown("""
    **写真の保存方法:**

    📱 **iPhone から:**
    1. LINE で写真を長押し → 「保存」（カメラロール経由）
    2. Google Drive アプリを開く → `reel_maker/inbox` フォルダへアップロード

    💻 **Mac から:**
    1. LINE Mac で写真を右クリック → 「画像を保存」
    2. Drive Desktop の `reel_maker/inbox/` を保存先に選択

    保存後、下のボタンで再読み込みしてください。
    """)
    if st.button("🔄 再読み込み", key="reload"):
        st.cache_resource.clear()
        st.rerun()
    st.stop()

# ── プログレス ────────────────────────────────────────────────────────────────
total = len(photos) + st.session_state.get("sorted_count", 0)
sorted_n = st.session_state.get("sorted_count", 0)
pct = int((sorted_n / total) * 100) if total > 0 else 0
st.markdown(
    f'<div class="progress-bar"><div class="progress-fill" style="width:{pct}%"></div></div>'
    f'<div style="text-align:center; color:#aaa; margin-bottom:1rem;">'
    f'残り {len(photos)}枚 / 全{total}枚</div>',
    unsafe_allow_html=True,
)

# ── 現在の写真を表示 ─────────────────────────────────────────────────────────
photo = photos[0]
photo_id = photo["id"]
photo_name = photo["name"]
mime = photo.get("mimeType", "")

# Drive のサムネイルURL（800px幅）
thumb_url = storage.get_thumbnail_url(photo_id)

if mime.startswith("video/"):
    st.info(f"🎬 動画: {photo_name}（プレビュー省略）")
else:
    st.markdown(
        f'<img src="{thumb_url}" style="width:100%;border-radius:12px;'
        f'box-shadow:0 4px 24px rgba(0,0,0,0.4);" />',
        unsafe_allow_html=True,
    )

st.caption(f"📄 {photo_name}")

# ── 振り分けボタン（1〜5） ───────────────────────────────────────────────────
st.markdown("### このカテゴリへ")
cols = st.columns(5)
for i, col in enumerate(cols, start=1):
    with col:
        if st.button(str(i), key=f"sort_{i}"):
            new_name = photo_name
            if priority and not new_name.startswith("0_"):
                new_name = "0_" + new_name
            try:
                storage.move(photo_id, f"pool_{i}",
                             new_name=new_name if new_name != photo_name else None)
                st.session_state.sorted_count = sorted_n + 1
                st.rerun()
            except Exception as e:
                st.error(f"移動失敗: {e}")

# ── スキップ・削除 ────────────────────────────────────────────────────────────
st.markdown('<div class="secondary-row">', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    if st.button("⏭️ スキップ", key="skip"):
        # 末尾扱いにするには削除→再Upしか無いので、いったん非表示用にセッションに記録
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
