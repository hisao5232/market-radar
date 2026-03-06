import feedparser
import os
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai
from groq import Groq  # 追加
import db

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def analyze_with_groq(text):
    """バックアップ用のGroq (Llama 3.3) で分析"""
    if not GROQ_API_KEY:
        return "Groq APIキー未設定"
    
    client = Groq(api_key=GROQ_API_KEY)
    try:
        response = client.chat.completions.create(  # ここが response
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "あなたはプロの証券アナリストです。影響企業、株価予測、視点を簡潔にまとめてください。"},
                {"role": "user", "content": f"以下の記事を分析してください:\n\n{text[:4000]}"}
            ]
        )
        # 修正：completion -> response
        return f"[Groq分析結果]\n{response.choices[0].message.content}"
    except Exception as e:
        return f"Groqエラー: {e}"

def analyze_stock_impact(text):
    """メインのGeminiで分析。429エラー時はGroqに切り替え"""
    if not GEMINI_API_KEY:
        return "Gemini APIキー未設定"
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Geminiのリトライループ
    for attempt in range(2): # リトライ回数を少し減らして早めにGroqへ回す
        try:
            response = client.models.generate_content(
                model="models/gemini-2.0-flash",
                contents=f"証券アナリストとして分析せよ。影響企業、株価予測、視点。\n\n【本文】\n{text[:8000]}"
            )
            return response.text
        except Exception as e:
            if "429" in str(e):
                print(f"Gemini制限中... (試行 {attempt+1})")
                time.sleep(10)
            else:
                print(f"Gemini予期せぬエラー: {e}")
                break
    
    # GeminiがダメならGroqを召喚
    print("--- Geminiが制限中のため、Groq(Llama)でバックアップ分析を開始します ---")
    return analyze_with_groq(text)

def main():
    db.init_db()
    
    base_dir = os.path.dirname(__file__)
    kw_path = os.path.join(base_dir, "keywords.txt")
    with open(kw_path, 'r', encoding='utf-8') as f:
        target_keywords = [line.strip() for line in f if line.strip()]

    feed = feedparser.parse("https://prtimes.jp/index.rdf")
    print(f"--- 監視開始 : {len(feed.entries)}件 ---")

    for entry in feed.entries:
        title = entry.get('title', '')
        summary = entry.get('summary', '') or entry.get('description', '')
        link = entry.get('link', '')

        if any(kw in (title + summary).lower() for kw in target_keywords):
            if db.is_processed(link):
                continue
            
            print(f"\n★発見 : {title}")
            try:
                res = requests.get(link, timeout=10)
                soup = BeautifulSoup(res.text, 'html.parser')
                body = soup.select_one('.press-release-body-v3-0-0')
                text_content = body.get_text() if body else soup.get_text()

                analysis = analyze_stock_impact(text_content)
                
                # 保存
                db.save_article(link, title, analysis)
                print(f"保存完了")
                
                # 次の記事へ行く前に少し休む
                time.sleep(5)
                
            except Exception as e:
                print(f"エラー発生: {e}")

if __name__ == "__main__":
    main()
