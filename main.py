"""
Reel Maker - ホーム画面（Drive API対応・モバイル最適化）
"""

import os
import sys
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drive_storage import get_storage_from_streamlit

st.set_page_config(
    page_title="Reel Maker",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── モバイルファーストのCSS ───────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #0d0d1a; color: #fff; }
  [data-testid="stHeader"] { background: transparent; }
  [data-testid="stSidebar"] { background: #12122a; }

  h1 { color: #ff5078 !important; font-size: 2rem !important; }
  h2 { color: #fff !important; font-size: 1.3rem !important; }
  h3 { color: #ff5078 !important; font-size: 1.1rem !important; }

  div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #ff5078, #c850c0);
    color: white !important; border: none; border-radius: 16px;
    padding: 1.5rem 1rem !important;
    font-weight: 700; font-size: 1.1rem !important;
    width: 100%; min-height: 90px;
    margin-bottom: 0.6rem; line-height: 1.4;
    box-shadow: 0 4px 20px rgba(255, 80, 120, 0.25);
  }
  div[data-testid="stButton"] > button:hover { transform: translateY(-2px); }

  .status-card {
    background: #1a1a2e; border: 1px solid #2a2a4a;
    border-radius: 14px; padding: 14px 18px; margin-bottom: 12px;
  }
  .status-row {
    display: flex; justify-content: space-between;
    padding: 6px 0; border-bottom: 1px solid #2a2a4a;
  }
  .status-row:last-child { border-bottom: none; }
  .status-label { color: #aaa; font-size: 0.95rem; }
  .status-value { color: #fff; font-weight: 700; }
  .pool-empty .status-label { color: #ff8090 !important; }
  .pool-ok .status-label { color: #1aaa55 !important; }
</style>
""", unsafe_allow_html=True)


# ── Drive 接続 ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_storage():
    return get_storage_from_streamlit()

try:
    storage = get_storage()
except Exception as e:
    st.error(f"Drive接続エラー: {e}")
    st.stop()


def _switch_page(page_name: str):
    try:
        st.switch_page(page_name)
    except Exception:
        st.rerun()


# ── ヘッダー ──────────────────────────────────────────────────────────────────
st.title("🎬 Reel Maker")
st.caption("LINEから保存 → 振り分け → リール自動生成")

# ── 状況サマリー ─────────────────────────────────────────────────────────────
inbox_count = len(storage.list_files("inbox"))
pool_counts = [len(storage.list_files(f"pool_{n}")) for n in range(1, 6)]

st.markdown('<div class="status-card">', unsafe_allow_html=True)
st.markdown(
    f'<div class="status-row"><span class="status-label">📥 振り分け待ち</span>'
    f'<span class="status-value">{inbox_count}枚</span></div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="status-row"><span class="status-label">📁 プール状況</span>'
    '<span class="status-value">　</span></div>',
    unsafe_allow_html=True,
)
for n, c in enumerate(pool_counts, 1):
    state = "ok" if c > 0 else "empty"
    icon = "✅" if c > 0 else "⬜"
    st.markdown(
        f'<div class="status-row pool-{state}">'
        f'<span class="status-label">{icon} Pool {n}</span>'
        f'<span class="status-value">{c}枚</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown(
    '<div class="status-row"><span class="status-label">💾 保存先</span>'
    '<span class="status-value">☁️ Google Drive</span></div>',
    unsafe_allow_html=True,
)
st.markdown('</div>', unsafe_allow_html=True)

# ── ナビゲーションボタン ─────────────────────────────────────────────────────
st.markdown("### メニュー")

label1 = f"📥 写真を振り分ける\n（{inbox_count}枚 待機中）" if inbox_count > 0 else "📥 写真を振り分ける"
if st.button(label1):
    _switch_page("pages/1_📥_振り分け.py")

if st.button("🎬 リールを作る\nパターンを選んで自動生成"):
    _switch_page("pages/2_🎬_リール作成.py")

if st.button("⚙️ 設定\n保存先・共有Drive・テキスト"):
    _switch_page("pages/3_⚙️_設定.py")

with st.expander("ℹ️ 使い方"):
    st.markdown("""
    **基本フロー**
    1. **LINEから写真を保存** → Drive の `inbox` フォルダへ
    2. **📥 振り分け** で各写真をpool 1〜5に分類（ワンタップ）
    3. **🎬 リール作成** でパターンと長さを選んで生成
    4. 出力されたMP4は**Drive**に自動保存

    **パターン**
    - **1-2-3-4-5**: 全プールから1枚ずつ（5クリップ）
    - **1-2-3-1**: pool 1を2回使う（4クリップ）

    **0番優先**
    ファイル名が `0_` で始まる写真は優先的に最初に使われます
    """)
