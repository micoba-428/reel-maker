import os
import glob

# Instagram Reel specs
TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
FPS = 30
VIDEO_BITRATE = "8000k"
AUDIO_BITRATE = "192k"

# Timing defaults
DEFAULT_IMAGE_DURATION = 4.0   # seconds per still image
TRANSITION_DURATION = 0.6      # seconds for transitions
DEFAULT_ENDING_DURATION = 3.5  # seconds for ending CTA screen

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")

# ── Data location auto-detection ──────────────────────────────────────────────
# 構造:  <data root>/app/<this file>   ←  app コードの親=データルート
#       <data root>/pool_1〜pool_5/   ←  写真プール
#       <data root>/output/           ←  生成MP4
#
# 1. BASE_DIR が "<...>/reel_maker/app" 形式 → 親 (reel_maker) をDATA_ROOTに
# 2. それ以外（旧構造で実行）→ Drive をスキャンしてDATA_ROOTを推定
def _resolve_data_root() -> str:
    parent = os.path.dirname(BASE_DIR)
    if os.path.basename(BASE_DIR) == "app" and os.path.basename(parent) == "reel_maker":
        return parent
    cloud = os.path.expanduser("~/Library/CloudStorage")
    if os.path.isdir(cloud):
        candidates = glob.glob(os.path.join(cloud, "GoogleDrive-*/マイドライブ/reel_maker"))
        if candidates:
            return sorted(candidates)[0]
    return BASE_DIR

DATA_ROOT       = _resolve_data_root()
DRIVE_REEL_DIR  = DATA_ROOT if "CloudStorage" in DATA_ROOT else ""
POOL_BASE       = DATA_ROOT
OUTPUT_DIR      = os.path.join(DATA_ROOT, "output")
TEMP_DIR        = os.path.join(DATA_ROOT, ".temp")  # 処理中の一時ファイル

# Font paths (macOS system fonts fallback chain)
FONT_PATHS = [
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "/Library/Fonts/Arial Bold.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]

# Text styles
TITLE_FONT_SIZE = 72
MESSAGE_FONT_SIZE = 52
ENDING_USERNAME_SIZE = 64
ENDING_CTA_SIZE = 48

# Colors
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_ACCENT = (255, 80, 120)   # Instagram pink
COLOR_SEMI_BLACK = (0, 0, 0, 160)  # RGBA for text background

# Pool names (1-indexed)
POOL_NAMES = {
    1: "外の外観",
    2: "ランチ",
    3: "デザート＆ドリンク",
    4: "室内",
    5: "その他",
}

# Transition types
TRANSITIONS = ["auto", "crossdissolve", "fade", "wipe_left", "wipe_up", "zoom_blur", "glitch"]
TRANSITION_LABELS = {
    "auto":        "🤖 自動選択（おすすめ）",
    "crossdissolve": "✨ クロスディゾルブ",
    "fade":        "⚫ フェード",
    "wipe_left":   "➡️ ワイプ（横）",
    "wipe_up":     "⬆️ ワイプ（縦）",
    "zoom_blur":   "🔍 ズームブラー",
    "glitch":      "⚡ グリッチ",
}
