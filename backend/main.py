import feedparser
import os
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from groq import Groq
import db  # db.py に delete_old_articles() が実装されている前提

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def analyze_with_groq(title, text):
    """Groq (Llama 3.3) で分析。影響企業を確実にリストアップするプロンプト"""
    if not GROQ_API_KEY:
        return "Groq APIキー未設定"
    
    client = Groq(api_key=GROQ_API_KEY)
    
    # 1983年生まれのエンジニアらしい、構造化を重視したプロンプト
    prompt = f"""
あなたはプロの証券アナリストです。以下のニュースを分析し、投資判断に役立つ情報を出力してください。

【出力形式】
### 🤖 AI分析スコア & 理由
(0-100点でのスコアと、その根拠を200文字程度で)

### 🏢 影響を受ける企業リスト
- **[企業名]** (証券コードがあれば併記): 理由を一行で
- **[企業名]**: 理由を一行で

### 📈 株価予測・視点
(短期的・長期的な展望を簡潔に)

【対象記事】
タイトル: {title}
本文: {text[:6000]}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "マークダウン形式で、特に影響を受ける企業名を具体的に特定して回答してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2, # 精度重視のため低めに設定
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Groq分析エラー: {e}"

def main():
    # 1. データベースの初期化と「1週間前の掃除」
    db.init_db()
    print("--- データベース清掃開始 ---")
    try:
        db.delete_old_articles() # db.pyに追加した削除ロジックを呼び出し
        print("1週間以上前の古いデータを削除しました。")
    except Exception as e:
        print(f"清掃エラー: {e}")
    
    # 2. キーワード読み込み
    base_dir = os.path.dirname(__file__)
    kw_path = os.path.join(base_dir, "keywords.txt")
    if not os.path.exists(kw_path):
        print("keywords.txt が見つかりません。")
        return
        
    with open(kw_path, 'r', encoding='utf-8') as f:
        target_keywords = [line.strip() for line in f if line.strip()]

    # 3. RSSフィード巡回
    feed = feedparser.parse("https://prtimes.jp/index.rdf")
    print(f"--- 監視開始 : {len(feed.entries)}件 ---")

    for entry in feed.entries:
        title = entry.get('title', '')
        summary = entry.get('summary', '') or entry.get('description', '')
        link = entry.get('link', '')

        # キーワード判定
        if any(kw in (title + summary).lower() for kw in target_keywords):
            if db.is_processed(link):
                continue
            
            print(f"\n★重要ニュース発見 : {title}")
            try:
                res = requests.get(link, timeout=10)
                soup = BeautifulSoup(res.text, 'html.parser')
                body = soup.select_one('.press-release-body-v3-0-0')
                text_content = body.get_text() if body else soup.get_text()

                # Groqで分析実行
                analysis = analyze_with_groq(title, text_content)
                
                # DB保存
                db.save_article(link, title, analysis)
                print(f"分析完了・保存しました")
                
                # 連続アクセスによる負荷軽減（始業点検のような余裕を）
                time.sleep(2)
                
            except Exception as e:
                print(f"処理エラー: {e}")

if __name__ == "__main__":
    main()
    