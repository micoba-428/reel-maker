#!/bin/bash
# Reel Maker 起動スクリプト（Drive版・どのMacからでも起動可能）
cd "$(dirname "$0")"
echo "🎬 Reel Maker を起動中..."
echo "📁 データ保存先: $(cd .. && pwd)"
python3 -m streamlit run main.py --server.port 8504 --server.address 0.0.0.0 --server.headless false
