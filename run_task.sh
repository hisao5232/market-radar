#!/bin/bash
cd ~/market-radar
# ニュース取得とAI分析を実行
docker compose exec -T backend python main.py
# 古いデータの削除（もしmain.pyに組み込まない場合、専用スクリプトを叩く）
docker compose exec -T backend python -c "import db; db.delete_old_articles()"
