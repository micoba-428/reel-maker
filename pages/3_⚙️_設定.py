"""
設定ページ - Drive 構成・共有方法のガイド
"""

import os
import sys
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from drive_storage import get_storage_from_streamlit

st.set_page_config(
    page_title="設定 | Reel Maker",
    page_icon="⚙️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #0d0d1a; color: #fff; }
  [data-testid="stSidebar"] { background: #12122a; }
  h1 { color: #ff5078 !important; font-size: 1.8rem !important; }
  h3 { color: #ff5078 !important; font-size: 1.05rem !important; }

  div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #ff5078, #c850c0);
    color: white !important; border: none; border-radius: 14px;
    padding: 0.8rem !important; font-weight: 700; font-size: 1rem !important;
    width: 100%; min-height: 50px;
  }
  div[data-testid="stButton"] > button[kind="secondary"] {
    background: transparent !important; color: #aaa !important;
    border: 1px solid #555 !important; min-height: 40px !important;
    font-size: 0.95rem !important;
  }

  .info-card {
    background: #1a1a2e; border: 1px solid #2a2a4a;
    border-radius: 12px; padding: 14px; margin-bottom: 10px;
  }
  .info-card code { color: #ff8090; word-break: break-all; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_storage():
    return get_storage_from_streamlit()

try:
    storage = get_storage()
    drive_ok = True
except Exception as e:
    storage = None
    drive_ok = False
    drive_err = str(e)

# ── 戻るボタン ───────────────────────────────────────────────────────────────
if st.button("← ホームに戻る", type="secondary", key="back"):
    st.switch_page("main.py")

st.title("⚙️ 設定")

# ── 接続状態 ─────────────────────────────────────────────────────────────────
st.markdown("### ☁️ Google Drive 接続状況")
if drive_ok:
    st.success("✅ 接続成功")
    root = storage.root_id()
    if root and not str(root).startswith("/"):
        drive_url = f"https://drive.google.com/drive/folders/{root}"
        st.markdown(f"[Driveでフォルダを開く]({drive_url})")
    else:
        st.caption("この環境ではアプリ内の作業領域へ保存します。")
else:
    st.error(f"❌ 接続エラー: {drive_err}")

st.markdown("---")

# ── 写真追加方法 ────────────────────────────────────────────────────────────
st.markdown("### 📥 写真アプリから追加")
st.markdown("""
**📱 iPhone:**
1. アプリの「📥 写真を追加する」を開く
2. 追加先のPoolを選ぶ
3. 「写真を選択」からフォトライブラリの写真を選ぶ
4. 「Poolに追加する」でGoogle Driveへ保存

**💻 Mac:**
1. アプリの「📥 写真を追加する」を開く
2. 追加先のPoolを選ぶ
3. 写真ファイルを選択して「Poolに追加する」
""")

st.markdown("---")

# ── 投稿アカウントとの共有 ────────────────────────────────────────────────────
st.markdown("### 🤝 投稿アカウントと共有")
st.markdown("""
**手順:**
1. Google Drive で `reel_maker` フォルダを右クリック
2. 「共有」→ 投稿用アカウントのGmailを追加
3. 権限: **編集者**
4. 完了

これで投稿用アカウントから直接 `output` フォルダの動画にアクセスでき、
Instagram Creator Studioや予約投稿アプリ（Later, Buffer等）から投稿できます。
""")

st.markdown("---")

# ── システム情報 ─────────────────────────────────────────────────────────────
with st.expander("ℹ️ システム情報"):
    if drive_ok:
        st.code(f"Drive root_id: {storage.root_id()}")
    else:
        st.code("Drive 未接続")
