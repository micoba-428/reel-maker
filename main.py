"""
Reel Maker - ホーム画面（Drive API対応・モバイル最適化）
"""

import os
import sys
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drive_storage import get_storage_from_streamlit
import config

st.set_page_config(
    page_title="Reel Maker ✨",
    page_icon="🌸",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── iPhoneホーム画面アイコン & ファビコン注入 ──────────────────────────────
ICON_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FF5078"/>
      <stop offset="60%" stop-color="#C850C0"/>
      <stop offset="100%" stop-color="#8B5CF6"/>
    </linearGradient>
    <linearGradient id="shine" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="white" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="white" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <!-- Background rounded rect -->
  <rect width="200" height="200" rx="44" fill="url(#bg)"/>
  <rect width="200" height="200" rx="44" fill="url(#shine)"/>

  <!-- Camera body -->
  <rect x="34" y="72" width="132" height="90" rx="18" fill="white" opacity="0.92"/>
  <!-- Lens ring outer -->
  <circle cx="100" cy="117" r="32" fill="#F0A0C0" opacity="0.5"/>
  <!-- Lens ring inner -->
  <circle cx="100" cy="117" r="24" fill="url(#bg)" opacity="0.9"/>
  <!-- Lens highlight -->
  <circle cx="100" cy="117" r="16" fill="white" opacity="0.15"/>
  <circle cx="92" cy="109" r="5" fill="white" opacity="0.55"/>
  <!-- Viewfinder bump -->
  <rect x="70" y="56" width="60" height="22" rx="10" fill="white" opacity="0.92"/>
  <!-- Flash dot -->
  <circle cx="148" cy="84" r="7" fill="#FFD6E0" opacity="0.9"/>

  <!-- Sparkles -->
  <text x="22" y="54" font-size="22" fill="white" opacity="0.8">✦</text>
  <text x="155" y="44" font-size="14" fill="white" opacity="0.65">✦</text>
  <text x="16" y="158" font-size="11" fill="white" opacity="0.5">✦</text>
  <text x="158" y="170" font-size="18" fill="white" opacity="0.7">✦</text>

  <!-- Highlight strip -->
  <rect x="34" y="72" width="132" height="28" rx="18" fill="white" opacity="0.12"/>
</svg>
"""

import base64
import streamlit.components.v1 as components

svg_b64 = base64.b64encode(ICON_SVG.encode()).decode()

# st.components.v1.html で <script> を実行（iframeから親ドキュメントへ注入）
components.html(f"""
<script>
(function() {{
  var pd = window.parent.document;
  var link180 = pd.createElement('link');
  link180.rel = 'apple-touch-icon';
  link180.sizes = '180x180';
  link180.href = 'data:image/svg+xml;base64,{svg_b64}';
  pd.head.appendChild(link180);

  var metaCapable = pd.createElement('meta');
  metaCapable.name = 'apple-mobile-web-app-capable';
  metaCapable.content = 'yes';
  pd.head.appendChild(metaCapable);

  var metaTitle = pd.createElement('meta');
  metaTitle.name = 'apple-mobile-web-app-title';
  metaTitle.content = 'Reel Maker';
  pd.head.appendChild(metaTitle);

  var metaColor = pd.createElement('meta');
  metaColor.name = 'apple-mobile-web-app-status-bar-style';
  metaColor.content = 'black-translucent';
  pd.head.appendChild(metaColor);

  var favicon = pd.querySelector("link[rel*='icon']");
  if (!favicon) {{
    favicon = pd.createElement('link');
    favicon.rel = 'icon';
    pd.head.appendChild(favicon);
  }}
  favicon.type = 'image/svg+xml';
  favicon.href = 'data:image/svg+xml;base64,{svg_b64}';
}})();
</script>
""", height=0)

# ── モバイルファーストのCSS ───────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stAppViewContainer"] {
    background: linear-gradient(160deg, #0d0d1a 0%, #1a0d2e 100%);
    color: #fff;
  }
  [data-testid="stHeader"] { background: transparent; }
  [data-testid="stSidebar"] { background: #12122a; }

  h1 { color: #ff5078 !important; font-size: 2rem !important; }
  h2 { color: #fff !important; font-size: 1.3rem !important; }
  h3 { color: #ff9ab0 !important; font-size: 1.1rem !important; }

  div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #ff5078, #c850c0);
    color: white !important; border: none; border-radius: 16px;
    padding: 1.5rem 1rem !important;
    font-weight: 700; font-size: 1.1rem !important;
    width: 100%; min-height: 90px;
    margin-bottom: 0.6rem; line-height: 1.4;
    box-shadow: 0 4px 20px rgba(255, 80, 120, 0.3);
  }
  div[data-testid="stButton"] > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(255, 80, 120, 0.45);
  }

  .status-card {
    background: linear-gradient(135deg, #1a1a2e, #2a1a3e);
    border: 1px solid #3a2a5a;
    border-radius: 18px; padding: 16px 20px; margin-bottom: 16px;
    box-shadow: 0 4px 20px rgba(200, 80, 192, 0.1);
  }
  .status-row {
    display: flex; justify-content: space-between;
    padding: 7px 0; border-bottom: 1px solid #2a2a4a;
  }
  .status-row:last-child { border-bottom: none; }
  .status-label { color: #bbb; font-size: 0.95rem; }
  .status-value { color: #fff; font-weight: 700; }
  .pool-empty .status-label { color: #ff8090 !important; }
  .pool-ok .status-label { color: #80e0a0 !important; }

  .app-hero {
    text-align: center;
    padding: 1rem 0 0.5rem;
  }
  .app-hero .icon {
    font-size: 3.5rem;
    display: block;
    margin-bottom: 0.2rem;
    filter: drop-shadow(0 4px 12px rgba(255,80,120,0.5));
  }
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
st.markdown('<div class="app-hero"><span class="icon">🌸</span></div>', unsafe_allow_html=True)
st.title("Reel Maker")
st.caption("写真を選んで → 振り分けて → リール自動生成")

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
    '<div class="status-row"><span class="status-label">📁 フォルダー状況</span>'
    '<span class="status-value">　</span></div>',
    unsafe_allow_html=True,
)
for n, c in enumerate(pool_counts, 1):
    name = config.POOL_NAMES[n]
    state = "ok" if c > 0 else "empty"
    icon = "✅" if c > 0 else "⬜"
    st.markdown(
        f'<div class="status-row pool-{state}">'
        f'<span class="status-label">{icon} {n}.{name}</span>'
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

label1 = f"📸 写真を選んで振り分ける\n（{inbox_count}枚 待機中）" if inbox_count > 0 else "📸 写真を選んで振り分ける"
if st.button(label1):
    _switch_page("pages/1_📥_振り分け.py")

if st.button("🎬 リールを作る\nパターンを選んで自動生成"):
    _switch_page("pages/2_🎬_リール作成.py")

if st.button("⚙️ 設定\n保存先・共有Drive・テキスト"):
    _switch_page("pages/3_⚙️_設定.py")

with st.expander("ℹ️ 使い方"):
    st.markdown("""
    **基本フロー**
    1. **📸 写真を選ぶ** → カメラロールから直接アップロード or Drive の `inbox` フォルダへ
    2. **振り分け** でフォルダを選んで分類（ワンタップ）
    3. **🎬 リール作成** でパターンと長さを選んで生成
    4. 出力されたMP4は**Google Drive**に自動保存

    **フォルダー構成**
    - **1. 外の外観** → お店の外観・外観写真
    - **2. ランチ** → ランチメニューの写真
    - **3. デザート＆ドリンク** → スイーツ・ドリンク
    - **4. 室内** → 店内・インテリア
    - **5. その他** → その他の素材

    **パターン**
    - **1-2-3-4-5**: 全フォルダから1枚ずつ（5クリップ）
    - **1-2-3-1**: 外観を2回使う（4クリップ）
    """)
