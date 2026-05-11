#!/bin/bash
# Reel Maker 起動スクリプト（Drive版・どのMacからでも起動可能）
cd "$(dirname "$0")"
echo "🎬 Reel Maker を起動中..."
echo "📁 データ保存先: $(cd .. && pwd)"
PYTHON_BIN="/usr/bin/python3"
VENV_DIR="$PWD/.venv"

if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "🧰 初回セットアップ中..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

if ! "$VENV_DIR/bin/python" -c "import streamlit" >/dev/null 2>&1; then
  echo "📦 必要な部品を準備中..."
  "$VENV_DIR/bin/python" -m pip install --upgrade pip
  "$VENV_DIR/bin/python" -m pip install -r requirements.txt
fi

"$VENV_DIR/bin/python" -m streamlit run main.py --server.port 8506 --server.address 127.0.0.1 --server.headless false
