import os
import json
import time
import feedparser
import requests
from bs4 import BeautifulSoup
from groq import Groq
import db

def analyze_with_groq(title, text):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    # 構造化データを取り出すためのプロンプト
    prompt = f"""
あなたはプロの証券アナリストです。以下のニュースを読み、投資家に必要な情報だけを抽出してください。
要約(analysis)は、箇条書きなどを使って読みやすく日本語で作成してください。

【出力ルール】
1. analysis: 
   - 「AI分析スコア」を0-100で提示。
   - スコアの理由と今後の展望を200文字程度の自然な日本語で。
   - 言葉の繰り返しや不自然な日本語を避けること。
2. companies: 影響を受ける企業（最大3社）
   - name: 企業名
   - ticker: 上場企業なら証券コード（例: 7203.T, AAPL）。未上場なら必ず "None" と記述。
   - reason: 提携内容や影響の理由を1行で。

【ニュース詳細】
タイトル: {title}
本文: {text[:4000]}

【JSONフォーマット】
{{
  "analysis": "### 🤖 AI分析スコア: 75\\n\\n理由: 〇〇の提携により...",
  "companies": [
    {{"name": "企業名", "ticker": "7203.T", "reason": "〇〇による収益拡大"}}
  ]
}}
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "出力は必ず純粋なJSON形式のみで行ってください。"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}, # JSONモードを有効化
            temperature=0.1,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Groq分析エラー: {e}")
        return None

def main():
    db.init_db() # 起動時にDBをリセット
    
    # キーワード読み込み
    with open(os.path.join(os.path.dirname(__file__), "keywords.txt"), 'r') as f:
        target_keywords = [line.strip() for line in f if line.strip()]

    feed = feedparser.parse("https://prtimes.jp/index.rdf")
    for entry in feed.entries:
        title = entry.get('title', '')
        link = entry.get('link', '')
        
        if any(kw in title.lower() for kw in target_keywords):
            if db.is_processed(link): continue
            
            print(f"★重要ニュース発見: {title}")
            try:
                res = requests.get(link, timeout=10)
                soup = BeautifulSoup(res.text, 'html.parser')
                body = soup.select_one('.press-release-body-v3-0-0') or soup.body
                
                # ニュース分析
                result = analyze_with_groq(title, body.get_text())
                
                if result:
                    # DB保存（分析文と企業リストを分けて渡す）
                    db.save_article(
                        link, 
                        title, 
                        result.get("analysis", ""), 
                        result.get("companies", [])
                    )
                    print("分析完了・銘柄特定しました")
                
                time.sleep(2)
            except Exception as e:
                print(f"処理エラー: {e}")

if __name__ == "__main__":
    main()
