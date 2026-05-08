"""
リール作成ページ - Drive API版
パターン選択 + テキスト + 自動生成 → Driveに保存
"""

import os
import sys
import tempfile
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from drive_storage import get_storage_from_streamlit
from batch_producer import BatchProducer

st.set_page_config(
    page_title="リール作成 | Reel Maker",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #0d0d1a; color: #fff; }
  [data-testid="stSidebar"] { background: #12122a; }
  h1 { color: #ff5078 !important; font-size: 1.8rem !important; }
  h2 { color: #fff !important; font-size: 1.2rem !important; }
  h3 { color: #ff5078 !important; font-size: 1.05rem !important; }

  div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #ff5078, #c850c0);
    color: white !important; border: none; border-radius: 14px;
    padding: 1rem !important; font-weight: 700; font-size: 1.1rem !important;
    width: 100%; min-height: 60px;
  }
  div[data-testid="stButton"] > button[kind="secondary"] {
    background: transparent !important; color: #aaa !important;
    border: 1px solid #555 !important; min-height: 40px !important;
    font-size: 0.95rem !important; padding: 0.5rem !important;
  }

  .pattern-card {
    background: #1a1a2e; border: 2px solid #2a2a4a;
    border-radius: 14px; padding: 1rem; margin-bottom: 0.6rem;
  }
  .pattern-card.active {
    border-color: #ff5078; background: #2a1a2e;
    box-shadow: 0 0 20px rgba(255, 80, 120, 0.3);
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

st.title("🎬 リール作成")

# ── プール状況 ────────────────────────────────────────────────────────────────
def _load_pool_files(pool_num: int):
    """Drive から指定 pool のファイル一覧を取得（0_優先ソート）."""
    files = storage.list_files(f"pool_{pool_num}")
    files = [f for f in files if any(
        f.get("mimeType", "").startswith(m) for m in ("image/", "video/")
    )]
    # 0_ で始まるファイルを優先
    priority = [f for f in files if f["name"].startswith("0_")]
    normal = [f for f in files if not f["name"].startswith("0_")]
    priority.sort(key=lambda x: x["name"])
    normal.sort(key=lambda x: x["name"])
    return priority + normal


pools = {n: _load_pool_files(n) for n in range(1, 6)}
counts = {n: len(p) for n, p in pools.items()}

st.markdown("### 📁 プール状況")
for n in range(1, 6):
    c = counts[n]
    icon = "✅" if c > 0 else "⬜"
    color = "#1aaa55" if c > 0 else "#ff8090"
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;'
        f'padding:6px 12px;background:#1a1a2e;border-radius:8px;margin-bottom:4px;">'
        f'<span style="color:{color}">{icon} Pool {n}</span>'
        f'<span style="font-weight:700">{c}枚</span></div>',
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── パターン選択 ─────────────────────────────────────────────────────────────
st.markdown("### 🎯 パターンを選ぶ")

if "pattern" not in st.session_state:
    st.session_state.pattern = "12345"

p = st.session_state.pattern

c1, c2 = st.columns(2)
with c1:
    cls_a = "active" if p == "12345" else ""
    st.markdown(
        f'<div class="pattern-card {cls_a}">'
        f'<h3 style="margin:0;color:{"#ff5078" if p == "12345" else "#fff"}">A: 1-2-3-4-5</h3>'
        f'<div style="color:#aaa;font-size:.9rem">全プール使用<br>5クリップ・素材豊富向け</div>'
        f'</div>', unsafe_allow_html=True,
    )
    if st.button("Aを選択", key="pat_a"):
        st.session_state.pattern = "12345"
        st.rerun()

with c2:
    cls_b = "active" if p == "1231" else ""
    st.markdown(
        f'<div class="pattern-card {cls_b}">'
        f'<h3 style="margin:0;color:{"#ff5078" if p == "1231" else "#fff"}">B: 1-2-3-1</h3>'
        f'<div style="color:#aaa;font-size:.9rem">Pool 1を2回使用<br>4クリップ・素材少なめ向け</div>'
        f'</div>', unsafe_allow_html=True,
    )
    if st.button("Bを選択", key="pat_b"):
        st.session_state.pattern = "1231"
        st.rerun()

# 必須プールチェック
required_pools = sorted(set(int(c) for c in p))
missing = [n for n in required_pools if counts[n] == 0]
if missing:
    st.warning(f"⚠️ Pool {missing} に写真がありません。")

st.markdown("---")

# ── 長さ ───────────────────────────────────────────────────────────────────
st.markdown("### ⏱️ リールの長さ")
length_sec = st.select_slider("全体の長さ（秒）", options=[30, 35, 40, 45, 50, 55, 60], value=45)

n_clips = len(p)
ending_sec = 4
clip_sec = round((length_sec - ending_sec) / n_clips, 1)
st.caption(f"= {n_clips}クリップ × {clip_sec}秒 + エンディング {ending_sec}秒")

st.markdown("---")

# ── テキスト ─────────────────────────────────────────────────────────────────
st.markdown("### ✍️ テキスト（任意）")
title_text = st.text_input("タイトル（最初のクリップに表示）", value="", placeholder="例: 今日のランチ")

st.markdown("---")

# ── 本数 ─────────────────────────────────────────────────────────────────────
st.markdown("### 🎬 生成本数")
num_reels = st.number_input("作る本数", min_value=1, max_value=30, value=1, step=1)

st.markdown("---")

# ── エンディング設定 ──────────────────────────────────────────────────────────
with st.expander("⚙️ エンディング・トランジション"):
    username = st.text_input("Instagramユーザー名", value="@your_account")
    cta_text = st.text_input("CTAテキスト", value="フォローはこちら 👆")
    transition = st.selectbox(
        "トランジション",
        options=config.TRANSITIONS,
        format_func=lambda x: config.TRANSITION_LABELS.get(x, x),
    )

# ── 生成 ─────────────────────────────────────────────────────────────────────
can_gen = not missing
if st.button(f"🎬 {num_reels}本 生成する", disabled=not can_gen):
    try:
        producer = BatchProducer()
        durations = [clip_sec] * n_clips
        progress = st.progress(0)
        status = st.empty()
        uploaded_paths = []

        for i in range(num_reels):
            day = i + 1
            status.info(f"📥 Day {day}: 写真をDrive からダウンロード中...")

            # 各プールから写真を1枚ずつ取得→ローカルにDL
            local_paths = []
            for pos_str in p:
                pool_num = int(pos_str)
                pool_files = pools[pool_num]
                if not pool_files:
                    continue
                f = pool_files[(day - 1) % len(pool_files)]
                ext = os.path.splitext(f["name"])[1] or ".jpg"
                local_paths.append(storage.download_to_temp(f["id"], suffix=ext))

            day_plan = {"day": day, "clips": local_paths}

            status.info(f"🎬 Day {day}: レンダリング中...")
            reel_bar = st.empty()
            bar = reel_bar.progress(0)

            def _cb(pp, _b=bar):
                _b.progress(min(pp, 1.0))

            tmp_out = tempfile.mkdtemp(prefix="reel_")
            local_path = producer.generate_reel(
                day_plan,
                durations=durations,
                ending_duration=ending_sec,
                title_template=title_text or " ",
                username=username,
                cta_text=cta_text,
                transition=transition,
                output_dir=tmp_out,
                progress_callback=_cb,
            )
            reel_bar.empty()

            status.info(f"☁️ Day {day}: Driveへアップロード中...")
            file_id = storage.upload(local_path, "output")
            uploaded_paths.append((os.path.basename(local_path), file_id))

            # クリーンアップ
            for p_local in local_paths:
                try:
                    os.remove(p_local)
                except Exception:
                    pass
            try:
                os.remove(local_path)
            except Exception:
                pass

            progress.progress((i + 1) / num_reels)

        status.success(f"🎉 完了！ {num_reels}本のリールを生成しDriveに保存しました")

        st.markdown("**📁 Driveの保存先:** `マイドライブ / reel_maker / output/`")
        for fname, fid in uploaded_paths:
            link = f"https://drive.google.com/file/d/{fid}/view"
            st.markdown(f"- [{fname}]({link})")

    except Exception as e:
        st.error(f"エラー: {e}")
        raise
