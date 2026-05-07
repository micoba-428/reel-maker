"""
設定ページ - 共有Drive・出力先・LINE保存先の確認
"""

import os
import sys
import json
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

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
    font-size: 0.95rem !important; padding: 0.5rem !important;
  }

  .info-card {
    background: #1a1a2e; border: 1px solid #2a2a4a;
    border-radius: 12px; padding: 14px; margin-bottom: 10px;
  }
  .info-card code { color: #ff8090; word-break: break-all; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)


# ── 戻るボタン ───────────────────────────────────────────────────────────────
if st.button("← ホームに戻る", type="secondary", key="back"):
    st.switch_page("main.py")

st.title("⚙️ 設定")


SETTINGS_FILE = os.path.join(config.DATA_ROOT, "settings.json")


def _load_settings() -> dict:
    if os.path.isfile(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_settings(s: dict):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)


settings = _load_settings()

# ── パス情報 ────────────────────────────────────────────────────────────────
st.markdown("### 📍 保存先パス")

st.markdown('<div class="info-card">', unsafe_allow_html=True)
st.markdown("**📥 LINE保存先（inbox）**")
st.code(config.INBOX_DIR, language="text")
st.caption("LINE Mac → 写真を右クリック → 画像を保存 → 上のフォルダを選択")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="info-card">', unsafe_allow_html=True)
st.markdown("**📁 プールフォルダ（pool_1〜pool_5）**")
st.code(config.POOL_BASE, language="text")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="info-card">', unsafe_allow_html=True)
st.markdown("**🎬 出力先（生成リール）**")
default_output = os.path.join(config.DATA_ROOT, "output")
output_path = settings.get("output_dir", default_output)
new_output = st.text_input(
    "出力先パス",
    value=output_path,
    help="共有Driveパスに変更すると、投稿アカウントから直接アクセスできます",
)
if new_output != output_path:
    settings["output_dir"] = new_output
    _save_settings(settings)
    st.success("保存しました")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# ── 共有Driveの設定方法 ──────────────────────────────────────────────────────
st.markdown("### 🤝 共有Driveの使い方")
st.markdown("""
**投稿アカウントと共有する手順:**
1. Google Drive で `reel_maker` フォルダを右クリック
2. 「共有」→ 投稿アカウントのGmailアドレスを追加
3. 権限は「**編集者**」に設定
4. 投稿アカウント側でも Drive Desktop でアクセス可能になります

これで投稿アカウントから生成済みリールを直接 Instagram に予約投稿できます。
""")

st.markdown("---")

# ── デフォルト値 ──────────────────────────────────────────────────────────────
st.markdown("### 🎨 デフォルト設定")

with st.form("defaults"):
    default_username = st.text_input(
        "Instagramユーザー名",
        value=settings.get("username", "@your_account"),
    )
    default_cta = st.text_input(
        "CTAテキスト",
        value=settings.get("cta_text", "フォローはこちら 👆"),
    )
    default_length = st.select_slider(
        "デフォルトのリール長さ（秒）",
        options=[30, 35, 40, 45, 50, 55, 60],
        value=settings.get("default_length", 45),
    )

    if st.form_submit_button("💾 保存"):
        settings.update({
            "username": default_username,
            "cta_text": default_cta,
            "default_length": default_length,
        })
        _save_settings(settings)
        st.success("✅ 設定を保存しました")

st.markdown("---")

# ── システム情報 ─────────────────────────────────────────────────────────────
st.markdown("### ℹ️ システム情報")
with st.expander("詳細"):
    st.code(f"""
DATA_ROOT  : {config.DATA_ROOT}
BASE_DIR   : {config.BASE_DIR}
DRIVE_REEL : {config.DRIVE_REEL_DIR or "未検出"}
    """.strip())
