"""
振り分けページ - モバイル最適化
1枚ずつ大きく表示して、大きなボタンでpool 1〜5に振り分け
"""

import os
import sys
import shutil

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

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

  /* 大きな番号ボタン（タップしやすく） */
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

  /* 戻るボタン */
  div[data-testid="stButton"] > button[kind="secondary"] {
    background: transparent !important; color: #aaa !important;
    border: 1px solid #555 !important; min-height: 40px !important;
    font-size: 0.95rem !important;
  }

  /* 削除・スキップ */
  .secondary-row div[data-testid="stButton"] > button {
    background: #444; font-size: 0.9rem; min-height: 50px;
  }

  /* プログレス */
  .progress-bar {
    background: #2a2a4a; border-radius: 10px; height: 8px;
    overflow: hidden; margin: 10px 0;
  }
  .progress-fill {
    background: linear-gradient(90deg, #ff5078, #c850c0);
    height: 100%;
  }
</style>
""", unsafe_allow_html=True)


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".mp4", ".mov"}


def _scan_inbox():
    d = config.INBOX_DIR
    os.makedirs(d, exist_ok=True)
    files = []
    for f in os.listdir(d):
        if f.startswith("."):
            continue
        if os.path.splitext(f)[1].lower() in IMAGE_EXTS:
            full = os.path.join(d, f)
            files.append((full, os.path.getmtime(full)))
    files.sort(key=lambda x: x[1])
    return [f for f, _ in files]


def _move_to_pool(src: str, pool_num: int, priority: bool):
    dest_dir = os.path.join(config.POOL_BASE, f"pool_{pool_num}")
    os.makedirs(dest_dir, exist_ok=True)
    base = os.path.basename(src)
    if priority and not base.startswith("0_"):
        base = "0_" + base
    dest = os.path.join(dest_dir, base)
    if os.path.exists(dest):
        stem, ext = os.path.splitext(base)
        for i in range(2, 999):
            cand = os.path.join(dest_dir, f"{stem}_{i}{ext}")
            if not os.path.exists(cand):
                dest = cand
                break
    shutil.move(src, dest)


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

photos = _scan_inbox()

if not photos:
    st.info("📭 inboxは空です")
    st.markdown(f"""
    **写真の保存先:**
    ```
    {config.INBOX_DIR}
    ```

    LINE Mac → 写真を右クリック → 「画像を保存」→ 上のフォルダを選択

    保存後、下のボタンで再読み込みしてください。
    """)
    if st.button("🔄 再読み込み", key="reload"):
        st.rerun()
    st.stop()

# ── プログレスバー ────────────────────────────────────────────────────────────
total = len(photos) + st.session_state.get("sorted_count", 0)
sorted_n = st.session_state.get("sorted_count", 0)
pct = int((sorted_n / total) * 100) if total > 0 else 0

st.markdown(
    f'<div class="progress-bar"><div class="progress-fill" style="width:{pct}%"></div></div>'
    f'<div style="text-align:center; color:#aaa; margin-bottom:1rem;">'
    f'残り {len(photos)}枚 / 全{total}枚</div>',
    unsafe_allow_html=True,
)

# ── 現在の写真を1枚大きく表示 ────────────────────────────────────────────────
photo_path = photos[0]
ext = os.path.splitext(photo_path)[1].lower()

if ext in {".mp4", ".mov"}:
    st.video(photo_path)
else:
    try:
        st.image(photo_path, use_container_width=True)
    except Exception:
        st.warning(f"表示不可: {os.path.basename(photo_path)}")

st.caption(f"📄 {os.path.basename(photo_path)}")

# ── 振り分けボタン（1〜5） ───────────────────────────────────────────────────
st.markdown("### このカテゴリへ")
cols = st.columns(5)
for i, col in enumerate(cols, start=1):
    with col:
        if st.button(str(i), key=f"sort_{i}"):
            _move_to_pool(photo_path, i, priority=priority)
            st.session_state.sorted_count = sorted_n + 1
            st.rerun()

# ── スキップ・削除 ────────────────────────────────────────────────────────────
st.markdown('<div class="secondary-row">', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    if st.button("⏭️ スキップ", key="skip"):
        # 末尾に移動（ファイル日時を更新）
        os.utime(photo_path, None)
        st.rerun()
with c2:
    if st.button("🗑️ 削除", key="delete"):
        os.remove(photo_path)
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)
